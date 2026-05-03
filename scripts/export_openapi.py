"""Export the FastAPI OpenAPI schema to stdout as JSON.

This script is called by the frontend codegen script to extract the schema
without running the backend server.

Uses FastAPI's TestClient (httpx + Starlette ASGI in-process) to hit
/openapi.json, which is the same endpoint the running server would serve.
This sidesteps the Pydantic v2 + `from __future__ import annotations`
forward-reference issue that affects direct app.openapi() calls.
"""

import json
import sys


def main() -> None:
    """Import app, spin up test client, hit /openapi.json, print to stdout."""
    try:
        from fastapi.testclient import TestClient  # noqa: PLC0415
    except ImportError:
        print("ERROR: fastapi[testclient] (httpx) not available in the venv.", file=sys.stderr)
        sys.exit(1)

    from app.fast_api_app import app  # noqa: PLC0415

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/openapi.json")

    if response.status_code != 200:
        print(f"ERROR: /openapi.json returned HTTP {response.status_code}", file=sys.stderr)
        print(response.text[:2000], file=sys.stderr)
        sys.exit(1)

    print(response.text)


if __name__ == "__main__":
    main()
