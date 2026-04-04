"""Tests for tool honesty renames.

Verifies that 7 misleadingly-named tools have been renamed to honest
names that reflect their actual behavior (providing guidance/knowledge
rather than performing real-world actions).
"""

import importlib
import subprocess
import sys

import pytest


# =============================================================================
# Individual rename tests
# =============================================================================


class TestToolRenames:
    """Each renamed tool can be imported by its new name and the old name is gone."""

    def test_hubspot_renamed(self):
        """manage_hubspot -> hubspot_setup_guide."""
        from app.agents.enhanced_tools import hubspot_setup_guide  # noqa: F401

        import app.agents.enhanced_tools as et

        assert not hasattr(et, "manage_hubspot"), "Old name 'manage_hubspot' still exists"

    def test_security_renamed(self):
        """run_security_audit -> security_checklist."""
        from app.agents.enhanced_tools import security_checklist  # noqa: F401

        import app.agents.enhanced_tools as et

        assert not hasattr(et, "run_security_audit"), "Old name 'run_security_audit' still exists"

    def test_container_renamed(self):
        """deploy_container -> container_deployment_guide."""
        from app.agents.enhanced_tools import container_deployment_guide  # noqa: F401

        import app.agents.enhanced_tools as et

        assert not hasattr(et, "deploy_container"), "Old name 'deploy_container' still exists"

    def test_cloud_renamed(self):
        """architect_cloud_solution -> cloud_architecture_guide."""
        from app.agents.enhanced_tools import cloud_architecture_guide  # noqa: F401

        import app.agents.enhanced_tools as et

        assert not hasattr(et, "architect_cloud_solution"), (
            "Old name 'architect_cloud_solution' still exists"
        )

    def test_seo_renamed(self):
        """perform_seo_audit -> seo_fundamentals_guide."""
        from app.agents.enhanced_tools import seo_fundamentals_guide  # noqa: F401

        import app.agents.enhanced_tools as et

        assert not hasattr(et, "perform_seo_audit"), "Old name 'perform_seo_audit' still exists"

    def test_roadmap_renamed(self):
        """generate_product_roadmap -> product_roadmap_guide."""
        from app.agents.enhanced_tools import product_roadmap_guide  # noqa: F401

        import app.agents.enhanced_tools as et

        assert not hasattr(et, "generate_product_roadmap"), (
            "Old name 'generate_product_roadmap' still exists"
        )

    def test_rag_renamed(self):
        """design_rag_pipeline -> rag_architecture_guide."""
        from app.agents.enhanced_tools import rag_architecture_guide  # noqa: F401

        import app.agents.enhanced_tools as et

        assert not hasattr(et, "design_rag_pipeline"), (
            "Old name 'design_rag_pipeline' still exists"
        )


# =============================================================================
# Codebase grep test
# =============================================================================


class TestNoOldNamesInCodebase:
    """No old tool names remain anywhere in app/ directory."""

    OLD_NAMES = [
        "manage_hubspot",
        "run_security_audit",
        "deploy_container",
        "architect_cloud_solution",
        "perform_seo_audit",
        "generate_product_roadmap",
        "design_rag_pipeline",
    ]

    def test_no_old_names_in_codebase(self):
        """Grep app/ for all 7 old function names. Must return zero matches."""
        pattern = "|".join(self.OLD_NAMES)
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", pattern, "app/"],
            capture_output=True,
            text=True,
            cwd=str(importlib.import_module("app").__path__[0]).rstrip("app").rstrip("/\\"),
        )
        matches = [
            line
            for line in result.stdout.strip().split("\n")
            if line and not line.startswith("Binary")
        ]
        assert len(matches) == 0, f"Old tool names found in app/:\n" + "\n".join(matches)


# =============================================================================
# Docstring honesty tests
# =============================================================================


class TestDocstringsHonest:
    """Each renamed function's docstring uses honest language."""

    HONEST_WORDS = {"guide", "guidance", "checklist", "best practices", "fundamentals"}
    DISHONEST_WORDS = {"manage", "run", "deploy", "audit", "generate", "design", "architect"}

    def _check_docstring(self, func_name: str):
        """Check that a function's docstring uses honest language."""
        import app.agents.enhanced_tools as et

        func = getattr(et, func_name)
        doc = (func.__doc__ or "").lower()
        assert any(w in doc for w in self.HONEST_WORDS), (
            f"{func_name}.__doc__ lacks honest words (guide/guidance/checklist/best practices). "
            f"Got: {func.__doc__!r}"
        )

    def test_hubspot_docstring(self):
        self._check_docstring("hubspot_setup_guide")

    def test_security_docstring(self):
        self._check_docstring("security_checklist")

    def test_container_docstring(self):
        self._check_docstring("container_deployment_guide")

    def test_cloud_docstring(self):
        self._check_docstring("cloud_architecture_guide")

    def test_seo_docstring(self):
        self._check_docstring("seo_fundamentals_guide")

    def test_roadmap_docstring(self):
        self._check_docstring("product_roadmap_guide")

    def test_rag_docstring(self):
        self._check_docstring("rag_architecture_guide")


# =============================================================================
# Org chart tool kind classification
# =============================================================================


class TestOrgChartToolKinds:
    """Tool kind classification for org chart badges."""

    @pytest.fixture(autouse=True)
    def _patch_org_imports(self, monkeypatch):
        """Patch heavy dependencies so we can import app.routers.org in tests."""
        # The org router imports middleware.rate_limiter which reads .env at
        # module level.  We stub just enough to let the module load.
        import types

        fake_limiter_mod = types.ModuleType("app.middleware.rate_limiter")
        fake_limiter_mod.get_user_persona_limit = "10/minute"  # type: ignore[attr-defined]

        class _FakeLimiter:
            def limit(self, *a, **kw):  # noqa: ARG002
                def _decorator(fn):
                    return fn
                return _decorator

        fake_limiter_mod.limiter = _FakeLimiter()  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "app.middleware.rate_limiter", fake_limiter_mod)

        # Also stub the onboarding router dependency
        fake_onboarding_mod = types.ModuleType("app.routers.onboarding")
        fake_onboarding_mod.get_current_user_id = lambda: "test-user"  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "app.routers.onboarding", fake_onboarding_mod)

        # Clear cached module so re-import picks up our stubs
        monkeypatch.delitem(sys.modules, "app.routers.org", raising=False)

    def test_org_chart_tool_kinds(self):
        """_build_tool_kinds classifies knowledge and action tools correctly."""
        from app.routers.org import _build_tool_kinds

        result = _build_tool_kinds(["hubspot_setup_guide", "send_email"])
        assert result == {
            "hubspot_setup_guide": "knowledge",
            "send_email": "action",
        }

    def test_all_knowledge_tools_classified(self):
        """Every entry in _KNOWLEDGE_TOOLS is classified as knowledge."""
        from app.routers.org import _KNOWLEDGE_TOOLS, _build_tool_kinds

        result = _build_tool_kinds(list(_KNOWLEDGE_TOOLS))
        for tool_name in _KNOWLEDGE_TOOLS:
            assert result[tool_name] == "knowledge", (
                f"Expected '{tool_name}' to be 'knowledge', got '{result[tool_name]}'"
            )

    def test_empty_list_returns_empty_dict(self):
        """Empty tool list returns empty dict."""
        from app.routers.org import _build_tool_kinds

        assert _build_tool_kinds([]) == {}
