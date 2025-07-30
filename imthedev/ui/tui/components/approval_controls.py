"""Approval controls component for imthedev TUI.

This module provides keyboard-driven command approval/denial controls.
Compatible with Textual v5.0.1.
"""

from textual.widget import Widget


class ApprovalControls(Widget):
    """Widget for command approval and denial controls.
    
    This component provides a keyboard-driven interface for approving or
    denying proposed commands, with hotkeys A (approve) and D (deny).
    
    Attributes:
        can_approve: Whether approval actions are currently available
        pending_command: Command awaiting approval/denial
    """
    
    pass