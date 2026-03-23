"""Unit tests for admin_knowledge_video handler in WorkflowWorker.

Tests verify:
- test_handle_admin_knowledge_video: handle_job_type dispatches to process_video_transcript
- test_handle_admin_knowledge_video_failure: errors propagate (WorkflowWorker fires fail_ai_job)
- test_admin_knowledge_video_in_handlers: 'admin_knowledge_video' exists in dispatch map
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Patch targets
_PROCESS_VIDEO_TRANSCRIPT_PATCH = "app.workflows.worker.process_video_transcript"
_WORKER_GET_SUPABASE_PATCH = "app.workflows.worker.WorkflowWorker._get_supabase"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_worker() -> "WorkflowWorker":  # type: ignore[name-defined]
    """Instantiate WorkflowWorker with all external deps mocked."""
    from app.workflows.worker import WorkflowWorker

    with (
        patch(_WORKER_GET_SUPABASE_PATCH, return_value=MagicMock()),
        patch("app.workflows.worker.get_workflow_engine", return_value=MagicMock()),
        patch("app.workflows.worker.StepExecutor", return_value=MagicMock()),
    ):
        worker = WorkflowWorker()
    return worker


# ===========================================================================
# test_admin_knowledge_video_in_handlers
# ===========================================================================


def test_admin_knowledge_video_in_handlers():
    """'admin_knowledge_video' key is present in WorkflowWorker.handle_job_type dispatch map."""
    import inspect

    from app.workflows.worker import WorkflowWorker

    # Read the source to confirm the key is registered
    source = inspect.getsource(WorkflowWorker.handle_job_type)
    assert "admin_knowledge_video" in source, (
        "Expected 'admin_knowledge_video' to be registered in handle_job_type dispatch map"
    )


# ===========================================================================
# test_handle_admin_knowledge_video
# ===========================================================================


@pytest.mark.asyncio
async def test_handle_admin_knowledge_video():
    """handle_job_type('admin_knowledge_video', input_data) calls process_video_transcript with correct args."""
    worker = _make_worker()

    input_data = {
        "entry_id": "entry-uuid-123",
        "file_path": "entry-uuid-123/training.mp4",
        "agent_scope": "operations",
        "mime_type": "video/mp4",
    }
    expected_result = {
        "entry_id": "entry-uuid-123",
        "chunk_count": 5,
        "status": "completed",
        "transcript_length": 312,
    }

    with patch(_PROCESS_VIDEO_TRANSCRIPT_PATCH, new_callable=AsyncMock, return_value=expected_result) as mock_pvt:
        result = await worker.handle_job_type("admin_knowledge_video", input_data)

    assert result == expected_result
    mock_pvt.assert_called_once_with(
        entry_id="entry-uuid-123",
        file_path="entry-uuid-123/training.mp4",
        agent_scope="operations",
        mime_type="video/mp4",
    )


# ===========================================================================
# test_handle_admin_knowledge_video_failure
# ===========================================================================


@pytest.mark.asyncio
async def test_handle_admin_knowledge_video_failure():
    """handle_job_type('admin_knowledge_video', bad_data) propagates exception for fail_ai_job."""
    worker = _make_worker()

    input_data = {
        "entry_id": "entry-bad",
        "file_path": "entry-bad/corrupt.mp4",
        "agent_scope": None,
        "mime_type": "video/mp4",
    }

    with patch(
        _PROCESS_VIDEO_TRANSCRIPT_PATCH,
        new_callable=AsyncMock,
        side_effect=RuntimeError("ffmpeg audio extraction failed"),
    ):
        with pytest.raises(RuntimeError, match="ffmpeg audio extraction failed"):
            await worker.handle_job_type("admin_knowledge_video", input_data)
