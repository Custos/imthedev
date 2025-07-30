"""Main application module for imthedev TUI.

This module contains the main Textual application class that orchestrates
all TUI components and manages the overall application lifecycle.
Compatible with Textual v5.0.1.
"""

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
    ]
    
    TITLE = "imthedev - SuperClaude Workflow Manager"
    
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
        # TODO: Implement autopilot toggle logic
        pass
    
    def action_approve_command(self) -> None:
        """Approve the current command."""
        # TODO: Implement command approval logic
        pass
    
    def action_deny_command(self) -> None:
        """Deny the current command."""
        # TODO: Implement command denial logic
        pass


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

#command-dashboard {
    height: 1fr;
    border: solid $primary;
    margin: 1;
}

#approval-controls {
    height: 5;
    border: solid $primary;
    margin: 1;
}

#status-bar {
    height: 3;
    dock: bottom;
}
"""