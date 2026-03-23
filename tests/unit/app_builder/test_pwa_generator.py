"""Unit tests for pwa_generator.py — PWA manifest, service worker, and iOS meta tags."""

import io
import json
import zipfile

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _open_zip(result: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(result), "r")


def _read_from_zip(zf: zipfile.ZipFile, name: str) -> str:
    return zf.read(name).decode("utf-8")


# ---------------------------------------------------------------------------
# Test 1: generate_pwa_zip returns valid ZIP bytes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_pwa_zip_returns_valid_zip_bytes() -> None:
    """generate_pwa_zip must return bytes that zipfile recognises as a valid ZIP."""
    from app.services.pwa_generator import generate_pwa_zip

    result = await generate_pwa_zip(app_name="My App", html_content="<p>Hello</p>")

    assert isinstance(result, bytes), "result must be bytes"
    assert zipfile.is_zipfile(io.BytesIO(result)), "result must be a valid ZIP archive"


# ---------------------------------------------------------------------------
# Test 2: manifest.json present with required PWA fields
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_manifest_json_has_required_pwa_fields() -> None:
    """manifest.json must contain name, short_name, start_url, display, bg_color, theme_color, icons."""
    from app.services.pwa_generator import generate_pwa_zip

    result = await generate_pwa_zip(app_name="My App", html_content="<p>Hello</p>")

    with _open_zip(result) as zf:
        assert "manifest.json" in zf.namelist(), "manifest.json must be in the ZIP"
        manifest = json.loads(_read_from_zip(zf, "manifest.json"))

    assert manifest["name"] == "My App"
    assert "short_name" in manifest
    assert manifest["start_url"] == "/"
    assert manifest["display"] == "standalone"
    assert "background_color" in manifest
    assert "theme_color" in manifest
    assert "icons" in manifest


# ---------------------------------------------------------------------------
# Test 3: icons array has 192x192, 512x512, and maskable entries
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_manifest_icons_has_three_entries_with_correct_sizes() -> None:
    """icons array must have 3 entries: 192x192, 512x512, 512x512 maskable."""
    from app.services.pwa_generator import generate_pwa_zip

    result = await generate_pwa_zip(app_name="My App", html_content="<p>Hello</p>")

    with _open_zip(result) as zf:
        manifest = json.loads(_read_from_zip(zf, "manifest.json"))

    icons = manifest["icons"]
    assert len(icons) == 3, f"Expected 3 icons, got {len(icons)}"

    sizes = [icon["sizes"] for icon in icons]
    assert "192x192" in sizes, "192x192 icon missing"
    assert "512x512" in sizes, "512x512 icon missing"

    maskable = [icon for icon in icons if icon.get("purpose") == "maskable"]
    assert len(maskable) == 1, "Exactly one maskable icon required"
    assert maskable[0]["sizes"] == "512x512", "Maskable icon must be 512x512"


# ---------------------------------------------------------------------------
# Test 4: sw.js has install and fetch event listeners
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sw_js_has_install_and_fetch_event_listeners() -> None:
    """sw.js must contain install and fetch event listener registrations."""
    from app.services.pwa_generator import generate_pwa_zip

    result = await generate_pwa_zip(app_name="My App", html_content="<p>Hello</p>")

    with _open_zip(result) as zf:
        assert "sw.js" in zf.namelist(), "sw.js must be in the ZIP"
        sw_content = _read_from_zip(zf, "sw.js")

    assert "addEventListener('install'" in sw_content or 'addEventListener("install"' in sw_content, (
        "sw.js must register an install event listener"
    )
    assert "addEventListener('fetch'" in sw_content or 'addEventListener("fetch"' in sw_content, (
        "sw.js must register a fetch event listener"
    )


# ---------------------------------------------------------------------------
# Test 5: index.html has Apple iOS meta tags
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_index_html_has_apple_ios_meta_tags() -> None:
    """index.html must contain apple-mobile-web-app meta tags and apple-touch-icon link."""
    from app.services.pwa_generator import generate_pwa_zip

    result = await generate_pwa_zip(app_name="My App", html_content="<p>Hello</p>")

    with _open_zip(result) as zf:
        assert "index.html" in zf.namelist(), "index.html must be in the ZIP"
        html = _read_from_zip(zf, "index.html")

    assert "apple-mobile-web-app-capable" in html, "Missing apple-mobile-web-app-capable meta tag"
    assert "apple-mobile-web-app-title" in html, "Missing apple-mobile-web-app-title meta tag"
    assert "apple-touch-icon" in html, "Missing apple-touch-icon link"


# ---------------------------------------------------------------------------
# Test 6: index.html has manifest link
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_index_html_has_manifest_link() -> None:
    """index.html must contain <link rel="manifest" href="manifest.json">."""
    from app.services.pwa_generator import generate_pwa_zip

    result = await generate_pwa_zip(app_name="My App", html_content="<p>Hello</p>")

    with _open_zip(result) as zf:
        html = _read_from_zip(zf, "index.html")

    assert 'rel="manifest"' in html, "Missing rel='manifest' link tag"
    assert "manifest.json" in html, "manifest link must point to manifest.json"


# ---------------------------------------------------------------------------
# Test 7: theme_color from design_system appears in manifest and meta tag
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_theme_color_from_design_system_used_in_manifest_and_meta() -> None:
    """theme_color from design_system must appear in manifest.json and meta theme-color tag."""
    from app.services.pwa_generator import generate_pwa_zip

    design_system = {"theme_color": "#ff5733", "background_color": "#1a1a1a"}
    result = await generate_pwa_zip(
        app_name="My App",
        html_content="<p>Hello</p>",
        design_system=design_system,
    )

    with _open_zip(result) as zf:
        manifest = json.loads(_read_from_zip(zf, "manifest.json"))
        html = _read_from_zip(zf, "index.html")

    assert manifest["theme_color"] == "#ff5733", (
        f"manifest theme_color should be #ff5733, got {manifest['theme_color']}"
    )
    assert "#ff5733" in html, "theme_color #ff5733 must appear in index.html meta theme-color tag"
