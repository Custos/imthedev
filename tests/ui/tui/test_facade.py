"""Tests for the CoreFacade integration layer.

This module tests the facade that bridges the UI and core services.
"""

from typing import List
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import UUID, uuid4

import pytest

from imthedev.core import (
    AIOrchestrator,
    ApplicationState,
    Command,
    CommandEngine,
    CommandStatus,
    ContextService,
    Event,
    EventBus,
    EventTypes,
    Project,
    ProjectContext,
    ProjectService,
    StateManager,
)
from imthedev.ui.tui import CoreFacade
from datetime import datetime
from pathlib import Path
from imthedev.core import ProjectSettings


def create_test_project(name: str = "Test Project", path: str = "/test") -> Project:
    """Helper function to create a test project with all required fields."""
    return Project(
        id=uuid4(),
        name=name,
        path=Path(path),
        created_at=datetime.now(),
        context=ProjectContext(),
        settings=ProjectSettings()
    )


@pytest.fixture
def mock_event_bus() -> Mock:
    """Create a mock event bus."""
    return Mock(spec=EventBus)


@pytest.fixture
def mock_project_service() -> Mock:
    """Create a mock project service."""
    service = Mock(spec=ProjectService)
    service.list_projects = AsyncMock(return_value=[])
    service.create_project = AsyncMock()
    service.set_current_project = AsyncMock()
    service.get_current_project = AsyncMock(return_value=None)
    return service


@pytest.fixture
def mock_context_service() -> Mock:
    """Create a mock context service."""
    service = Mock(spec=ContextService)
    service.load_context = AsyncMock(return_value=ProjectContext())
    service.save_context = AsyncMock()
    return service


@pytest.fixture
def mock_command_engine() -> Mock:
    """Create a mock command engine."""
    engine = Mock(spec=CommandEngine)
    engine.propose_command = AsyncMock()
    engine.approve_command = AsyncMock()
    engine.reject_command = AsyncMock()
    engine.get_pending_commands = AsyncMock(return_value=[])
    return engine


@pytest.fixture
def mock_ai_orchestrator() -> Mock:
    """Create a mock AI orchestrator."""
    orchestrator = Mock(spec=AIOrchestrator)
    orchestrator.generate_command = AsyncMock(return_value=("echo test", "Test command"))
    orchestrator.get_available_models = Mock(return_value=["claude", "gpt-4"])
    return orchestrator


@pytest.fixture
def mock_state_manager() -> Mock:
    """Create a mock state manager."""
    manager = Mock(spec=StateManager)
    state = ApplicationState(
        current_project_id=None,
        autopilot_enabled=False,
        selected_ai_model="claude",
        ui_preferences={}
    )
    manager.get_state = AsyncMock(return_value=state)
    manager.update_state = AsyncMock()
    return manager


@pytest.fixture
def facade(
    mock_event_bus,
    mock_project_service,
    mock_context_service,
    mock_command_engine,
    mock_ai_orchestrator,
    mock_state_manager
) -> CoreFacade:
    """Create a CoreFacade instance with mocked dependencies."""
    return CoreFacade(
        event_bus=mock_event_bus,
        project_service=mock_project_service,
        context_service=mock_context_service,
        command_engine=mock_command_engine,
        ai_orchestrator=mock_ai_orchestrator,
        state_manager=mock_state_manager,
    )


class TestCoreFacade:
    """Test suite for CoreFacade."""
    
    def test_facade_initialization(self, facade, mock_event_bus):
        """Test that facade initializes and subscribes to events."""
        # Check that services are set
        assert facade.event_bus is not None
        assert facade.project_service is not None
        assert facade.context_service is not None
        assert facade.command_engine is not None
        assert facade.ai_orchestrator is not None
        assert facade.state_manager is not None
        
        # Check that event subscriptions were made
        assert mock_event_bus.subscribe.called
        
        # Verify specific event subscriptions
        expected_events = [
            EventTypes.PROJECT_CREATED,
            EventTypes.PROJECT_SELECTED,
            EventTypes.COMMAND_PROPOSED,
            EventTypes.COMMAND_APPROVED,
            EventTypes.STATE_AUTOPILOT_ENABLED,
        ]
        
        subscribed_events = [call[0][0] for call in mock_event_bus.subscribe.call_args_list]
        for event in expected_events:
            assert event in subscribed_events
    
    def test_ui_event_registration(self, facade):
        """Test UI event handler registration."""
        # Register a handler
        handler = Mock()
        facade.on_ui_event("test.event", handler)
        
        # Emit the event
        facade._emit_ui_event("test.event", {"test": "data"})
        
        # Check handler was called
        handler.assert_called_once()
        event = handler.call_args[0][0]
        assert event.type == "test.event"
        assert event.payload == {"test": "data"}
    
    @pytest.mark.asyncio
    async def test_get_projects(self, facade, mock_project_service):
        """Test getting projects through facade."""
        # Setup mock data
        projects = [
            create_test_project(name="Test Project", path="/test"),
            create_test_project(name="Another Project", path="/another"),
        ]
        mock_project_service.list_projects.return_value = projects
        
        # Get projects
        result = await facade.get_projects()
        
        # Verify
        assert result == projects
        mock_project_service.list_projects.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_project(self, facade, mock_project_service):
        """Test creating a project through facade."""
        # Setup mock
        project = create_test_project(name="New Project", path="/new")
        mock_project_service.create_project.return_value = project
        
        # Create project
        result = await facade.create_project("New Project", "/new")
        
        # Verify
        assert result == project
        mock_project_service.create_project.assert_called_once_with("New Project", "/new", None)
    
    @pytest.mark.asyncio
    async def test_select_project(self, facade, mock_project_service, mock_context_service, mock_state_manager):
        """Test selecting a project."""
        project_id = uuid4()
        
        # Select project
        await facade.select_project(project_id)
        
        # Verify calls
        mock_project_service.set_current_project.assert_called_once_with(project_id)
        mock_context_service.load_context.assert_called_once_with(project_id)
        mock_state_manager.update_state.assert_called_once_with({"current_project_id": project_id})
    
    @pytest.mark.asyncio
    async def test_propose_command(self, facade, mock_project_service, mock_context_service, mock_ai_orchestrator, mock_command_engine):
        """Test proposing a command."""
        # Setup mocks
        project = create_test_project(name="Test", path="/test")
        mock_project_service.get_current_project.return_value = project
        
        command = Command(
            id=uuid4(),
            project_id=project.id,
            command_text="echo test",
            ai_reasoning="Test command",
            status=CommandStatus.PROPOSED
        )
        mock_command_engine.propose_command.return_value = command
        
        # Propose command
        result = await facade.propose_command("run a test")
        
        # Verify
        assert result == command
        mock_ai_orchestrator.generate_command.assert_called_once()
        mock_command_engine.propose_command.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_propose_command_no_project(self, facade, mock_project_service):
        """Test proposing a command with no project selected."""
        mock_project_service.get_current_project.return_value = None
        
        # Should raise error
        with pytest.raises(ValueError, match="No project selected"):
            await facade.propose_command("test")
    
    @pytest.mark.asyncio
    async def test_toggle_autopilot(self, facade, mock_state_manager):
        """Test toggling autopilot mode."""
        # Setup initial state
        state = ApplicationState(
            current_project_id=None,
            autopilot_enabled=False,
            selected_ai_model="claude",
            ui_preferences={}
        )
        mock_state_manager.get_state.return_value = state
        
        # Toggle autopilot
        result = await facade.toggle_autopilot()
        
        # Verify
        assert result is True
        mock_state_manager.update_state.assert_called_once_with({"autopilot_enabled": True})
    
    @pytest.mark.asyncio
    async def test_get_available_models(self, facade, mock_ai_orchestrator):
        """Test getting available AI models."""
        models = await facade.get_available_models()
        
        assert models == ["claude", "gpt-4"]
        mock_ai_orchestrator.get_available_models.assert_called_once()
    
    def test_core_event_handlers(self, facade):
        """Test that core event handlers emit UI events."""
        # Set up UI event handler
        ui_handler = Mock()
        facade.on_ui_event("ui.command.proposed", ui_handler)
        
        # Simulate core event
        core_event = Event(
            type=EventTypes.COMMAND_PROPOSED,
            payload={"command_id": "123", "command_text": "test"}
        )
        facade._handle_command_proposed(core_event)
        
        # Check UI event was emitted
        ui_handler.assert_called_once()
        ui_event = ui_handler.call_args[0][0]
        assert ui_event.type == "ui.command.proposed"
        assert ui_event.payload == core_event.payload
    
    @pytest.mark.asyncio
    async def test_initialize(self, facade, mock_state_manager, mock_context_service):
        """Test facade initialization."""
        # Setup state with current project
        project_id = uuid4()
        state = ApplicationState(
            current_project_id=project_id,
            autopilot_enabled=True,
            selected_ai_model="claude",
            ui_preferences={}
        )
        mock_state_manager.get_state.return_value = state
        
        # Initialize
        await facade.initialize()
        
        # Verify context was loaded
        mock_context_service.load_context.assert_called_once_with(project_id)
    
    @pytest.mark.asyncio
    async def test_initialize_with_invalid_project(self, facade, mock_state_manager, mock_context_service):
        """Test initialization with invalid current project."""
        # Setup state with current project
        project_id = uuid4()
        state = ApplicationState(
            current_project_id=project_id,
            autopilot_enabled=True,
            selected_ai_model="claude",
            ui_preferences={}
        )
        mock_state_manager.get_state.return_value = state
        
        # Make context loading fail
        mock_context_service.load_context.side_effect = Exception("Project not found")
        
        # Initialize
        await facade.initialize()
        
        # Verify state was cleared
        mock_state_manager.update_state.assert_called_once_with({"current_project_id": None})
    
    @pytest.mark.asyncio
    async def test_shutdown(self, facade, mock_state_manager):
        """Test facade shutdown."""
        # Add some handlers
        facade.on_ui_event("test", Mock())
        
        # Shutdown
        await facade.shutdown()
        
        # Verify state was accessed (triggers persistence)
        mock_state_manager.get_state.assert_called_once()
        
        # Verify handlers were cleared
        assert len(facade._ui_event_handlers) == 0