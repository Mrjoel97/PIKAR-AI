"""Unit tests for real HR tool implementations (assign_training, post_job_board).

Tests verify that assign_training and post_job_board return status="completed"
(not "degraded_completed") and create real database records via their
respective services.

Phase 65-04 (HR-06): Replace degraded tools with real implementations.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAssignTraining:
    """Tests for the real assign_training tool."""

    @pytest.fixture(autouse=True)
    def mock_user_context(self):
        """Ensure get_current_user_id returns a test user for all tests."""
        with patch(
            "app.services.request_context.get_current_user_id",
            return_value="test-user-123",
        ):
            yield

    @pytest.mark.asyncio
    async def test_assign_training_creates_record_and_returns_completed(self):
        """assign_training("GDPR Compliance", "Jane Doe") creates a training_assignment record and returns status='completed'."""
        mock_assignment = {
            "id": "ta-001",
            "training_name": "GDPR Compliance",
            "assignee": "Jane Doe",
            "status": "assigned",
        }

        with patch(
            "app.services.training_service.TrainingService"
        ) as MockService:
            instance = MockService.return_value
            instance.assign_training = AsyncMock(return_value=mock_assignment)

            with patch(
                "app.agents.data.tools.track_event", new_callable=AsyncMock
            ):
                from app.agents.hr.tools import assign_training

                result = await assign_training(
                    training_name="GDPR Compliance",
                    assignee="Jane Doe",
                )

        assert result["success"] is True
        assert result["status"] == "completed"
        assert result["tool"] == "assign_training"
        assert "assignment" in result
        assert result["assignment"]["training_name"] == "GDPR Compliance"

    @pytest.mark.asyncio
    async def test_assign_training_with_due_date(self):
        """assign_training with optional due_date persists the due date."""
        mock_assignment = {
            "id": "ta-002",
            "training_name": "Safety Training",
            "assignee": "Team",
            "due_date": "2026-05-01",
            "status": "assigned",
        }

        with patch(
            "app.services.training_service.TrainingService"
        ) as MockService:
            instance = MockService.return_value
            instance.assign_training = AsyncMock(return_value=mock_assignment)

            with patch(
                "app.agents.data.tools.track_event", new_callable=AsyncMock
            ):
                from app.agents.hr.tools import assign_training

                result = await assign_training(
                    training_name="Safety Training",
                    assignee="Team",
                    due_date="2026-05-01",
                )

        assert result["success"] is True
        assert result["status"] == "completed"
        # Verify service was called with due_date
        instance.assign_training.assert_called_once()
        call_kwargs = instance.assign_training.call_args
        assert call_kwargs.kwargs.get("due_date") == "2026-05-01" or (
            len(call_kwargs.args) > 3 and call_kwargs.args[3] == "2026-05-01"
        )


class TestTrainingService:
    """Tests for TrainingService backend operations."""

    @pytest.fixture(autouse=True)
    def mock_user_id(self):
        """Ensure get_current_user_id returns a test user."""
        with patch(
            "app.services.request_context.get_current_user_id",
            return_value="test-user-123",
        ):
            yield

    @pytest.fixture
    def mock_supabase_client(self):
        """Create a mock Supabase client."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_supabase_client):
        """Create TrainingService with mocked dependencies."""
        with patch.dict(
            "os.environ",
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_ANON_KEY": "test-key",
            },
        ):
            from app.services.training_service import TrainingService

            svc = TrainingService(user_token="test-token")
            svc._client = mock_supabase_client
            return svc

    @pytest.mark.asyncio
    async def test_assign_training_stores_record(self, service, mock_supabase_client):
        """TrainingService.assign_training stores record with training_name, assignee, status='assigned'."""
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "ta-100",
                "training_name": "GDPR Compliance",
                "assignee": "Jane Doe",
                "status": "assigned",
                "user_id": "test-user-123",
            }
        ]
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = (
            mock_response
        )

        result = await service.assign_training(
            training_name="GDPR Compliance",
            assignee="Jane Doe",
        )

        assert result["training_name"] == "GDPR Compliance"
        assert result["assignee"] == "Jane Doe"
        assert result["status"] == "assigned"
        # Verify insert data
        insert_call = mock_supabase_client.table.return_value.insert
        insert_data = insert_call.call_args[0][0]
        assert insert_data["training_name"] == "GDPR Compliance"
        assert insert_data["assignee"] == "Jane Doe"
        assert insert_data["status"] == "assigned"

    @pytest.mark.asyncio
    async def test_list_assignments_filterable_by_assignee(
        self, service, mock_supabase_client
    ):
        """TrainingService.list_assignments returns assignments filterable by assignee."""
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "ta-101",
                "training_name": "Security 101",
                "assignee": "Jane Doe",
                "status": "assigned",
            }
        ]
        # Chain: table().select().eq().eq().order().execute()
        chain = mock_supabase_client.table.return_value.select.return_value
        chain.eq.return_value.eq.return_value.order.return_value.execute.return_value = (
            mock_response
        )
        # Also handle the case without assignee filter
        chain.eq.return_value.order.return_value.execute.return_value = mock_response

        result = await service.list_assignments(assignee="Jane Doe")

        assert len(result) == 1
        assert result[0]["assignee"] == "Jane Doe"


class TestPostJobBoard:
    """Tests for the real post_job_board tool."""

    @pytest.fixture(autouse=True)
    def mock_user_context(self):
        """Ensure get_current_user_id returns a test user for all tests."""
        with patch(
            "app.services.request_context.get_current_user_id",
            return_value="test-user-123",
        ):
            yield

    @pytest.mark.asyncio
    async def test_post_job_board_publishes_matching_draft(self):
        """post_job_board(role="Senior Engineer") finds a draft job and publishes it."""
        mock_jobs = [
            {
                "id": "job-draft-001",
                "title": "Senior Engineer",
                "status": "draft",
                "department": "Engineering",
            }
        ]
        mock_published_job = {
            "id": "job-draft-001",
            "title": "Senior Engineer",
            "status": "published",
            "department": "Engineering",
        }

        with patch(
            "app.services.recruitment_service.RecruitmentService"
        ) as MockService:
            instance = MockService.return_value
            instance.list_jobs = AsyncMock(return_value=mock_jobs)
            instance.update_job = AsyncMock(return_value=mock_published_job)

            with patch(
                "app.agents.data.tools.track_event", new_callable=AsyncMock
            ):
                from app.agents.hr.tools import post_job_board

                result = await post_job_board(role="Senior Engineer")

        assert result["success"] is True
        assert result["status"] == "completed"
        assert result["tool"] == "post_job_board"
        assert result["job"]["status"] == "published"

    @pytest.mark.asyncio
    async def test_post_job_board_with_job_id_publishes_directly(self):
        """post_job_board with job_id publishes that specific job."""
        mock_published_job = {
            "id": "job-123",
            "title": "Data Analyst",
            "status": "published",
        }

        with patch(
            "app.services.recruitment_service.RecruitmentService"
        ) as MockService:
            instance = MockService.return_value
            instance.update_job = AsyncMock(return_value=mock_published_job)

            with patch(
                "app.agents.data.tools.track_event", new_callable=AsyncMock
            ):
                from app.agents.hr.tools import post_job_board

                result = await post_job_board(role="Data Analyst", job_id="job-123")

        assert result["success"] is True
        assert result["status"] == "completed"
        # update_job should have been called directly with the job_id
        instance.update_job.assert_called_once()
        call_args = instance.update_job.call_args
        assert call_args[0][0] == "job-123"

    @pytest.mark.asyncio
    async def test_post_job_board_creates_new_when_no_match(self):
        """post_job_board creates a new published job when no matching draft exists."""
        mock_new_job = {
            "id": "job-new-001",
            "title": "Product Manager",
            "status": "published",
            "department": "Product",
        }

        with patch(
            "app.services.recruitment_service.RecruitmentService"
        ) as MockService:
            instance = MockService.return_value
            instance.list_jobs = AsyncMock(return_value=[])  # No drafts
            instance.create_job = AsyncMock(return_value=mock_new_job)

            with patch(
                "app.agents.data.tools.track_event", new_callable=AsyncMock
            ):
                from app.agents.hr.tools import post_job_board

                result = await post_job_board(
                    role="Product Manager", department="Product"
                )

        assert result["success"] is True
        assert result["status"] == "completed"
        assert result["job"]["status"] == "published"
        # create_job should have been called
        instance.create_job.assert_called_once()
        call_kwargs = instance.create_job.call_args
        assert call_kwargs.kwargs.get("status") == "published"
