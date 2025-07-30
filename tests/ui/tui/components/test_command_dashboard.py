"""Tests for the CommandDashboard component.

This module contains tests for the command dashboard widget.
"""

import pytest

from imthedev.ui.tui.components import CommandDashboard


class TestCommandDashboard:
    """Test suite for CommandDashboard widget."""
    
    def test_command_dashboard_initialization(self) -> None:
        """Test that CommandDashboard can be initialized."""
        dashboard = CommandDashboard()
        assert isinstance(dashboard, CommandDashboard)
        
    def test_command_dashboard_is_widget(self) -> None:
        """Test that CommandDashboard is a proper Textual Widget."""
        from textual.widget import Widget
        
        dashboard = CommandDashboard()
        assert isinstance(dashboard, Widget)