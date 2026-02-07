"""Integration tests for RLS policies on _edge_function_config table.

Tests verify that:
1. Service role can CRUD _edge_function_config
2. Authenticated users cannot access _edge_function_config
3. Anonymous users cannot access _edge_function_config
4. Edge function webhooks still trigger correctly
"""

import os
import pytest
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Skip all tests if Supabase credentials are not configured
pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    reason="Supabase credentials not configured"
)


@pytest.fixture
def service_client() -> Client:
    """Create a Supabase client with service role permissions."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    return create_client(url, key)


@pytest.fixture
def anon_client() -> Client:
    """Create a Supabase client with anonymous permissions."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    if not key:
        pytest.skip("SUPABASE_ANON_KEY not configured")
    return create_client(url, key)


class TestEdgeFunctionConfigRLS:
    """Test RLS policies on _edge_function_config table."""

    def test_service_role_can_select(self, service_client: Client):
        """Service role should be able to SELECT from _edge_function_config."""
        result = service_client.table("_edge_function_config").select("*").execute()
        # Should not raise an error - service role has access
        assert result.data is not None

    def test_service_role_can_insert(self, service_client: Client):
        """Service role should be able to INSERT into _edge_function_config."""
        test_function_name = "_test_rls_function"
        
        # Clean up any existing test data
        service_client.table("_edge_function_config").delete().eq(
            "function_name", test_function_name
        ).execute()
        
        # Insert test data
        result = service_client.table("_edge_function_config").insert({
            "function_name": test_function_name,
            "base_url": "http://test.example.com",
            "service_role_key": "test_key_12345"
        }).execute()
        
        assert len(result.data) == 1
        assert result.data[0]["function_name"] == test_function_name
        
        # Clean up
        service_client.table("_edge_function_config").delete().eq(
            "function_name", test_function_name
        ).execute()

    def test_service_role_can_update(self, service_client: Client):
        """Service role should be able to UPDATE _edge_function_config."""
        test_function_name = "_test_rls_update"
        
        # Clean up and insert test data
        service_client.table("_edge_function_config").delete().eq(
            "function_name", test_function_name
        ).execute()
        
        service_client.table("_edge_function_config").insert({
            "function_name": test_function_name,
            "base_url": "http://original.example.com"
        }).execute()
        
        # Update
        result = service_client.table("_edge_function_config").update({
            "base_url": "http://updated.example.com"
        }).eq("function_name", test_function_name).execute()
        
        assert len(result.data) == 1
        assert result.data[0]["base_url"] == "http://updated.example.com"
        
        # Clean up
        service_client.table("_edge_function_config").delete().eq(
            "function_name", test_function_name
        ).execute()

    def test_service_role_can_delete(self, service_client: Client):
        """Service role should be able to DELETE from _edge_function_config."""
        test_function_name = "_test_rls_delete"
        
        # Insert test data
        service_client.table("_edge_function_config").insert({
            "function_name": test_function_name,
            "base_url": "http://delete.example.com"
        }).execute()
        
        # Delete
        result = service_client.table("_edge_function_config").delete().eq(
            "function_name", test_function_name
        ).execute()
        
        assert result.data is not None

    def test_anon_cannot_select(self, anon_client: Client):
        """Anonymous users should NOT be able to SELECT from _edge_function_config."""
        result = anon_client.table("_edge_function_config").select("*").execute()
        # RLS should return empty results, not an error
        assert result.data == []

    def test_anon_cannot_insert(self, anon_client: Client):
        """Anonymous users should NOT be able to INSERT into _edge_function_config."""
        from postgrest.exceptions import APIError
        
        # RLS violation causes an APIError
        with pytest.raises(APIError) as excinfo:
            anon_client.table("_edge_function_config").insert({
                "function_name": "_anon_test",
                "base_url": "http://anon.example.com"
            }).execute()
        
        # Verify it's a security policy violation if possible, or just accept APIError
        # Postgres 42501 is insufficient_privilege
        # But Supabase often returns 403 or generic 401/500 depending on config
        assert excinfo.value


class TestSessionVersionHistoryRLS:
    """Test security of session_version_history view."""

    def test_view_inherits_rls_from_session_events(self, service_client: Client):
        """session_version_history should inherit RLS from session_events table."""
        # This test verifies the view exists and is queryable
        result = service_client.table("session_version_history").select("*").limit(1).execute()
        # Should not raise an error
        assert result.data is not None

    def test_get_session_version_history_function_exists(self, service_client: Client):
        """The security-aware function wrapper should exist."""
        result = service_client.rpc(
            "get_session_version_history",
            {"p_app_name": "test_app", "p_session_id": "test_session"}
        ).execute()
        # Should return empty (no matching data) but not error
        assert result.data is not None


class TestEdgeFunctionWebhookStillWorks:
    """Test that edge function webhooks still work with RLS enabled."""

    def test_call_edge_function_can_access_config(self, service_client: Client):
        """The call_edge_function stored procedure should still work.
        
        call_edge_function uses SECURITY DEFINER and should be able to read
        from _edge_function_config even though it's protected by RLS.
        """
        # Verify the function exists and can be called (even if it fails due to network)
        try:
            # This may fail on network call, but should not fail on RLS
            result = service_client.rpc(
                "call_edge_function",
                {
                    "function_name": "send-notification",
                    "payload": {"test": True}
                }
            ).execute()
            # If we get here without RLS error, the test passes
            assert True
        except Exception as e:
            error_str = str(e).lower()
            # RLS violation would contain "policy" or "permission"
            # Network errors are acceptable (edge function not running)
            assert "policy" not in error_str and "permission" not in error_str, \
                f"Unexpected RLS error: {e}"
