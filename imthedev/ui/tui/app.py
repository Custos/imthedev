"""Main application module for imthedev TUI.

This module contains the main Textual application class that orchestrates
all TUI components and manages the overall application lifecycle.
Compatible with Textual v5.0.1.
"""

from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header

from imthedev.core import Event
from imthedev.ui.tui.components import (
    ApprovalControls,
    CommandDashboard,
    ProjectSelector,
    StatusBar,
)
from imthedev.ui.tui.facade import CoreFacade


class ImTheDevApp(App):
    """Main TUI application for imthedev.
    
    This application provides a keyboard-driven interface for managing
    SuperClaude workflows with project selection, command approval,
    and AI model management.
    
    Attributes:
        CSS_PATH: Path to the application stylesheet (if any)
        BINDINGS: Application-level key bindings
        TITLE: Application title displayed in the header
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("p", "toggle_autopilot", "Toggle Autopilot"),
        ("a", "approve_command", "Approve"),
        ("d", "deny_command", "Deny"),
        ("n", "create_project", "New Project"),
        ("tab", "focus_next", "Next"),
        ("shift+tab", "focus_previous", "Previous"),
        ("ctrl+p", "focus_projects", "Focus Projects"),
        ("ctrl+c", "focus_commands", "Focus Commands"),
    ]
    
    TITLE = "imthedev - SuperClaude Workflow Manager"
    
    def __init__(self, core_facade: Optional[CoreFacade] = None) -> None:
        """Initialize the application.
        
        Args:
            core_facade: Optional facade for core services integration
        """
        super().__init__()
        self.autopilot_enabled = False
        self.current_focus_widget: Optional[str] = None
        self.core_facade = core_facade
        
        # Register for UI events if facade is provided
        if self.core_facade:
            self._register_ui_event_handlers()
    
    def compose(self) -> ComposeResult:
        """Compose the application layout.
        
        Creates the main application layout with:
        - Header at the top
        - Main content area with project selector and command dashboard
        - Approval controls below the main content
        - Status bar at the bottom
        - Footer with key bindings help
        
        Yields:
            ComposeResult: The composed widget hierarchy
        """
        # Application header
        yield Header()
        
        # Main content container
        with Container(id="main-container"):
            # Horizontal layout for project selector and command area
            with Horizontal(id="content-area"):
                # Left sidebar with project selector
                with Vertical(id="sidebar", classes="sidebar"):
                    yield ProjectSelector(id="project-selector")
                
                # Main content area
                with Vertical(id="main-content", classes="main-content"):
                    # Command dashboard takes most of the space
                    yield CommandDashboard(id="command-dashboard")
                    
                    # Approval controls at the bottom of main content
                    yield ApprovalControls(id="approval-controls")
        
        # Status bar
        yield StatusBar(id="status-bar")
        
        # Footer with key bindings
        yield Footer()
    
    def action_toggle_autopilot(self) -> None:
        """Toggle autopilot mode on/off."""
        if self.core_facade:
            # Use facade to toggle autopilot
            self.run_worker(self._toggle_autopilot_async())
        else:
            # Fallback to local toggle
            self.autopilot_enabled = not self.autopilot_enabled
            
            # Update status bar to reflect autopilot state
            status_bar = self.query_one("#status-bar", StatusBar)
            if hasattr(status_bar, 'autopilot_enabled'):
                status_bar.autopilot_enabled = self.autopilot_enabled
            
            # Log the state change for debugging
            self.log(f"Autopilot mode: {'enabled' if self.autopilot_enabled else 'disabled'}")
    
    async def _toggle_autopilot_async(self) -> None:
        """Toggle autopilot asynchronously through facade."""
        new_state = await self.core_facade.toggle_autopilot()
        self.autopilot_enabled = new_state
        self.log(f"Autopilot mode: {'enabled' if new_state else 'disabled'}")
    
    async def _create_project_async(self) -> None:
        """Create a new demo project asynchronously."""
        import datetime
        from pathlib import Path
        
        # Generate a unique project name with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        project_name = f"Demo Project {timestamp}"
        project_path = Path.home() / "imthedev_projects" / f"demo_{timestamp}"
        
        try:
            # Create the project using the core facade
            project = await self.core_facade.create_project(
                name=project_name,
                path=str(project_path)
            )
            
            self.log(f"Created project: {project.name} at {project.path}")
            
            # Refresh the project list to show the new project
            await self._load_projects()
            
            # Select the newly created project
            project_selector = self.query_one("#project-selector", ProjectSelector)
            if hasattr(project_selector, 'select_project'):
                project_selector.select_project(str(project.id))
            
        except Exception as e:
            self.log(f"Failed to create project: {str(e)}")
    
    def action_approve_command(self) -> None:
        """Approve the current command."""
        if self.core_facade:
            # Get the current pending command and approve it
            # In a real implementation, we'd get the command ID from the UI
            self.log("Command approval requested - facade integration pending")
        else:
            # Get the approval controls widget
            approval_controls = self.query_one("#approval-controls", ApprovalControls)
            
            # Notify that approval was triggered
            self.log("Command approved")
    
    def action_deny_command(self) -> None:
        """Deny the current command."""
        if self.core_facade:
            # Get the current pending command and deny it
            # In a real implementation, we'd get the command ID from the UI
            self.log("Command denial requested - facade integration pending")
        else:
            # Get the approval controls widget
            approval_controls = self.query_one("#approval-controls", ApprovalControls)
            
            # Notify that denial was triggered
            self.log("Command denied")
    
    def action_focus_projects(self) -> None:
        """Focus on the project selector widget."""
        project_selector = self.query_one("#project-selector", ProjectSelector)
        project_selector.focus()
        self.current_focus_widget = "project-selector"
        self.log("Focused on project selector")
    
    def action_focus_commands(self) -> None:
        """Focus on the command dashboard widget."""
        command_dashboard = self.query_one("#command-dashboard", CommandDashboard)
        command_dashboard.focus()
        self.current_focus_widget = "command-dashboard"
        self.log("Focused on command dashboard")
    
    def action_create_project(self) -> None:
        """Create a new demo project."""
        if self.core_facade:
            self.run_worker(self._create_project_async())
        else:
            self.log("Cannot create project without core facade")
    
    def on_mount(self) -> None:
        """Called when the app is mounted."""
        # Set initial focus to project selector
        self.action_focus_projects()
        
        # Initialize core facade if available
        if self.core_facade:
            self.run_worker(self._initialize_facade())
    
    async def _initialize_facade(self) -> None:
        """Initialize the core facade asynchronously."""
        await self.core_facade.initialize()
        
        # Load initial data
        await self._load_projects()
        await self._update_ui_state()
    
    async def _load_projects(self) -> None:
        """Load projects from core and update UI."""
        if not self.core_facade:
            return
            
        projects = await self.core_facade.get_projects()
        project_selector = self.query_one("#project-selector", ProjectSelector)
        
        # Update project selector with projects
        project_selector.update_projects(projects)
    
    async def _update_ui_state(self) -> None:
        """Update UI state from core state."""
        if not self.core_facade:
            return
            
        # Update autopilot status
        self.autopilot_enabled = await self.core_facade.get_autopilot_status()
        
        # Update status bar
        status_bar = self.query_one("#status-bar", StatusBar)
        if hasattr(status_bar, 'autopilot_enabled'):
            status_bar.autopilot_enabled = self.autopilot_enabled
    
    def _register_ui_event_handlers(self) -> None:
        """Register handlers for UI events from core."""
        # Command events
        self.core_facade.on_ui_event("ui.command.proposed", self._on_command_proposed)
        self.core_facade.on_ui_event("ui.command.approved", self._on_command_approved)
        self.core_facade.on_ui_event("ui.command.rejected", self._on_command_rejected)
        self.core_facade.on_ui_event("ui.command.executing", self._on_command_executing)
        self.core_facade.on_ui_event("ui.command.completed", self._on_command_completed)
        self.core_facade.on_ui_event("ui.command.failed", self._on_command_failed)
        
        # Project events
        self.core_facade.on_ui_event("ui.project.created", self._on_project_created)
        self.core_facade.on_ui_event("ui.project.selected", self._on_project_selected)
        
        # State events
        self.core_facade.on_ui_event("ui.autopilot.enabled", self._on_autopilot_enabled)
        self.core_facade.on_ui_event("ui.autopilot.disabled", self._on_autopilot_disabled)
    
    # UI Event Handlers
    
    def _on_command_proposed(self, event: Event) -> None:
        """Handle command proposed event."""
        command_dashboard = self.query_one("#command-dashboard", CommandDashboard)
        # Update dashboard with proposed command
        self.log(f"Command proposed: {event.payload.get('command_text', '')}")
    
    def _on_command_approved(self, event: Event) -> None:
        """Handle command approved event."""
        self.log(f"Command approved: {event.payload.get('command_id', '')}")
    
    def _on_command_rejected(self, event: Event) -> None:
        """Handle command rejected event."""
        self.log(f"Command rejected: {event.payload.get('command_id', '')}")
    
    def _on_command_executing(self, event: Event) -> None:
        """Handle command executing event."""
        self.log(f"Command executing: {event.payload.get('command_id', '')}")
    
    def _on_command_completed(self, event: Event) -> None:
        """Handle command completed event."""
        self.log(f"Command completed: {event.payload.get('command_id', '')}")
    
    def _on_command_failed(self, event: Event) -> None:
        """Handle command failed event."""
        self.log(f"Command failed: {event.payload.get('command_id', '')}")
    
    def _on_project_created(self, event: Event) -> None:
        """Handle project created event."""
        self.log(f"Project created: {event.payload.get('name', '')}")
        # Reload projects
        self.run_worker(self._load_projects())
    
    def _on_project_selected(self, event: Event) -> None:
        """Handle project selected event."""
        self.log(f"Project selected: {event.payload.get('project_id', '')}")
    
    def _on_autopilot_enabled(self, event: Event) -> None:
        """Handle autopilot enabled event."""
        self.autopilot_enabled = True
        status_bar = self.query_one("#status-bar", StatusBar)
        if hasattr(status_bar, 'autopilot_enabled'):
            status_bar.autopilot_enabled = True
    
    def _on_autopilot_disabled(self, event: Event) -> None:
        """Handle autopilot disabled event."""
        self.autopilot_enabled = False
        status_bar = self.query_one("#status-bar", StatusBar)
        if hasattr(status_bar, 'autopilot_enabled'):
            status_bar.autopilot_enabled = False


# Optional: Default CSS for basic layout
DEFAULT_CSS = """
#main-container {
    height: 1fr;
}

#content-area {
    height: 1fr;
}

#sidebar {
    width: 30;
    border-right: solid $primary;
}

#main-content {
    width: 1fr;
}

#project-selector {
    height: 1fr;
    margin: 1;
    border: solid $primary-background;
}

#project-selector:focus {
    border: solid $primary;
}

#command-dashboard {
    height: 1fr;
    border: solid $primary-background;
    margin: 1;
}

#command-dashboard:focus {
    border: solid $primary;
}

#approval-controls {
    height: 5;
    border: solid $primary-background;
    margin: 1;
}

#approval-controls:focus {
    border: solid $primary;
}

#status-bar {
    height: 3;
    dock: bottom;
}

/* Highlight focused widgets */
Widget:focus {
    background: $boost;
}
"""