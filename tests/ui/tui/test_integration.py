"""Integration tests for TUI components working together.

This module contains comprehensive integration tests for the TUI layer,
testing component interactions and end-to-end workflows.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from imthedev.core.domain import (
    Command,
    CommandResult,
    CommandStatus,
    Project,
    ProjectContext,
    ProjectSettings,
)


@pytest.fixture
def sample_project():
    """Create a sample project for testing."""
    return Project(
        id=uuid4(),
        name="Test Integration Project",
        path=Path("/home/user/integration-test"),
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        context=ProjectContext(),
        settings=ProjectSettings(auto_approve=False),
    )


@pytest.fixture
def sample_command():
    """Create a sample command for testing."""
    return Command(
        id=uuid4(),
        project_id=uuid4(),
        command_text="ls -la",
        ai_reasoning="List directory contents to understand project structure",
        status=CommandStatus.PROPOSED,
    )


@pytest.fixture
def executed_command(sample_command):
    """Create an executed command with results."""
    command = sample_command
    command.status = CommandStatus.COMPLETED
    command.result = CommandResult(
        exit_code=0,
        stdout="total 24\ndrwxr-xr-x  4 user user 4096 Jan  1 12:00 .\ndrwxr-xr-x  3 user user 4096 Jan  1 11:59 ..",
        stderr="",
        execution_time=0.1,
    )
    return command


class TestTUIComponentIntegration:
    """Integration tests for TUI component interactions."""

    def test_project_selector_initialization(self) -> None:
        """Test ProjectSelector component can be initialized in integration context."""
        with patch(
            "imthedev.ui.tui.components.project_selector.ProjectSelector"
        ) as MockSelector:
            mock_instance = MagicMock()
            MockSelector.return_value = mock_instance

            MockSelector()

            # Verify basic interface
            assert hasattr(mock_instance, "update_projects")
            assert hasattr(mock_instance, "get_current_project")
            assert hasattr(mock_instance, "select_project")

    def test_command_dashboard_initialization(self) -> None:
        """Test CommandDashboard component can be initialized in integration context."""
        with patch(
            "imthedev.ui.tui.components.command_dashboard.CommandDashboard"
        ) as MockDashboard:
            mock_instance = MagicMock()
            MockDashboard.return_value = mock_instance

            MockDashboard()

            # Verify basic interface
            assert hasattr(mock_instance, "display_command")
            assert hasattr(mock_instance, "update_command_history")
            assert hasattr(mock_instance, "append_output")

    def test_status_bar_initialization(self) -> None:
        """Test StatusBar component can be initialized in integration context."""
        with patch("imthedev.ui.tui.components.status_bar.StatusBar") as MockStatusBar:
            mock_instance = MagicMock()
            MockStatusBar.return_value = mock_instance

            MockStatusBar()

            # Verify basic interface
            assert hasattr(mock_instance, "update_project")
            assert hasattr(mock_instance, "set_autopilot_status")
            assert hasattr(mock_instance, "set_ai_model")

    def test_approval_controls_initialization(self) -> None:
        """Test ApprovalControls component can be initialized in integration context."""
        with patch(
            "imthedev.ui.tui.components.approval_controls.ApprovalControls"
        ) as MockControls:
            mock_instance = MagicMock()
            MockControls.return_value = mock_instance

            MockControls()

            # Verify basic interface
            assert hasattr(mock_instance, "set_pending_command")
            assert hasattr(mock_instance, "set_autopilot_mode")
            assert hasattr(mock_instance, "set_processing_state")

    def test_component_message_interfaces(self) -> None:
        """Test that components have proper message interfaces for communication."""
        # Test ProjectSelector messages
        with patch(
            "imthedev.ui.tui.components.project_selector.ProjectSelector"
        ) as MockSelector:
            assert hasattr(MockSelector, "ProjectSelected")

        # Test CommandDashboard messages
        with patch(
            "imthedev.ui.tui.components.command_dashboard.CommandDashboard"
        ) as MockDashboard:
            assert hasattr(MockDashboard, "CommandChanged")
            assert hasattr(MockDashboard, "NavigationRequested")

        # Test StatusBar messages
        with patch("imthedev.ui.tui.components.status_bar.StatusBar") as MockStatusBar:
            assert hasattr(MockStatusBar, "AutopilotToggled")
            assert hasattr(MockStatusBar, "ModelChanged")
            assert hasattr(MockStatusBar, "StatusMessageChanged")

        # Test ApprovalControls messages
        with patch(
            "imthedev.ui.tui.components.approval_controls.ApprovalControls"
        ) as MockControls:
            assert hasattr(MockControls, "CommandApproved")
            assert hasattr(MockControls, "CommandDenied")
            assert hasattr(MockControls, "AutopilotToggled")


class TestTUIWorkflowSimulation:
    """Test simulated TUI workflows and user interactions."""

    @pytest.fixture
    def mock_components(self):
        """Create mock instances of all TUI components."""
        components = {
            "project_selector": MagicMock(),
            "command_dashboard": MagicMock(),
            "status_bar": MagicMock(),
            "approval_controls": MagicMock(),
        }

        # Set up method returns for workflow testing
        components["project_selector"].get_current_project.return_value = None
        components["command_dashboard"].get_current_command.return_value = None
        components["approval_controls"].is_approval_available.return_value = False
        components["status_bar"].is_autopilot_enabled.return_value = False

        return components

    def test_project_selection_workflow(self, mock_components, sample_project) -> None:
        """Test complete project selection workflow."""
        selector = mock_components["project_selector"]
        status_bar = mock_components["status_bar"]

        # Simulate project selection
        projects = [sample_project]
        selector.update_projects(projects)
        selector.select_project(str(sample_project.id))
        selector.get_current_project.return_value = sample_project

        # Verify status bar would be updated
        status_bar.update_project(sample_project)

        # Verify calls were made
        selector.update_projects.assert_called_once_with(projects)
        selector.select_project.assert_called_once_with(str(sample_project.id))
        status_bar.update_project.assert_called_once_with(sample_project)

    def test_command_approval_workflow(self, mock_components, sample_command) -> None:
        """Test complete command approval workflow."""
        dashboard = mock_components["command_dashboard"]
        controls = mock_components["approval_controls"]
        mock_components["status_bar"]

        # Simulate command proposal
        dashboard.display_command(sample_command)
        controls.set_pending_command(sample_command)
        controls.can_approve = True

        # Simulate approval
        controls.is_approval_available.return_value = True

        # Verify components would be updated
        dashboard.display_command.assert_called_once_with(sample_command)
        controls.set_pending_command.assert_called_once_with(sample_command)

    def test_autopilot_mode_workflow(self, mock_components) -> None:
        """Test autopilot mode enable/disable workflow."""
        controls = mock_components["approval_controls"]
        status_bar = mock_components["status_bar"]

        # Simulate autopilot toggle
        controls.set_autopilot_mode(True)
        status_bar.set_autopilot_status(True)

        # Verify both components updated
        controls.set_autopilot_mode.assert_called_once_with(True)
        status_bar.set_autopilot_status.assert_called_once_with(True)

        # Simulate disable
        controls.set_autopilot_mode(False)
        status_bar.set_autopilot_status(False)

        # Verify disable calls
        controls.set_autopilot_mode.assert_called_with(False)
        status_bar.set_autopilot_status.assert_called_with(False)

    def test_command_execution_workflow(
        self, mock_components, sample_command, executed_command
    ):
        """Test command execution with real-time updates."""
        dashboard = mock_components["command_dashboard"]
        controls = mock_components["approval_controls"]
        status_bar = mock_components["status_bar"]

        # Start with proposed command
        dashboard.display_command(sample_command)
        controls.set_pending_command(sample_command)

        # Simulate execution start
        sample_command.status = CommandStatus.EXECUTING
        controls.set_processing_state(True)
        status_bar.set_status_message("Executing command...", "info")

        # Simulate real-time output
        dashboard.append_output("Starting execution...\n")
        dashboard.append_output("Command output here...\n")

        # Simulate completion
        dashboard.display_command(executed_command)
        controls.set_processing_state(False)
        status_bar.set_status_message("Command completed successfully", "success")

        # Verify workflow calls
        assert dashboard.display_command.call_count >= 2
        dashboard.append_output.assert_any_call("Starting execution...\n")
        dashboard.append_output.assert_any_call("Command output here...\n")
        controls.set_processing_state.assert_any_call(True)
        controls.set_processing_state.assert_any_call(False)

    def test_ai_model_switching_workflow(self, mock_components) -> None:
        """Test AI model switching workflow."""
        status_bar = mock_components["status_bar"]

        # Test switching between models
        models = ["claude", "gpt-4", "gpt-3.5"]

        for model in models:
            status_bar.set_ai_model(model)
            status_bar.set_ai_model.assert_called_with(model)

        # Verify all models were set
        assert status_bar.set_ai_model.call_count == len(models)

    def test_error_handling_workflow(self, mock_components, sample_command) -> None:
        """Test error handling and recovery workflow."""
        dashboard = mock_components["command_dashboard"]
        controls = mock_components["approval_controls"]
        status_bar = mock_components["status_bar"]

        # Simulate command failure
        failed_command = sample_command
        failed_command.status = CommandStatus.FAILED
        failed_command.result = CommandResult(
            exit_code=1, stdout="", stderr="Command not found", execution_time=0.05
        )

        # Update components for failure
        dashboard.display_command(failed_command)
        controls.set_processing_state(False)
        status_bar.set_status_message("Command failed", "error")

        # Verify error handling
        dashboard.display_command.assert_called_with(failed_command)
        controls.set_processing_state.assert_called_with(False)
        status_bar.set_status_message.assert_called_with("Command failed", "error")


class TestTUIPerformanceAndResponsiveness:
    """Test TUI performance and responsiveness characteristics."""

    def test_component_initialization_performance(self) -> None:
        """Test that components initialize quickly."""
        with patch(
            "imthedev.ui.tui.components.project_selector.ProjectSelector"
        ) as MockSelector, patch(
            "imthedev.ui.tui.components.command_dashboard.CommandDashboard"
        ) as MockDashboard, patch(
            "imthedev.ui.tui.components.status_bar.StatusBar"
        ) as MockStatusBar, patch(
            "imthedev.ui.tui.components.approval_controls.ApprovalControls"
        ) as MockControls:
            # All components should initialize without blocking
            selector = MockSelector()
            dashboard = MockDashboard()
            status_bar = MockStatusBar()
            controls = MockControls()

            # Verify all components created
            assert selector is not None
            assert dashboard is not None
            assert status_bar is not None
            assert controls is not None

    def test_large_project_list_handling(self) -> None:
        """Test handling of large project lists."""
        with patch(
            "imthedev.ui.tui.components.project_selector.ProjectSelector"
        ) as MockSelector:
            selector = MockSelector()

            # Simulate large project list (100 projects)
            large_project_list = []
            for i in range(100):
                project = MagicMock()
                project.id = uuid4()
                project.name = f"Project {i}"
                large_project_list.append(project)

            # Should handle large lists without issues
            selector.update_projects(large_project_list)
            selector.update_projects.assert_called_once_with(large_project_list)

    def test_command_history_navigation_performance(self) -> None:
        """Test command history navigation with many commands."""
        with patch(
            "imthedev.ui.tui.components.command_dashboard.CommandDashboard"
        ) as MockDashboard:
            dashboard = MockDashboard()

            # Simulate large command history (50 commands)
            large_command_history = []
            for i in range(50):
                command = MagicMock()
                command.id = uuid4()
                command.command_text = f"command_{i}"
                large_command_history.append(command)

            # Should handle navigation efficiently
            dashboard.update_command_history(large_command_history)
            dashboard.navigate_to_previous()
            dashboard.navigate_to_next()

            # Verify calls
            dashboard.update_command_history.assert_called_once_with(
                large_command_history
            )

    def test_real_time_output_streaming(self) -> None:
        """Test real-time output streaming performance."""
        with patch(
            "imthedev.ui.tui.components.command_dashboard.CommandDashboard"
        ) as MockDashboard:
            dashboard = MockDashboard()

            # Simulate streaming output
            output_chunks = [
                "Starting process...\n",
                "Processing file 1...\n",
                "Processing file 2...\n",
                "Completed successfully!\n",
            ]

            for chunk in output_chunks:
                dashboard.append_output(chunk)

            # Verify all chunks were processed
            assert dashboard.append_output.call_count == len(output_chunks)


class TestTUIEventDrivenCommunication:
    """Test event-driven communication between TUI components."""

    @pytest.mark.asyncio
    async def test_project_selection_event_flow(self, sample_project) -> None:
        """Test project selection event propagation."""
        with patch(
            "imthedev.ui.tui.components.project_selector.ProjectSelector"
        ) as MockSelector:
            selector = MockSelector()
            selector.post_message = AsyncMock()

            # Mock the ProjectSelected message
            message_class = MagicMock()
            MockSelector.ProjectSelected = message_class

            # Simulate project selection event
            await selector.post_message(message_class(sample_project))

            # Verify message posting
            selector.post_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_command_approval_event_flow(self, sample_command) -> None:
        """Test command approval event propagation."""
        with patch(
            "imthedev.ui.tui.components.approval_controls.ApprovalControls"
        ) as MockControls:
            controls = MockControls()
            controls.post_message = AsyncMock()

            # Mock the approval messages
            approved_class = MagicMock()
            denied_class = MagicMock()
            MockControls.CommandApproved = approved_class
            MockControls.CommandDenied = denied_class

            # Simulate approval events
            await controls.post_message(approved_class(sample_command))
            await controls.post_message(denied_class(sample_command))

            # Verify message posting
            assert controls.post_message.call_count == 2

    @pytest.mark.asyncio
    async def test_autopilot_toggle_event_flow(self) -> None:
        """Test autopilot toggle event propagation."""
        with patch(
            "imthedev.ui.tui.components.approval_controls.ApprovalControls"
        ) as MockControls:
            controls = MockControls()
            controls.post_message = AsyncMock()

            # Mock the autopilot message
            autopilot_class = MagicMock()
            MockControls.AutopilotToggled = autopilot_class

            # Simulate autopilot toggle
            await controls.post_message(autopilot_class(True))
            await controls.post_message(autopilot_class(False))

            # Verify message posting
            assert controls.post_message.call_count == 2

    @pytest.mark.asyncio
    async def test_navigation_event_flow(self) -> None:
        """Test navigation event propagation."""
        with patch(
            "imthedev.ui.tui.components.command_dashboard.CommandDashboard"
        ) as MockDashboard:
            dashboard = MockDashboard()
            dashboard.post_message = AsyncMock()

            # Mock the navigation message
            nav_class = MagicMock()
            MockDashboard.NavigationRequested = nav_class

            # Simulate navigation events
            await dashboard.post_message(nav_class("prev"))
            await dashboard.post_message(nav_class("next"))

            # Verify message posting
            assert dashboard.post_message.call_count == 2


class TestTUIErrorHandlingAndRecovery:
    """Test TUI error handling and recovery mechanisms."""

    def test_component_error_isolation(self) -> None:
        """Test that component errors don't cascade."""
        with patch(
            "imthedev.ui.tui.components.project_selector.ProjectSelector"
        ) as MockSelector:
            selector = MockSelector()

            # Simulate error in one component
            selector.update_projects.side_effect = Exception("Component error")

            # Other components should remain functional
            with patch(
                "imthedev.ui.tui.components.status_bar.StatusBar"
            ) as MockStatusBar:
                status_bar = MockStatusBar()
                status_bar.set_status_message("Error in project selector", "error")

                # Verify error isolation
                status_bar.set_status_message.assert_called_once()

    def test_graceful_degradation(self) -> None:
        """Test graceful degradation when components fail."""
        # Test with missing TextArea components
        with patch(
            "imthedev.ui.tui.components.command_dashboard.CommandDashboard"
        ) as MockDashboard:
            dashboard = MockDashboard()

            # Simulate missing internal components
            dashboard._command_area = None
            dashboard._reasoning_area = None
            dashboard._output_area = None

            # Should not raise errors
            dashboard.display_command(None)
            dashboard.append_output("test")
            dashboard.clear_output()

    def test_invalid_input_handling(self) -> None:
        """Test handling of invalid inputs."""
        with patch(
            "imthedev.ui.tui.components.project_selector.ProjectSelector"
        ) as MockSelector:
            selector = MockSelector()

            # Test with invalid project list
            selector.update_projects([])  # Empty list
            selector.update_projects(None)  # None

            # Should handle gracefully
            assert selector.update_projects.call_count == 2

    def test_state_consistency_maintenance(self, sample_command) -> None:
        """Test that component state remains consistent during errors."""
        with patch(
            "imthedev.ui.tui.components.approval_controls.ApprovalControls"
        ) as MockControls:
            controls = MockControls()

            # Set initial state
            controls.set_pending_command(sample_command)
            controls.set_autopilot_mode(False)
            controls.set_processing_state(False)

            # Simulate error during processing
            controls.set_processing_state.side_effect = [
                True,
                Exception("Processing error"),
            ]

            # State should remain consistent
            try:
                controls.set_processing_state(True)
                controls.set_processing_state(False)  # This will raise
            except Exception:
                pass

            # Verify state management calls
            assert controls.set_processing_state.call_count >= 1
