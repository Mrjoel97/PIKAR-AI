"""Unit tests for AdminAgent integration tools.

Tests verify:
- test_sentry_get_issues_returns_data: sentry_get_issues calls IntegrationProxyService.call
  with provider="sentry", operation="get_issues" and returns the proxy result
- test_sentry_get_issues_blocked: sentry_get_issues returns error dict when autonomy level
  is "blocked"
- test_sentry_get_issues_not_configured: sentry_get_issues returns error when integration row
  missing or inactive
- test_sentry_get_issue_detail_returns_data: sentry_get_issue_detail fetches specific issue
  by ID via proxy
- test_posthog_query_events_returns_data: posthog_query_events calls proxy with
  operation="get_events"
- test_posthog_get_insights_returns_data: posthog_get_insights calls proxy with
  operation="get_insights"
- test_github_list_prs_returns_data: github_list_prs calls proxy with operation="get_prs"
- test_github_get_pr_status_returns_data: github_get_pr_status calls proxy with
  operation="get_pr_status" and pr_number param
- test_budget_exhausted: any tool returns error dict when check_session_budget returns False
- test_null_api_key_guarded: tool returns error when api_key_encrypted is NULL
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Patch targets at the integration tools module level
_SERVICE_CLIENT_PATCH = "app.agents.admin.tools.integrations.get_service_client"
_PROXY_CALL_PATCH = "app.agents.admin.tools.integrations.IntegrationProxyService.call"
_BUDGET_PATCH = "app.agents.admin.tools.integrations.check_session_budget"


# ---------------------------------------------------------------------------
# Fixtures — autonomy mocks
# ---------------------------------------------------------------------------


def _build_autonomy_client(level: str) -> MagicMock:
    """Build a mock Supabase client that returns the given autonomy level."""
    client = MagicMock()
    table_mock = MagicMock()
    client.table.return_value = table_mock
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.order.return_value = table_mock
    table_mock.execute.return_value = MagicMock(data=[{"autonomy_level": level}])
    return client


@pytest.fixture
def client_auto():
    """Supabase mock returning autonomy_level='auto'."""
    return _build_autonomy_client("auto")


@pytest.fixture
def client_blocked():
    """Supabase mock returning autonomy_level='blocked'."""
    return _build_autonomy_client("blocked")


def _build_integration_client(
    is_active: bool = True,
    api_key_encrypted: str | None = "encrypted_key",
) -> MagicMock:
    """Build a mock Supabase client that returns an integration row."""
    client = MagicMock()

    def _table(name: str):
        """Return the correct mock depending on table name."""
        tbl = MagicMock()
        if name == "admin_agent_permissions":
            # autonomy check → auto
            tbl.select.return_value = tbl
            tbl.eq.return_value = tbl
            tbl.limit.return_value = tbl
            tbl.execute.return_value = MagicMock(data=[{"autonomy_level": "auto"}])
        elif name == "admin_integrations":
            if api_key_encrypted is None:
                row_data = [
                    {
                        "api_key_encrypted": None,
                        "config": {},
                        "is_active": True,
                        "base_url": None,
                    }
                ]
            elif not is_active:
                row_data = [
                    {
                        "api_key_encrypted": "enc",
                        "config": {},
                        "is_active": False,
                        "base_url": None,
                    }
                ]
            else:
                row_data = [
                    {
                        "api_key_encrypted": api_key_encrypted,
                        "config": {},
                        "is_active": True,
                        "base_url": None,
                    }
                ]
            tbl.select.return_value = tbl
            tbl.eq.return_value = tbl
            tbl.limit.return_value = tbl
            tbl.execute.return_value = MagicMock(data=row_data)
        return tbl

    client.table.side_effect = _table
    return client


def _build_no_row_integration_client() -> MagicMock:
    """Build a mock Supabase client that returns no integration row."""
    client = MagicMock()

    def _table(name: str):
        tbl = MagicMock()
        if name == "admin_agent_permissions":
            tbl.select.return_value = tbl
            tbl.eq.return_value = tbl
            tbl.limit.return_value = tbl
            tbl.execute.return_value = MagicMock(data=[{"autonomy_level": "auto"}])
        elif name == "admin_integrations":
            tbl.select.return_value = tbl
            tbl.eq.return_value = tbl
            tbl.limit.return_value = tbl
            tbl.execute.return_value = MagicMock(data=[])
        return tbl

    client.table.side_effect = _table
    return client


# ---------------------------------------------------------------------------
# Test 1: sentry_get_issues returns data (happy path)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sentry_get_issues_returns_data():
    """Auto tier + configured: sentry_get_issues calls proxy and returns data."""
    fake_issues = [{"id": "1", "title": "OOM Error"}]
    client = _build_integration_client()
    proxy_mock = AsyncMock(return_value=fake_issues)
    budget_mock = AsyncMock(return_value=True)

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=client),
        patch(_PROXY_CALL_PATCH, new=proxy_mock),
        patch(_BUDGET_PATCH, new=budget_mock),
        patch(
            "app.agents.admin.tools.integrations.decrypt_secret",
            return_value="plain_key",
        ),
    ):
        from app.agents.admin.tools.integrations import sentry_get_issues

        result = await sentry_get_issues(limit=10)

    assert result == fake_issues
    proxy_mock.assert_called_once()
    call_kwargs = proxy_mock.call_args.kwargs
    assert call_kwargs["provider"] == "sentry"
    assert call_kwargs["operation"] == "get_issues"
    assert call_kwargs["params"]["limit"] == 10


# ---------------------------------------------------------------------------
# Test 2: sentry_get_issues blocked tier
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sentry_get_issues_blocked():
    """Blocked tier: sentry_get_issues returns error dict without calling proxy."""
    proxy_mock = AsyncMock()
    budget_mock = AsyncMock(return_value=True)

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=_build_autonomy_client("blocked")),
        patch(_PROXY_CALL_PATCH, new=proxy_mock),
        patch(_BUDGET_PATCH, new=budget_mock),
    ):
        from app.agents.admin.tools.integrations import sentry_get_issues

        result = await sentry_get_issues()

    assert "error" in result
    assert "block" in result["error"].lower()
    proxy_mock.assert_not_called()


# ---------------------------------------------------------------------------
# Test 3: sentry_get_issues not configured (missing row)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sentry_get_issues_not_configured():
    """No integration row: sentry_get_issues returns error dict."""
    proxy_mock = AsyncMock()
    budget_mock = AsyncMock(return_value=True)
    client = _build_no_row_integration_client()

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=client),
        patch(_PROXY_CALL_PATCH, new=proxy_mock),
        patch(_BUDGET_PATCH, new=budget_mock),
    ):
        from app.agents.admin.tools.integrations import sentry_get_issues

        result = await sentry_get_issues()

    assert "error" in result
    proxy_mock.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4: sentry_get_issue_detail returns data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sentry_get_issue_detail_returns_data():
    """Auto tier: sentry_get_issue_detail calls proxy with get_issue_detail operation."""
    fake_detail = {"id": "abc", "title": "NPE", "metadata": {}, "tags": []}
    client = _build_integration_client()
    proxy_mock = AsyncMock(return_value=fake_detail)
    budget_mock = AsyncMock(return_value=True)

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=client),
        patch(_PROXY_CALL_PATCH, new=proxy_mock),
        patch(_BUDGET_PATCH, new=budget_mock),
        patch(
            "app.agents.admin.tools.integrations.decrypt_secret",
            return_value="plain_key",
        ),
    ):
        from app.agents.admin.tools.integrations import sentry_get_issue_detail

        result = await sentry_get_issue_detail(issue_id="abc")

    assert result == fake_detail
    call_kwargs = proxy_mock.call_args.kwargs
    assert call_kwargs["provider"] == "sentry"
    assert call_kwargs["operation"] == "get_issue_detail"
    assert call_kwargs["params"]["issue_id"] == "abc"


# ---------------------------------------------------------------------------
# Test 5: posthog_query_events returns data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_posthog_query_events_returns_data():
    """Auto tier: posthog_query_events calls proxy with get_events operation."""
    fake_events = {"results": [], "count": 0}
    client = _build_integration_client()
    proxy_mock = AsyncMock(return_value=fake_events)
    budget_mock = AsyncMock(return_value=True)

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=client),
        patch(_PROXY_CALL_PATCH, new=proxy_mock),
        patch(_BUDGET_PATCH, new=budget_mock),
        patch(
            "app.agents.admin.tools.integrations.decrypt_secret",
            return_value="plain_key",
        ),
    ):
        from app.agents.admin.tools.integrations import posthog_query_events

        result = await posthog_query_events(limit=50)

    assert result == fake_events
    call_kwargs = proxy_mock.call_args.kwargs
    assert call_kwargs["provider"] == "posthog"
    assert call_kwargs["operation"] == "get_events"
    assert call_kwargs["params"]["limit"] == 50


# ---------------------------------------------------------------------------
# Test 6: posthog_get_insights returns data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_posthog_get_insights_returns_data():
    """Auto tier: posthog_get_insights calls proxy with get_insights operation."""
    fake_insights = {"results": [{"id": 1, "name": "Funnel"}], "count": 1}
    client = _build_integration_client()
    proxy_mock = AsyncMock(return_value=fake_insights)
    budget_mock = AsyncMock(return_value=True)

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=client),
        patch(_PROXY_CALL_PATCH, new=proxy_mock),
        patch(_BUDGET_PATCH, new=budget_mock),
        patch(
            "app.agents.admin.tools.integrations.decrypt_secret",
            return_value="plain_key",
        ),
    ):
        from app.agents.admin.tools.integrations import posthog_get_insights

        result = await posthog_get_insights()

    assert result == fake_insights
    call_kwargs = proxy_mock.call_args.kwargs
    assert call_kwargs["provider"] == "posthog"
    assert call_kwargs["operation"] == "get_insights"


# ---------------------------------------------------------------------------
# Test 7: github_list_prs returns data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_github_list_prs_returns_data():
    """Auto tier: github_list_prs calls proxy with get_prs operation."""
    fake_prs = [{"number": 42, "title": "feat: add thing", "state": "open"}]
    client = _build_integration_client()
    proxy_mock = AsyncMock(return_value=fake_prs)
    budget_mock = AsyncMock(return_value=True)

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=client),
        patch(_PROXY_CALL_PATCH, new=proxy_mock),
        patch(_BUDGET_PATCH, new=budget_mock),
        patch(
            "app.agents.admin.tools.integrations.decrypt_secret",
            return_value="plain_key",
        ),
    ):
        from app.agents.admin.tools.integrations import github_list_prs

        result = await github_list_prs(state="open")

    assert result == fake_prs
    call_kwargs = proxy_mock.call_args.kwargs
    assert call_kwargs["provider"] == "github"
    assert call_kwargs["operation"] == "get_prs"
    assert call_kwargs["params"]["state"] == "open"


# ---------------------------------------------------------------------------
# Test 8: github_get_pr_status returns data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_github_get_pr_status_returns_data():
    """Auto tier: github_get_pr_status calls proxy with get_pr_status and pr_number."""
    fake_status = {
        "number": 42,
        "state": "open",
        "checks": [],
        "review_state": "PENDING",
    }
    client = _build_integration_client()
    proxy_mock = AsyncMock(return_value=fake_status)
    budget_mock = AsyncMock(return_value=True)

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=client),
        patch(_PROXY_CALL_PATCH, new=proxy_mock),
        patch(_BUDGET_PATCH, new=budget_mock),
        patch(
            "app.agents.admin.tools.integrations.decrypt_secret",
            return_value="plain_key",
        ),
    ):
        from app.agents.admin.tools.integrations import github_get_pr_status

        result = await github_get_pr_status(pr_number=42)

    assert result == fake_status
    call_kwargs = proxy_mock.call_args.kwargs
    assert call_kwargs["provider"] == "github"
    assert call_kwargs["operation"] == "get_pr_status"
    assert call_kwargs["params"]["pr_number"] == 42


# ---------------------------------------------------------------------------
# Test 9: Budget exhausted — any tool returns error dict
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_budget_exhausted():
    """Budget exhausted: sentry_get_issues returns error dict when budget returns False."""
    client = _build_integration_client()
    proxy_mock = AsyncMock()
    budget_mock = AsyncMock(return_value=False)

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=client),
        patch(_PROXY_CALL_PATCH, new=proxy_mock),
        patch(_BUDGET_PATCH, new=budget_mock),
        patch(
            "app.agents.admin.tools.integrations.decrypt_secret",
            return_value="plain_key",
        ),
    ):
        from app.agents.admin.tools.integrations import sentry_get_issues

        result = await sentry_get_issues()

    assert "error" in result
    assert "budget" in result["error"].lower()
    proxy_mock.assert_not_called()


# ---------------------------------------------------------------------------
# Test 10: NULL api_key_encrypted guarded — tool returns error without decrypt attempt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_null_api_key_guarded():
    """NULL api_key_encrypted: tool returns error without attempting decrypt."""
    client = _build_integration_client(api_key_encrypted=None)
    proxy_mock = AsyncMock()
    budget_mock = AsyncMock(return_value=True)
    decrypt_mock = MagicMock()

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=client),
        patch(_PROXY_CALL_PATCH, new=proxy_mock),
        patch(_BUDGET_PATCH, new=budget_mock),
        patch("app.agents.admin.tools.integrations.decrypt_secret", new=decrypt_mock),
    ):
        from app.agents.admin.tools.integrations import sentry_get_issues

        result = await sentry_get_issues()

    assert "error" in result
    decrypt_mock.assert_not_called()
    proxy_mock.assert_not_called()
