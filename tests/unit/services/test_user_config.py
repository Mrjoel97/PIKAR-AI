"""Unit tests for user_config helpers — Supabase client mocked."""
from unittest.mock import MagicMock, patch


def _mock_table(rows: list[dict]) -> MagicMock:
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table
    table.execute.return_value = MagicMock(data=rows)
    table.upsert.return_value = table
    return table


def test_get_user_api_key_returns_value_when_row_exists():
    from app.services import user_config

    table = _mock_table([{"config_value": "tvly-secret"}])
    client = MagicMock()
    client.table.return_value = table

    with patch.object(user_config, "get_service_client", return_value=client):
        assert user_config.get_user_api_key("u1", "STITCH_API_KEY") == "tvly-secret"

    client.table.assert_called_with("user_configurations")
    table.eq.assert_any_call("user_id", "u1")
    table.eq.assert_any_call("config_key", "STITCH_API_KEY")


def test_get_user_api_key_returns_none_when_no_row():
    from app.services import user_config

    table = _mock_table([])
    client = MagicMock()
    client.table.return_value = table

    with patch.object(user_config, "get_service_client", return_value=client):
        assert user_config.get_user_api_key("u1", "STITCH_API_KEY") is None


def test_get_user_api_key_returns_none_for_blank_value():
    from app.services import user_config

    table = _mock_table([{"config_value": "   "}])
    client = MagicMock()
    client.table.return_value = table

    with patch.object(user_config, "get_service_client", return_value=client):
        assert user_config.get_user_api_key("u1", "STITCH_API_KEY") is None


def test_set_user_api_key_upserts_with_is_sensitive_true():
    from app.services import user_config

    table = _mock_table([])
    client = MagicMock()
    client.table.return_value = table

    with patch.object(user_config, "get_service_client", return_value=client):
        user_config.set_user_api_key("u1", "STITCH_API_KEY", "tvly-secret")

    table.upsert.assert_called_once()
    payload = table.upsert.call_args.args[0]
    assert payload["user_id"] == "u1"
    assert payload["config_key"] == "STITCH_API_KEY"
    assert payload["config_value"] == "tvly-secret"
    assert payload["is_sensitive"] is True
    assert table.upsert.call_args.kwargs.get("on_conflict") == "user_id,config_key"
