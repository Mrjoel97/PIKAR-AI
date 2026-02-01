"""Unit tests for ComplianceService.

Tests CRUD operations for audits and risk assessments used by ComplianceRiskAgent.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestComplianceService:
    """Test suite for ComplianceService."""

    @pytest.fixture
    def mock_supabase_client(self):
        """Create a mock Supabase client."""
        mock_client = MagicMock()
        return mock_client

    @pytest.fixture
    def service(self, mock_supabase_client):
        """Create ComplianceService with mocked dependencies."""
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_ROLE_KEY': 'test-key'
        }):
            with patch('app.services.compliance_service.create_client') as mock_create:
                mock_create.return_value = mock_supabase_client
                from app.services.compliance_service import ComplianceService
                return ComplianceService()

    def test_initialization_success(self, service):
        """Test that service initializes correctly."""
        assert service is not None
        assert service._audits_table == "compliance_audits"
        assert service._risks_table == "compliance_risks"

    @pytest.mark.asyncio
    async def test_create_audit(self, service, mock_supabase_client):
        """Test creating an audit."""
        mock_response = MagicMock()
        mock_response.data = [{
            "id": "audit-001",
            "title": "Q1 Security Audit",
            "status": "scheduled"
        }]
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_response

        result = await service.create_audit(
            title="Q1 Security Audit",
            scope="Infrastructure",
            auditor="Internal IT",
            scheduled_date="2026-03-01"
        )
        assert result["id"] == "audit-001"
        assert result["status"] == "scheduled"

    @pytest.mark.asyncio
    async def test_get_audit(self, service, mock_supabase_client):
        """Test retrieving an audit."""
        mock_response = MagicMock()
        mock_response.data = {"id": "audit-001", "title": "Audit"}
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response

        result = await service.get_audit("audit-001")
        assert result["id"] == "audit-001"

    @pytest.mark.asyncio
    async def test_update_audit(self, service, mock_supabase_client):
        """Test updating an audit."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "audit-001", "status": "completed"}]
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response

        result = await service.update_audit("audit-001", status="completed")
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_create_risk(self, service, mock_supabase_client):
        """Test creating a risk item."""
        mock_response = MagicMock()
        mock_response.data = [{
            "id": "risk-99",
            "title": "Data Loss",
            "severity": "high"
        }]
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_response

        result = await service.create_risk(
            title="Data Loss",
            description="Server crash",
            severity="high",
            mitigation_plan="Backup daily"
        )
        assert result["id"] == "risk-99"

    @pytest.mark.asyncio
    async def test_update_risk(self, service, mock_supabase_client):
        """Test updating a risk."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "risk-99", "severity": "medium"}]
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response

        result = await service.update_risk("risk-99", severity="medium")
        assert result["severity"] == "medium"

    @pytest.mark.asyncio
    async def test_list_risks(self, service, mock_supabase_client):
        """Test listing risks."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "risk-1"}, {"id": "risk-2"}]
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        result = await service.list_risks(status="active")
        assert len(result) == 2
