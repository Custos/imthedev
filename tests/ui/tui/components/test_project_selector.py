"""Tests for the ProjectSelector component.

This module contains tests for the project selection widget.
"""

import pytest

from imthedev.ui.tui.components import ProjectSelector


class TestProjectSelector:
    """Test suite for ProjectSelector widget."""
    
    def test_project_selector_initialization(self) -> None:
        """Test that ProjectSelector can be initialized."""
        selector = ProjectSelector()
        assert isinstance(selector, ProjectSelector)
        
    def test_project_selector_is_widget(self) -> None:
        """Test that ProjectSelector is a proper Textual Widget."""
        from textual.widget import Widget
        
        selector = ProjectSelector()
        assert isinstance(selector, Widget)