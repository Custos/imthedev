"""Status bar component for imthedev TUI.

This module provides a status bar widget showing autopilot status and current model.
Compatible with Textual v5.0.1.
"""

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static, Label

from imthedev.core.domain import Project


class StatusBar(Widget):
    """Widget for displaying application status information.
    
    This component shows the current autopilot status, selected AI model,
    and other relevant status information at the bottom of the TUI.
    
    Attributes:
        autopilot_enabled: Whether autopilot mode is currently active
        current_model: Currently selected AI model
        current_project: Currently active project
        connection_status: AI service connection status
        status_message: Temporary status message
    """
    
    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text;
        width: 100%;
    }
    
    StatusBar Horizontal {
        height: 1;
        width: 100%;
        align: left middle;
    }
    
    StatusBar .project-info {
        margin-right: 2;
        color: $text;
        text-style: bold;
    }
    
    StatusBar .autopilot-enabled {
        background: $success;
        color: $success-lighten-3;
        text-style: bold;
        margin-right: 2;
        padding: 0 1;
    }
    
    StatusBar .autopilot-disabled {
        background: $error;
        color: $error-lighten-3;
        text-style: bold;
        margin-right: 2;
        padding: 0 1;
    }
    
    StatusBar .model-info {
        background: $accent;
        color: $accent-lighten-3;
        text-style: bold;
        margin-right: 2;
        padding: 0 1;
    }
    
    StatusBar .connection-online {
        background: $success;
        color: $success-lighten-3;
        margin-right: 2;
        padding: 0 1;
    }
    
    StatusBar .connection-offline {
        background: $error;
        color: $error-lighten-3;
        margin-right: 2;
        padding: 0 1;
    }
    
    StatusBar .connection-connecting {
        background: $warning;
        color: $warning-lighten-3;
        margin-right: 2;
        padding: 0 1;
    }
    
    StatusBar .status-message {
        color: $text-muted;
        width: 1fr;
        text-align: right;
        margin-right: 1;
    }
    
    StatusBar .status-error {
        color: $error;
        text-style: bold;
    }
    
    StatusBar .status-success {
        color: $success;
        text-style: bold;
    }
    
    StatusBar .status-warning {
        color: $warning;
        text-style: bold;
    }
    """
    
    class AutopilotToggled(Message):
        """Message sent when autopilot is toggled."""
        
        def __init__(self, enabled: bool) -> None:
            self.enabled = enabled
            super().__init__()
    
    class ModelChanged(Message):
        """Message sent when AI model is changed."""
        
        def __init__(self, model: str) -> None:
            self.model = model
            super().__init__()
    
    class StatusMessageChanged(Message):
        """Message sent when status message changes."""
        
        def __init__(self, message: str, message_type: str = "info") -> None:
            self.message = message
            self.message_type = message_type  # "info", "success", "warning", "error"
            super().__init__()
    
    autopilot_enabled: reactive[bool] = reactive(False)
    current_model: reactive[str] = reactive("claude")
    connection_status: reactive[str] = reactive("offline")
    
    def __init__(self, **kwargs):
        """Initialize the StatusBar widget."""
        super().__init__(**kwargs)
        self.current_project: Optional[Project] = None
        self.status_message: str = "Ready"
        self._project_label: Optional[Static] = None
        self._autopilot_label: Optional[Static] = None
        self._model_label: Optional[Static] = None
        self._connection_label: Optional[Static] = None
        self._status_label: Optional[Static] = None
    
    def compose(self) -> ComposeResult:
        """Compose the status bar layout."""
        with Horizontal():
            # Project information
            self._project_label = Static("No project", classes="project-info")
            yield self._project_label
            
            # Autopilot status
            self._autopilot_label = Static("Manual", classes="autopilot-disabled")
            yield self._autopilot_label
            
            # AI model
            self._model_label = Static("Claude", classes="model-info")
            yield self._model_label
            
            # Connection status
            self._connection_label = Static("Offline", classes="connection-offline")
            yield self._connection_label
            
            # Status message
            self._status_label = Static("Ready", classes="status-message")
            yield self._status_label
    
    def update_project(self, project: Optional[Project]) -> None:
        """Update the current project information.
        
        Args:
            project: Current project or None if no project
        """
        self.current_project = project
        
        if not self._project_label:
            return
        
        if project:
            # Show project name and truncated path
            path_str = str(project.path)
            if len(path_str) > 30:
                path_str = "..." + path_str[-27:]
            
            display_text = f"{project.name} ({path_str})"
        else:
            display_text = "No project"
        
        self._project_label.update(display_text)
    
    def set_autopilot_status(self, enabled: bool) -> None:
        """Set the autopilot status.
        
        Args:
            enabled: Whether autopilot is enabled
        """
        self.autopilot_enabled = enabled
        
        if not self._autopilot_label:
            return
        
        if enabled:
            self._autopilot_label.update("Autopilot")
            self._autopilot_label.remove_class("autopilot-disabled")
            self._autopilot_label.add_class("autopilot-enabled")
        else:
            self._autopilot_label.update("Manual")
            self._autopilot_label.remove_class("autopilot-enabled")
            self._autopilot_label.add_class("autopilot-disabled")
    
    def set_ai_model(self, model: str) -> None:
        """Set the current AI model.
        
        Args:
            model: Name of the AI model
        """
        self.current_model = model
        
        if not self._model_label:
            return
        
        # Capitalize and format model name
        display_name = model.title()
        if model.lower() == "claude":
            display_name = "Claude"
        elif model.lower().startswith("gpt"):
            display_name = model.upper()
        
        self._model_label.update(display_name)
    
    def set_connection_status(self, status: str) -> None:
        """Set the AI service connection status.
        
        Args:
            status: Connection status ("online", "offline", "connecting", "error")
        """
        self.connection_status = status
        
        if not self._connection_label:
            return
        
        # Remove existing connection classes
        self._connection_label.remove_class(
            "connection-online", "connection-offline", "connection-connecting"
        )
        
        # Update text and styling based on status
        if status == "online":
            self._connection_label.update("Connected")
            self._connection_label.add_class("connection-online")
        elif status == "connecting":
            self._connection_label.update("Connecting...")
            self._connection_label.add_class("connection-connecting")
        elif status == "error":
            self._connection_label.update("Error")
            self._connection_label.add_class("connection-offline")
        else:  # offline
            self._connection_label.update("Offline")
            self._connection_label.add_class("connection-offline")
    
    def set_status_message(self, message: str, message_type: str = "info") -> None:
        """Set a temporary status message.
        
        Args:
            message: Status message to display
            message_type: Type of message ("info", "success", "warning", "error")
        """
        self.status_message = message
        
        if not self._status_label:
            return
        
        # Remove existing status classes
        self._status_label.remove_class("status-error", "status-success", "status-warning")
        
        # Add appropriate class based on message type
        if message_type == "error":
            self._status_label.add_class("status-error")
        elif message_type == "success":
            self._status_label.add_class("status-success")
        elif message_type == "warning":
            self._status_label.add_class("status-warning")
        
        self._status_label.update(message)
    
    def clear_status_message(self) -> None:
        """Clear the status message, returning to default."""
        self.set_status_message("Ready", "info")
    
    def get_project_name(self) -> str:
        """Get the current project name.
        
        Returns:
            Current project name or "No project" if none selected
        """
        return self.current_project.name if self.current_project else "No project"
    
    def get_project_path(self) -> str:
        """Get the current project path.
        
        Returns:
            Current project path or empty string if none selected
        """
        return str(self.current_project.path) if self.current_project else ""
    
    def is_autopilot_enabled(self) -> bool:
        """Check if autopilot is currently enabled.
        
        Returns:
            True if autopilot is enabled
        """
        return self.autopilot_enabled
    
    def get_current_model(self) -> str:
        """Get the current AI model name.
        
        Returns:
            Current AI model name
        """
        return self.current_model
    
    def get_connection_status(self) -> str:
        """Get the current connection status.
        
        Returns:
            Current connection status
        """
        return self.connection_status
    
    def update_status_from_state(
        self, 
        project: Optional[Project] = None,
        autopilot: Optional[bool] = None,
        model: Optional[str] = None,
        connection: Optional[str] = None,
        message: Optional[str] = None,
        message_type: str = "info"
    ) -> None:
        """Update multiple status elements at once.
        
        Args:
            project: Project to set (if provided)
            autopilot: Autopilot status (if provided)
            model: AI model (if provided)
            connection: Connection status (if provided)
            message: Status message (if provided)
            message_type: Type of status message
        """
        if project is not None:
            self.update_project(project)
        
        if autopilot is not None:
            self.set_autopilot_status(autopilot)
        
        if model is not None:
            self.set_ai_model(model)
        
        if connection is not None:
            self.set_connection_status(connection)
        
        if message is not None:
            self.set_status_message(message, message_type)