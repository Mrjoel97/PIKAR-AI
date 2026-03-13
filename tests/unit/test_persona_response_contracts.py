from app.personas.prompt_fragments import build_delegation_handoff_fragment
from app.services.user_agent_factory import build_runtime_personalization_block



def test_financial_persona_blocks_diverge_materially_by_persona() -> None:
    blocks = {
        persona: build_runtime_personalization_block(
            {"persona": persona},
            agent_name="FinancialAnalysisAgent",
        )
        for persona in ("solopreneur", "startup", "sme", "enterprise")
    }

    assert "cash snapshot" in blocks["solopreneur"].lower()
    assert "runway" in blocks["startup"].lower()
    assert "margin" in blocks["sme"].lower()
    assert "executive summary" in blocks["enterprise"].lower()



def test_operations_delegation_handoff_carries_output_contract_and_role_shape() -> None:
    handoff = build_delegation_handoff_fragment("enterprise", "OperationsOptimizationAgent")

    assert "Planning horizon:" in handoff
    assert "Output contract:" in handoff
    assert "Target role focus:" in handoff
    assert "Target deliverable:" in handoff
    assert "change plan" in handoff.lower() or "rollout" in handoff.lower()