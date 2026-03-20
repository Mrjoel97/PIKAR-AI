"""Email digest formatter and sender for daily briefings.

Formats triage items into a branded HTML email and sends via Gmail
using the user's stored OAuth refresh token (background mode).
"""

import logging
import os
from datetime import date, datetime, timezone
from typing import Any

from supabase import Client

logger = logging.getLogger(__name__)

_MAX_DIGEST_ITEMS = 10

# Priority display config: (label, bg colour, text colour)
_PRIORITY_STYLES: dict[str, tuple[str, str, str]] = {
    "urgent": ("URGENT", "#dc2626", "#ffffff"),
    "important": ("IMPORTANT", "#f59e0b", "#1e293b"),
    "normal": ("NORMAL", "#6366f1", "#ffffff"),
    "low": ("LOW", "#94a3b8", "#1e293b"),
}

_ACTION_LABELS: dict[str, str] = {
    "needs_reply": "Reply needed",
    "needs_review": "Review",
    "fyi": "FYI",
    "auto_handle": "Auto-handled",
    "spam": "Spam",
}


async def format_digest_html(
    triage_items: list[dict],
    user_name: str = "there",
    digest_date: date | None = None,
) -> str:
    """Format email triage items into an HTML email digest.

    Args:
        triage_items: List of email_triage rows for the day.
        user_name: User's display name for greeting.
        digest_date: Date for the digest header (defaults to today UTC).

    Returns:
        HTML string for the email body.
    """
    if digest_date is None:
        digest_date = datetime.now(timezone.utc).date()

    # Compute summary stats
    counts_by_priority: dict[str, int] = {"urgent": 0, "important": 0, "normal": 0, "low": 0}
    for item in triage_items:
        priority = item.get("priority", "normal")
        if priority in counts_by_priority:
            counts_by_priority[priority] += 1

    total = len(triage_items)
    date_display = digest_date.strftime("%A, %B %d, %Y")
    app_url = os.getenv("NEXT_PUBLIC_APP_URL", "http://localhost:3000")

    # Sort items: urgent first, then important, normal, low
    priority_order = {"urgent": 0, "important": 1, "normal": 2, "low": 3}
    sorted_items = sorted(
        triage_items,
        key=lambda i: priority_order.get(i.get("priority", "normal"), 9),
    )
    display_items = sorted_items[:_MAX_DIGEST_ITEMS]

    # Build summary stats row
    stats_cells = ""
    for priority, count in counts_by_priority.items():
        if count == 0:
            continue
        label, bg, fg = _PRIORITY_STYLES.get(priority, ("", "#94a3b8", "#1e293b"))
        stats_cells += (
            f'<td style="padding:4px 12px;border-radius:8px;background:{bg};'
            f'color:{fg};font-size:13px;font-weight:600;text-align:center;">'
            f"{count} {label}</td>"
            '<td width="8"></td>'
        )

    # Build item rows
    item_rows = ""
    for item in display_items:
        priority = item.get("priority", "normal")
        _label, bg, fg = _PRIORITY_STYLES.get(priority, ("NORMAL", "#6366f1", "#ffffff"))
        badge_html = (
            f'<span style="display:inline-block;padding:2px 8px;border-radius:6px;'
            f'background:{bg};color:{fg};font-size:10px;font-weight:700;'
            f'letter-spacing:0.03em;text-transform:uppercase;">{_label}</span>'
        )
        sender = item.get("sender_name") or item.get("sender", "Unknown")
        subject = item.get("subject", "(no subject)")
        action_type = item.get("action_type", "fyi")
        action_label = _ACTION_LABELS.get(action_type, action_type)
        draft_preview = ""
        if item.get("draft_reply"):
            draft_text = item["draft_reply"][:120]
            if len(item["draft_reply"]) > 120:
                draft_text += "..."
            draft_preview = (
                f'<p style="margin:4px 0 0;font-size:12px;color:#94a3b8;'
                f'font-style:italic;">Draft: {draft_text}</p>'
            )

        item_rows += f"""\
<tr><td style="padding:14px 0;border-bottom:1px solid #f1f5f9;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
    <td>
      {badge_html}
      <span style="margin-left:8px;font-size:12px;color:#64748b;">{action_label}</span>
    </td>
  </tr></table>
  <p style="margin:6px 0 2px;font-size:14px;font-weight:600;color:#1e293b;">{subject}</p>
  <p style="margin:0;font-size:13px;color:#64748b;">From: {sender}</p>
  {draft_preview}
</td></tr>"""

    remaining = total - len(display_items)
    more_row = ""
    if remaining > 0:
        more_row = (
            f'<tr><td style="padding:14px 0;text-align:center;font-size:13px;color:#64748b;">'
            f"+ {remaining} more item{'s' if remaining != 1 else ''} in your dashboard</td></tr>"
        )

    html = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Daily Briefing Digest</title>
</head>
<body style="margin:0;padding:0;background-color:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f8fafc;padding:40px 16px;">
<tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background-color:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(15,23,42,0.08);">

<!-- Header -->
<tr><td style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:28px 32px;">
  <table role="presentation" cellpadding="0" cellspacing="0"><tr>
    <td style="padding-right:12px;">
      <div style="width:36px;height:36px;border-radius:10px;background:rgba(255,255,255,0.2);text-align:center;line-height:36px;font-size:18px;color:#fff;">&#9993;</div>
    </td>
    <td>
      <div style="font-size:13px;font-weight:600;letter-spacing:0.05em;color:rgba(255,255,255,0.85);text-transform:uppercase;">Daily Briefing</div>
      <div style="font-size:11px;color:rgba(255,255,255,0.65);margin-top:2px;">Pikar AI</div>
    </td>
  </tr></table>
</td></tr>

<!-- Greeting & Date -->
<tr><td style="padding:24px 32px 0;">
  <h2 style="margin:0;font-size:20px;font-weight:700;color:#1e293b;">Good morning, {user_name}</h2>
  <p style="margin:4px 0 16px;font-size:13px;color:#64748b;">{date_display}</p>
</td></tr>

<!-- Summary Stats -->
<tr><td style="padding:0 32px 16px;">
  <table role="presentation" cellpadding="0" cellspacing="0"><tr>
    <td style="padding:4px 12px;border-radius:8px;background:#1e293b;color:#ffffff;font-size:13px;font-weight:600;text-align:center;">{total} email{"s" if total != 1 else ""}</td>
    <td width="8"></td>
    {stats_cells}
  </tr></table>
</td></tr>

<!-- Divider -->
<tr><td style="padding:0 32px;"><hr style="border:none;border-top:1px solid #e2e8f0;margin:0;"></td></tr>

<!-- Items -->
<tr><td style="padding:8px 32px 0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
  {item_rows}
  {more_row}
  </table>
</td></tr>

<!-- CTA Button -->
<tr><td style="padding:24px 32px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
    <td align="center">
      <a href="{app_url}/dashboard" target="_blank" style="display:inline-block;padding:14px 32px;border-radius:12px;background:#6366f1;color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;text-align:center;box-shadow:0 4px 14px rgba(99,102,241,0.3);">
        Open Pikar AI
      </a>
    </td>
  </tr></table>
</td></tr>

<!-- Footer -->
<tr><td style="padding:16px 32px;border-top:1px solid #f1f5f9;text-align:center;">
  <p style="margin:0;font-size:11px;color:#94a3b8;">You receive this digest because email digest is enabled in your briefing preferences. <a href="{app_url}/settings/briefing" style="color:#6366f1;text-decoration:none;">Manage preferences</a></p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""

    return html


def _format_plain_text(triage_items: list[dict], user_name: str, digest_date: date) -> str:
    """Build a plain-text fallback of the digest.

    Args:
        triage_items: Triage rows.
        user_name: User greeting name.
        digest_date: Date for the header.

    Returns:
        Plain text string.
    """
    priority_order = {"urgent": 0, "important": 1, "normal": 2, "low": 3}
    sorted_items = sorted(
        triage_items,
        key=lambda i: priority_order.get(i.get("priority", "normal"), 9),
    )
    display_items = sorted_items[:_MAX_DIGEST_ITEMS]

    lines = [
        f"Good morning, {user_name}",
        f"Daily Briefing — {digest_date.strftime('%A, %B %d, %Y')}",
        f"{len(triage_items)} emails triaged",
        "",
    ]

    for item in display_items:
        priority = (item.get("priority") or "normal").upper()
        sender = item.get("sender_name") or item.get("sender", "Unknown")
        subject = item.get("subject", "(no subject)")
        action_label = _ACTION_LABELS.get(item.get("action_type", "fyi"), "FYI")
        lines.append(f"[{priority}] {subject}")
        lines.append(f"  From: {sender} | Action: {action_label}")
        if item.get("draft_reply"):
            draft_preview = item["draft_reply"][:120]
            lines.append(f"  Draft: {draft_preview}")
        lines.append("")

    remaining = len(triage_items) - len(display_items)
    if remaining > 0:
        lines.append(f"+ {remaining} more items in your dashboard")
        lines.append("")

    app_url = os.getenv("NEXT_PUBLIC_APP_URL", "http://localhost:3000")
    lines.extend([
        f"Open Pikar AI: {app_url}/dashboard",
        "",
        "---",
        "This digest was generated by Pikar AI.",
        f"Manage preferences: {app_url}/settings/briefing",
    ])

    return "\n".join(lines)


async def send_digest_email(user_id: str) -> dict[str, Any]:
    """Send the daily briefing digest email to a user.

    1. Fetch user briefing preferences.
    2. Query today's email_triage items for the user.
    3. If no items, skip (don't send empty digests).
    4. Format HTML + plain-text digest.
    5. Send via Gmail API using stored refresh token.
    6. Record last_digest_sent timestamp.

    Args:
        user_id: Supabase user ID.

    Returns:
        Dict with ``sent`` (bool), ``items`` count, and optional error info.
    """
    from app.services.supabase import get_service_client

    db: Client = get_service_client()

    # --- 1. Fetch preferences ---
    prefs_resp = (
        db.table("user_briefing_preferences")
        .select("*")
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    prefs = prefs_resp.data
    if not prefs:
        logger.debug("No briefing preferences for user %s — skipping digest", user_id)
        return {"sent": False, "reason": "no_preferences"}

    if not prefs.get("email_digest_enabled", False):
        return {"sent": False, "reason": "digest_disabled"}

    frequency = prefs.get("email_digest_frequency", "daily")
    if frequency == "off":
        return {"sent": False, "reason": "frequency_off"}

    # Weekday-only check (Mon=0 .. Sun=6)
    today = datetime.now(timezone.utc).date()
    if frequency == "weekdays" and today.weekday() >= 5:
        return {"sent": False, "reason": "weekend_skip"}

    # --- 2. Fetch today's triage items ---
    today_str = today.isoformat()
    items_resp = (
        db.table("email_triage")
        .select(
            "id, sender, sender_name, subject, priority, action_type, "
            "category, confidence, draft_reply, status, created_at"
        )
        .eq("user_id", user_id)
        .gte("created_at", f"{today_str}T00:00:00+00:00")
        .order("created_at", desc=True)
        .execute()
    )
    items = items_resp.data or []

    # --- 3. Skip if no items ---
    if not items:
        logger.debug("No triage items for user %s on %s — skipping digest", user_id, today_str)
        return {"sent": False, "items": 0, "reason": "no_items"}

    # --- 4. Resolve user display name and email ---
    user_name = "there"
    user_email: str | None = None
    try:
        # Use Supabase admin API to get user metadata
        user_resp = db.auth.admin.get_user_by_id(user_id)
        if user_resp and hasattr(user_resp, "user") and user_resp.user:
            user_obj = user_resp.user
            user_email = getattr(user_obj, "email", None)
            metadata = getattr(user_obj, "user_metadata", {}) or {}
            user_name = (
                metadata.get("full_name")
                or metadata.get("name")
                or (user_email.split("@")[0] if user_email else "there")
            )
    except Exception as exc:
        logger.warning("Could not fetch user metadata for %s: %s", user_id, exc)

    if not user_email:
        logger.warning("No email address for user %s — cannot send digest", user_id)
        return {"sent": False, "reason": "no_email"}

    # --- 5. Format digest ---
    html_body = await format_digest_html(items, user_name=user_name, digest_date=today)
    plain_body = _format_plain_text(items, user_name=user_name, digest_date=today)

    # --- 6. Send via Gmail ---
    refresh_token = _get_refresh_token(db, user_id)
    if not refresh_token:
        logger.info("No Gmail refresh token for user %s — cannot send digest", user_id)
        return {"sent": False, "reason": "no_refresh_token"}

    try:
        from app.integrations.google.client import get_user_gmail_credentials
        from app.integrations.google.gmail import GmailService

        credentials = get_user_gmail_credentials(refresh_token)
        gmail = GmailService(credentials)
        urgent_count = sum(1 for i in items if i.get("priority") == "urgent")
        subject_prefix = f"[{urgent_count} urgent] " if urgent_count else ""
        send_result = gmail.send_email(
            to=[user_email],
            subject=f"{subject_prefix}Your Daily Briefing — {today.strftime('%b %d')}",
            body=plain_body,
            body_html=html_body,
        )
        logger.info(
            "Digest sent to %s (%d items, message_id=%s)",
            user_email,
            len(items),
            send_result.get("message_id"),
        )
    except Exception as exc:
        logger.error("Failed to send digest email for user %s: %s", user_id, exc)
        return {"sent": False, "items": len(items), "error": str(exc)}

    # --- 7. Record send timestamp in preferences ---
    try:
        db.table("user_briefing_preferences").update(
            {"updated_at": datetime.now(timezone.utc).isoformat()}
        ).eq("user_id", user_id).execute()
    except Exception as exc:
        logger.warning("Failed to update digest timestamp for %s: %s", user_id, exc)

    return {"sent": True, "items": len(items), "email": user_email}


def _get_refresh_token(db: Client, user_id: str) -> str | None:
    """Resolve the Google OAuth refresh token for background Gmail access.

    Uses the same RPC + fallback strategy as ``EmailTriageWorker``.

    Args:
        db: Supabase service-role client.
        user_id: Supabase user ID.

    Returns:
        Refresh token string or ``None``.
    """
    try:
        rpc_resp = db.rpc(
            "get_user_provider_refresh_token",
            {"p_user_id": user_id},
        ).execute()
        token = rpc_resp.data
        if isinstance(token, str) and token:
            return token
        if isinstance(token, list) and token:
            first = token[0]
            if isinstance(first, str):
                return first
            if isinstance(first, dict):
                return first.get("provider_refresh_token")
    except Exception as exc:
        logger.debug("RPC get_user_provider_refresh_token failed for %s: %s", user_id, exc)

    # Fallback: user_oauth_tokens table
    try:
        resp = (
            db.table("user_oauth_tokens")
            .select("refresh_token")
            .eq("user_id", user_id)
            .eq("provider", "google")
            .limit(1)
            .execute()
        )
        if resp.data:
            return resp.data[0].get("refresh_token")
    except Exception as exc:
        logger.debug("Fallback token lookup failed for %s: %s", user_id, exc)

    return None
