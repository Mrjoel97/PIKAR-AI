"""Unit tests for HR auto-onboarding and team org chart tools.

Tests auto_generate_onboarding and get_team_org_chart tools,
and TeamOrgService used by HRRecruitmentAgent for HR-04 and HR-05 requirements.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# auto_generate_onboarding tests
# ---------------------------------------------------------------------------


class TestAutoGenerateOnboarding:
    """Test suite for auto_generate_onboarding tool."""

    @pytest.fixture(autouse=True)
    def mock_user_context(self):
        """Ensure get_current_user_id returns a test user for all tests."""
        with patch(
            "app.services.request_context.get_current_user_id",
            return_value="test-user-123",
        ):
            yield

    def _mock_candidate(self, department="Engineering", seniority="mid"):
        """Build a mock hired candidate record."""
        return {
            "id": "cand-001",
            "name": "Jane Doe",
            "email": "jane@example.com",
            "job_id": "job-001",
            "status": "hired",
            "user_id": "test-user-123",
        }

    def _mock_job(self, department="Engineering", seniority="mid"):
        """Build a mock job record."""
        return {
            "id": "job-001",
            "title": "Software Engineer",
            "department": department,
            "seniority_level": seniority,
            "status": "published",
            "user_id": "test-user-123",
        }

    @pytest.mark.asyncio
    async def test_onboarding_returns_complete_checklist(self):
        """auto_generate_onboarding returns a checklist with all four sections."""
        with (
            patch(
                "app.services.recruitment_service.RecruitmentService"
            ) as MockRecruit,
            patch(
                "app.services.team_org_service.TeamOrgService"
            ) as MockOrg,
        ):
            recruit_instance = MockRecruit.return_value
            recruit_instance.get_candidate = AsyncMock(return_value=self._mock_candidate())
            recruit_instance.get_job = AsyncMock(return_value=self._mock_job())

            org_instance = MockOrg.return_value
            org_instance.add_team_member = AsyncMock(return_value={
                "id": "member-001",
                "name": "Jane Doe",
                "position": "Software Engineer",
                "department": "Engineering",
            })

            from app.agents.hr.tools import auto_generate_onboarding

            result = await auto_generate_onboarding(candidate_id="cand-001")

        assert result["success"] is True
        checklist = result["onboarding_checklist"]
        assert "pre_boarding" in checklist
        assert "day_1" in checklist
        assert "week_1" in checklist
        assert "thirty_sixty_ninety" in checklist

    @pytest.mark.asyncio
    async def test_engineering_hire_gets_dev_tools(self):
        """Engineering hire's pre-boarding includes dev tool setup items."""
        with (
            patch(
                "app.services.recruitment_service.RecruitmentService"
            ) as MockRecruit,
            patch(
                "app.services.team_org_service.TeamOrgService"
            ) as MockOrg,
        ):
            recruit_instance = MockRecruit.return_value
            recruit_instance.get_candidate = AsyncMock(
                return_value=self._mock_candidate(department="Engineering")
            )
            recruit_instance.get_job = AsyncMock(
                return_value=self._mock_job(department="Engineering")
            )

            org_instance = MockOrg.return_value
            org_instance.add_team_member = AsyncMock(return_value={
                "id": "member-001",
                "name": "Jane Doe",
                "position": "Software Engineer",
                "department": "Engineering",
            })

            from app.agents.hr.tools import auto_generate_onboarding

            result = await auto_generate_onboarding(candidate_id="cand-001")

        checklist = result["onboarding_checklist"]
        pre_boarding_text = " ".join(checklist["pre_boarding"]).lower()
        assert "ide" in pre_boarding_text or "monitor" in pre_boarding_text

    @pytest.mark.asyncio
    async def test_marketing_hire_gets_analytics_tools(self):
        """Marketing hire's pre-boarding includes analytics/design tool access."""
        with (
            patch(
                "app.services.recruitment_service.RecruitmentService"
            ) as MockRecruit,
            patch(
                "app.services.team_org_service.TeamOrgService"
            ) as MockOrg,
        ):
            recruit_instance = MockRecruit.return_value
            recruit_instance.get_candidate = AsyncMock(
                return_value=self._mock_candidate(department="Marketing")
            )
            recruit_instance.get_job = AsyncMock(
                return_value=self._mock_job(department="Marketing", seniority="mid")
            )

            org_instance = MockOrg.return_value
            org_instance.add_team_member = AsyncMock(return_value={
                "id": "member-002",
                "name": "Jane Doe",
                "position": "Marketing Manager",
                "department": "Marketing",
            })

            from app.agents.hr.tools import auto_generate_onboarding

            result = await auto_generate_onboarding(candidate_id="cand-001")

        checklist = result["onboarding_checklist"]
        pre_boarding_text = " ".join(checklist["pre_boarding"]).lower()
        assert "design" in pre_boarding_text or "analytics" in pre_boarding_text

    @pytest.mark.asyncio
    async def test_onboarding_creates_team_member(self):
        """auto_generate_onboarding creates a team_member record from hired candidate."""
        with (
            patch(
                "app.services.recruitment_service.RecruitmentService"
            ) as MockRecruit,
            patch(
                "app.services.team_org_service.TeamOrgService"
            ) as MockOrg,
        ):
            recruit_instance = MockRecruit.return_value
            recruit_instance.get_candidate = AsyncMock(return_value=self._mock_candidate())
            recruit_instance.get_job = AsyncMock(return_value=self._mock_job())

            member_record = {
                "id": "member-001",
                "name": "Jane Doe",
                "position": "Software Engineer",
                "department": "Engineering",
            }
            org_instance = MockOrg.return_value
            org_instance.add_team_member = AsyncMock(return_value=member_record)

            from app.agents.hr.tools import auto_generate_onboarding

            result = await auto_generate_onboarding(candidate_id="cand-001")

        assert result["success"] is True
        assert result["team_member"]["id"] == "member-001"
        org_instance.add_team_member.assert_called_once()


# ---------------------------------------------------------------------------
# get_team_org_chart tests
# ---------------------------------------------------------------------------


class TestGetTeamOrgChart:
    """Test suite for get_team_org_chart tool."""

    @pytest.fixture(autouse=True)
    def mock_user_context(self):
        """Ensure get_current_user_id returns a test user for all tests."""
        with patch(
            "app.services.request_context.get_current_user_id",
            return_value="test-user-123",
        ):
            yield

    @pytest.mark.asyncio
    async def test_org_chart_returns_members_and_vacancies(self):
        """get_team_org_chart returns nodes for members and open positions."""
        org_data = {
            "members": [
                {
                    "id": "m-001",
                    "name": "Alice",
                    "position": "CTO",
                    "department": "Engineering",
                    "reports_to": None,
                    "status": "active",
                    "hire_date": "2026-01-15",
                },
                {
                    "id": "m-002",
                    "name": "Bob",
                    "position": "Software Engineer",
                    "department": "Engineering",
                    "reports_to": "m-001",
                    "status": "active",
                    "hire_date": "2026-03-01",
                },
            ],
            "open_positions": [
                {
                    "job_id": "job-099",
                    "title": "Senior Backend Engineer",
                    "department": "Engineering",
                    "status": "vacant",
                },
            ],
            "departments": ["Engineering"],
        }

        with patch(
            "app.services.team_org_service.TeamOrgService"
        ) as MockOrg:
            org_instance = MockOrg.return_value
            org_instance.get_org_chart = AsyncMock(return_value=org_data)

            from app.agents.hr.tools import get_team_org_chart

            result = await get_team_org_chart()

        assert result["success"] is True
        chart = result["org_chart"]
        assert len(chart["members"]) == 2
        assert len(chart["open_positions"]) == 1
        assert chart["open_positions"][0]["status"] == "vacant"

    @pytest.mark.asyncio
    async def test_org_chart_filters_by_department(self):
        """get_team_org_chart filters to a specific department when provided."""
        org_data = {
            "members": [
                {
                    "id": "m-001",
                    "name": "Alice",
                    "position": "CTO",
                    "department": "Engineering",
                    "reports_to": None,
                    "status": "active",
                    "hire_date": "2026-01-15",
                },
                {
                    "id": "m-003",
                    "name": "Carol",
                    "position": "Marketing Lead",
                    "department": "Marketing",
                    "reports_to": None,
                    "status": "active",
                    "hire_date": "2026-02-01",
                },
            ],
            "open_positions": [
                {
                    "job_id": "job-099",
                    "title": "Content Writer",
                    "department": "Marketing",
                    "status": "vacant",
                },
            ],
            "departments": ["Engineering", "Marketing"],
        }

        with patch(
            "app.services.team_org_service.TeamOrgService"
        ) as MockOrg:
            org_instance = MockOrg.return_value
            org_instance.get_org_chart = AsyncMock(return_value=org_data)

            from app.agents.hr.tools import get_team_org_chart

            result = await get_team_org_chart(department="Marketing")

        assert result["success"] is True
        chart = result["org_chart"]
        # Only Marketing members should be returned
        for member in chart["members"]:
            assert member["department"] == "Marketing"
        for pos in chart["open_positions"]:
            assert pos["department"] == "Marketing"


# ---------------------------------------------------------------------------
# TeamOrgService tests
# ---------------------------------------------------------------------------


class TestTeamOrgService:
    """Test suite for TeamOrgService."""

    @pytest.fixture(autouse=True)
    def mock_user_context(self):
        """Ensure get_current_user_id returns a test user for all tests."""
        with patch(
            "app.services.request_context.get_current_user_id",
            return_value="test-user-123",
        ):
            yield

    @pytest.mark.asyncio
    async def test_add_team_member_creates_record(self):
        """TeamOrgService.add_team_member creates a record with all fields."""
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "member-001",
                "name": "Jane Doe",
                "email": "jane@example.com",
                "position": "Software Engineer",
                "department": "Engineering",
                "reports_to": None,
                "user_id": "test-user-123",
            }
        ]

        with patch(
            "app.services.team_org_service.execute_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            from app.services.team_org_service import TeamOrgService

            service = TeamOrgService()
            result = await service.add_team_member(
                name="Jane Doe",
                email="jane@example.com",
                position="Software Engineer",
                department="Engineering",
                user_id="test-user-123",
            )

        assert result["name"] == "Jane Doe"
        assert result["position"] == "Software Engineer"
        assert result["department"] == "Engineering"
