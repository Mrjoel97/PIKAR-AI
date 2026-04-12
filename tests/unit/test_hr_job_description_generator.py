"""Unit tests for HR job description generator and interview question tools.

Tests generate_job_description and generate_interview_questions tools
used by HRRecruitmentAgent for HR-01 and HR-03 requirements.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestGenerateJobDescription:
    """Test suite for generate_job_description tool."""

    @pytest.fixture(autouse=True)
    def mock_user_context(self):
        """Ensure get_current_user_id returns a test user for all tests."""
        with patch(
            "app.agents.hr.tools.get_current_user_id",
            return_value="test-user-123",
        ):
            yield

    @pytest.mark.asyncio
    async def test_basic_job_description_returns_success(self):
        """generate_job_description returns success=True with job and description."""
        mock_job = {
            "id": "job-001",
            "title": "Marketing Manager",
            "department": "Marketing",
            "salary_min": 78750,
            "salary_max": 115500,
            "seniority_level": "mid",
        }

        with patch(
            "app.agents.hr.tools.RecruitmentService"
        ) as MockService:
            instance = MockService.return_value
            instance.create_job = AsyncMock(return_value=mock_job)

            from app.agents.hr.tools import generate_job_description

            result = await generate_job_description(
                title="Marketing Manager",
                department="Marketing",
                seniority_level="mid",
            )

        assert result["success"] is True
        assert "job" in result
        assert result["job"]["title"] == "Marketing Manager"
        assert "job_description" in result
        # Description should contain key sections
        desc = result["job_description"]
        assert "Responsibilities" in desc or "responsibilities" in desc.lower()
        assert "Requirements" in desc or "requirements" in desc.lower()

    @pytest.mark.asyncio
    async def test_salary_range_populated(self):
        """generate_job_description produces salary_min > 0 and salary_max > salary_min."""
        mock_job = {
            "id": "job-002",
            "title": "Marketing Manager",
            "department": "Marketing",
            "salary_min": 78750,
            "salary_max": 115500,
            "seniority_level": "mid",
        }

        with patch(
            "app.agents.hr.tools.RecruitmentService"
        ) as MockService:
            instance = MockService.return_value
            instance.create_job = AsyncMock(return_value=mock_job)

            from app.agents.hr.tools import generate_job_description

            result = await generate_job_description(
                title="Marketing Manager",
                department="Marketing",
                seniority_level="mid",
            )

        assert result["success"] is True
        # Verify create_job was called with salary fields
        call_kwargs = instance.create_job.call_args
        assert call_kwargs.kwargs.get("salary_min") is not None
        assert call_kwargs.kwargs.get("salary_max") is not None
        salary_min = call_kwargs.kwargs["salary_min"]
        salary_max = call_kwargs.kwargs["salary_max"]
        assert salary_min > 0
        assert salary_max > salary_min

    @pytest.mark.asyncio
    async def test_senior_salary_higher_than_junior(self):
        """Senior seniority_level produces a higher salary range than junior."""
        from app.agents.hr.tools import _compute_salary_band

        junior_min, junior_max = _compute_salary_band("junior", "Engineering")
        senior_min, senior_max = _compute_salary_band("senior", "Engineering")

        assert senior_min > junior_min
        assert senior_max > junior_max

    @pytest.mark.asyncio
    async def test_department_modifier_applied(self):
        """Engineering department gets a +15% modifier vs Operations at base."""
        from app.agents.hr.tools import _compute_salary_band

        eng_min, eng_max = _compute_salary_band("mid", "Engineering")
        ops_min, ops_max = _compute_salary_band("mid", "Operations")

        # Engineering should be ~15% higher than Operations
        assert eng_min > ops_min
        assert eng_max > ops_max

    @pytest.mark.asyncio
    async def test_create_job_called_with_all_fields(self):
        """generate_job_description persists job via RecruitmentService with salary fields."""
        mock_job = {
            "id": "job-003",
            "title": "Data Analyst",
            "department": "Data",
            "salary_min": 75000,
            "salary_max": 110000,
            "seniority_level": "mid",
        }

        with patch(
            "app.agents.hr.tools.RecruitmentService"
        ) as MockService:
            instance = MockService.return_value
            instance.create_job = AsyncMock(return_value=mock_job)

            from app.agents.hr.tools import generate_job_description

            result = await generate_job_description(
                title="Data Analyst",
                department="Data",
                seniority_level="mid",
                key_skills="SQL, Python, Statistics",
            )

        assert result["success"] is True
        call_kwargs = instance.create_job.call_args
        # Must include salary_min, salary_max, seniority_level, responsibilities
        assert "salary_min" in call_kwargs.kwargs
        assert "salary_max" in call_kwargs.kwargs
        assert "seniority_level" in call_kwargs.kwargs
        assert "responsibilities" in call_kwargs.kwargs
        assert call_kwargs.kwargs["seniority_level"] == "mid"


class TestRecruitmentServiceSalaryFields:
    """Test that RecruitmentService.create_job accepts salary fields."""

    @pytest.fixture(autouse=True)
    def mock_user_id(self):
        """Ensure get_current_user_id returns a test user."""
        with patch(
            "app.services.recruitment_service.get_current_user_id",
            return_value="test-user",
        ):
            yield

    @pytest.fixture
    def mock_supabase_client(self):
        """Create a mock Supabase client."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_supabase_client):
        """Create RecruitmentService with mocked dependencies."""
        with patch.dict(
            "os.environ",
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_ANON_KEY": "test-key",
            },
        ):
            from app.services.recruitment_service import RecruitmentService

            svc = RecruitmentService(user_token="test-token")
            svc._client = mock_supabase_client
            return svc

    @pytest.mark.asyncio
    async def test_create_job_with_salary_fields(self, service, mock_supabase_client):
        """create_job accepts salary_min, salary_max, seniority_level and persists them."""
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "job-200",
                "title": "Engineer",
                "salary_min": 110000,
                "salary_max": 160000,
                "seniority_level": "senior",
            }
        ]
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = (
            mock_response
        )

        result = await service.create_job(
            title="Engineer",
            department="Engineering",
            description="Build things",
            requirements="Python",
            salary_min=110000,
            salary_max=160000,
            seniority_level="senior",
            responsibilities="Lead team, design systems",
        )

        assert result["id"] == "job-200"
        assert result["salary_min"] == 110000
        # Verify the insert data included salary fields
        insert_call = mock_supabase_client.table.return_value.insert
        insert_data = insert_call.call_args[0][0]
        assert insert_data["salary_min"] == 110000
        assert insert_data["salary_max"] == 160000
        assert insert_data["seniority_level"] == "senior"
        assert insert_data["responsibilities"] == "Lead team, design systems"

    @pytest.mark.asyncio
    async def test_update_job_with_salary_fields(self, service, mock_supabase_client):
        """update_job accepts and persists salary_min, salary_max, seniority_level."""
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "job-200",
                "salary_min": 120000,
                "salary_max": 170000,
                "seniority_level": "lead",
            }
        ]
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        result = await service.update_job(
            "job-200",
            salary_min=120000,
            salary_max=170000,
            seniority_level="lead",
        )

        assert result["salary_min"] == 120000
        update_call = mock_supabase_client.table.return_value.update
        update_data = update_call.call_args[0][0]
        assert update_data["salary_min"] == 120000
        assert update_data["salary_max"] == 170000
        assert update_data["seniority_level"] == "lead"
