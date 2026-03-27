import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.fast_api_app import app

@pytest.mark.asyncio
async def test_create_initiative_from_braindump():
    with (
        patch('app.routers.initiatives.start_initiative_from_idea') as mock_start_initiative,
        patch('app.routers.initiatives.get_current_user_id', return_value="test_user_id"),
    ):

        # Arrange
        mock_start_initiative.return_value = {"success": True, "initiative": {"id": "test_initiative_id"}}
        client = TestClient(app)

        # Act
        response = client.post("/initiatives/from-braindump", json={"braindump_id": "test_braindump_id"})

        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["initiative"]["id"] == "test_initiative_id"
        mock_start_initiative.assert_called_once_with(braindump_id="test_braindump_id")
