# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""StripeSyncService — Import Stripe transactions into financial_records.

Provides:
- Historical balance-transaction sync via ``sync_history()``
- Real-time webhook handlers for payment, refund, and payout events
- Idempotent upserts using ``external_id`` (ON CONFLICT DO NOTHING)

All webhook-triggered writes use ``AdminService`` (service role) because
inbound webhooks carry no user JWT.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar

from app.services.base_service import AdminService, BaseService
from app.services.integration_manager import IntegrationManager
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# Lazy import — stripe may not be installed in all environments
try:
    import stripe  # type: ignore[import]
except ImportError:  # pragma: no cover
    stripe = None  # type: ignore[assignment]


class StripeSyncService(BaseService):
    """Sync Stripe financial data into the ``financial_records`` table.

    Uses ``AdminService`` for webhook-triggered inserts (no user JWT)
    and ``BaseService`` for user-initiated sync (has JWT via constructor).
    """

    #: Map Stripe BalanceTransaction.type to financial_records.transaction_type.
    TYPE_MAP: ClassVar[dict[str, str]] = {
        "charge": "revenue",
        "payment": "revenue",
        "refund": "refund",
        "stripe_fee": "fee",
        "payout": "payout",
        "adjustment": "adjustment",
    }

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _map_transaction(self, bt: dict[str, Any], user_id: str) -> dict[str, Any]:
        """Convert a Stripe BalanceTransaction dict to a financial_records row.

        Args:
            bt: Raw Stripe BalanceTransaction object (dict-like).
            user_id: The owning user's UUID.

        Returns:
            A dict ready for upsert into ``financial_records``.
        """
        stripe_type = bt.get("type", "unknown")
        transaction_type = self.TYPE_MAP.get(stripe_type, "adjustment")

        # Stripe amounts are in smallest currency unit (cents)
        raw_amount = bt.get("amount", 0)
        amount = abs(raw_amount) / 100

        # Convert Unix timestamp to ISO-8601
        created_ts = bt.get("created", 0)
        transaction_date = datetime.fromtimestamp(
            created_ts, tz=timezone.utc
        ).isoformat()

        return {
            "user_id": user_id,
            "transaction_type": transaction_type,
            "amount": amount,
            "currency": bt.get("currency", "usd").upper(),
            "description": bt.get("description") or f"Stripe {stripe_type}",
            "source_type": "stripe",
            "source_id": bt.get("source"),
            "external_id": bt["id"],
            "transaction_date": transaction_date,
            "metadata": {
                "stripe_type": stripe_type,
                "fee": bt.get("fee", 0),
                "net": bt.get("net", 0),
            },
        }

    # ------------------------------------------------------------------
    # Historical sync
    # ------------------------------------------------------------------

    async def sync_history(
        self,
        user_id: str,
        months_back: int = 12,
    ) -> dict[str, Any]:
        """Import historical Stripe balance transactions.

        Fetches transactions from the last ``months_back`` months using
        ``stripe.BalanceTransaction.list()`` (run in a thread to avoid
        blocking the event loop) and batch-upserts them into
        ``financial_records``.

        Args:
            user_id: The owning user's UUID.
            months_back: How many months of history to import.

        Returns:
            ``{"imported": N, "skipped": N}`` counts.
        """
        if stripe is None:
            raise RuntimeError("Stripe SDK is not installed")

        # Ensure API key is set
        if not stripe.api_key:
            stripe.api_key = os.environ.get("STRIPE_API_KEY", "")

        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=months_back * 30)
        cutoff_ts = int(cutoff.timestamp())

        try:
            # Stripe SDK is synchronous — run in thread pool
            def _fetch() -> list[dict[str, Any]]:
                result = stripe.BalanceTransaction.list(
                    created={"gte": cutoff_ts},
                    limit=100,
                )
                return list(result.auto_paging_iter())

            transactions = await asyncio.to_thread(_fetch)
        except Exception as exc:
            logger.exception("Stripe sync_history API error for user=%s", user_id)
            # Update sync state with error
            try:
                mgr = IntegrationManager()
                await mgr.update_sync_state(
                    user_id=user_id,
                    provider="stripe",
                    error_count=1,
                    last_error=str(exc)[:500],
                )
            except Exception:
                logger.warning("Failed to update sync state after error")
            raise

        # Map transactions
        rows = [self._map_transaction(bt, user_id) for bt in transactions]

        if not rows:
            return {"imported": 0, "skipped": 0}

        # Batch upsert using AdminService (service role for reliable writes)
        admin = AdminService()
        result = await execute_async(
            admin.client.table("financial_records").upsert(
                rows,
                on_conflict="external_id",
                ignore_duplicates=True,
            ),
            op_name="stripe_sync.batch_upsert",
        )

        imported = len(result.data) if result.data else 0
        skipped = len(rows) - imported

        # Update sync state
        try:
            mgr = IntegrationManager()
            await mgr.update_sync_state(
                user_id=user_id,
                provider="stripe",
                last_sync_at=datetime.now(tz=timezone.utc).isoformat(),
                error_count=0,
                last_error=None,
                sync_cursor={"last_cutoff_ts": cutoff_ts},
            )
        except Exception:
            logger.warning("Failed to update sync state after successful sync")

        logger.info(
            "Stripe sync complete: user=%s imported=%d skipped=%d",
            user_id,
            imported,
            skipped,
        )
        return {"imported": imported, "skipped": skipped}

    # ------------------------------------------------------------------
    # Webhook handlers
    # ------------------------------------------------------------------

    async def handle_payment_intent_succeeded(
        self,
        event_data: dict[str, Any],
        user_id: str,
    ) -> None:
        """Process a ``payment_intent.succeeded`` webhook event.

        Creates a ``revenue`` record in ``financial_records``.

        Args:
            event_data: The PaymentIntent object from the webhook.
            user_id: The owning user's UUID.
        """
        pi = event_data
        row = {
            "user_id": user_id,
            "transaction_type": "revenue",
            "amount": abs(pi.get("amount_received", 0)) / 100,
            "currency": pi.get("currency", "usd").upper(),
            "description": pi.get("description") or "Stripe payment",
            "source_type": "stripe",
            "source_id": pi.get("id"),
            "external_id": f"pi_{pi['id']}",
            "transaction_date": datetime.now(tz=timezone.utc).isoformat(),
            "metadata": {"stripe_event": "payment_intent.succeeded"},
        }

        admin = AdminService()
        await execute_async(
            admin.client.table("financial_records").upsert(
                row,
                on_conflict="external_id",
                ignore_duplicates=True,
            ),
            op_name="stripe_sync.webhook_payment",
        )

    async def handle_charge_refunded(
        self,
        event_data: dict[str, Any],
        user_id: str,
    ) -> None:
        """Process a ``charge.refunded`` webhook event.

        Creates a ``refund`` record in ``financial_records``.

        Args:
            event_data: The Charge object from the webhook.
            user_id: The owning user's UUID.
        """
        charge = event_data
        row = {
            "user_id": user_id,
            "transaction_type": "refund",
            "amount": abs(charge.get("amount_refunded", 0)) / 100,
            "currency": charge.get("currency", "usd").upper(),
            "description": charge.get("description") or "Stripe refund",
            "source_type": "stripe",
            "source_id": charge.get("id"),
            "external_id": f"re_{charge['id']}",
            "transaction_date": datetime.now(tz=timezone.utc).isoformat(),
            "metadata": {"stripe_event": "charge.refunded"},
        }

        admin = AdminService()
        await execute_async(
            admin.client.table("financial_records").upsert(
                row,
                on_conflict="external_id",
                ignore_duplicates=True,
            ),
            op_name="stripe_sync.webhook_refund",
        )

    async def handle_payout_paid(
        self,
        event_data: dict[str, Any],
        user_id: str,
    ) -> None:
        """Process a ``payout.paid`` webhook event.

        Creates a ``payout`` record in ``financial_records``.

        Args:
            event_data: The Payout object from the webhook.
            user_id: The owning user's UUID.
        """
        payout = event_data
        row = {
            "user_id": user_id,
            "transaction_type": "payout",
            "amount": abs(payout.get("amount", 0)) / 100,
            "currency": payout.get("currency", "usd").upper(),
            "description": payout.get("description") or "Stripe payout",
            "source_type": "stripe",
            "source_id": payout.get("id"),
            "external_id": f"po_{payout['id']}",
            "transaction_date": datetime.now(tz=timezone.utc).isoformat(),
            "metadata": {"stripe_event": "payout.paid"},
        }

        admin = AdminService()
        await execute_async(
            admin.client.table("financial_records").upsert(
                row,
                on_conflict="external_id",
                ignore_duplicates=True,
            ),
            op_name="stripe_sync.webhook_payout",
        )
