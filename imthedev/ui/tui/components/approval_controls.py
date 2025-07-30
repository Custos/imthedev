"""Approval controls component for imthedev TUI.

This module provides keyboard-driven command approval/denial controls.
Compatible with Textual v5.0.1.
"""

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Static, Label

from imthedev.core.domain import Command, CommandStatus


class ApprovalControls(Widget):
    """Widget for command approval and denial controls.
    
    This component provides a keyboard-driven interface for approving or
    denying proposed commands, with hotkeys A (approve) and D (deny).
    
    Attributes:
        can_approve: Whether approval actions are currently available
        pending_command: Command awaiting approval/denial
        autopilot_enabled: Whether autopilot mode is active
        is_processing: Whether a command is currently being processed
    """
    
    DEFAULT_CSS = """
    ApprovalControls {
        height: auto;
        width: 100%;
        layout: vertical;
        padding: 1;
        background: $surface;
        border: solid $primary;
    }
    
    ApprovalControls .controls-title {
        text-style: bold;
        color: $accent;
        text-align: center;
        margin-bottom: 1;
    }
    
    ApprovalControls .controls-row {
        height: auto;
        width: 100%;
        layout: horizontal;
        align: center middle;
    }
    
    ApprovalControls .action-button {
        width: 12;
        height: 3;
        margin: 0 1;
        text-style: bold;
    }
    
    ApprovalControls .approve-button {
        background: $success;
        color: $success-lighten-3;
    }
    
    ApprovalControls .approve-button:hover {
        background: $success-lighten-1;
    }
    
    ApprovalControls .approve-button:focus {
        background: $success-lighten-2;
        border: thick $success-lighten-1;
    }
    
    ApprovalControls .deny-button {
        background: $error;
        color: $error-lighten-3;
    }
    
    ApprovalControls .deny-button:hover {
        background: $error-lighten-1;
    }
    
    ApprovalControls .deny-button:focus {
        background: $error-lighten-2;
        border: thick $error-lighten-1;
    }
    
    ApprovalControls .autopilot-button {
        background: $warning;
        color: $warning-lighten-3;
        width: 16;
    }
    
    ApprovalControls .autopilot-button:hover {
        background: $warning-lighten-1;
    }
    
    ApprovalControls .autopilot-enabled {
        background: $success;
        color: $success-lighten-3;
    }
    
    ApprovalControls .disabled-button {
        background: $surface-lighten-1;
        color: $text-muted;
    }
    
    ApprovalControls .disabled-button:hover {
        background: $surface-lighten-1;
        color: $text-muted;
    }
    
    ApprovalControls .processing {
        background: $warning;
        color: $warning-lighten-3;
    }
    
    ApprovalControls .status-text {
        text-align: center;
        color: $text-muted;
        margin-top: 1;
        height: auto;
    }
    
    ApprovalControls .hint-text {
        text-align: center;
        color: $text-muted;
        text-style: italic;
        height: auto;
        margin-bottom: 1;
    }
    
    ApprovalControls .command-status {
        text-align: center;
        color: $accent;
        text-style: bold;
        height: auto;
        margin-bottom: 1;
    }
    """
    
    class CommandApproved(Message):
        """Message sent when a command is approved."""
        
        def __init__(self, command: Command) -> None:
            self.command = command
            super().__init__()
    
    class CommandDenied(Message):
        """Message sent when a command is denied."""
        
        def __init__(self, command: Command) -> None:
            self.command = command
            super().__init__()
    
    class AutopilotToggled(Message):
        """Message sent when autopilot mode is toggled."""
        
        def __init__(self, enabled: bool) -> None:
            self.enabled = enabled
            super().__init__()
    
    can_approve: reactive[bool] = reactive(False)
    autopilot_enabled: reactive[bool] = reactive(False)
    is_processing: reactive[bool] = reactive(False)
    
    def __init__(self, **kwargs):
        """Initialize the ApprovalControls widget."""
        super().__init__(**kwargs)
        self.pending_command: Optional[Command] = None
        self._approve_button: Optional[Button] = None
        self._deny_button: Optional[Button] = None
        self._autopilot_button: Optional[Button] = None
        self._status_label: Optional[Static] = None
        self._hint_label: Optional[Static] = None
        self._command_status_label: Optional[Static] = None
    
    def compose(self) -> ComposeResult:
        """Compose the approval controls layout."""
        yield Label("Command Controls", classes="controls-title")
        
        # Command status display
        self._command_status_label = Static("No command pending", classes="command-status")
        yield self._command_status_label
        
        # Keyboard hints
        self._hint_label = Static("A: Approve | D: Deny | P: Toggle Autopilot", classes="hint-text")
        yield self._hint_label
        
        # Control buttons
        with Horizontal(classes="controls-row"):
            self._approve_button = Button("✓ Approve (A)", id="approve", classes="action-button approve-button")
            yield self._approve_button
            
            self._deny_button = Button("✗ Deny (D)", id="deny", classes="action-button deny-button")
            yield self._deny_button
            
            self._autopilot_button = Button("🤖 Autopilot (P)", id="autopilot", classes="autopilot-button")
            yield self._autopilot_button
        
        # Status information
        self._status_label = Static("Waiting for command...", classes="status-text")
        yield self._status_label
    
    def set_pending_command(self, command: Optional[Command]) -> None:
        """Set the command awaiting approval.
        
        Args:
            command: Command to approve/deny, or None to clear
        """
        self.pending_command = command
        self.can_approve = command is not None and command.status == CommandStatus.PROPOSED
        
        self._update_display()
    
    def set_autopilot_mode(self, enabled: bool) -> None:
        """Set autopilot mode status.
        
        Args:
            enabled: Whether autopilot mode is enabled
        """
        self.autopilot_enabled = enabled
        self._update_autopilot_display()
    
    def set_processing_state(self, processing: bool) -> None:
        """Set the processing state.
        
        Args:
            processing: Whether commands are currently being processed
        """
        self.is_processing = processing
        self._update_button_states()
    
    def _update_display(self) -> None:
        """Update the entire display based on current state."""
        self._update_command_status()
        self._update_button_states()
        self._update_status_text()
    
    def _update_command_status(self) -> None:
        """Update the command status display."""
        if not self._command_status_label:
            return
        
        if self.pending_command:
            status_text = f"Command Status: {self.pending_command.status.value.title()}"
            
            if self.pending_command.status == CommandStatus.PROPOSED:
                status_text = "⏳ Command Awaiting Approval"
            elif self.pending_command.status == CommandStatus.EXECUTING:
                status_text = "⚡ Command Executing..."
            elif self.pending_command.status == CommandStatus.COMPLETED:
                status_text = "✅ Command Completed"
            elif self.pending_command.status == CommandStatus.FAILED:
                status_text = "❌ Command Failed"
            elif self.pending_command.status == CommandStatus.REJECTED:
                status_text = "🚫 Command Rejected"
        else:
            status_text = "No command pending"
        
        self._command_status_label.update(status_text)
    
    def _update_button_states(self) -> None:
        """Update button enabled/disabled states and styling."""
        if not all([self._approve_button, self._deny_button, self._autopilot_button]):
            return
        
        # Determine if approval buttons should be enabled
        approval_enabled = self.can_approve and not self.is_processing and not self.autopilot_enabled
        
        # Update approve button
        if approval_enabled:
            self._approve_button.disabled = False
            self._approve_button.remove_class("disabled-button")
            self._approve_button.add_class("approve-button")
        else:
            self._approve_button.disabled = True
            self._approve_button.remove_class("approve-button")
            self._approve_button.add_class("disabled-button")
        
        # Update deny button
        if approval_enabled:
            self._deny_button.disabled = False
            self._deny_button.remove_class("disabled-button")
            self._deny_button.add_class("deny-button")
        else:
            self._deny_button.disabled = True
            self._deny_button.remove_class("deny-button")
            self._deny_button.add_class("disabled-button")
        
        # Update processing states
        if self.is_processing:
            self._approve_button.add_class("processing")
            self._deny_button.add_class("processing")
        else:
            self._approve_button.remove_class("processing")
            self._deny_button.remove_class("processing")
    
    def _update_autopilot_display(self) -> None:
        """Update autopilot button display."""
        if not self._autopilot_button:
            return
        
        if self.autopilot_enabled:
            self._autopilot_button.label = "🤖 Autopilot ON"
            self._autopilot_button.remove_class("autopilot-button")
            self._autopilot_button.add_class("autopilot-enabled")
        else:
            self._autopilot_button.label = "🤖 Autopilot OFF"
            self._autopilot_button.remove_class("autopilot-enabled")
            self._autopilot_button.add_class("autopilot-button")
    
    def _update_status_text(self) -> None:
        """Update the status text display."""
        if not self._status_label:
            return
        
        if self.autopilot_enabled:
            status_text = "Autopilot mode: Commands auto-approved"
        elif self.is_processing:
            status_text = "Processing command..."
        elif self.can_approve:
            status_text = "Use A to approve, D to deny"
        else:
            status_text = "Waiting for command..."
        
        self._status_label.update(status_text)
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.
        
        Args:
            event: Button press event
        """
        if event.button.id == "approve" and self.can_approve and not self.is_processing:
            await self._approve_command()
        elif event.button.id == "deny" and self.can_approve and not self.is_processing:
            await self._deny_command()
        elif event.button.id == "autopilot":
            await self._toggle_autopilot()
    
    async def on_key(self, event: Key) -> None:
        """Handle keyboard events for approval controls.
        
        Args:
            event: Key event
        """
        # Handle approval/denial hotkeys
        if event.key == "a" and self.can_approve and not self.is_processing and not self.autopilot_enabled:
            await self._approve_command()
            event.prevent_default()
        
        elif event.key == "d" and self.can_approve and not self.is_processing and not self.autopilot_enabled:
            await self._deny_command()
            event.prevent_default()
        
        elif event.key == "p":
            await self._toggle_autopilot()
            event.prevent_default()
    
    async def _approve_command(self) -> None:
        """Handle command approval."""
        if self.pending_command and self.can_approve:
            # Provide visual feedback
            if self._approve_button:
                self._approve_button.add_class("processing")
            
            await self.post_message(self.CommandApproved(self.pending_command))
    
    async def _deny_command(self) -> None:
        """Handle command denial."""
        if self.pending_command and self.can_approve:
            # Provide visual feedback
            if self._deny_button:
                self._deny_button.add_class("processing")
            
            await self.post_message(self.CommandDenied(self.pending_command))
    
    async def _toggle_autopilot(self) -> None:
        """Handle autopilot mode toggle."""
        new_state = not self.autopilot_enabled
        self.set_autopilot_mode(new_state)
        await self.post_message(self.AutopilotToggled(new_state))
    
    def get_pending_command(self) -> Optional[Command]:
        """Get the currently pending command.
        
        Returns:
            Pending command or None if none
        """
        return self.pending_command
    
    def is_approval_available(self) -> bool:
        """Check if approval actions are currently available.
        
        Returns:
            True if commands can be approved/denied
        """
        return self.can_approve and not self.is_processing and not self.autopilot_enabled
    
    def is_autopilot_enabled(self) -> bool:
        """Check if autopilot mode is enabled.
        
        Returns:
            True if autopilot is enabled
        """
        return self.autopilot_enabled
    
    def reset_visual_feedback(self) -> None:
        """Reset any visual feedback indicators."""
        if self._approve_button:
            self._approve_button.remove_class("processing")
        if self._deny_button:
            self._deny_button.remove_class("processing")