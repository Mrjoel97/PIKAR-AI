from app.personas.policy_registry import get_persona_policy, list_persona_policies, normalize_persona
from app.personas.prompt_fragments import build_agent_persona_fragment, resolve_agent_name



def test_all_supported_persona_policies_are_registered() -> None:
    policies = list_persona_policies()

    assert set(policies) == {"solopreneur", "startup", "sme", "enterprise"}
    for policy in policies.values():
        assert policy.core_objectives
        assert policy.default_kpis
        assert policy.planning_horizon
        assert policy.output_contract
        assert policy.delegation_style
        assert policy.preferred_agents
        assert policy.routing_priorities
        assert policy.anti_patterns



def test_startup_policy_contains_growth_execution_contract() -> None:
    policy = get_persona_policy("startup")

    assert policy is not None
    assert "MRR growth" in policy.default_kpis
    assert "hypothesis" in policy.output_contract.lower() or "experiment" in policy.output_contract.lower()
    assert any(agent == "FinancialAnalysisAgent" for agent in policy.preferred_agents)



def test_normalize_persona_rejects_unknown_values() -> None:
    assert normalize_persona("SME") == "sme"
    assert normalize_persona("unknown") is None



def test_agent_aliases_resolve_to_top_level_persona_guidance() -> None:
    assert resolve_agent_name("VideoDirectorAgent") == "ContentCreationAgent"
    fragment = build_agent_persona_fragment("VideoDirectorAgent", "solopreneur")
    assert "repurposing" in fragment.lower() or "publishing" in fragment.lower()