"""Shared fixtures for admin unit tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase service client."""
    client = MagicMock()
    rpc_mock = MagicMock()
    rpc_mock.execute.return_value = MagicMock(data=True)
    client.rpc.return_value = rpc_mock
    return client


@pytest.fixture
def admin_user_dict():
    """A user dict that represents an admin user."""
    return {
        "id": "user-admin-uuid",
        "email": "admin@test.com",
        "role": "authenticated",
        "metadata": {},
    }


@pytest.fixture
def non_admin_user_dict():
    """A user dict that represents a non-admin user."""
    return {
        "id": "user-nonadmin-uuid",
        "email": "regular@test.com",
        "role": "authenticated",
        "metadata": {},
    }


@pytest.fixture
def mock_verify_token(admin_user_dict):
    """Async mock for verify_token that returns an admin user dict."""
    mock = AsyncMock(return_value=admin_user_dict)
    return mock
