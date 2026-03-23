"""Unit tests for capacitor_generator.py — Capacitor project scaffold ZIP."""

import io
import json
import zipfile
from unittest.mock import AsyncMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _open_zip(result: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(result), "r")


def _read_from_zip(zf: zipfile.ZipFile, name: str) -> str:
    return zf.read(name).decode("utf-8")


# ---------------------------------------------------------------------------
# Test 1: generate_capacitor_zip returns valid ZIP bytes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_capacitor_zip_returns_valid_zip_bytes() -> None:
    """generate_capacitor_zip must return bytes that zipfile recognises as valid ZIP."""
    with patch(
        "app.services.capacitor_generator._resolve_npm_version",
        new=AsyncMock(return_value="7.2.0"),
    ):
        from app.services.capacitor_generator import generate_capacitor_zip

        result = await generate_capacitor_zip(
            app_name="My App", html_content="<p>Hello</p>"
        )

    assert isinstance(result, bytes), "result must be bytes"
    assert zipfile.is_zipfile(io.BytesIO(result)), "result must be a valid ZIP archive"


# ---------------------------------------------------------------------------
# Test 2: ZIP contains capacitor.config.ts with appId and appName
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_capacitor_config_ts_contains_app_id_and_app_name() -> None:
    """capacitor.config.ts must include the reverse-domain appId and appName."""
    with patch(
        "app.services.capacitor_generator._resolve_npm_version",
        new=AsyncMock(return_value="7.2.0"),
    ):
        from app.services.capacitor_generator import generate_capacitor_zip

        result = await generate_capacitor_zip(
            app_name="My App", html_content="<p>Hello</p>"
        )

    with _open_zip(result) as zf:
        assert "capacitor.config.ts" in zf.namelist(), (
            "capacitor.config.ts must be in the ZIP"
        )
        config_ts = _read_from_zip(zf, "capacitor.config.ts")

    assert "appId" in config_ts, "capacitor.config.ts must contain appId"
    assert "appName" in config_ts, "capacitor.config.ts must contain appName"
    assert "My App" in config_ts, "appName value must be the app_name argument"


# ---------------------------------------------------------------------------
# Test 3: ZIP contains package.json with all 4 Capacitor packages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_package_json_contains_capacitor_packages() -> None:
    """package.json must list @capacitor/core, /cli, /ios, /android."""
    with patch(
        "app.services.capacitor_generator._resolve_npm_version",
        new=AsyncMock(return_value="7.2.0"),
    ):
        from app.services.capacitor_generator import generate_capacitor_zip

        result = await generate_capacitor_zip(
            app_name="My App", html_content="<p>Hello</p>"
        )

    with _open_zip(result) as zf:
        assert "package.json" in zf.namelist(), "package.json must be in the ZIP"
        pkg = json.loads(_read_from_zip(zf, "package.json"))

    all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    assert "@capacitor/core" in all_deps, "@capacitor/core missing from package.json"
    assert "@capacitor/cli" in all_deps, "@capacitor/cli missing from package.json"
    assert "@capacitor/ios" in all_deps, "@capacitor/ios missing from package.json"
    assert "@capacitor/android" in all_deps, "@capacitor/android missing from package.json"


# ---------------------------------------------------------------------------
# Test 4: package.json versions come from mocked _resolve_npm_version
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_package_json_versions_are_resolved_not_hardcoded() -> None:
    """package.json must use the version returned by _resolve_npm_version."""
    with patch(
        "app.services.capacitor_generator._resolve_npm_version",
        new=AsyncMock(return_value="7.2.0"),
    ):
        from app.services.capacitor_generator import generate_capacitor_zip

        result = await generate_capacitor_zip(
            app_name="My App", html_content="<p>Hello</p>"
        )

    with _open_zip(result) as zf:
        pkg = json.loads(_read_from_zip(zf, "package.json"))

    all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    for pkg_name, version in all_deps.items():
        if pkg_name.startswith("@capacitor/"):
            assert version == "7.2.0", (
                f"{pkg_name} version should be 7.2.0 (from mock), got {version}"
            )


# ---------------------------------------------------------------------------
# Test 5: ZIP contains www/index.html with the provided HTML content
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_www_index_html_contains_provided_html_content() -> None:
    """www/index.html must exist and contain the html_content argument."""
    html_content = "<h1>My Capacitor App</h1>"
    with patch(
        "app.services.capacitor_generator._resolve_npm_version",
        new=AsyncMock(return_value="7.2.0"),
    ):
        from app.services.capacitor_generator import generate_capacitor_zip

        result = await generate_capacitor_zip(
            app_name="My App", html_content=html_content
        )

    with _open_zip(result) as zf:
        assert "www/index.html" in zf.namelist(), "www/index.html must be in the ZIP"
        index_content = _read_from_zip(zf, "www/index.html")

    assert html_content in index_content, (
        "www/index.html must contain the provided html_content"
    )


# ---------------------------------------------------------------------------
# Test 6: ZIP contains README.md mentioning npx cap add
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_readme_md_contains_npx_cap_add_instructions() -> None:
    """README.md must exist and mention 'npx cap add' for developer instructions."""
    with patch(
        "app.services.capacitor_generator._resolve_npm_version",
        new=AsyncMock(return_value="7.2.0"),
    ):
        from app.services.capacitor_generator import generate_capacitor_zip

        result = await generate_capacitor_zip(
            app_name="My App", html_content="<p>Hello</p>"
        )

    with _open_zip(result) as zf:
        assert "README.md" in zf.namelist(), "README.md must be in the ZIP"
        readme = _read_from_zip(zf, "README.md")

    assert "npx cap add" in readme, "README.md must mention 'npx cap add'"


# ---------------------------------------------------------------------------
# Test 7: appId derived from app_name via slugification with com.pikar. prefix
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_app_id_derived_from_app_name_with_pikar_prefix() -> None:
    """appId must be derived via slugify and prefixed with com.pikar."""
    with patch(
        "app.services.capacitor_generator._resolve_npm_version",
        new=AsyncMock(return_value="7.2.0"),
    ):
        from app.services.capacitor_generator import generate_capacitor_zip

        result = await generate_capacitor_zip(
            app_name="My Cool App", html_content="<p>Hello</p>"
        )

    with _open_zip(result) as zf:
        config_ts = _read_from_zip(zf, "capacitor.config.ts")

    # appId should be "com.pikar.my-cool-app" (spaces -> hyphens, lowercase)
    assert "com.pikar." in config_ts, "appId must start with com.pikar."
    assert "my-cool-app" in config_ts, (
        "appId slug must be lowercase with hyphens (my-cool-app)"
    )
