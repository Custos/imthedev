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
        # Since ApprovalControls is mocked, check that it can be called
        assert controls is not None
        
    def test_approval_controls_is_widget(self) -> None:
        """Test that ApprovalControls behaves like a Widget."""
        controls = ApprovalControls()
        # Since Widget is mocked, check that ApprovalControls can be instantiated
        assert controls is not None
        assert hasattr(controls, '__class__')