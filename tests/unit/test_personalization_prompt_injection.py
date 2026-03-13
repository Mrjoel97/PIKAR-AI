from types import SimpleNamespace

from app.agents.context_extractor import (
    USER_AGENT_PERSONALIZATION_STATE_KEY,
    USER_CONTEXT_STATE_KEY,
    context_memory_before_model_callback,
)
from app.services.user_agent_factory import build_runtime_personalization_block


class DummyConfig:
    def __init__(self, system_instruction: str = "BASE") -> None:
        self.system_instruction = system_instruction


class DummyRequest:
    def __init__(self, system_instruction: str = "BASE") -> None:
        self.config = DummyConfig(system_instruction)
        self.contents = []


class DummyContext(SimpleNamespace):
    pass


def test_runtime_personalization_block_includes_agent_specific_guidance() -> None:
    block = build_runtime_personalization_block(
        {
            "persona": "startup",
            "business_context": {"company_name": "Acme", "goals": ["Grow MRR"]},
            "preferences": {"tone": "direct", "verbosity": "concise"},
        },
        agent_name="FinancialAnalysisAgent",
    )

    assert "ACTIVE PERSONA POLICY: STARTUP" in block
    assert "Company: Acme" in block
    assert "Tone: direct" in block
    assert "Output contract:" in block
    assert "[DELEGATION CONTRACT]" in block
    assert "runway" in block.lower() or "growth efficiency" in block.lower()


def test_context_extractor_appends_personalization_and_memory() -> None:
    callback_context = DummyContext(
        state={
            USER_AGENT_PERSONALIZATION_STATE_KEY: {
                "persona": "sme",
                "business_context": {"company_name": "Northwind"},
            },
            USER_CONTEXT_STATE_KEY: {"industry": "Manufacturing"},
        },
        agent_name="OperationsOptimizationAgent",
    )
    llm_request = DummyRequest()

    result = context_memory_before_model_callback(callback_context, llm_request)

    assert result is None
    assert "USER PERSONALIZATION PROFILE" in llm_request.config.system_instruction
    assert "ACTIVE PERSONA POLICY: SME" in llm_request.config.system_instruction
    assert "[DELEGATION CONTRACT]" in llm_request.config.system_instruction
    assert "REMEMBERED USER CONTEXT" in llm_request.config.system_instruction
    assert "Manufacturing" in llm_request.config.system_instruction


def test_root_prompt_override_applies_only_to_executive_agent() -> None:
    callback_context = DummyContext(
        state={
            USER_AGENT_PERSONALIZATION_STATE_KEY: {
                "persona": "enterprise",
                "system_prompt_override": "CUSTOM EXECUTIVE ROOT",
            }
        },
        agent_name="ExecutiveAgent",
    )
    llm_request = DummyRequest("BASE")

    context_memory_before_model_callback(callback_context, llm_request)

    assert llm_request.config.system_instruction.startswith("CUSTOM EXECUTIVE ROOT")
