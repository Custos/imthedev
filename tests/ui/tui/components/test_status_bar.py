"""Tests for the StatusBar component.

This module contains tests for the status bar widget.
"""

import pytest

from imthedev.ui.tui.components import StatusBar


class TestStatusBar:
    """Test suite for StatusBar widget."""
    
    def test_status_bar_initialization(self) -> None:
        """Test that StatusBar can be initialized."""
        status_bar = StatusBar()
        assert isinstance(status_bar, StatusBar)
        
    def test_status_bar_is_widget(self) -> None:
        """Test that StatusBar is a proper Textual Widget."""
        from textual.widget import Widget
        
        status_bar = StatusBar()
        assert isinstance(status_bar, Widget)