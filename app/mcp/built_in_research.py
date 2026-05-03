"""Shared definitions for platform-managed built-in research providers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BuiltInResearchProvider:
    """Metadata for a research provider bundled into the platform."""

    id: str
    name: str
    description: str
    admin_display_name: str
    base_url_attr: str
    operator_check_method: str
    capabilities: tuple[str, ...]


BUILT_IN_RESEARCH_PROVIDERS: tuple[BuiltInResearchProvider, ...] = (
    BuiltInResearchProvider(
        id="tavily",
        name="Web Search (Tavily)",
        description="AI-powered web search - automatically used for research tasks.",
        admin_display_name="Tavily Search",
        base_url_attr="tavily_base_url",
        operator_check_method="is_tavily_configured",
        capabilities=("web_search",),
    ),
    BuiltInResearchProvider(
        id="firecrawl",
        name="Web Scraping (Firecrawl)",
        description="Content extraction from webpages - automatically used for deep research.",
        admin_display_name="Firecrawl",
        base_url_attr="firecrawl_base_url",
        operator_check_method="is_firecrawl_configured",
        capabilities=("web_scrape", "web_crawl"),
    ),
)

_PROVIDERS_BY_ID = {provider.id: provider for provider in BUILT_IN_RESEARCH_PROVIDERS}


def list_built_in_research_providers() -> tuple[BuiltInResearchProvider, ...]:
    """Return the platform-managed research providers."""

    return BUILT_IN_RESEARCH_PROVIDERS


def get_built_in_research_provider(
    provider_id: str,
) -> BuiltInResearchProvider | None:
    """Look up a built-in research provider by identifier."""

    return _PROVIDERS_BY_ID.get(provider_id)


def is_platform_managed_research_provider(provider_id: str) -> bool:
    """Return True when the provider is bundled and managed by the platform."""

    return provider_id in _PROVIDERS_BY_ID


def is_provider_available_to_all_users(provider_id: str) -> bool:
    """Built-in research providers are always presented as active to users."""

    return is_platform_managed_research_provider(provider_id)


def get_provider_user_status(provider_id: str) -> str:
    """Return the user-facing availability label for a built-in provider."""

    if is_provider_available_to_all_users(provider_id):
        return "Active for all users"
    return "Bundled in the app"


def get_provider_operator_configured(provider_id: str, config) -> bool:
    """Return whether the server-side credentials are present for the provider."""

    provider = get_built_in_research_provider(provider_id)
    if provider is None:
        return False

    checker = getattr(config, provider.operator_check_method, None)
    if not callable(checker):
        return False

    return bool(checker())


def get_provider_operator_status(provider_id: str, config) -> str:
    """Return an operator-focused health label for the provider."""

    if get_provider_operator_configured(provider_id, config):
        return "Server API key configured"
    return "Server API key missing"


def get_provider_base_url(provider_id: str, config) -> str:
    """Return the configured base URL for the provider."""

    provider = get_built_in_research_provider(provider_id)
    if provider is None:
        return ""
    return str(getattr(config, provider.base_url_attr, ""))

