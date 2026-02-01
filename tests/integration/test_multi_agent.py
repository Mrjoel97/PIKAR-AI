# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Integration tests for the multi-agent system.

Tests end-to-end workflows, agent delegation, and orchestration patterns.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestAgentIntegration:
    """Tests for agent integration and delegation."""

    def test_executive_agent_has_all_required_tools(self):
        """Test that the Executive Agent has all required tools configured."""
        from app.agent import executive_agent
        
        tool_names = [tool.__name__ if hasattr(tool, '__name__') else str(tool) 
                      for tool in executive_agent.tools]
        
        # Verify core business tools
        assert "get_revenue_stats" in tool_names
        assert "search_business_knowledge" in tool_names
        assert "update_initiative_status" in tool_names
        assert "create_task" in tool_names
        
        # Verify orchestration tools
        assert "get_available_agents" in tool_names
        assert "delegate_to_agent" in tool_names

    def test_specialized_agents_are_defined(self):
        """Test that all 10 specialized agents are properly defined."""
        from app.agents import SPECIALIZED_AGENTS
        
        # Should have exactly 10 specialized agents
        assert len(SPECIALIZED_AGENTS) == 10
        
        agent_names = [agent.name for agent in SPECIALIZED_AGENTS]
        assert "FinancialAnalysisAgent" in agent_names
        assert "ContentCreationAgent" in agent_names
        assert "StrategicPlanningAgent" in agent_names
        assert "SalesIntelligenceAgent" in agent_names
        assert "MarketingAutomationAgent" in agent_names
        assert "OperationsOptimizationAgent" in agent_names
        assert "HRRecruitmentAgent" in agent_names
        assert "ComplianceRiskAgent" in agent_names
        assert "CustomerSupportAgent" in agent_names
        assert "DataAnalysisAgent" in agent_names

    def test_delegation_to_financial_agent(self):
        """Test delegating a task to the Financial Analysis Agent."""
        from app.orchestration.tools import delegate_to_agent
        
        result = delegate_to_agent(
            agent_name="Financial Analysis Agent",
            task_description="Analyze Q4 revenue and forecast Q1"
        )
        
        assert result["success"] is True
        assert result["status"] == "delegated"

    def test_delegation_to_content_agent(self):
        """Test delegating a task to the Content Creation Agent."""
        from app.orchestration.tools import delegate_to_agent
        
        result = delegate_to_agent(
            agent_name="Content Creation Agent",
            task_description="Create marketing copy for new product launch"
        )
        
        assert result["success"] is True

    def test_delegation_to_strategic_agent(self):
        """Test delegating a task to the Strategic Planning Agent."""
        from app.orchestration.tools import delegate_to_agent
        
        result = delegate_to_agent(
            agent_name="Strategic Planning Agent",
            task_description="Define Q2 OKRs for the product team"
        )
        
        assert result["success"] is True

    def test_delegation_to_hr_agent(self):
        """Test delegating a task to the HR & Recruitment Agent."""
        from app.orchestration.tools import delegate_to_agent
        
        result = delegate_to_agent(
            agent_name="HR & Recruitment Agent",
            task_description="Draft job description for senior engineer role"
        )
        
        assert result["success"] is True

    def test_delegation_to_compliance_agent(self):
        """Test delegating a task to the Compliance & Risk Agent."""
        from app.orchestration.tools import delegate_to_agent
        
        result = delegate_to_agent(
            agent_name="Compliance & Risk Agent",
            task_description="Review GDPR compliance for new feature"
        )
        
        assert result["success"] is True

    def test_delegation_to_customer_support_agent(self):
        """Test delegating a task to the Customer Support Agent."""
        from app.orchestration.tools import delegate_to_agent
        
        result = delegate_to_agent(
            agent_name="Customer Support Agent",
            task_description="Create knowledge base article for login issues"
        )
        
        assert result["success"] is True

    def test_delegation_to_data_agent(self):
        """Test delegating a task to the Data Analysis Agent."""
        from app.orchestration.tools import delegate_to_agent
        
        result = delegate_to_agent(
            agent_name="Data Analysis Agent",
            task_description="Analyze user engagement trends for Q4"
        )
        
        assert result["success"] is True


class TestRagIntegration:
    """Tests for RAG system integration."""

    def test_search_business_knowledge_integration(self):
        """Test that search_business_knowledge integrates with RAG."""
        from app.agent import search_business_knowledge
        
        result = search_business_knowledge("company overview")
        
        assert "results" in result or "query" in result

    def test_embedding_service_returns_correct_dimensions(self):
        """Test that embedding service returns 768-dimensional vectors."""
        from app.rag.embedding_service import generate_embedding
        
        with patch('app.rag.embedding_service.TextEmbeddingModel') as mock_model:
            mock_embedding = MagicMock()
            mock_embedding.values = [0.1] * 768
            mock_model_instance = MagicMock()
            mock_model_instance.get_embeddings.return_value = [mock_embedding]
            mock_model.from_pretrained.return_value = mock_model_instance
            
            result = generate_embedding("test text")
            
            assert len(result) == 768


class TestOrchestrationPatterns:
    """Tests for orchestration patterns."""

    def test_sequential_delegation_pattern(self):
        """Test sequential delegation to multiple agents."""
        from app.orchestration.tools import delegate_to_agent
        
        # Step 1: Research with Strategic Planning
        result1 = delegate_to_agent(
            "Strategic Planning Agent", 
            "Research market opportunity"
        )
        assert result1["success"] is True
        
        # Step 2: Create content based on research
        result2 = delegate_to_agent(
            "Content Creation Agent",
            "Create campaign content"
        )
        assert result2["success"] is True
        
        # Step 3: Plan marketing campaign
        result3 = delegate_to_agent(
            "Marketing Automation Agent",
            "Plan campaign rollout"
        )
        assert result3["success"] is True

    def test_parallel_agent_query(self):
        """Test querying multiple agents in parallel (for consensus)."""
        from app.orchestration.tools import request_agent_consensus
        
        result = request_agent_consensus(
            question="Should we expand into the European market?",
            agent_names=[
                "Financial Analysis Agent",
                "Strategic Planning Agent",
                "Sales Intelligence Agent"
            ]
        )
        
        assert "agents_consulted" in result
        assert len(result["agents_consulted"]) == 3


class TestEndToEndWorkflows:
    """End-to-end workflow tests."""

    def test_marketing_campaign_workflow(self):
        """Test a complete marketing campaign creation workflow."""
        from app.orchestration.tools import delegate_to_agent, get_available_agents
        from app.agent import search_business_knowledge, create_task
        
        # 1. Get available agents
        agents = get_available_agents()
        assert "agents" in agents
        
        # 2. Search for existing brand guidelines
        knowledge = search_business_knowledge("brand voice guidelines")
        assert "results" in knowledge or "query" in knowledge
        
        # 3. Delegate content creation
        content_result = delegate_to_agent(
            "Content Creation Agent",
            "Create social media campaign for Q1 product launch"
        )
        assert content_result["success"] is True
        
        # 4. Create tracking task
        task_result = create_task(
            description="Review marketing campaign content",
            priority="high"
        )
        assert "task_id" in task_result

    def test_financial_review_workflow(self):
        """Test a financial review workflow."""
        from app.agent import get_revenue_stats
        from app.orchestration.tools import delegate_to_agent
        
        # 1. Get current revenue stats
        stats = get_revenue_stats()
        assert "revenue" in stats
        
        # 2. Delegate detailed analysis
        analysis = delegate_to_agent(
            "Financial Analysis Agent",
            f"Analyze revenue trend: current is ${stats['revenue']}"
        )
        assert analysis["success"] is True
