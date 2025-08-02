"""Tests for the main ImTheDevApp TUI application.

This tests the integration of all components and overall app functionality.
"""

import pytest

from tests.ui.tui.test_isolation import mock_tui_components, clean_imports


class TestImTheDevAppWithMocks:
    """Test ImTheDevApp with mocked components for isolated testing."""
    
    @pytest.fixture(autouse=True)
    def setup_app(self, mock_tui_components, clean_imports):
        """Set up the app with mocked components for each test."""
        # Import app after mocks are set up
        from imthedev.ui.tui.app import ImTheDevApp
        self.app_class = ImTheDevApp
        self.mocker = mock_tui_components
    
    def test_app_initialization(self):
        """Test that ImTheDevApp initializes properly."""
        app = self.app_class()
        
        # Check basic attributes
        assert app.TITLE == "imthedev - AI Development Assistant"
        assert app.CSS_PATH == "app.css"
        assert app.current_project_id is None
        
        # Check key bindings are defined
        assert len(app.BINDINGS) > 0
        binding_keys = [binding[0] for binding in app.BINDINGS]
        assert "q" in binding_keys
        assert "n" in binding_keys
        assert "tab" in binding_keys
    
    def test_compose_creates_components(self):
        """Test that compose creates all required components."""
        app = self.app_class()
        
        # Mock the necessary methods
        from unittest.mock import MagicMock
        app.query_one = MagicMock()
        
        # Call compose to create components
        components = list(app.compose())
        
        # Check that components were created
        assert app.project_selector is not None
        assert app.command_dashboard is not None
        assert app.approval_controls is not None
        
        # Verify they're instances of mocked components
        assert app.project_selector.__class__.__name__ == "ProjectSelector"
        assert app.command_dashboard.__class__.__name__ == "CommandDashboard"
        assert app.approval_controls.__class__.__name__ == "ApprovalControls"
    
    def test_action_new_project(self):
        """Test the new project action."""
        app = self.app_class()
        
        # Setup components
        from unittest.mock import MagicMock
        app.project_selector = MagicMock()
        app.project_selector.projects = []
        app.project_selector.update_projects = MagicMock()
        app.log = MagicMock()
        
        # Call action
        app.action_new_project()
        
        # Verify project selector was updated
        app.project_selector.update_projects.assert_called_once()
        
        # Verify log was called
        app.log.assert_called_once()
        log_message = app.log.call_args[0][0]
        assert "Creating new project" in log_message
    
    def test_action_toggle_project_list(self):
        """Test toggling project list visibility."""
        app = self.app_class()
        
        # Mock query_one
        from unittest.mock import MagicMock
        left_panel = MagicMock()
        left_panel.visible = True
        app.query_one = MagicMock(return_value=left_panel)
        app.log = MagicMock()
        
        # Toggle visibility
        app.action_toggle_project_list()
        
        # Check visibility was toggled
        assert left_panel.visible is False
        
        # Check log was called
        app.log.assert_called_once()
        assert "hidden" in app.log.call_args[0][0]
        
        # Toggle back
        app.action_toggle_project_list()
        assert left_panel.visible is True
        assert app.log.call_count == 2
        # Get the second call's arguments
        second_call_args = app.log.call_args_list[1][0]
        assert "shown" in second_call_args[0]
    
    def test_action_clear_command(self):
        """Test clearing the current command."""
        app = self.app_class()
        
        # Setup command dashboard
        from unittest.mock import MagicMock
        app.command_dashboard = MagicMock()
        app.command_dashboard.action_clear_command = MagicMock()
        
        # Clear command
        app.action_clear_command()
        
        # Verify dashboard method was called
        app.command_dashboard.action_clear_command.assert_called_once()
    
    def test_action_show_help(self):
        """Test showing help information."""
        app = self.app_class()
        
        # Mock log
        from unittest.mock import MagicMock
        app.log = MagicMock()
        
        # Show help
        app.action_show_help()
        
        # Verify help was logged
        app.log.assert_called_once()
        help_text = app.log.call_args[0][0]
        assert "imthedev Help" in help_text
        assert "Tab/Shift+Tab" in help_text
        assert "N - Create new project" in help_text
    
    def test_on_project_selector_project_selected(self):
        """Test handling project selection message."""
        app = self.app_class()
        
        # Setup components
        from unittest.mock import MagicMock
        from uuid import uuid4
        from pathlib import Path
        from datetime import datetime
        
        app.command_dashboard = MagicMock()
        app.command_dashboard.update_current_command = MagicMock()
        app.approval_controls = MagicMock()
        app.approval_controls.set_pending_command = MagicMock()
        app.log = MagicMock()
        
        # Create a mock project
        from imthedev.core.domain import Project
        project = Project.create(
            name="Test Project",
            path=Path("/test/path")
        )
        
        # Create message
        ProjectSelector = self.mocker.get_mock("project_selector")
        message = ProjectSelector.ProjectSelected(project=project)
        message.project = project
        
        # Handle message
        app.on_project_selector_project_selected(message)
        
        # Verify state update
        assert app.current_project_id == project.id
        
        # Verify command dashboard was updated
        app.command_dashboard.update_current_command.assert_called_once()
        
        # Verify approval controls were updated
        app.approval_controls.set_pending_command.assert_called_once()
        
        # Verify log was called
        app.log.assert_called_once()
        log_message = app.log.call_args[0][0]
        assert "Project selected: Test Project" in log_message
    
    def test_on_command_dashboard_command_submitted(self):
        """Test handling command submission message."""
        app = self.app_class()
        
        # Setup components
        from unittest.mock import MagicMock
        from uuid import uuid4
        
        app.approval_controls = MagicMock()
        app.approval_controls.set_pending_command = MagicMock()
        app.log = MagicMock()
        
        # Create message
        CommandDashboard = self.mocker.get_mock("command_dashboard")
        command_id = str(uuid4())
        message = CommandDashboard.CommandSubmitted(
            command="test command",
            command_id=command_id
        )
        
        # Handle message
        app.on_command_dashboard_command_submitted(message)
        
        # Verify approval controls were updated
        app.approval_controls.set_pending_command.assert_called_once_with(command_id)
        
        # Verify log was called
        app.log.assert_called_once()
        log_message = app.log.call_args[0][0]
        assert "Command submitted: test command" in log_message


# Integration tests that require real Textual components
@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires real Textual components, not mocked")
async def test_new_project_action_integration():
    """Test creating a new project with real components."""
    pass


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires real Textual components, not mocked")
async def test_toggle_project_list_integration():
    """Test toggling the project list visibility with real components."""
    pass


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires real Textual components, not mocked")
async def test_focus_cycling_integration():
    """Test that tab cycles focus between components with real components."""
    pass


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires real Textual components, not mocked")
async def test_component_integration():
    """Test that components communicate properly with real components."""
    pass


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires real Textual components, not mocked")
async def test_command_submission_flow_integration():
    """Test the full command submission flow with real components."""
    pass


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires real Textual components, not mocked")
async def test_autopilot_toggle_integration():
    """Test toggling autopilot mode with real components."""
    pass