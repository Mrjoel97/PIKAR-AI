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

    # Save and restore the module so popping it here doesn't change class
    # identity for tests that ran first and cached `from ...types import X`.
    # Without restore, isinstance checks in later tests would fail because
    # the reloaded module produces a different class object.
    original = sys.modules.get("app.agents.runtime.types")
    sys.modules.pop("app.agents.runtime.types", None)
    try:
        import app.agents.runtime  # noqa: F401

        assert "app.agents.runtime.types" not in sys.modules
    finally:
        if original is not None:
            sys.modules["app.agents.runtime.types"] = original
