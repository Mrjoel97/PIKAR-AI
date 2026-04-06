# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Integration provider registry.

Defines the canonical set of third-party providers that Pikar-AI can connect
to, along with their OAuth/API-key configuration metadata.  The registry is
used by the IntegrationManager service and the integrations router to drive
OAuth flows and display provider information in the UI.

Adding a new provider
---------------------
1. Add a ``ProviderConfig`` entry to ``PROVIDER_REGISTRY``.
2. Set the corresponding ``{PROVIDER}_CLIENT_ID`` and
   ``{PROVIDER}_CLIENT_SECRET`` environment variables.
3. No database migration is needed — the ``provider`` column is plain text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ProviderConfig:
    """Immutable configuration for a single integration provider.

    Attributes:
        name: Human-readable display name.
        auth_type: Authentication mechanism (``oauth2`` or ``api_key``).
        auth_url: OAuth2 authorization endpoint (empty for api_key providers).
        token_url: OAuth2 token exchange endpoint (empty for api_key providers).
        scopes: Default OAuth scopes requested during authorization.
        client_id_env: Environment variable name for the OAuth client ID.
        client_secret_env: Environment variable name for the OAuth client secret.
        webhook_secret_header: HTTP header containing webhook signature, if any.
        icon_url: URL to the provider's icon/logo for UI display.
        category: Functional category for grouping in the UI.
    """

    name: str
    auth_type: Literal["oauth2", "api_key"]
    auth_url: str
    token_url: str
    scopes: list[str]
    client_id_env: str
    client_secret_env: str
    webhook_secret_header: str | None
    icon_url: str
    category: Literal[
        "crm_sales",
        "finance_commerce",
        "productivity",
        "analytics",
        "communication",
    ]


PROVIDER_REGISTRY: dict[str, ProviderConfig] = {
    "hubspot": ProviderConfig(
        name="HubSpot",
        auth_type="oauth2",
        auth_url="https://app.hubspot.com/oauth/authorize",
        token_url="https://api.hubapi.com/oauth/v1/token",
        scopes=[
            "crm.objects.contacts.read",
            "crm.objects.contacts.write",
            "crm.objects.deals.read",
            "crm.objects.deals.write",
            "crm.objects.companies.read",
        ],
        client_id_env="HUBSPOT_CLIENT_ID",
        client_secret_env="HUBSPOT_CLIENT_SECRET",
        webhook_secret_header="X-HubSpot-Signature-v3",
        icon_url="https://cdn.pikar.ai/icons/hubspot.svg",
        category="crm_sales",
    ),
    "stripe": ProviderConfig(
        name="Stripe",
        auth_type="oauth2",
        auth_url="https://connect.stripe.com/oauth/authorize",
        token_url="https://connect.stripe.com/oauth/token",
        scopes=["read_write"],
        client_id_env="STRIPE_CLIENT_ID",
        client_secret_env="STRIPE_CLIENT_SECRET",
        webhook_secret_header="Stripe-Signature",
        icon_url="https://cdn.pikar.ai/icons/stripe.svg",
        category="finance_commerce",
    ),
    "shopify": ProviderConfig(
        name="Shopify",
        auth_type="oauth2",
        auth_url="https://{shop}.myshopify.com/admin/oauth/authorize",
        token_url="https://{shop}.myshopify.com/admin/oauth/access_token",
        scopes=[
            "read_products",
            "read_orders",
            "read_customers",
            "read_analytics",
        ],
        client_id_env="SHOPIFY_CLIENT_ID",
        client_secret_env="SHOPIFY_CLIENT_SECRET",
        webhook_secret_header="X-Shopify-Hmac-Sha256",
        icon_url="https://cdn.pikar.ai/icons/shopify.svg",
        category="finance_commerce",
    ),
    "linear": ProviderConfig(
        name="Linear",
        auth_type="oauth2",
        auth_url="https://linear.app/oauth/authorize",
        token_url="https://api.linear.app/oauth/token",
        scopes=["read", "write", "issues:create", "comments:create"],
        client_id_env="LINEAR_CLIENT_ID",
        client_secret_env="LINEAR_CLIENT_SECRET",
        webhook_secret_header="Linear-Signature",
        icon_url="https://cdn.pikar.ai/icons/linear.svg",
        category="productivity",
    ),
    "asana": ProviderConfig(
        name="Asana",
        auth_type="oauth2",
        auth_url="https://app.asana.com/-/oauth_authorize",
        token_url="https://app.asana.com/-/oauth_token",
        scopes=["default"],
        client_id_env="ASANA_CLIENT_ID",
        client_secret_env="ASANA_CLIENT_SECRET",
        webhook_secret_header="X-Hook-Secret",
        icon_url="https://cdn.pikar.ai/icons/asana.svg",
        category="productivity",
    ),
    "slack": ProviderConfig(
        name="Slack",
        auth_type="oauth2",
        auth_url="https://slack.com/oauth/v2/authorize",
        token_url="https://slack.com/api/oauth.v2.access",
        scopes=[
            "channels:read",
            "chat:write",
            "chat:write.public",
            "users:read",
            "files:read",
        ],
        client_id_env="SLACK_CLIENT_ID",
        client_secret_env="SLACK_CLIENT_SECRET",
        webhook_secret_header="X-Slack-Signature",
        icon_url="https://cdn.pikar.ai/icons/slack.svg",
        category="communication",
    ),
    "teams": ProviderConfig(
        name="Microsoft Teams",
        auth_type="api_key",
        auth_url="",
        token_url="",
        scopes=[],
        client_id_env="",
        client_secret_env="",
        webhook_secret_header=None,
        icon_url="https://cdn.pikar.ai/icons/teams.svg",
        category="communication",
    ),
    "postgresql": ProviderConfig(
        name="PostgreSQL",
        auth_type="api_key",
        auth_url="",
        token_url="",
        scopes=[],
        client_id_env="",
        client_secret_env="",
        webhook_secret_header=None,
        icon_url="https://cdn.pikar.ai/icons/postgresql.svg",
        category="analytics",
    ),
    "bigquery": ProviderConfig(
        name="BigQuery",
        auth_type="oauth2",
        auth_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        scopes=[
            "https://www.googleapis.com/auth/bigquery.readonly",
            "https://www.googleapis.com/auth/cloud-platform.read-only",
        ],
        client_id_env="BIGQUERY_CLIENT_ID",
        client_secret_env="BIGQUERY_CLIENT_SECRET",
        webhook_secret_header=None,
        icon_url="https://cdn.pikar.ai/icons/bigquery.svg",
        category="analytics",
    ),
    "google_ads": ProviderConfig(
        name="Google Ads",
        auth_type="oauth2",
        auth_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/adwords"],
        client_id_env="GOOGLE_ADS_CLIENT_ID",
        client_secret_env="GOOGLE_ADS_CLIENT_SECRET",
        webhook_secret_header=None,
        icon_url="https://cdn.pikar.ai/icons/google-ads.svg",
        category="analytics",
    ),
    "meta_ads": ProviderConfig(
        name="Meta Ads",
        auth_type="oauth2",
        auth_url="https://www.facebook.com/v19.0/dialog/oauth",
        token_url="https://graph.facebook.com/v19.0/oauth/access_token",
        scopes=["ads_management", "ads_read", "business_management"],
        client_id_env="META_ADS_CLIENT_ID",
        client_secret_env="META_ADS_CLIENT_SECRET",
        webhook_secret_header=None,
        icon_url="https://cdn.pikar.ai/icons/meta-ads.svg",
        category="analytics",
    ),
}


def get_provider(name: str) -> ProviderConfig | None:
    """Look up a provider configuration by key.

    Args:
        name: Provider key (e.g. ``"hubspot"``).

    Returns:
        The ``ProviderConfig`` if found, otherwise ``None``.
    """
    return PROVIDER_REGISTRY.get(name)
