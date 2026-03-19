"""Skill eval dataset validation tests.

Validates that:
1. Every skill referenced in eval datasets exists in the registry
2. Each skill is accessible by the agents declared in the eval
3. Eval structure is well-formed (required fields, assertion types)
4. No duplicate eval IDs within a dataset
5. Skill knowledge content is non-empty
"""

import json
import os
import glob
import pytest
from unittest.mock import patch

from app.skills.registry import Skill, SkillsRegistry, AgentID, AGENT_ID_TO_NAME


# Map agent display names (used in evals) back to AgentID enum values
AGENT_NAME_TO_ID = {v: k for k, v in AGENT_ID_TO_NAME.items()}
# Add common aliases used in eval files
AGENT_NAME_TO_ID.update({
    "FinancialAgent": AgentID.FIN,
    "ComplianceAgent": AgentID.LEGAL,
    "ComplianceRiskAgent": AgentID.LEGAL,
    "MarketingAgent": AgentID.MKT,
    "SalesAgent": AgentID.SALES,
    "ContentAgent": AgentID.CONT,
    "StrategicAgent": AgentID.STRAT,
    "DataAgent": AgentID.DATA,
    "HRAgent": AgentID.HR,
    "OperationsAgent": AgentID.OPS,
    "ExecutiveAgent": AgentID.EXEC,
    "CustomerSupportAgent": AgentID.SUPP,
    # Full names from registry
    "FinancialAnalysisAgent": AgentID.FIN,
    "ContentCreationAgent": AgentID.CONT,
    "StrategicPlanningAgent": AgentID.STRAT,
    "SalesIntelligenceAgent": AgentID.SALES,
    "MarketingAutomationAgent": AgentID.MKT,
    "OperationsOptimizationAgent": AgentID.OPS,
    "HRRecruitmentAgent": AgentID.HR,
    "DataAnalysisAgent": AgentID.DATA,
})

EVAL_DIR = os.path.join(os.path.dirname(__file__), "..", "eval_datasets")
VALID_ASSERTION_TYPES = {"behavior", "tool_use"}


def _load_eval_datasets():
    """Load all skill eval JSON files."""
    datasets = []
    for path in sorted(glob.glob(os.path.join(EVAL_DIR, "skills_*.json"))):
        with open(path) as f:
            data = json.load(f)
        datasets.append((os.path.basename(path), data))
    return datasets


def _get_registry_with_professional_skills():
    """Build a fresh registry loaded with professional skills only."""
    # Reset singleton for isolated testing
    SkillsRegistry._instance = None
    registry = SkillsRegistry()

    # Import all professional skill modules
    from app.skills.professional_finance_legal import (
        financial_statements_generation,
        variance_analysis,
        journal_entry_preparation,
        month_end_close_management,
        account_reconciliation,
        sox_testing_methodology,
        audit_support_framework,
        contract_review_framework,
        nda_triage,
        legal_risk_assessment,
        compliance_check_framework,
        vendor_agreement_check,
        e_signature_routing,
        legal_meeting_briefing,
        legal_inquiry_response,
        legal_briefing_generation,
    )
    from app.skills.professional_marketing_sales import (
        campaign_planning,
        email_sequence_design,
        marketing_performance_report,
        competitive_brief_generation,
        brand_voice_review,
        seo_audit_comprehensive,
        account_research,
        outreach_drafting,
        call_preparation,
        call_summary_processing,
        pipeline_review,
        sales_forecasting,
        competitive_intelligence_battlecard,
        sales_asset_creation,
    )
    from app.skills.professional_operations_data import (
        process_documentation,
        compliance_tracking,
        change_management_request,
        capacity_planning,
        vendor_review_framework,
        status_report_generation,
        operational_runbook,
        operational_risk_assessment,
        process_optimization,
        sql_query_writing,
        data_exploration,
        statistical_analysis_methods,
        data_visualization_best_practices,
        data_validation_qa,
        dashboard_building,
        data_analysis_workflow,
    )
    from app.skills.professional_pm_productivity_content import (
        product_spec_writing,
        user_research_synthesis,
        stakeholder_update,
        sprint_planning,
        product_roadmap_management,
        product_metrics_review,
        product_competitive_brief,
        task_prioritization,
        meeting_management,
        goal_setting_framework,
        project_status_tracking,
        content_strategy,
        copywriting_frameworks,
        design_system_guidelines,
        video_content_strategy,
        content_distribution,
    )

    # Register all skills
    all_skills = [
        # Finance & Legal
        financial_statements_generation, variance_analysis,
        journal_entry_preparation, month_end_close_management,
        account_reconciliation, sox_testing_methodology,
        audit_support_framework, contract_review_framework,
        nda_triage, legal_risk_assessment, compliance_check_framework,
        vendor_agreement_check, e_signature_routing,
        legal_meeting_briefing, legal_inquiry_response,
        legal_briefing_generation,
        # Marketing & Sales
        campaign_planning, email_sequence_design,
        marketing_performance_report, competitive_brief_generation,
        brand_voice_review, seo_audit_comprehensive,
        account_research, outreach_drafting, call_preparation,
        call_summary_processing, pipeline_review, sales_forecasting,
        competitive_intelligence_battlecard, sales_asset_creation,
        # Operations & Data
        process_documentation, compliance_tracking,
        change_management_request, capacity_planning,
        vendor_review_framework, status_report_generation,
        operational_runbook, operational_risk_assessment,
        process_optimization, sql_query_writing, data_exploration,
        statistical_analysis_methods, data_visualization_best_practices,
        data_validation_qa, dashboard_building, data_analysis_workflow,
        # PM, Productivity & Content
        product_spec_writing, user_research_synthesis,
        stakeholder_update, sprint_planning, product_roadmap_management,
        product_metrics_review, product_competitive_brief,
        task_prioritization, meeting_management,
        goal_setting_framework, project_status_tracking,
        content_strategy, copywriting_frameworks,
        design_system_guidelines, video_content_strategy,
        content_distribution,
    ]

    for skill in all_skills:
        registry.register(skill)

    return registry


@pytest.fixture(scope="module")
def registry():
    """Module-scoped registry with all professional skills loaded."""
    return _get_registry_with_professional_skills()


@pytest.fixture(scope="module")
def eval_datasets():
    """Module-scoped eval datasets."""
    return _load_eval_datasets()


class TestEvalDatasetStructure:
    """Validate eval dataset file structure."""

    def test_eval_files_exist(self):
        datasets = _load_eval_datasets()
        assert len(datasets) >= 4, f"Expected at least 4 eval files, found {len(datasets)}"

    @pytest.mark.parametrize("filename,data", _load_eval_datasets())
    def test_required_top_level_fields(self, filename, data):
        assert "domain" in data, f"{filename}: missing 'domain' field"
        assert "evals" in data, f"{filename}: missing 'evals' field"
        assert isinstance(data["evals"], list), f"{filename}: 'evals' must be a list"
        assert len(data["evals"]) > 0, f"{filename}: 'evals' must not be empty"

    @pytest.mark.parametrize("filename,data", _load_eval_datasets())
    def test_no_duplicate_ids(self, filename, data):
        ids = [e["id"] for e in data["evals"]]
        assert len(ids) == len(set(ids)), f"{filename}: duplicate eval IDs found"

    @pytest.mark.parametrize("filename,data", _load_eval_datasets())
    def test_eval_required_fields(self, filename, data):
        for eval_item in data["evals"]:
            eval_id = eval_item.get("id", "?")
            assert "id" in eval_item, f"{filename}[{eval_id}]: missing 'id'"
            assert "skill_name" in eval_item, f"{filename}[{eval_id}]: missing 'skill_name'"
            assert "prompt" in eval_item, f"{filename}[{eval_id}]: missing 'prompt'"
            assert "expected_output" in eval_item, f"{filename}[{eval_id}]: missing 'expected_output'"
            assert len(eval_item["prompt"]) > 10, f"{filename}[{eval_id}]: prompt too short"
            assert len(eval_item["expected_output"]) > 20, f"{filename}[{eval_id}]: expected_output too short"

    @pytest.mark.parametrize("filename,data", _load_eval_datasets())
    def test_assertions_well_formed(self, filename, data):
        for eval_item in data["evals"]:
            eval_id = eval_item.get("id", "?")
            assertions = eval_item.get("assertions", [])
            assert len(assertions) >= 2, (
                f"{filename}[{eval_id}]: needs at least 2 assertions (1 tool_use + 1 behavior)"
            )
            types_found = set()
            for assertion in assertions:
                assert "text" in assertion, f"{filename}[{eval_id}]: assertion missing 'text'"
                assert "type" in assertion, f"{filename}[{eval_id}]: assertion missing 'type'"
                assert assertion["type"] in VALID_ASSERTION_TYPES, (
                    f"{filename}[{eval_id}]: invalid assertion type '{assertion['type']}'"
                )
                types_found.add(assertion["type"])
            assert "tool_use" in types_found, (
                f"{filename}[{eval_id}]: must have at least one tool_use assertion"
            )
            assert "behavior" in types_found, (
                f"{filename}[{eval_id}]: must have at least one behavior assertion"
            )


class TestSkillRegistryAlignment:
    """Validate that eval datasets reference skills that exist in the registry."""

    @pytest.mark.parametrize("filename,data", _load_eval_datasets())
    def test_all_skills_exist_in_registry(self, filename, data, registry):
        missing = []
        for eval_item in data["evals"]:
            skill_name = eval_item["skill_name"]
            skill = registry.get(skill_name)
            if skill is None:
                missing.append(skill_name)
        assert not missing, (
            f"{filename}: skills not found in registry: {sorted(set(missing))}"
        )

    @pytest.mark.parametrize("filename,data", _load_eval_datasets())
    def test_skills_have_knowledge(self, filename, data, registry):
        empty = []
        for eval_item in data["evals"]:
            skill_name = eval_item["skill_name"]
            skill = registry.get(skill_name)
            if skill and not skill.knowledge:
                empty.append(skill_name)
        unique_empty = sorted(set(empty))
        assert not unique_empty, (
            f"{filename}: skills with empty knowledge: {unique_empty}"
        )

    @pytest.mark.parametrize("filename,data", _load_eval_datasets())
    def test_agent_can_access_skill(self, filename, data, registry):
        """Verify the eval's declared agent has access to the skill."""
        access_errors = []
        for eval_item in data["evals"]:
            skill_name = eval_item["skill_name"]
            agent_name = eval_item.get("agent")
            if not agent_name:
                continue

            skill = registry.get(skill_name)
            if not skill:
                continue

            # Skills with empty agent_ids are available to all agents
            if not skill.agent_ids:
                continue

            agent_id = AGENT_NAME_TO_ID.get(agent_name)
            if agent_id and agent_id not in skill.agent_ids:
                access_errors.append(
                    f"eval {eval_item['id']}: agent '{agent_name}' ({agent_id}) "
                    f"cannot access skill '{skill_name}' "
                    f"(allowed: {[a.value for a in skill.agent_ids]})"
                )

        assert not access_errors, (
            f"{filename}: agent access violations:\n" + "\n".join(access_errors)
        )


class TestEvalCoverage:
    """Verify that eval datasets cover all professional skills."""

    def test_all_professional_skills_have_evals(self, registry, eval_datasets):
        """Every registered professional skill should have at least one eval."""
        all_eval_skills = set()
        for _, data in eval_datasets:
            for eval_item in data["evals"]:
                all_eval_skills.add(eval_item["skill_name"])

        registered_skills = set(registry.list_names())
        missing = registered_skills - all_eval_skills
        assert not missing, (
            f"Skills without evals: {sorted(missing)}"
        )

    def test_minimum_evals_per_skill(self, eval_datasets):
        """Each skill should have at least 2 eval prompts."""
        skill_counts = {}
        for _, data in eval_datasets:
            for eval_item in data["evals"]:
                name = eval_item["skill_name"]
                skill_counts[name] = skill_counts.get(name, 0) + 1

        undercovered = {k: v for k, v in skill_counts.items() if v < 2}
        assert not undercovered, (
            f"Skills with fewer than 2 evals: {undercovered}"
        )

    def test_total_eval_count(self, eval_datasets):
        """Sanity check: should have 150+ evals total."""
        total = sum(len(data["evals"]) for _, data in eval_datasets)
        assert total >= 150, f"Expected 150+ evals, found {total}"
