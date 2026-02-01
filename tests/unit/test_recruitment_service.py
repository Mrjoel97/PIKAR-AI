"""Unit tests for RecruitmentService.

Tests CRUD operations for jobs and candidates used by HRRecruitmentAgent.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestRecruitmentService:
    """Test suite for RecruitmentService."""

    @pytest.fixture
    def mock_supabase_client(self):
        """Create a mock Supabase client."""
        mock_client = MagicMock()
        return mock_client

    @pytest.fixture
    def service(self, mock_supabase_client):
        """Create RecruitmentService with mocked dependencies."""
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_ROLE_KEY': 'test-key'
        }):
            with patch('app.services.recruitment_service.create_client') as mock_create:
                mock_create.return_value = mock_supabase_client
                from app.services.recruitment_service import RecruitmentService
                return RecruitmentService()

    def test_initialization_success(self, service):
        """Test that service initializes correctly."""
        assert service is not None
        assert service._jobs_table == "recruitment_jobs"
        assert service._candidates_table == "recruitment_candidates"

    @pytest.mark.asyncio
    async def test_create_job(self, service, mock_supabase_client):
        """Test creating a job posting."""
        mock_response = MagicMock()
        mock_response.data = [{
            "id": "job-101",
            "title": "Senior Engineer",
            "department": "Engineering",
            "status": "draft"
        }]
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_response

        result = await service.create_job(
            title="Senior Engineer",
            department="Engineering",
            description="Leading headers",
            requirements="Python, AI"
        )
        assert result["id"] == "job-101"
        assert result["status"] == "draft"

    @pytest.mark.asyncio
    async def test_get_job(self, service, mock_supabase_client):
        """Test retrieving a job."""
        mock_response = MagicMock()
        mock_response.data = {"id": "job-101", "title": "Senior Engineer"}
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response

        result = await service.get_job("job-101")
        assert result["id"] == "job-101"

    @pytest.mark.asyncio
    async def test_update_job(self, service, mock_supabase_client):
        """Test updating a job."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "job-101", "status": "published"}]
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response

        result = await service.update_job("job-101", status="published")
        assert result["status"] == "published"

    @pytest.mark.asyncio
    async def test_add_candidate(self, service, mock_supabase_client):
        """Test adding a candidate."""
        mock_response = MagicMock()
        mock_response.data = [{
            "id": "cand-500",
            "name": "Jane Doe",
            "status": "applied"
        }]
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_response

        result = await service.add_candidate(
            name="Jane Doe",
            email="jane@example.com",
            job_id="job-101"
        )
        assert result["id"] == "cand-500"

    @pytest.mark.asyncio
    async def test_update_candidate_status(self, service, mock_supabase_client):
        """Test updating candidate status."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "cand-500", "status": "interviewing"}]
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response

        result = await service.update_candidate_status("cand-500", "interviewing")
        assert result["status"] == "interviewing"

    @pytest.mark.asyncio
    async def test_list_candidates(self, service, mock_supabase_client):
        """Test listing candidates."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "cand-500"}, {"id": "cand-501"}]
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        result = await service.list_candidates(job_id="job-101")
        assert len(result) == 2
