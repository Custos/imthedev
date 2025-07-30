"""Main application module for imthedev TUI.

This module contains the main Textual application class that orchestrates
all TUI components and manages the overall application lifecycle.
Compatible with Textual v5.0.1.
"""

from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header

from imthedev.ui.tui.components import (
    ApprovalControls,
    CommandDashboard,
    ProjectSelector,
    StatusBar,
)


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
        ("tab", "focus_next", "Next"),
        ("shift+tab", "focus_previous", "Previous"),
        ("ctrl+p", "focus_projects", "Focus Projects"),
        ("ctrl+c", "focus_commands", "Focus Commands"),
    ]
    
    TITLE = "imthedev - SuperClaude Workflow Manager"
    
    def __init__(self) -> None:
        """Initialize the application."""
        super().__init__()
        self.autopilot_enabled = False
        self.current_focus_widget: Optional[str] = None
    
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
        self.autopilot_enabled = not self.autopilot_enabled
        
        # Update status bar to reflect autopilot state
        status_bar = self.query_one("#status-bar", StatusBar)
        if hasattr(status_bar, 'autopilot_enabled'):
            status_bar.autopilot_enabled = self.autopilot_enabled
        
        # Log the state change for debugging
        self.log(f"Autopilot mode: {'enabled' if self.autopilot_enabled else 'disabled'}")
    
    def action_approve_command(self) -> None:
        """Approve the current command."""
        # Get the approval controls widget
        approval_controls = self.query_one("#approval-controls", ApprovalControls)
        
        # Notify that approval was triggered
        self.log("Command approved")
        
        # In a real implementation, this would:
        # 1. Get the current pending command from CommandDashboard
        # 2. Send approval to the CommandEngine
        # 3. Update UI to reflect approval
    
    def action_deny_command(self) -> None:
        """Deny the current command."""
        # Get the approval controls widget
        approval_controls = self.query_one("#approval-controls", ApprovalControls)
        
        # Notify that denial was triggered
        self.log("Command denied")
        
        # In a real implementation, this would:
        # 1. Get the current pending command from CommandDashboard
        # 2. Send denial to the CommandEngine
        # 3. Update UI to reflect denial
    
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
    
    def on_mount(self) -> None:
        """Called when the app is mounted."""
        # Set initial focus to project selector
        self.action_focus_projects()


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