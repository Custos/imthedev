"""Tests for the ApprovalControls component.

This module contains tests for the approval controls widget.
"""

import pytest

from imthedev.ui.tui.components import ApprovalControls


class TestApprovalControls:
    """Test suite for ApprovalControls widget."""
    
    def test_approval_controls_initialization(self) -> None:
        """Test that ApprovalControls can be initialized."""
        controls = ApprovalControls()
        assert isinstance(controls, ApprovalControls)
        
    def test_approval_controls_is_widget(self) -> None:
        """Test that ApprovalControls is a proper Textual Widget."""
        from textual.widget import Widget
        
        controls = ApprovalControls()
        assert isinstance(controls, Widget)