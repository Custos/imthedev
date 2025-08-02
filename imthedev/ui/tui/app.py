"""Main TUI application for imthedev.

This module provides the central Textual application that orchestrates
all UI components for the imthedev terminal interface.
Compatible with Textual v5.0.1.
"""

from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from imthedev.core.domain import Project
from imthedev.ui.tui.components.approval_controls import ApprovalControls
from imthedev.ui.tui.components.command_dashboard import CommandDashboard
from imthedev.ui.tui.components.project_selector import ProjectSelector


class ImTheDevApp(App[None]):
    """Main TUI application for imthedev.

    This app provides a keyboard-driven interface for managing AI-assisted
    development workflows across multiple projects.
    """

    TITLE = "imthedev - AI Development Assistant"
    CSS_PATH = "app.css"

    # Define global key bindings
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("n", "new_project", "New Project"),
        ("tab", "focus_next", "Next Focus"),
        ("shift+tab", "focus_previous", "Previous Focus"),
        ("ctrl+p", "toggle_project_list", "Toggle Projects"),
        ("ctrl+c", "clear_command", "Clear Command"),
        ("?", "show_help", "Help"),
    ]

    def __init__(self) -> None:
        """Initialize the ImTheDevApp."""
        super().__init__()
        self.project_selector: ProjectSelector | None = None
        self.command_dashboard: CommandDashboard | None = None
        self.approval_controls: ApprovalControls | None = None
        self.current_project_id: UUID | None = None

    def compose(self) -> ComposeResult:
        """Compose the main application layout."""
        # Header shows app title and current context
        yield Header()

        # Main content area with three panels
        with Container(id="main-container"), Horizontal(id="content-area"):
            # Left panel: Project selector
            with Vertical(id="left-panel"):
                yield Static("[bold]Projects[/bold]", id="projects-header")
                self.project_selector = ProjectSelector(id="project-selector")
                yield self.project_selector

            # Center panel: Command dashboard
            with Vertical(id="center-panel"):
                yield Static("[bold]Command Workflow[/bold]", id="workflow-header")
                self.command_dashboard = CommandDashboard(id="command-dashboard")
                yield self.command_dashboard

            # Right panel: Approval controls
            with Vertical(id="right-panel"):
                self.approval_controls = ApprovalControls(id="approval-controls")
                yield self.approval_controls

        # Footer shows key bindings
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted. Initialize with sample data."""
        # Initialize with sample projects
        sample_projects = [
            Project.create(
                name="Web App Project",
                path=Path("~/projects/webapp"),
            ),
            Project.create(
                name="API Service",
                path=Path("~/projects/api"),
            ),
            Project.create(
                name="ML Pipeline",
                path=Path("~/projects/ml-pipeline"),
            ),
        ]

        if self.project_selector:
            self.project_selector.update_projects(sample_projects)

        # Set initial focus to project selector
        if self.project_selector:
            self.project_selector.focus()

        self.log("ImTheDevApp initialized and ready")

    def action_new_project(self) -> None:
        """Handle the new project action."""
        # Generate a new dummy project
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_project_name = f"New Project {timestamp}"
        new_project_path = f"~/projects/new_{timestamp}"

        self.log(f"Creating new project: {new_project_name}")

        # Add to project selector
        if self.project_selector:
            current_projects = (
                list(self.project_selector.projects)
                if self.project_selector.projects
                else []
            )
            new_project = Project.create(
                name=new_project_name,
                path=Path(new_project_path),
            )
            current_projects.append(new_project)
            self.project_selector.update_projects(current_projects)

    def action_toggle_project_list(self) -> None:
        """Toggle visibility of the project list."""
        left_panel = self.query_one("#left-panel")
        left_panel.visible = not left_panel.visible
        self.log(f"Project list {'shown' if left_panel.visible else 'hidden'}")

    def action_clear_command(self) -> None:
        """Clear the current command."""
        if self.command_dashboard:
            self.command_dashboard.action_clear_command()

    def action_show_help(self) -> None:
        """Show help information."""
        help_text = """
imthedev Help:
  Tab/Shift+Tab - Navigate between panels
  N - Create new project
  Q - Quit application
  Ctrl+P - Toggle project list
  Ctrl+C - Clear current command

 In Project List:
  Enter - Select project
  Up/Down - Navigate projects

 In Command Dashboard:
  Ctrl+Enter - Submit command
  Escape - Clear command
  Up/Down - Navigate command history

 In Approval Controls:
  A - Approve command
  D - Deny command
  P - Toggle autopilot mode
"""
        self.log(help_text)

    # Message handlers for component communication

    def on_project_selector_project_selected(
        self, message: ProjectSelector.ProjectSelected
    ) -> None:
        """Handle project selection from the ProjectSelector.

        Args:
            message: The project selected message
        """
        self.current_project_id = message.project.id
        self.log(f"Project selected: {message.project.name} (ID: {message.project.id})")

        # Update the header to show current project
        # Note: Header widget in this version doesn't support sub_title attribute
        # This would be implemented with a custom header widget

        # Simulate AI proposing a command for the selected project
        if self.command_dashboard:
            sample_command = (
                f"cd {message.project.name.lower().replace(' ', '-')} && git status"
            )
            self.command_dashboard.update_current_command(sample_command)

            # Set pending command in approval controls
            if self.approval_controls:
                command_id = str(uuid4())
                self.approval_controls.set_pending_command(command_id)

    def on_command_dashboard_command_submitted(
        self, message: CommandDashboard.CommandSubmitted
    ) -> None:
        """Handle command submission from the CommandDashboard.

        Args:
            message: The command submitted message
        """
        self.log(f"Command submitted: {message.command} (ID: {message.command_id})")

        # Set as pending in approval controls
        if self.approval_controls:
            self.approval_controls.set_pending_command(message.command_id)

    def on_command_dashboard_command_cleared(
        self, message: CommandDashboard.CommandCleared
    ) -> None:
        """Handle command clearing from the CommandDashboard.

        Args:
            message: The command cleared message
        """
        del message  # Currently unused
        self.log("Command cleared")

        # Clear pending command in approval controls
        if self.approval_controls:
            self.approval_controls.set_pending_command(None)

    def on_approval_controls_command_approved(
        self, message: ApprovalControls.CommandApproved
    ) -> None:
        """Handle command approval from ApprovalControls.

        Args:
            message: The command approved message
        """
        self.log(f"Command approved: {message.command_id}")

        # Update command status in dashboard
        if self.command_dashboard:
            self.command_dashboard.update_command_status(
                message.command_id, "completed"
            )

        # Simulate command execution and AI proposing next command
        if self.command_dashboard:
            next_command = "npm install && npm run build"
            self.command_dashboard.update_current_command(next_command)

            # Set new pending command
            if self.approval_controls:
                new_command_id = str(uuid4())
                self.approval_controls.set_pending_command(new_command_id)

    def on_approval_controls_command_denied(
        self, message: ApprovalControls.CommandDenied
    ) -> None:
        """Handle command denial from ApprovalControls.

        Args:
            message: The command denied message
        """
        self.log(f"Command denied: {message.command_id}")

        # Update command status in dashboard
        if self.command_dashboard:
            self.command_dashboard.update_command_status(
                message.command_id, "cancelled"
            )

        # Clear current command
        if self.command_dashboard:
            self.command_dashboard.action_clear_command()

    def on_approval_controls_autopilot_toggled(
        self, message: ApprovalControls.AutopilotToggled
    ) -> None:
        """Handle autopilot toggle from ApprovalControls.

        Args:
            message: The autopilot toggled message
        """
        mode = "enabled" if message.enabled else "disabled"
        self.log(f"Autopilot mode {mode}")

        # Update header to show autopilot status
        # Note: Header widget in this version doesn't support text attribute
        # This would be implemented with a custom header widget


if __name__ == "__main__":
    app = ImTheDevApp()
    app.run()
