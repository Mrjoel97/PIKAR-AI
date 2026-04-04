# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for integration provider registry and credential encryption."""

from __future__ import annotations

from dataclasses import fields

import pytest

from app.config.integration_providers import PROVIDER_REGISTRY, ProviderConfig, get_provider


class TestProviderConfig:
    """Tests for the ProviderConfig dataclass."""

    def test_provider_config_is_frozen_dataclass(self) -> None:
        """ProviderConfig should be a frozen dataclass (immutable)."""
        config = ProviderConfig(
            name="Test",
            auth_type="oauth2",
            auth_url="https://example.com/auth",
            token_url="https://example.com/token",
            scopes=["read"],
            client_id_env="TEST_CLIENT_ID",
            client_secret_env="TEST_CLIENT_SECRET",
            webhook_secret_header=None,
            icon_url="https://example.com/icon.svg",
            category="crm_sales",
        )
        with pytest.raises(AttributeError):
            config.name = "Modified"  # type: ignore[misc]

    def test_provider_config_has_expected_fields(self) -> None:
        """ProviderConfig should have all expected fields."""
        field_names = {f.name for f in fields(ProviderConfig)}
        expected = {
            "name",
            "auth_type",
            "auth_url",
            "token_url",
            "scopes",
            "client_id_env",
            "client_secret_env",
            "webhook_secret_header",
            "icon_url",
            "category",
        }
        assert expected == field_names


class TestProviderRegistry:
    """Tests for the PROVIDER_REGISTRY."""

    def test_registry_contains_hubspot(self) -> None:
        """PROVIDER_REGISTRY should contain hubspot with correct fields."""
        assert "hubspot" in PROVIDER_REGISTRY
        hubspot = PROVIDER_REGISTRY["hubspot"]
        assert isinstance(hubspot, ProviderConfig)
        assert hubspot.name == "HubSpot"
        assert hubspot.auth_type == "oauth2"
        assert hubspot.auth_url
        assert hubspot.token_url
        assert hubspot.client_id_env == "HUBSPOT_CLIENT_ID"
        assert hubspot.client_secret_env == "HUBSPOT_CLIENT_SECRET"
        assert hubspot.category == "crm_sales"

    def test_registry_has_eight_providers(self) -> None:
        """PROVIDER_REGISTRY should have at least 8 provider entries."""
        assert len(PROVIDER_REGISTRY) >= 8

    def test_all_registry_entries_are_provider_config(self) -> None:
        """Every entry in PROVIDER_REGISTRY should be a ProviderConfig."""
        for key, config in PROVIDER_REGISTRY.items():
            assert isinstance(config, ProviderConfig), f"{key} is not a ProviderConfig"

    def test_get_provider_returns_config(self) -> None:
        """get_provider should return the ProviderConfig for a known provider."""
        config = get_provider("hubspot")
        assert config is not None
        assert config.name == "HubSpot"

    def test_get_provider_returns_none_for_unknown(self) -> None:
        """get_provider should return None for an unknown provider."""
        assert get_provider("nonexistent_provider") is None

    def test_all_providers_have_valid_categories(self) -> None:
        """All providers should have a valid category."""
        valid_categories = {
            "crm_sales",
            "finance_commerce",
            "productivity",
            "analytics",
            "communication",
        }
        for key, config in PROVIDER_REGISTRY.items():
            assert config.category in valid_categories, (
                f"{key} has invalid category: {config.category}"
            )

    def test_all_oauth2_providers_have_auth_urls(self) -> None:
        """All oauth2 providers should have auth_url and token_url."""
        for key, config in PROVIDER_REGISTRY.items():
            if config.auth_type == "oauth2":
                assert config.auth_url, f"{key} missing auth_url"
                assert config.token_url, f"{key} missing token_url"
