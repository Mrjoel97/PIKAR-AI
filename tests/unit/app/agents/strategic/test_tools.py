import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.agents.strategic.tools import start_initiative_from_idea

@pytest.mark.asyncio
async def test_start_initiative_from_idea_with_braindump():
    with (patch('app.agents.tools.brain_dump.get_braindump_document', new_callable=AsyncMock) as mock_get_braindump,
          patch('app.services.initiative_service.InitiativeService') as mock_initiative_service_class,
          patch('app.services.request_context.get_current_user_id') as mock_get_current_user_id,
          patch('app.workflows.engine.get_workflow_engine', new_callable=AsyncMock) as mock_get_workflow_engine):

        # Arrange
        mock_get_braindump.return_value = {"content": "This is a test brain dump"}
        
        mock_initiative_service_instance = MagicMock()
        mock_initiative_service_instance.create_initiative = AsyncMock(return_value={"id": "test_initiative_id"})
        mock_initiative_service_class.return_value = mock_initiative_service_instance

        mock_get_current_user_id.return_value = "test_user_id"
        mock_get_workflow_engine.return_value.start_workflow.return_value = {"execution_id": "test_execution_id"}


        # Act
        result = await start_initiative_from_idea(braindump_id="test_braindump_id")

        # Assert
        assert result["success"] is True
        assert result["initiative"]["id"] == "test_initiative_id"
        mock_get_braindump.assert_called_once_with("test_braindump_id")
        mock_initiative_service_instance.create_initiative.assert_called_once()

@pytest.mark.asyncio
async def test_start_initiative_from_idea_without_braindump():
    with patch('app.services.initiative_service.InitiativeService') as mock_initiative_service_class, \
         patch('app.services.request_context.get_current_user_id') as mock_get_current_user_id, \
         patch('app.workflows.engine.get_workflow_engine', new_callable=AsyncMock) as mock_get_workflow_engine:

        # Arrange
        mock_initiative_service_instance = MagicMock()
        mock_initiative_service_instance.create_initiative = AsyncMock(return_value={"id": "test_initiative_id"})
        mock_initiative_service_class.return_value = mock_initiative_service_instance

        mock_get_current_user_id.return_value = "test_user_id"
        mock_get_workflow_engine.return_value.start_workflow.return_value = {"execution_id": "test_execution_id"}


        # Act
        result = await start_initiative_from_idea(idea="Test Idea", context="Test Context")

        # Assert
        assert result["success"] is True
        assert result["initiative"]["id"] == "test_initiative_id"
        mock_initiative_service_instance.create_initiative.assert_called_once()

@pytest.mark.asyncio
async def test_start_initiative_from_idea_with_braindump_error():
    with patch('app.agents.tools.brain_dump.get_braindump_document', new_callable=AsyncMock) as mock_get_braindump:

        # Arrange
        mock_get_braindump.return_value = {"error": "Test Error"}

        # Act
        result = await start_initiative_from_idea(braindump_id="test_braindump_id")

        # Assert
        assert result["success"] is False
        assert result["error"] == "Test Error"
