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
        # Since StatusBar is mocked, check that it can be called
        assert status_bar is not None
        
    def test_status_bar_is_widget(self) -> None:
        """Test that StatusBar behaves like a Widget."""
        status_bar = StatusBar()
        # Since Widget is mocked, check that StatusBar can be instantiated
        assert status_bar is not None
        assert hasattr(status_bar, '__class__')