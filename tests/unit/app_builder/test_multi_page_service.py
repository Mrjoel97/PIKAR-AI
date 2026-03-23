"""Unit tests for multi_page_service — baton loop, nav baton, nav rewriter, nav injection.

Tests cover:
1. Baton loop yields correct event types and order for a 3-page sitemap
2. Nav baton accumulates growing context with each page added
3. Design system markdown is prepended to every page prompt
4. NavLinkRewriter rewrites /slug hrefs to absolute Supabase URLs
5. inject_navigation_links downloads, rewrites, and re-uploads HTML
6. Design markdown appears in every page prompt across the full baton loop
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"
TEST_PROJECT_ID = "aaaaaaaa-0000-0000-0000-000000000001"
TEST_STITCH_PROJECT_ID = "stitch-proj-001"

SITEMAP = [
    {"page": "home", "title": "Home", "sections": ["hero", "features"]},
    {"page": "about", "title": "About", "sections": ["team", "mission"]},
    {"page": "contact", "title": "Contact", "sections": ["form"]},
]

STITCH_RESPONSE = {
    "screenId": "stitch-screen-001",
    "html_url": "https://temp.stitch.dev/html",
    "screenshot_url": "https://temp.stitch.dev/screenshot.png",
}

PERSISTED_URLS = {
    "html_url": "https://supabase.co/storage/v1/object/public/stitch-assets/uid/pid/sid/v0/screen.html",
    "screenshot_url": "https://supabase.co/storage/v1/object/public/stitch-assets/uid/pid/sid/v0/screenshot.png",
}


def _make_supabase_mock() -> MagicMock:
    """Return a MagicMock mimicking the Supabase service client chain."""
    client = MagicMock()
    insert_result = MagicMock(data=[{"id": "test-id"}])
    client.table.return_value.insert.return_value.execute.return_value = insert_result
    return client


def _make_stitch_mock() -> MagicMock:
    """Return a mock StitchMCPService with call_tool as AsyncMock."""
    service = MagicMock()
    service.call_tool = AsyncMock(return_value=STITCH_RESPONSE)
    return service


# ---------------------------------------------------------------------------
# Test 1 — baton loop yields correct events for a 3-page sitemap
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_baton_loop_yields_correct_events():
    """build_all_pages yields 3 page_started + 3 page_complete + 1 build_complete in order."""
    from app.services.multi_page_service import build_all_pages

    mock_supabase = _make_supabase_mock()
    mock_stitch = _make_stitch_mock()

    with (
        patch(
            "app.services.multi_page_service.get_stitch_service",
            return_value=mock_stitch,
        ),
        patch(
            "app.services.multi_page_service.persist_screen_assets",
            new=AsyncMock(return_value=PERSISTED_URLS),
        ),
        patch(
            "app.services.multi_page_service.get_service_client",
            return_value=mock_supabase,
        ),
    ):
        events = []
        async for event in build_all_pages(
            project_id=TEST_PROJECT_ID,
            user_id=TEST_USER_ID,
            sitemap=SITEMAP,
            design_markdown="DESIGN:red",
            stitch_project_id=TEST_STITCH_PROJECT_ID,
        ):
            events.append(event)

    steps = [e["step"] for e in events]

    # Total: 3 page_started + 3 page_complete + 1 build_complete = 7 events
    assert len(events) == 7

    # Correct ordering: interleaved page_started, page_complete
    assert steps[0] == "page_started"
    assert steps[1] == "page_complete"
    assert steps[2] == "page_started"
    assert steps[3] == "page_complete"
    assert steps[4] == "page_started"
    assert steps[5] == "page_complete"
    assert steps[6] == "build_complete"

    # page_slugs are correct
    page_started_events = [e for e in events if e["step"] == "page_started"]
    slugs = [e["page_slug"] for e in page_started_events]
    assert slugs == ["home", "about", "contact"]

    page_complete_events = [e for e in events if e["step"] == "page_complete"]
    complete_slugs = [e["page_slug"] for e in page_complete_events]
    assert complete_slugs == ["home", "about", "contact"]

    # build_complete has correct total_pages and screens list
    build_event = events[-1]
    assert build_event["total_pages"] == 3
    assert len(build_event["screens"]) == 3


# ---------------------------------------------------------------------------
# Test 2 — nav baton accumulates correctly
# ---------------------------------------------------------------------------


def test_nav_baton_accumulates():
    """_build_nav_baton returns empty string for 0 screens, grows with each screen."""
    from app.services.multi_page_service import _build_nav_baton

    # 0 screens: empty string (first page has no nav context)
    result_0 = _build_nav_baton([])
    assert result_0 == ""

    # 1 screen: contains page 1 slug
    screens_1 = [
        {"page_slug": "home", "page_title": "Home", "screen_id": "s1", "html_url": "https://example.com/home.html"},
    ]
    result_1 = _build_nav_baton(screens_1)
    assert "home" in result_1
    assert result_1 != ""

    # 2 screens: contains both slugs
    screens_2 = screens_1 + [
        {"page_slug": "about", "page_title": "About", "screen_id": "s2", "html_url": "https://example.com/about.html"},
    ]
    result_2 = _build_nav_baton(screens_2)
    assert "home" in result_2
    assert "about" in result_2
    # Result grows longer as pages accumulate
    assert len(result_2) > len(result_1)


# ---------------------------------------------------------------------------
# Test 3 — design system markdown is prepended to page prompt
# ---------------------------------------------------------------------------


def test_design_system_injected_in_prompt():
    """_build_page_prompt prepends 'DESIGN SYSTEM:\\n{design_markdown}' to the prompt."""
    from app.services.multi_page_service import _build_page_prompt

    prompt = _build_page_prompt(
        design_markdown="DESIGN:red",
        page_title="Home",
        page_slug="home",
        sections=["hero"],
        nav_context="",
    )

    assert prompt.startswith("DESIGN SYSTEM:\nDESIGN:red")


# ---------------------------------------------------------------------------
# Test 4 — NavLinkRewriter rewrites /slug hrefs to absolute Supabase URLs
# ---------------------------------------------------------------------------


def test_nav_link_rewriter():
    """NavLinkRewriter converts /about to the absolute Supabase Storage URL."""
    from app.services.multi_page_service import NavLinkRewriter

    slug_to_url = {
        "home": "https://supabase.co/storage/home.html",
        "about": "https://supabase.co/storage/about.html",
    }

    rewriter = NavLinkRewriter(slug_to_url)
    html_input = '<a href="/about">About</a>'
    rewriter.feed(html_input)
    output = "".join(rewriter.output)

    assert "https://supabase.co/storage/about.html" in output
    # The original /about href (as a standalone href attribute) should be rewritten
    assert 'href="/about"' not in output


def test_nav_link_rewriter_no_match_passthrough():
    """NavLinkRewriter passes through hrefs that don't match any slug unchanged."""
    from app.services.multi_page_service import NavLinkRewriter

    slug_to_url = {"home": "https://supabase.co/storage/home.html"}

    rewriter = NavLinkRewriter(slug_to_url)
    rewriter.feed('<a href="https://external.com">External</a>')
    output = "".join(rewriter.output)

    assert "https://external.com" in output


# ---------------------------------------------------------------------------
# Test 5 — inject_navigation_links downloads, rewrites, and re-uploads HTML
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nav_injection_uploads():
    """inject_navigation_links calls supabase storage upload with rewritten HTML."""
    from app.services.multi_page_service import inject_navigation_links

    screens = [
        {
            "page_slug": "home",
            "page_title": "Home",
            "screen_id": "screen-home",
            "html_url": "https://supabase.co/storage/home.html",
        },
        {
            "page_slug": "about",
            "page_title": "About",
            "screen_id": "screen-about",
            "html_url": "https://supabase.co/storage/about.html",
        },
    ]

    html_with_link = '<html><body><a href="/about">About</a></body></html>'

    mock_response = MagicMock()
    mock_response.text = html_with_link

    mock_supabase = MagicMock()
    upload_result = MagicMock()
    mock_supabase.storage.from_.return_value.upload.return_value = upload_result

    mock_http_get = AsyncMock(return_value=mock_response)

    with (
        patch(
            "app.services.multi_page_service.get_service_client",
            return_value=mock_supabase,
        ),
        patch(
            "app.services.multi_page_service.httpx.AsyncClient",
        ) as mock_http_client_cls,
    ):
        # Set up the async context manager
        mock_http_ctx = MagicMock()
        mock_http_ctx.__aenter__ = AsyncMock(return_value=MagicMock(get=mock_http_get))
        mock_http_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_http_client_cls.return_value = mock_http_ctx

        await inject_navigation_links(
            screens=screens,
            user_id=TEST_USER_ID,
            project_id=TEST_PROJECT_ID,
        )

    # Storage upload should have been called once per screen (2 screens)
    assert mock_supabase.storage.from_.return_value.upload.call_count == 2

    # Verify upsert=true was used
    call_kwargs = mock_supabase.storage.from_.return_value.upload.call_args_list[0][1]
    assert call_kwargs.get("file_options", {}).get("upsert") == "true"


# ---------------------------------------------------------------------------
# Test 6 — design markdown appears in every page prompt across the baton loop
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_design_system_injected_in_every_page_prompt():
    """Every call to Stitch contains the design markdown in the prompt."""
    from app.services.multi_page_service import build_all_pages

    mock_supabase = _make_supabase_mock()
    mock_stitch = _make_stitch_mock()
    design_markdown = "DESIGN:red"

    with (
        patch(
            "app.services.multi_page_service.get_stitch_service",
            return_value=mock_stitch,
        ),
        patch(
            "app.services.multi_page_service.persist_screen_assets",
            new=AsyncMock(return_value=PERSISTED_URLS),
        ),
        patch(
            "app.services.multi_page_service.get_service_client",
            return_value=mock_supabase,
        ),
    ):
        async for _ in build_all_pages(
            project_id=TEST_PROJECT_ID,
            user_id=TEST_USER_ID,
            sitemap=SITEMAP,
            design_markdown=design_markdown,
            stitch_project_id=TEST_STITCH_PROJECT_ID,
        ):
            pass

    # call_tool was called 3 times (once per page)
    assert mock_stitch.call_tool.call_count == 3

    # Every prompt contains the design markdown
    for call in mock_stitch.call_tool.call_args_list:
        args, kwargs = call
        tool_args = args[1] if len(args) > 1 else kwargs.get("args", {})
        prompt = tool_args.get("prompt", "")
        assert design_markdown in prompt, f"Design markdown missing in prompt: {prompt[:200]}"
