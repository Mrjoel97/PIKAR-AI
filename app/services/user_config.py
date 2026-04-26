"""Per-user API key storage helpers backed by `user_configurations`.

Keys are stored with `is_sensitive=true`. Reads bypass RLS via the service-role
client. Both helpers are synchronous because the Supabase Python client is sync.
"""

from app.services.supabase import get_service_client


def get_user_api_key(user_id: str, key_name: str) -> str | None:
    """Return the user's stored API key, or None if unset/blank."""
    client = get_service_client()
    result = (
        client.table("user_configurations")
        .select("config_value")
        .eq("user_id", user_id)
        .eq("config_key", key_name)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    raw = result.data[0].get("config_value")
    if not raw:
        return None
    stripped = raw.strip()
    return stripped or None


def set_user_api_key(user_id: str, key_name: str, api_key: str) -> None:
    """Upsert a user's API key with `is_sensitive=true`."""
    client = get_service_client()
    client.table("user_configurations").upsert(
        {
            "user_id": user_id,
            "config_key": key_name,
            "config_value": api_key,
            "is_sensitive": True,
        },
        on_conflict="user_id,config_key",
    ).execute()
