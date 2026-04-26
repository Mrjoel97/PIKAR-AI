# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""React Converter — transforms Stitch-generated HTML into modular React/TypeScript components.

Uses Gemini Flash structured output to decompose HTML into named TSX components,
extracts Tailwind theme tokens, and packages everything into a downloadable ZIP.
npm versions are resolved live from the npm registry with hardcoded fallbacks.
"""

import asyncio
import io
import json
import logging
import zipfile

import httpx

try:
    from google import genai
    from google.genai import types as genai_types
except (
    Exception
):  # pragma: no cover - import guard for environments without google-genai
    genai = None  # type: ignore[assignment]
    genai_types = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_NPM_REGISTRY = "https://registry.npmjs.org"

_FALLBACK_VERSIONS: dict[str, str] = {
    "react": "19.0.0",
    "react-dom": "19.0.0",
    "tailwindcss": "4.0.0",
    "typescript": "5.7.0",
    "@types/react": "19.0.0",
    "@types/react-dom": "19.0.0",
}

# ---------------------------------------------------------------------------
# Gemini JSON schema for structured HTML-to-React output
# ---------------------------------------------------------------------------

REACT_CONVERTER_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "components": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "filename": {"type": "string"},
                    "code": {"type": "string"},
                    "section": {"type": "string"},
                },
                "required": ["name", "filename", "code", "section"],
            },
        },
        "tailwind_theme": {
            "type": "object",
            "properties": {
                "colors": {"type": "object"},
                "fontFamily": {"type": "object"},
                "spacing": {"type": "object"},
            },
        },
        "index_tsx": {"type": "string"},
    },
    "required": ["components", "tailwind_theme", "index_tsx"],
}

# ---------------------------------------------------------------------------
# npm version resolution
# ---------------------------------------------------------------------------


async def resolve_npm_version(package: str) -> str:
    """Resolve the latest stable version of an npm package from the registry.

    Args:
        package: npm package name, e.g. "react" or "tailwindcss".

    Returns:
        Version string from dist-tags.latest, or hardcoded fallback on error,
        or "latest" for unknown packages when the registry is unreachable.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{_NPM_REGISTRY}/{package}")
            response.raise_for_status()
            data = response.json()
            return data["dist-tags"]["latest"]
    except Exception as exc:
        fallback = _FALLBACK_VERSIONS.get(package, "latest")
        logger.warning(
            "resolve_npm_version: registry lookup failed for '%s' (%s) — using %s",
            package,
            exc,
            fallback,
        )
        return fallback


# ---------------------------------------------------------------------------
# Internal rendering helpers
# ---------------------------------------------------------------------------


def _render_tailwind_config(theme: dict) -> str:
    """Generate tailwind.config.ts content from a theme dict.

    Args:
        theme: dict with optional keys: colors, fontFamily, spacing.

    Returns:
        TypeScript source string for tailwind.config.ts.
    """
    colors = theme.get("colors", {})
    font_family = theme.get("fontFamily", {})
    spacing = theme.get("spacing", {})

    colors_str = json.dumps(colors, indent=6)
    font_str = json.dumps(font_family, indent=6)
    spacing_str = json.dumps(spacing, indent=6)

    return f"""\
import type {{ Config }} from 'tailwindcss';

const config: Config = {{
  content: ['./src/**/*.{{ts,tsx}}'],
  theme: {{
    extend: {{
      colors: {colors_str},
      fontFamily: {font_str},
      spacing: {spacing_str},
    }},
  }},
  plugins: [],
}};

export default config;
"""


def _render_package_json(deps: list[str], versions: dict[str, str]) -> str:
    """Generate package.json content with resolved dependency versions.

    Args:
        deps: list of package names to include as runtime dependencies.
        versions: mapping of package name -> resolved version string.

    Returns:
        JSON string for package.json.
    """
    dependencies: dict[str, str] = {}
    for pkg in deps:
        ver = versions.get(pkg, _FALLBACK_VERSIONS.get(pkg, "latest"))
        dependencies[pkg] = f"^{ver}" if not ver.startswith("^") else ver

    dev_dependencies: dict[str, str] = {}
    for pkg in ("typescript", "@types/react", "@types/react-dom"):
        ver = versions.get(pkg, _FALLBACK_VERSIONS.get(pkg, "latest"))
        dev_dependencies[pkg] = f"^{ver}" if not ver.startswith("^") else ver

    pkg = {
        "name": "pikar-app",
        "version": "0.1.0",
        "private": True,
        "scripts": {
            "dev": "vite",
            "build": "tsc && vite build",
            "preview": "vite preview",
        },
        "dependencies": dependencies,
        "devDependencies": dev_dependencies,
    }
    return json.dumps(pkg, indent=2)


# ---------------------------------------------------------------------------
# ZIP assembly
# ---------------------------------------------------------------------------


def _build_react_zip(
    components: list[dict],
    tailwind_theme: dict,
    index_tsx: str,
    versions: dict[str, str],
) -> bytes:
    """Assemble an in-memory ZIP with all React project files.

    Args:
        components: list of component dicts with keys: name, filename, code, section.
        tailwind_theme: Tailwind theme dict (colors, fontFamily, spacing).
        index_tsx: root App.tsx source string.
        versions: resolved npm versions for package.json generation.

    Returns:
        ZIP archive bytes ready for storage upload or HTTP response.
    """
    buf = io.BytesIO()
    runtime_deps = ["react", "react-dom", "tailwindcss"]

    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for comp in components:
            zf.writestr(f"src/components/{comp['filename']}", comp["code"])

        zf.writestr("src/App.tsx", index_tsx)
        zf.writestr("tailwind.config.ts", _render_tailwind_config(tailwind_theme))
        zf.writestr("package.json", _render_package_json(runtime_deps, versions))

    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def convert_html_to_react_zip(
    html_content: str,
    screen_name: str,
    design_system: dict | None = None,
) -> bytes:
    """Convert Stitch-generated HTML into a modular React/TypeScript ZIP archive.

    Calls Gemini Flash with structured output to decompose the HTML into named
    TSX components and extract a Tailwind theme. npm versions for package.json
    are resolved live from the registry (with fallbacks on error).

    Args:
        html_content: Raw HTML string from Stitch / Supabase Storage.
        screen_name: Human-readable screen name used in the Gemini prompt.
        design_system: Optional design system dict injected into the prompt
                       for visual consistency (mirrors project pattern).

    Returns:
        In-memory ZIP bytes containing src/components/*.tsx, src/App.tsx,
        tailwind.config.ts, and package.json.

    Raises:
        RuntimeError: if google-genai is not available.
        Exception: propagates Gemini API errors to the caller.
    """
    if genai is None:  # pragma: no cover
        raise RuntimeError(
            "convert_html_to_react_zip: google-genai is not installed. "
            "Run `uv add google-genai` to enable React conversion."
        )

    design_context = ""
    if design_system:
        design_context = f"\n\nDesign system: {json.dumps(design_system)}"

    prompt = (
        f"Convert this HTML to modular React TypeScript components with Tailwind CSS.\n"
        f"Extract inline styles into Tailwind classes where possible.\n"
        f"Return structured JSON matching the provided schema.\n"
        f"\nScreen name: {screen_name}{design_context}\n\nHTML:\n{html_content}"
    )

    client = genai.Client()
    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=REACT_CONVERTER_SCHEMA,
        ),
    )

    result = json.loads(response.text)
    components: list[dict] = result.get("components", [])
    tailwind_theme: dict = result.get("tailwind_theme", {})
    index_tsx: str = result.get(
        "index_tsx", "export default function App() { return null; }"
    )

    # Resolve npm versions concurrently
    packages = [
        "react",
        "react-dom",
        "tailwindcss",
        "typescript",
        "@types/react",
        "@types/react-dom",
    ]
    resolved = await asyncio.gather(*[resolve_npm_version(pkg) for pkg in packages])
    versions = dict(zip(packages, resolved, strict=True))

    logger.info(
        "convert_html_to_react_zip: screen=%s components=%d resolved_versions=%s",
        screen_name,
        len(components),
        versions,
    )

    return _build_react_zip(components, tailwind_theme, index_tsx, versions)
