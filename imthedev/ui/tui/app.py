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
from imthedev.infrastructure.config import AppConfig, ConfigManager
from imthedev.ui.tui.components.approval_controls import ApprovalControls
from imthedev.ui.tui.components.command_dashboard import CommandDashboard
from imthedev.ui.tui.components.configuration_screen import ConfigurationScreen
from imthedev.ui.tui.components.project_selector import ProjectSelector
from imthedev.core.services.project_persistence import ProjectPersistenceService


class ImTheDevApp(App):
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
        ("ctrl+s", "show_settings", "Settings"),
        ("?", "show_help", "Help"),
    ]

    def __init__(self) -> None:
        """Initialize the ImTheDevApp."""
        super().__init__()
        self.project_selector: ProjectSelector | None = None
        self.command_dashboard: CommandDashboard | None = None
        self.approval_controls: ApprovalControls | None = None
        self.configuration_screen: ConfigurationScreen | None = None
        self.current_project_id: UUID | None = None
        self.config: AppConfig | None = None
        self.config_manager: ConfigManager | None = None
        self.showing_settings = False

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

            # Center panel: Enhanced Command dashboard with Gemini-first approach
            with Vertical(id="center-panel"):
                yield Static("[bold]AI Command Generation - Powered by Gemini[/bold]", id="workflow-header")
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
        # Load projects from disk or initialize with sample
        if self.project_selector:
            # Try to load existing projects
            self.project_selector.load_projects_from_disk()
            
            # If no projects found, create sample projects
            if self.project_selector.get_project_count() == 0:
                self.log("No projects found, creating sample projects...")
                sample_projects = [
                    Project.create(
                        name="Web App Project",
                        path=Path("~/projects/webapp").expanduser(),
                    ),
                    Project.create(
                        name="API Service",
                        path=Path("~/projects/api").expanduser(),
                    ),
                    Project.create(
                        name="ML Pipeline",
                        path=Path("~/projects/ml-pipeline").expanduser(),
                    ),
                ]
                self.project_selector.update_projects(sample_projects)

        # Set initial focus to project selector
        if self.project_selector:
            self.project_selector.focus()
            
            # Subscribe to project events
            self.project_selector.ProjectCreated.subscribe(self.on_project_created)
            self.project_selector.ProjectUpdated.subscribe(self.on_project_updated)
            self.project_selector.ProjectDeleted.subscribe(self.on_project_deleted)

        self.log("ImTheDevApp initialized and ready")
    
    def on_project_created(self, message: ProjectSelector.ProjectCreated) -> None:
        """Handle project creation."""
        self.log(f"Project created: {message.project.name} at {message.project.path}")
    
    def on_project_updated(self, message: ProjectSelector.ProjectUpdated) -> None:
        """Handle project update."""
        self.log(f"Project updated: {message.project.name}")
    
    def on_project_deleted(self, message: ProjectSelector.ProjectDeleted) -> None:
        """Handle project deletion."""
        self.log(f"Project deleted: {message.project_id}")

    def action_new_project(self) -> None:
        """Handle the new project action."""
        # Delegate to the ProjectSelector's new project action
        if self.project_selector:
            self.project_selector.action_new_project()
            self.log("Opening new project dialog...")

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
  Ctrl+S - Open settings

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
    
    def action_show_settings(self) -> None:
        """Show the configuration settings screen."""
        if self.showing_settings:
            # Hide settings screen
            if self.configuration_screen:
                self.configuration_screen.remove()
                self.configuration_screen = None
            self.showing_settings = False
        else:
            # Load current configuration
            if not self.config_manager:
                self.config_manager = ConfigManager()
            
            if not self.config:
                try:
                    self.config = self.config_manager.load_config()
                except Exception as e:
                    self.log(f"Error loading configuration: {e}")
                    return
            
            # Create and show configuration screen
            self.configuration_screen = ConfigurationScreen(
                config=self.config,
                on_save=self._save_configuration,
                on_cancel=self._close_configuration,
            )
            
            # Mount as an overlay
            self.mount(self.configuration_screen)
            self.showing_settings = True
    
    def _save_configuration(self, config: AppConfig) -> None:
        """Save the configuration to file.
        
        Args:
            config: The updated configuration to save
        """
        if self.config_manager:
            try:
                # Note: save_config method needs to be implemented in ConfigManager
                # For now, we'll just update the in-memory config
                self.config = config
                self.log("Configuration saved successfully!")
                self._close_configuration()
            except Exception as e:
                self.log(f"Error saving configuration: {e}")
    
    def _close_configuration(self) -> None:
        """Close the configuration screen."""
        if self.configuration_screen:
            self.configuration_screen.remove()
            self.configuration_screen = None
        self.showing_settings = False

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
        self.log(f"Command submitted via {message.model}: {message.command} (ID: {message.command_id})")

        # Set as pending in approval controls
        if self.approval_controls:
            self.approval_controls.set_pending_command(message.command_id)

    def on_command_dashboard_command_generated(
        self, message: CommandDashboard.CommandGenerated
    ) -> None:
        """Handle command generation from the CommandDashboard.

        Args:
            message: The command generated message
        """
        self.log(f"Command generated using {message.model}: {message.command}")
        self.log(f"AI Reasoning: {message.reasoning}")
        
        # Set pending command in approval controls
        if self.approval_controls:
            command_id = str(uuid4())
            self.approval_controls.set_pending_command(command_id)

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
