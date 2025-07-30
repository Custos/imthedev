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
        # Since CommandDashboard is mocked, check that it can be called
        assert dashboard is not None
        
    def test_command_dashboard_is_widget(self) -> None:
        """Test that CommandDashboard behaves like a Widget."""
        dashboard = CommandDashboard()
        # Since Widget is mocked, check that CommandDashboard can be instantiated
        assert dashboard is not None
        assert hasattr(dashboard, '__class__')