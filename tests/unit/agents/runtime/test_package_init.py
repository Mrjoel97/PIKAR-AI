# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Smoke test: the runtime package is importable."""

from __future__ import annotations


def test_runtime_package_is_importable():
    import importlib

    mod = importlib.import_module("app.agents.runtime")
    assert mod.__name__ == "app.agents.runtime"


def test_runtime_package_is_a_namespace_for_submodules():
    # Importing the package must not eagerly import submodules
    # (those have heavy deps and would slow agent start-up).
    import sys

    sys.modules.pop("app.agents.runtime.types", None)
    import app.agents.runtime  # noqa: F401

    assert "app.agents.runtime.types" not in sys.modules
