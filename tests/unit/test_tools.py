from app.agent import get_revenue_stats, search_business_knowledge, update_initiative_status, create_task
import pytest

def test_get_revenue_stats():
    stats = get_revenue_stats()
    assert isinstance(stats, dict)
    assert "revenue" in stats
    assert isinstance(stats["revenue"], float)

def test_search_business_knowledge_returns_results():
    """Tests that search_business_knowledge returns a dictionary with a 'results' key."""
    result = search_business_knowledge("test query")
    assert isinstance(result, dict)
    assert "results" in result
    assert isinstance(result["results"], list)

def test_update_initiative_status_returns_success():
    """Tests that update_initiative_status returns a dictionary with a 'success' key."""
    result = update_initiative_status("test_id", "in_progress")
    assert isinstance(result, dict)
    assert "success" in result
    assert result["success"] is True

def test_create_task_returns_task_id():
    """Tests that create_task returns a dictionary with a 'task_id' key."""
    result = create_task("test task", "unassigned", "medium")
    assert isinstance(result, dict)
    assert "task_id" in result
    assert isinstance(result["task_id"], str)