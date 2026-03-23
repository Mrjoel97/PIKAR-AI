"""Capacitor Generator — produces a downloadable Capacitor project scaffold ZIP.

Generates a 4-file scaffold that a developer can unzip and immediately run:
  npm install && npx cap add ios && npx cap add android

npm versions are resolved from the npm registry at generation time, with local
fallbacks so generation succeeds even when the registry is unreachable.

No cross-service imports — npm resolution is fully self-contained in this module
to avoid circular imports between Plan 01 (react_converter) and Plan 02 when both
run in the same wave.
"""

import asyncio
import io
import json
import re
import zipfile

import httpx

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_NPM_REGISTRY = "https://registry.npmjs.org"

_CAPACITOR_FALLBACK_VERSIONS: dict[str, str] = {
    "@capacitor/core": "7.0.0",
    "@capacitor/cli": "7.0.0",
    "@capacitor/ios": "7.0.0",
    "@capacitor/android": "7.0.0",
}

_CAPACITOR_PACKAGES = list(_CAPACITOR_FALLBACK_VERSIONS.keys())

# ---------------------------------------------------------------------------
# npm version resolution (self-contained — do NOT import from react_converter)
# ---------------------------------------------------------------------------


async def _resolve_npm_version(package: str) -> str:
    """Resolve current stable version from npm registry; return fallback on error.

    Args:
        package: npm package name (e.g. ``@capacitor/core``).

    Returns:
        Version string such as ``"7.2.0"``, or the fallback if registry is
        unreachable or the package is unknown.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{_NPM_REGISTRY}/{package}",
                params={"fields": "dist-tags"},
            )
            resp.raise_for_status()
            data = resp.json()
            return data["dist-tags"]["latest"]
    except Exception:
        return _CAPACITOR_FALLBACK_VERSIONS.get(package, "latest")


# ---------------------------------------------------------------------------
# Slug / appId helpers
# ---------------------------------------------------------------------------


def _slugify(name: str) -> str:
    """Convert an app name to a URL/ID-safe slug.

    Args:
        name: Human-readable app name (e.g. ``"My Cool App"``).

    Returns:
        Lowercase slug with hyphens (e.g. ``"my-cool-app"``).
    """
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def _derive_app_id(app_name: str) -> str:
    """Derive a reverse-domain appId from the app name.

    Args:
        app_name: Human-readable app name.

    Returns:
        Reverse-domain string e.g. ``"com.pikar.my-cool-app"``.
    """
    return f"com.pikar.{_slugify(app_name)}"


# ---------------------------------------------------------------------------
# File renderers
# ---------------------------------------------------------------------------


def _render_cap_config(app_name: str, app_id: str) -> str:
    """Render a capacitor.config.ts with the given appId and appName.

    Args:
        app_name: Human-readable name shown in device settings.
        app_id: Reverse-domain identifier (e.g. ``"com.pikar.my-app"``).

    Returns:
        Full TypeScript source string.
    """
    return f"""\
import type {{ CapacitorConfig }} from '@capacitor/cli';

const config: CapacitorConfig = {{
  appId: '{app_id}',
  appName: '{app_name}',
  webDir: 'www',
  server: {{
    androidScheme: 'https',
  }},
}};

export default config;
"""


def _render_cap_package_json(app_name: str, versions: dict[str, str]) -> str:
    """Render a package.json for the Capacitor scaffold.

    Args:
        app_name: Used as the ``name`` field (slugified).
        versions: Mapping of Capacitor package names to resolved versions.

    Returns:
        JSON string.
    """
    pkg = {
        "name": _slugify(app_name),
        "version": "1.0.0",
        "scripts": {
            "build": "echo 'Copy your web app build output to www/'",
            "cap:add:ios": "npx cap add ios",
            "cap:add:android": "npx cap add android",
            "cap:sync": "npx cap sync",
        },
        "dependencies": {
            "@capacitor/core": versions.get("@capacitor/core", "latest"),
            "@capacitor/ios": versions.get("@capacitor/ios", "latest"),
            "@capacitor/android": versions.get("@capacitor/android", "latest"),
        },
        "devDependencies": {
            "@capacitor/cli": versions.get("@capacitor/cli", "latest"),
        },
    }
    return json.dumps(pkg, indent=2)


def _render_cap_readme(app_name: str) -> str:
    """Render a README.md with developer setup instructions.

    Args:
        app_name: Human-readable name used in headings.

    Returns:
        Markdown string.
    """
    return f"""\
# {app_name} — Capacitor Project

Generated by [Pikar AI](https://pikar.ai). Follow the steps below to add iOS
and Android targets.

## Prerequisites

- Node.js >= 18
- Xcode (for iOS)
- Android Studio (for Android)

## Setup

```bash
# 1. Install dependencies
npm install

# 2. Add platform targets
npx cap add ios
npx cap add android

# 3. Sync web assets into the native projects
npx cap sync
```

## Web Assets

Your compiled web app should be placed in the `www/` directory before
running `npx cap sync`. The generated `www/index.html` is a starting
point — replace it with your production build output.

## Opening in IDEs

```bash
# Open in Xcode
npx cap open ios

# Open in Android Studio
npx cap open android
```
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_capacitor_zip(app_name: str, html_content: str) -> bytes:
    """Generate an in-memory ZIP containing a Capacitor project scaffold.

    Produces four files:
    - ``capacitor.config.ts`` — Capacitor config with appId and webDir.
    - ``package.json`` — Capacitor dependencies with versions resolved from npm.
    - ``www/index.html`` — Starter web content (replace with production build).
    - ``README.md`` — Developer instructions for adding iOS/Android targets.

    Args:
        app_name: Human-readable app name used for appId derivation and appName.
        html_content: HTML to embed in ``www/index.html``.

    Returns:
        Raw ZIP bytes suitable for direct download or Supabase Storage upload.
    """
    app_id = _derive_app_id(app_name)

    # Resolve all four Capacitor package versions concurrently
    resolved = await asyncio.gather(
        *[_resolve_npm_version(pkg) for pkg in _CAPACITOR_PACKAGES]
    )
    versions: dict[str, str] = dict(zip(_CAPACITOR_PACKAGES, resolved, strict=True))

    cap_config = _render_cap_config(app_name, app_id)
    package_json = _render_cap_package_json(app_name, versions)
    readme = _render_cap_readme(app_name)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("capacitor.config.ts", cap_config)
        zf.writestr("package.json", package_json)
        zf.writestr("www/index.html", html_content)
        zf.writestr("README.md", readme)
    buf.seek(0)
    return buf.read()
