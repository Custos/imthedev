"""Status bar component for imthedev TUI.

This module provides a status bar widget showing autopilot status and current model.
Compatible with Textual v5.0.1.
"""

from textual.widget import Widget


class StatusBar(Widget):
    """Widget for displaying application status information.
    
    This component shows the current autopilot status, selected AI model,
    and other relevant status information at the bottom of the TUI.
    
    Attributes:
        autopilot_enabled: Whether autopilot mode is currently active
        current_model: Currently selected AI model
        project_name: Name of the current project
    """
    
    pass