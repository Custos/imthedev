"""Project selector component for imthedev TUI.

This module provides a widget for displaying and selecting projects in the TUI.
Compatible with Textual v5.0.1.
"""

from textual.widget import Widget


class ProjectSelector(Widget):
    """Widget for selecting and managing projects.
    
    This component displays a list of available projects and allows users
    to navigate and select them using keyboard controls.
    
    Attributes:
        projects: List of available projects
        selected_index: Currently selected project index
    """
    
    pass