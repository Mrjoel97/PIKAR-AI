"""Unit tests for react_converter — mocks Gemini calls and httpx for npm registry."""

import io
import json
import zipfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_gemini_response() -> dict:
    """Return a minimal structured Gemini response with 2 components."""
    return {
        "components": [
            {
                "name": "HeroSection",
                "filename": "HeroSection.tsx",
                "code": "export default function HeroSection() { return <div>Hero</div>; }",
                "section": "hero",
            },
            {
                "name": "FeaturesSection",
                "filename": "FeaturesSection.tsx",
                "code": "export default function FeaturesSection() { return <div>Features</div>; }",
                "section": "features",
            },
        ],
        "tailwind_theme": {
            "colors": {"primary": "#6366F1", "background": "#F9FAFB"},
            "fontFamily": {"sans": ["Inter", "sans-serif"]},
            "spacing": {},
        },
        "index_tsx": "import HeroSection from './components/HeroSection';\nimport FeaturesSection from './components/FeaturesSection';\nexport default function App() { return <><HeroSection /><FeaturesSection /></>; }",
    }


def _make_mock_genai_client(gemini_data: dict):
    """Return a MagicMock genai.Client() whose aio response returns gemini_data as JSON."""
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        return_value=MagicMock(text=json.dumps(gemini_data))
    )
    return mock_client


# ---------------------------------------------------------------------------
# Tests for resolve_npm_version
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_npm_version_returns_latest_from_registry():
    """resolve_npm_version returns dist-tags.latest when httpx succeeds."""
    from app.services import react_converter

    mock_response = MagicMock()
    mock_response.json.return_value = {"dist-tags": {"latest": "19.1.0"}}
    mock_response.raise_for_status = MagicMock()

    mock_async_client = AsyncMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)
    mock_async_client.get = AsyncMock(return_value=mock_response)

    with patch("app.services.react_converter.httpx") as mock_httpx:
        mock_httpx.AsyncClient.return_value = mock_async_client
        result = await react_converter.resolve_npm_version("react")

    assert result == "19.1.0"


@pytest.mark.asyncio
async def test_resolve_npm_version_returns_fallback_for_react_on_error():
    """resolve_npm_version returns hardcoded fallback for 'react' when httpx raises."""
    from app.services import react_converter

    mock_async_client = AsyncMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)
    mock_async_client.get = AsyncMock(side_effect=Exception("network error"))

    with patch("app.services.react_converter.httpx") as mock_httpx:
        mock_httpx.AsyncClient.return_value = mock_async_client
        result = await react_converter.resolve_npm_version("react")

    # Should return the hardcoded fallback for react (not "latest")
    assert result == react_converter._FALLBACK_VERSIONS["react"]
    assert result != "latest"


@pytest.mark.asyncio
async def test_resolve_npm_version_returns_latest_for_unknown_package_on_error():
    """resolve_npm_version returns 'latest' for unknown packages when httpx raises."""
    from app.services import react_converter

    mock_async_client = AsyncMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)
    mock_async_client.get = AsyncMock(side_effect=Exception("network error"))

    with patch("app.services.react_converter.httpx") as mock_httpx:
        mock_httpx.AsyncClient.return_value = mock_async_client
        result = await react_converter.resolve_npm_version("some-unknown-package-xyz")

    assert result == "latest"


# ---------------------------------------------------------------------------
# Tests for convert_html_to_react_zip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_convert_html_to_react_zip_returns_valid_zip_bytes():
    """convert_html_to_react_zip returns bytes that are a valid ZIP archive."""
    from app.services import react_converter

    gemini_data = _make_fake_gemini_response()
    mock_client = _make_mock_genai_client(gemini_data)

    # npm version resolve calls
    mock_npm_response = MagicMock()
    mock_npm_response.json.return_value = {"dist-tags": {"latest": "18.3.1"}}
    mock_npm_response.raise_for_status = MagicMock()

    mock_async_client = AsyncMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)
    mock_async_client.get = AsyncMock(return_value=mock_npm_response)

    with (
        patch("app.services.react_converter.genai") as mock_genai,
        patch("app.services.react_converter.httpx") as mock_httpx,
    ):
        mock_genai.Client.return_value = mock_client
        mock_httpx.AsyncClient.return_value = mock_async_client
        zip_bytes = await react_converter.convert_html_to_react_zip(
            html_content="<html><body><h1>Hello</h1></body></html>",
            screen_name="HomePage",
        )

    assert isinstance(zip_bytes, bytes)
    assert zipfile.is_zipfile(io.BytesIO(zip_bytes))


@pytest.mark.asyncio
async def test_convert_html_to_react_zip_contains_tsx_components():
    """ZIP contains src/components/*.tsx files matching Gemini response component count."""
    from app.services import react_converter

    gemini_data = _make_fake_gemini_response()
    mock_client = _make_mock_genai_client(gemini_data)

    mock_npm_response = MagicMock()
    mock_npm_response.json.return_value = {"dist-tags": {"latest": "1.0.0"}}
    mock_npm_response.raise_for_status = MagicMock()

    mock_async_client = AsyncMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)
    mock_async_client.get = AsyncMock(return_value=mock_npm_response)

    with (
        patch("app.services.react_converter.genai") as mock_genai,
        patch("app.services.react_converter.httpx") as mock_httpx,
    ):
        mock_genai.Client.return_value = mock_client
        mock_httpx.AsyncClient.return_value = mock_async_client
        zip_bytes = await react_converter.convert_html_to_react_zip(
            html_content="<html><body></body></html>",
            screen_name="LandingPage",
        )

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()

    tsx_components = [n for n in names if n.startswith("src/components/") and n.endswith(".tsx")]
    # Gemini response has 2 components: HeroSection.tsx and FeaturesSection.tsx
    assert len(tsx_components) == 2
    assert "src/components/HeroSection.tsx" in tsx_components
    assert "src/components/FeaturesSection.tsx" in tsx_components


@pytest.mark.asyncio
async def test_convert_html_to_react_zip_contains_app_tsx():
    """ZIP contains src/App.tsx root component."""
    from app.services import react_converter

    gemini_data = _make_fake_gemini_response()
    mock_client = _make_mock_genai_client(gemini_data)

    mock_npm_response = MagicMock()
    mock_npm_response.json.return_value = {"dist-tags": {"latest": "1.0.0"}}
    mock_npm_response.raise_for_status = MagicMock()

    mock_async_client = AsyncMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)
    mock_async_client.get = AsyncMock(return_value=mock_npm_response)

    with (
        patch("app.services.react_converter.genai") as mock_genai,
        patch("app.services.react_converter.httpx") as mock_httpx,
    ):
        mock_genai.Client.return_value = mock_client
        mock_httpx.AsyncClient.return_value = mock_async_client
        zip_bytes = await react_converter.convert_html_to_react_zip(
            html_content="<html></html>",
            screen_name="TestPage",
        )

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()

    assert "src/App.tsx" in names


@pytest.mark.asyncio
async def test_convert_html_to_react_zip_contains_tailwind_config():
    """ZIP contains tailwind.config.ts with theme colors from Gemini response."""
    from app.services import react_converter

    gemini_data = _make_fake_gemini_response()
    mock_client = _make_mock_genai_client(gemini_data)

    mock_npm_response = MagicMock()
    mock_npm_response.json.return_value = {"dist-tags": {"latest": "1.0.0"}}
    mock_npm_response.raise_for_status = MagicMock()

    mock_async_client = AsyncMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)
    mock_async_client.get = AsyncMock(return_value=mock_npm_response)

    with (
        patch("app.services.react_converter.genai") as mock_genai,
        patch("app.services.react_converter.httpx") as mock_httpx,
    ):
        mock_genai.Client.return_value = mock_client
        mock_httpx.AsyncClient.return_value = mock_async_client
        zip_bytes = await react_converter.convert_html_to_react_zip(
            html_content="<html></html>",
            screen_name="TestPage",
        )

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        tailwind_content = zf.read("tailwind.config.ts").decode()

    assert "tailwind.config.ts" in names
    # Theme colors from fake Gemini response should appear in the config
    assert "#6366F1" in tailwind_content or "primary" in tailwind_content


@pytest.mark.asyncio
async def test_convert_html_to_react_zip_contains_package_json_with_resolved_versions():
    """ZIP contains package.json with resolved npm versions (not hardcoded)."""
    from app.services import react_converter

    gemini_data = _make_fake_gemini_response()
    mock_client = _make_mock_genai_client(gemini_data)

    # Return a specific version from mock registry
    mock_npm_response = MagicMock()
    mock_npm_response.json.return_value = {"dist-tags": {"latest": "99.0.0"}}
    mock_npm_response.raise_for_status = MagicMock()

    mock_async_client = AsyncMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)
    mock_async_client.get = AsyncMock(return_value=mock_npm_response)

    with (
        patch("app.services.react_converter.genai") as mock_genai,
        patch("app.services.react_converter.httpx") as mock_httpx,
    ):
        mock_genai.Client.return_value = mock_client
        mock_httpx.AsyncClient.return_value = mock_async_client
        zip_bytes = await react_converter.convert_html_to_react_zip(
            html_content="<html></html>",
            screen_name="TestPage",
        )

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        pkg_content = zf.read("package.json").decode()

    pkg_data = json.loads(pkg_content)
    # All resolved versions should be "99.0.0" from mock registry
    deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
    # At least one dependency should have the resolved version
    assert any(v == "99.0.0" or v == "^99.0.0" for v in deps.values())


# ---------------------------------------------------------------------------
# Tests for _render_package_json
# ---------------------------------------------------------------------------


def test_render_package_json_includes_core_dependencies():
    """_render_package_json includes react, react-dom, tailwindcss as dependencies."""
    from app.services.react_converter import _render_package_json

    versions = {
        "react": "19.1.0",
        "react-dom": "19.1.0",
        "tailwindcss": "4.0.0",
        "typescript": "5.7.0",
    }
    pkg_json_str = _render_package_json(["react", "react-dom", "tailwindcss", "typescript"], versions)
    pkg = json.loads(pkg_json_str)

    # Core runtime dependencies
    deps = pkg.get("dependencies", {})
    assert "react" in deps
    assert "react-dom" in deps
    assert "tailwindcss" in deps

    # Has scripts section
    scripts = pkg.get("scripts", {})
    assert "dev" in scripts
    assert "build" in scripts
