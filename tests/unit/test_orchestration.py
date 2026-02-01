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

"""Unit tests for orchestration tools."""

import pytest
from unittest.mock import patch, MagicMock


class TestGetAvailableAgents:
    """Tests for get_available_agents tool."""

    def test_returns_agent_list(self):
        """Test that get_available_agents returns a list of agents."""
        from app.orchestration.tools import get_available_agents
        
        result = get_available_agents()
        
        assert "agents" in result
        assert isinstance(result["agents"], list)
        assert len(result["agents"]) > 0

    def test_agents_have_required_fields(self):
        """Test that each agent has name and role fields."""
        from app.orchestration.tools import get_available_agents
        
        result = get_available_agents()
        
        for agent in result["agents"]:
            assert "name" in agent
            assert "role" in agent


class TestDelegateToAgent:
    """Tests for delegate_to_agent tool."""

    def test_delegate_to_valid_agent_succeeds(self):
        """Test that delegating to a valid agent returns success."""
        from app.orchestration.tools import delegate_to_agent
        
        result = delegate_to_agent(
            agent_name="Financial Analysis Agent",
            task_description="Analyze Q4 revenue"
        )
        
        assert result["success"] is True
        assert result["agent"] == "Financial Analysis Agent"
        assert "status" in result

    def test_delegate_to_invalid_agent_fails(self):
        """Test that delegating to an invalid agent returns error."""
        from app.orchestration.tools import delegate_to_agent
        
        result = delegate_to_agent(
            agent_name="Nonexistent Agent",
            task_description="Do something"
        )
        
        assert result["success"] is False
        assert "error" in result


class TestRequestAgentConsensus:
    """Tests for request_agent_consensus tool."""

    def test_consensus_with_valid_agents(self):
        """Test requesting consensus from valid agents."""
        from app.orchestration.tools import request_agent_consensus
        
        result = request_agent_consensus(
            question="Should we expand to new market?",
            agent_names=["Financial Analysis Agent", "Strategic Planning Agent"]
        )
        
        assert "question" in result
        assert "agents_consulted" in result

    def test_consensus_with_no_agents_fails(self):
        """Test that consensus with no agents returns error."""
        from app.orchestration.tools import request_agent_consensus
        
        result = request_agent_consensus(
            question="Any question",
            agent_names=[]
        )
        
        assert "error" in result

    def test_consensus_with_invalid_agent_fails(self):
        """Test that consensus with invalid agent returns error."""
        from app.orchestration.tools import request_agent_consensus
        
        result = request_agent_consensus(
            question="Any question",
            agent_names=["Fake Agent"]
        )
        
        assert "error" in result
