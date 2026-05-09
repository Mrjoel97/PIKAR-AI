"""One-time backfill: encrypt legacy plaintext access_token / refresh_token rows.

Walks every row in ``public.connected_accounts``, attempts ``decrypt_secret`` on
each token column, and on ``InvalidToken`` (plaintext detected) re-encrypts the
value with the current Fernet primary key and updates the row in place.
Idempotent — rows that already decrypt cleanly are skipped on every pass.

This is safety-in-depth: ``app/social/connector.py`` already encrypts on every
write (since commit 861a2bc9) and ``_decrypt_token`` tolerates legacy plaintext
during reads. This script closes the gap for any rows persisted before the
encryption code path landed.

Usage::

    # Inspect what would change (no writes):
    uv run python scripts/migrate_connected_accounts_encryption.py --dry-run

    # Apply changes (requires SUPABASE_SERVICE_ROLE_KEY + ADMIN_ENCRYPTION_KEY):
    uv run python scripts/migrate_connected_accounts_encryption.py --apply

    # Verbose logging:
    uv run python scripts/migrate_connected_accounts_encryption.py --apply -v
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Any

from cryptography.fernet import InvalidToken

from app.services.encryption import decrypt_secret, encrypt_secret
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)


def is_already_fernet(value: str | None) -> bool:
    """Return True iff the value is None / empty / decrypts cleanly via Fernet.

    Treats ``None`` and empty strings as "nothing to do" (returns ``True``) so
    the caller skips columns that legitimately have no token (``refresh_token``
    is optional for several providers).

    Raises:
        RuntimeError: ``ADMIN_ENCRYPTION_KEY`` is not configured. Surfacing this
            at the helper boundary makes the backfill fail fast at process
            start instead of silently corrupting rows mid-run.
    """
    if not value:
        return True
    try:
        decrypt_secret(value)
        return True
    except InvalidToken:
        return False
    except RuntimeError:
        # Encryption not configured — surface to the caller; do not swallow.
        raise


def run(client: Any, *, dry_run: bool, verbose: bool = False) -> dict[str, int]:
    """Backfill all rows in ``connected_accounts``.

    Args:
        client: A Supabase client (sync) with a ``.table(name)`` API matching
            the supabase-py contract (``select / update / .eq / .execute``).
        dry_run: When True, count what WOULD migrate without writing.
        verbose: When True, log per-row decisions at INFO.

    Returns:
        ``{"total": N, "already_encrypted": A, "migrated": M, "failed": F}``.
        ``already_encrypted + migrated + failed == total`` is the invariant.
    """
    result = (
        client.table("connected_accounts")
        .select("id, access_token, refresh_token")
        .execute()
    )
    rows = result.data or []
    stats = {"total": len(rows), "already_encrypted": 0, "migrated": 0, "failed": 0}

    for row in rows:
        access_plain = row.get("access_token")
        refresh_plain = row.get("refresh_token")
        access_already = is_already_fernet(access_plain)
        refresh_already = is_already_fernet(refresh_plain)

        if access_already and refresh_already:
            stats["already_encrypted"] += 1
            if verbose:
                logger.info("row id=%s already encrypted; skipping", row.get("id"))
            continue

        update_payload: dict[str, str] = {}
        if not access_already and access_plain:
            update_payload["access_token"] = encrypt_secret(access_plain)
        if not refresh_already and refresh_plain:
            update_payload["refresh_token"] = encrypt_secret(refresh_plain)

        if not update_payload:
            # Defensive: both flagged dirty but both values were None/empty.
            stats["already_encrypted"] += 1
            continue

        if dry_run:
            stats["migrated"] += 1
            if verbose:
                logger.info(
                    "[dry-run] would migrate row id=%s (cols=%s)",
                    row.get("id"),
                    sorted(update_payload.keys()),
                )
            continue

        try:
            client.table("connected_accounts").update(update_payload).eq(
                "id", row["id"]
            ).execute()
            stats["migrated"] += 1
            if verbose:
                logger.info("migrated row id=%s", row.get("id"))
        except Exception as exc:
            logger.warning("Failed to migrate row id=%s: %s", row.get("id"), exc)
            stats["failed"] += 1

    return stats


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Encrypt legacy connected_accounts tokens (one-time backfill)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Report counts without writing.",
    )
    group.add_argument(
        "--apply",
        action="store_true",
        help="Apply the migration (writes to Supabase).",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    client = get_service_client()
    stats = run(client, dry_run=args.dry_run, verbose=args.verbose)
    logger.info("Backfill complete: %s", stats)
    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(_main())
