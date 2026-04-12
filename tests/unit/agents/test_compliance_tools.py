"""Unit tests for compliance agent tools (generate_legal_document, explain_contract_clause).

Tests verify that:
- generate_legal_document creates privacy policies, ToS, and refund policies via LLM
- explain_contract_clause produces plain-English explanations with risk assessment
- Input validation rejects invalid doc types and empty clause text
- Gemini API errors are handled gracefully

Phase 66-02 (LEGAL-02, LEGAL-04): Legal document generation and contract clause explanation.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_genai_response(text: str) -> MagicMock:
    """Create a mock Gemini response object with .text attribute."""
    response = MagicMock()
    response.text = text
    return response


def _make_genai_mock(response_text: str) -> MagicMock:
    """Build a mock google.genai.Client whose aio.models.generate_content returns text."""
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        return_value=_mock_genai_response(response_text),
    )
    return mock_client


# ===========================================================================
# generate_legal_document tests
# ===========================================================================


class TestGenerateLegalDocument:
    """Tests for the generate_legal_document tool."""

    @pytest.fixture(autouse=True)
    def _mock_user_context(self):
        """Ensure get_current_user_id returns a test user for all tests."""
        with patch(
            "app.services.request_context.get_current_user_id",
            return_value="test-user-123",
        ):
            yield

    @pytest.mark.asyncio
    async def test_privacy_policy_generation(self):
        """generate_legal_document with doc_type='privacy_policy' returns success with document content."""
        mock_client = _make_genai_mock(
            "Privacy Policy\n\n1. Introduction\nWe at Acme Corp respect your privacy..."
        )

        with patch("app.agents.compliance.tools.genai") as mock_genai:
            mock_genai.Client.return_value = mock_client
            from app.agents.compliance.tools import generate_legal_document

            result = await generate_legal_document(
                doc_type="privacy_policy",
                business_name="Acme Corp",
                business_description="Online widget store",
                jurisdiction="United States",
            )

        assert result["success"] is True
        assert result["document_type"] == "privacy_policy"
        assert "Privacy Policy" in result["content"]
        assert result["disclaimer"] is not None

    @pytest.mark.asyncio
    async def test_terms_of_service_generation(self):
        """generate_legal_document with doc_type='terms_of_service' returns success with document content."""
        mock_client = _make_genai_mock(
            "Terms of Service\n\n1. Acceptance of Terms\nBy accessing our services..."
        )

        with patch("app.agents.compliance.tools.genai") as mock_genai:
            mock_genai.Client.return_value = mock_client
            from app.agents.compliance.tools import generate_legal_document

            result = await generate_legal_document(
                doc_type="terms_of_service",
                business_name="Acme Corp",
                business_description="SaaS platform for project management",
                jurisdiction="European Union",
            )

        assert result["success"] is True
        assert result["document_type"] == "terms_of_service"
        assert result["business_name"] == "Acme Corp"
        assert result["jurisdiction"] == "European Union"
        assert len(result["content"]) > 0

    @pytest.mark.asyncio
    async def test_refund_policy_generation(self):
        """generate_legal_document with doc_type='refund_policy' returns success with document content."""
        mock_client = _make_genai_mock(
            "Refund Policy\n\n1. Returns\nWe offer a 30-day return window..."
        )

        with patch("app.agents.compliance.tools.genai") as mock_genai:
            mock_genai.Client.return_value = mock_client
            from app.agents.compliance.tools import generate_legal_document

            result = await generate_legal_document(
                doc_type="refund_policy",
                business_name="Widget World",
                business_description="E-commerce store selling custom widgets",
                jurisdiction="United Kingdom",
            )

        assert result["success"] is True
        assert result["document_type"] == "refund_policy"
        assert result["business_name"] == "Widget World"
        assert result["jurisdiction"] == "United Kingdom"
        assert len(result["content"]) > 0

    @pytest.mark.asyncio
    async def test_invalid_doc_type_returns_error(self):
        """generate_legal_document with invalid doc_type returns error without calling LLM."""
        from app.agents.compliance.tools import generate_legal_document

        result = await generate_legal_document(
            doc_type="employment_contract",
            business_name="Acme Corp",
            business_description="Tech startup",
        )

        assert result["success"] is False
        assert "error" in result
        assert (
            "invalid" in result["error"].lower()
            or "doc_type" in result["error"].lower()
        )

    @pytest.mark.asyncio
    async def test_includes_business_name_and_jurisdiction(self):
        """generate_legal_document includes business_name and jurisdiction in output."""
        mock_client = _make_genai_mock("Privacy Policy for TestBiz in Australia...")

        with patch("app.agents.compliance.tools.genai") as mock_genai:
            mock_genai.Client.return_value = mock_client
            from app.agents.compliance.tools import generate_legal_document

            result = await generate_legal_document(
                doc_type="privacy_policy",
                business_name="TestBiz",
                business_description="Consulting firm",
                jurisdiction="Australia",
            )

        assert result["success"] is True
        assert result["business_name"] == "TestBiz"
        assert result["jurisdiction"] == "Australia"

    @pytest.mark.asyncio
    async def test_genai_error_returns_error_dict(self):
        """generate_legal_document returns error dict when Gemini API fails."""
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=RuntimeError("Gemini quota exceeded"),
        )

        with patch("app.agents.compliance.tools.genai") as mock_genai:
            mock_genai.Client.return_value = mock_client
            from app.agents.compliance.tools import generate_legal_document

            result = await generate_legal_document(
                doc_type="privacy_policy",
                business_name="Acme Corp",
                business_description="Test",
            )

        assert result["success"] is False
        assert "Gemini quota exceeded" in result["error"]


# ===========================================================================
# explain_contract_clause tests
# ===========================================================================


class TestExplainContractClause:
    """Tests for the explain_contract_clause tool."""

    @pytest.fixture(autouse=True)
    def _mock_user_context(self):
        """Ensure get_current_user_id returns a test user for all tests."""
        with patch(
            "app.services.request_context.get_current_user_id",
            return_value="test-user-123",
        ):
            yield

    @pytest.mark.asyncio
    async def test_clause_explanation_returns_dict(self):
        """explain_contract_clause with a sample clause returns a plain-English explanation dict."""
        llm_response = (
            '{"explanation": "This clause requires you to compensate the other party for any losses.'
            '", "implications": ["You must pay for damages caused by your actions", '
            '"Coverage extends to legal fees"], "risk_level": "high", '
            '"watch_items": ["Unlimited liability exposure", "No cap on damages"]}'
        )
        mock_client = _make_genai_mock(llm_response)

        with patch("app.agents.compliance.tools.genai") as mock_genai:
            mock_genai.Client.return_value = mock_client
            from app.agents.compliance.tools import explain_contract_clause

            result = await explain_contract_clause(
                clause_text="The Contractor shall indemnify and hold harmless the Client from any and all claims.",
            )

        assert result["success"] is True
        assert "explanation" in result
        assert isinstance(result["explanation"], str)
        assert len(result["explanation"]) > 0

    @pytest.mark.asyncio
    async def test_clause_returns_implications_and_risk_level(self):
        """explain_contract_clause returns implications and risk_level fields."""
        llm_response = (
            '{"explanation": "This clause means both parties agree not to sue each other.'
            '", "implications": ["You waive your right to sue", "Dispute resolution limited to arbitration"], '
            '"risk_level": "medium", '
            '"watch_items": ["Arbitration may be costly"]}'
        )
        mock_client = _make_genai_mock(llm_response)

        with patch("app.agents.compliance.tools.genai") as mock_genai:
            mock_genai.Client.return_value = mock_client
            from app.agents.compliance.tools import explain_contract_clause

            result = await explain_contract_clause(
                clause_text="Both parties agree to resolve disputes through binding arbitration.",
                contract_type="service_agreement",
            )

        assert result["success"] is True
        assert "implications" in result
        assert isinstance(result["implications"], list)
        assert len(result["implications"]) > 0
        assert "risk_level" in result
        assert result["risk_level"] in ("low", "medium", "high")
        assert "watch_items" in result

    @pytest.mark.asyncio
    async def test_empty_clause_returns_error(self):
        """explain_contract_clause handles empty/whitespace clause input with error."""
        from app.agents.compliance.tools import explain_contract_clause

        result = await explain_contract_clause(clause_text="   ")

        assert result["success"] is False
        assert "error" in result
        assert "empty" in result["error"].lower() or "clause" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_genai_error_returns_error_dict(self):
        """explain_contract_clause returns error dict when Gemini API fails."""
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=RuntimeError("Model unavailable"),
        )

        with patch("app.agents.compliance.tools.genai") as mock_genai:
            mock_genai.Client.return_value = mock_client
            from app.agents.compliance.tools import explain_contract_clause

            result = await explain_contract_clause(
                clause_text="The tenant shall not sublease without written consent.",
            )

        assert result["success"] is False
        assert "Model unavailable" in result["error"]

    @pytest.mark.asyncio
    async def test_clause_text_truncated_in_response(self):
        """explain_contract_clause truncates long clause_text in the response to 500 chars."""
        long_clause = "A" * 1000
        llm_response = (
            '{"explanation": "Placeholder.", "implications": [], '
            '"risk_level": "low", "watch_items": []}'
        )
        mock_client = _make_genai_mock(llm_response)

        with patch("app.agents.compliance.tools.genai") as mock_genai:
            mock_genai.Client.return_value = mock_client
            from app.agents.compliance.tools import explain_contract_clause

            result = await explain_contract_clause(clause_text=long_clause)

        assert result["success"] is True
        assert len(result["clause_text"]) <= 503  # 500 + "..."
