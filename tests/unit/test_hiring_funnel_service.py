"""Unit tests for HiringFunnelService.

Tests hiring funnel aggregation: stage counting, conversion rates,
summary across multiple jobs, and the get_hiring_funnel agent tool.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestHiringFunnelService:
    """Test suite for HiringFunnelService."""

    @pytest.fixture(autouse=True)
    def mock_user_id(self):
        """Ensure get_current_user_id returns a test user for all tests."""
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
        """Create HiringFunnelService with mocked dependencies."""
        with patch.dict(
            "os.environ",
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_ANON_KEY": "test-key",
            },
        ):
            from app.services.hiring_funnel_service import HiringFunnelService

            svc = HiringFunnelService(user_token="test-token")
            svc._client = mock_supabase_client
            return svc

    @pytest.mark.asyncio
    async def test_get_funnel_for_job_stage_counts(self, service, mock_supabase_client):
        """Test that get_funnel_for_job returns correct stage counts."""
        # 10 applied, 6 screening, 4 interviewing, 2 offer, 1 hired, 3 rejected
        candidates = [
            {"status": "applied"} for _ in range(10)
        ] + [
            {"status": "screening"} for _ in range(6)
        ] + [
            {"status": "interviewing"} for _ in range(4)
        ] + [
            {"status": "offer"} for _ in range(2)
        ] + [
            {"status": "hired"} for _ in range(1)
        ] + [
            {"status": "rejected"} for _ in range(3)
        ]

        mock_response = MagicMock()
        mock_response.data = candidates

        with patch(
            "app.services.hiring_funnel_service.execute_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await service.get_funnel_for_job("job-101", user_id="test-user")

        assert result["job_id"] == "job-101"
        assert result["total"] == 26

        # Check stage counts
        stages = {s["name"]: s["count"] for s in result["stages"]}
        assert stages["applied"] == 10
        assert stages["screening"] == 6
        assert stages["interviewing"] == 4
        assert stages["offer"] == 2
        assert stages["hired"] == 1
        assert result["rejected"] == 3

    @pytest.mark.asyncio
    async def test_get_funnel_for_job_conversion_rates(
        self, service, mock_supabase_client
    ):
        """Test that conversion rates between stages are computed correctly."""
        candidates = (
            [{"status": "applied"} for _ in range(10)]
            + [{"status": "screening"} for _ in range(6)]
            + [{"status": "interviewing"} for _ in range(4)]
            + [{"status": "offer"} for _ in range(2)]
            + [{"status": "hired"} for _ in range(1)]
        )

        mock_response = MagicMock()
        mock_response.data = candidates

        with patch(
            "app.services.hiring_funnel_service.execute_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await service.get_funnel_for_job("job-101", user_id="test-user")

        rates = result["conversion_rates"]
        assert rates["applied_to_screening"] == pytest.approx(0.6)
        assert rates["screening_to_interviewing"] == pytest.approx(4 / 6)
        assert rates["interviewing_to_offer"] == pytest.approx(0.5)
        assert rates["offer_to_hired"] == pytest.approx(0.5)

    @pytest.mark.asyncio
    async def test_get_funnel_for_job_zero_candidates(
        self, service, mock_supabase_client
    ):
        """Test that funnel with zero candidates returns all stages at 0."""
        mock_response = MagicMock()
        mock_response.data = []

        with patch(
            "app.services.hiring_funnel_service.execute_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await service.get_funnel_for_job("job-empty", user_id="test-user")

        assert result["total"] == 0
        assert result["rejected"] == 0
        for stage in result["stages"]:
            assert stage["count"] == 0
        # Conversion rates should be 0 when no candidates
        for rate in result["conversion_rates"].values():
            assert rate == 0

    @pytest.mark.asyncio
    async def test_get_funnel_summary(self, service, mock_supabase_client):
        """Test get_funnel_summary returns funnels for all open jobs."""
        # Mock list_jobs response
        jobs_response = MagicMock()
        jobs_response.data = [
            {"id": "job-1", "title": "Engineer", "department": "Eng"},
            {"id": "job-2", "title": "Designer", "department": "Design"},
        ]

        # Mock candidate responses for each job
        cand_response_1 = MagicMock()
        cand_response_1.data = [
            {"status": "applied"},
            {"status": "applied"},
            {"status": "screening"},
        ]

        cand_response_2 = MagicMock()
        cand_response_2.data = [
            {"status": "applied"},
            {"status": "hired"},
        ]

        call_count = 0

        async def mock_execute(query, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return jobs_response
            elif call_count == 2:
                return cand_response_1
            else:
                return cand_response_2

        with patch(
            "app.services.hiring_funnel_service.execute_async",
            side_effect=mock_execute,
        ):
            result = await service.get_funnel_summary(user_id="test-user")

        assert len(result) == 2
        assert result[0]["job_id"] == "job-1"
        assert result[0]["title"] == "Engineer"
        assert result[0]["department"] == "Eng"
        assert result[0]["funnel"]["total"] == 3

        assert result[1]["job_id"] == "job-2"
        assert result[1]["title"] == "Designer"
        assert result[1]["funnel"]["total"] == 2


class TestGetHiringFunnelTool:
    """Test suite for the get_hiring_funnel agent tool."""

    @pytest.mark.asyncio
    async def test_get_hiring_funnel_with_job_id(self):
        """Test get_hiring_funnel tool returns success with funnel data for a specific job."""
        mock_funnel = {
            "job_id": "job-101",
            "stages": [{"name": "applied", "count": 5}],
            "rejected": 1,
            "total": 6,
            "conversion_rates": {},
        }

        with (
            patch.dict(
                "os.environ",
                {
                    "SUPABASE_URL": "https://test.supabase.co",
                    "SUPABASE_ANON_KEY": "test-key",
                },
            ),
            patch(
                "app.services.hiring_funnel_service.HiringFunnelService.get_funnel_for_job",
                new_callable=AsyncMock,
                return_value=mock_funnel,
            ),
        ):
            from app.agents.hr.tools import get_hiring_funnel

            result = await get_hiring_funnel(job_id="job-101")

        assert result["success"] is True
        assert result["funnel"]["job_id"] == "job-101"

    @pytest.mark.asyncio
    async def test_get_hiring_funnel_all_jobs(self):
        """Test get_hiring_funnel tool returns summary when no job_id given."""
        mock_summary = [
            {"job_id": "job-1", "title": "Engineer", "funnel": {"total": 5}},
        ]

        with (
            patch.dict(
                "os.environ",
                {
                    "SUPABASE_URL": "https://test.supabase.co",
                    "SUPABASE_ANON_KEY": "test-key",
                },
            ),
            patch(
                "app.services.hiring_funnel_service.HiringFunnelService.get_funnel_summary",
                new_callable=AsyncMock,
                return_value=mock_summary,
            ),
        ):
            from app.agents.hr.tools import get_hiring_funnel

            result = await get_hiring_funnel()

        assert result["success"] is True
        assert len(result["funnel"]) == 1
        assert result["funnel"][0]["job_id"] == "job-1"
