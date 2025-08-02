"""Command dashboard component for imthedev TUI.

This module provides a widget for displaying AI-generated commands and their history.
Compatible with Textual v5.0.1.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Label, Static


class CommandDashboard(Widget):
    """Widget for displaying and managing AI-generated commands.

    This component shows the current proposed command, command history,
    and provides an input area for command editing.

    Attributes:
        command_history: List of previously executed commands
        current_command: Currently proposed command
        command_input: Input widget for command editing
    """

    # Allow this widget to be focused for keyboard navigation
    can_focus = True

    # Define key bindings for command operations
    BINDINGS = [
        ("ctrl+enter", "submit_command", "Submit Command"),
        ("escape", "clear_command", "Clear Command"),
        ("up", "previous_command", "Previous Command"),
        ("down", "next_command", "Next Command"),
    ]

    class CommandSubmitted(Message):
        """Message sent when a command is submitted."""

        def __init__(self, command: str, command_id: str) -> None:
            self.command = command
            self.command_id = command_id
            super().__init__()

    class CommandCleared(Message):
        """Message sent when command input is cleared."""

        pass

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the CommandDashboard widget."""
        super().__init__(**kwargs)
        self.command_history: list[
            tuple[str, str, str, datetime]
        ] = []  # (id, command, status, timestamp)
        self.current_command: str | None = None
        self.command_input: Input | None = None
        self.history_container: ScrollableContainer | None = None
        self.history_index: int = -1

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        with Vertical(id="command-dashboard-container"):
            # Current command display
            yield Label("[bold]Current Command:[/bold]", id="current-command-label")
            yield Static("No command proposed yet", id="current-command-display")

            # Command input area
            yield Label("[bold]Edit Command:[/bold]", id="edit-command-label")
            self.command_input = Input(
                placeholder="Enter or edit command here...", id="command-input"
            )
            yield self.command_input

            # Command history
            yield Label("[bold]Command History:[/bold]", id="history-label")
            with ScrollableContainer(id="command-history-scroll"):
                self.history_container = ScrollableContainer(
                    id="command-history-container"
                )
                yield self.history_container

    def on_mount(self) -> None:
        """Called when the widget is mounted. Initialize with sample data."""
        # Add some sample command history
        sample_commands = [
            (str(uuid4()), "git status", "completed", datetime.now()),
            (str(uuid4()), "npm install textual", "completed", datetime.now()),
            (str(uuid4()), "python -m pytest", "completed", datetime.now()),
        ]

        for cmd_id, command, status, timestamp in sample_commands:
            self.add_to_history(cmd_id, command, status, timestamp)

    def update_current_command(self, command: str) -> None:
        """Update the currently proposed command.

        Args:
            command: The command to display
        """
        self.current_command = command
        current_display = self.query_one("#current-command-display", Static)
        current_display.update(f"[cyan]{command}[/cyan]")

        # Also update the input field
        if self.command_input:
            self.command_input.value = command

    def add_to_history(
        self, command_id: str, command: str, status: str, timestamp: datetime
    ) -> None:
        """Add a command to the history.

        Args:
            command_id: Unique ID for the command
            command: The command text
            status: Status of the command (completed, failed, cancelled)
            timestamp: When the command was executed
        """
        self.command_history.append((command_id, command, status, timestamp))

        if self.history_container:
            # Create history entry
            time_str = timestamp.strftime("%H:%M:%S")
            status_color = {
                "completed": "green",
                "failed": "red",
                "cancelled": "yellow",
            }.get(status, "white")

            history_entry = Static(
                f"[dim]{time_str}[/dim] [{status_color}]{status}[/{status_color}] {command}",
                id=f"history-{command_id}",
            )

            self.history_container.mount(history_entry)

            # Scroll to show latest
            self.history_container.scroll_end()

    def action_submit_command(self) -> None:
        """Handle command submission."""
        if self.command_input and self.command_input.value.strip():
            command = self.command_input.value.strip()
            command_id = str(uuid4())

            self.log(f"Submitting command: {command}")
            self.post_message(self.CommandSubmitted(command, command_id))

            # Add to history as pending
            self.add_to_history(command_id, command, "pending", datetime.now())

            # Clear input
            self.command_input.value = ""

    def action_clear_command(self) -> None:
        """Handle command clearing."""
        if self.command_input:
            self.command_input.value = ""
            self.current_command = None

            current_display = self.query_one("#current-command-display", Static)
            current_display.update("No command proposed yet")

            self.log("Command cleared")
            self.post_message(self.CommandCleared())

    def action_previous_command(self) -> None:
        """Navigate to previous command in history."""
        if not self.command_history:
            return

        if self.history_index == -1:
            self.history_index = len(self.command_history) - 1
        elif self.history_index > 0:
            self.history_index -= 1

        if 0 <= self.history_index < len(self.command_history):
            _, command, _, _ = self.command_history[self.history_index]
            if self.command_input:
                self.command_input.value = command

    def action_next_command(self) -> None:
        """Navigate to next command in history."""
        if not self.command_history:
            return

        if self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            _, command, _, _ = self.command_history[self.history_index]
            if self.command_input:
                self.command_input.value = command
        else:
            self.history_index = -1
            if self.command_input:
                self.command_input.value = ""

    def update_command_status(self, command_id: str, status: str) -> None:
        """Update the status of a command in history.

        Args:
            command_id: ID of the command to update
            status: New status (completed, failed, cancelled)
        """
        # Update in our history list
        for i, (cmd_id, cmd, _, timestamp) in enumerate(self.command_history):
            if cmd_id == command_id:
                self.command_history[i] = (cmd_id, cmd, status, timestamp)
                break

        # Update visual display
        try:
            history_entry = self.query_one(f"#history-{command_id}", Static)
            time_str = timestamp.strftime("%H:%M:%S")
            status_color = {
                "completed": "green",
                "failed": "red",
                "cancelled": "yellow",
            }.get(status, "white")

            history_entry.update(
                f"[dim]{time_str}[/dim] [{status_color}]{status}[/{status_color}] {cmd}"
            )
        except Exception:
            pass  # Entry might not be visible
