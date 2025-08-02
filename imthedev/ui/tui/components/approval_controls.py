"""Approval controls component for imthedev TUI.

This module provides keyboard-driven command approval/denial controls.
Compatible with Textual v5.0.1.
"""


from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Label, Static


class ApprovalControls(Widget):
    """Widget for command approval and denial controls.

    This component provides a keyboard-driven interface for approving or
    denying proposed commands, with hotkeys A (approve) and D (deny).

    Attributes:
        autopilot_enabled: Whether autopilot mode is active
        pending_command_id: ID of the command awaiting approval
    """

    # Allow this widget to be focused for approval actions
    can_focus = True

    # Define key bindings for approval actions
    BINDINGS = [
        ("a", "approve_command", "Approve Command"),
        ("d", "deny_command", "Deny Command"),
        ("p", "toggle_autopilot", "Toggle Autopilot"),
    ]

    class CommandApproved(Message):
        """Message sent when a command is approved."""

        def __init__(self, command_id: str) -> None:
            self.command_id = command_id
            super().__init__()

    class CommandDenied(Message):
        """Message sent when a command is denied."""

        def __init__(self, command_id: str) -> None:
            self.command_id = command_id
            super().__init__()

    class AutopilotToggled(Message):
        """Message sent when autopilot mode is toggled."""

        def __init__(self, enabled: bool) -> None:
            self.enabled = enabled
            super().__init__()

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the ApprovalControls widget."""
        super().__init__(**kwargs)
        self.autopilot_enabled: bool = False
        self.pending_command_id: str | None = None
        self.is_processing: bool = False
        self._approve_button: Button | None = None
        self._deny_button: Button | None = None
        self._autopilot_button: Button | None = None
        self._status_label: Static | None = None

    def compose(self) -> ComposeResult:
        """Compose the approval controls layout."""
        yield Label("[bold]Command Controls[/bold]", id="controls-title")

        # Status display
        self._status_label = Static("Waiting for command...", id="approval-status")
        yield self._status_label

        # Control buttons
        with Horizontal(id="approval-buttons"):
            self._approve_button = Button(
                "✓ Approve (A)", id="approve", variant="success"
            )
            yield self._approve_button

            self._deny_button = Button("✗ Deny (D)", id="deny", variant="error")
            yield self._deny_button

            self._autopilot_button = Button(
                "🤖 Auto OFF", id="autopilot", variant="warning"
            )
            yield self._autopilot_button

    def on_mount(self) -> None:
        """Called when the widget is mounted."""
        self._update_button_states()

    def set_pending_command(self, command_id: str | None) -> None:
        """Set the command awaiting approval.

        Args:
            command_id: ID of command to approve/deny, or None to clear
        """
        self.pending_command_id = command_id
        self.is_processing = False
        self._update_display()

    def set_autopilot_mode(self, enabled: bool) -> None:
        """Set autopilot mode status.

        Args:
            enabled: Whether autopilot mode is enabled
        """
        self.autopilot_enabled = enabled
        self._update_display()

    def set_processing_state(self, processing: bool) -> None:
        """Set the processing state.

        Args:
            processing: Whether commands are currently being processed
        """
        self.is_processing = processing
        self._update_display()

    def _update_display(self) -> None:
        """Update the display based on current state."""
        self._update_status_text()
        self._update_button_states()
        self._update_autopilot_button()

    def _update_status_text(self) -> None:
        """Update the status text display."""
        if not self._status_label:
            return

        if self.autopilot_enabled:
            status_text = "[cyan]Autopilot mode: Commands auto-approved[/cyan]"
        elif self.is_processing:
            status_text = "[yellow]Processing command...[/yellow]"
        elif self.pending_command_id:
            status_text = "[green]Command ready - Use A to approve, D to deny[/green]"
        else:
            status_text = "Waiting for command..."

        self._status_label.update(status_text)

    def _update_button_states(self) -> None:
        """Update button enabled/disabled states."""
        if not self._approve_button or not self._deny_button:
            return

        # Buttons enabled when command pending and not in autopilot
        can_approve = (
            bool(self.pending_command_id)
            and not self.autopilot_enabled
            and not self.is_processing
        )

        self._approve_button.disabled = not can_approve
        self._deny_button.disabled = not can_approve

    def _update_autopilot_button(self) -> None:
        """Update autopilot button display."""
        if not self._autopilot_button:
            return

        if self.autopilot_enabled:
            self._autopilot_button.label = "🤖 Auto ON"
            self._autopilot_button.variant = "success"
        else:
            self._autopilot_button.label = "🤖 Auto OFF"
            self._autopilot_button.variant = "warning"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: Button press event
        """
        if event.button.id == "approve":
            self.action_approve_command()
        elif event.button.id == "deny":
            self.action_deny_command()
        elif event.button.id == "autopilot":
            self.action_toggle_autopilot()

    def action_approve_command(self) -> None:
        """Action to approve the current command."""
        if not self.pending_command_id or self.autopilot_enabled or self.is_processing:
            return

        self.log(f"Approving command: {self.pending_command_id}")
        self.post_message(self.CommandApproved(self.pending_command_id))

        # Clear after approval
        self.pending_command_id = None
        self._update_display()

    def action_deny_command(self) -> None:
        """Action to deny the current command."""
        if not self.pending_command_id or self.autopilot_enabled or self.is_processing:
            return

        self.log(f"Denying command: {self.pending_command_id}")
        self.post_message(self.CommandDenied(self.pending_command_id))

        # Clear after denial
        self.pending_command_id = None
        self._update_display()

    def action_toggle_autopilot(self) -> None:
        """Action to toggle autopilot mode."""
        self.autopilot_enabled = not self.autopilot_enabled
        self.log(f"Autopilot mode: {'ON' if self.autopilot_enabled else 'OFF'}")

        self.post_message(self.AutopilotToggled(self.autopilot_enabled))
        self._update_display()
