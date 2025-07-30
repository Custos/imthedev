"""Command dashboard component for imthedev TUI.

This module provides the central command workflow display widget.
Compatible with Textual v5.0.1.
"""

from typing import List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.events import Key
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import TextArea, Label, Button, Static

from imthedev.core.domain import Command, CommandStatus


class CommandDashboard(Widget):
    """Central widget for displaying command workflow.
    
    This component shows proposed commands, AI reasoning, and command output.
    It serves as the main interaction area for command approval and monitoring.
    
    Attributes:
        current_command: Currently displayed command
        command_history: List of all commands for navigation
        history_index: Current position in command history
    """
    
    DEFAULT_CSS = """
    CommandDashboard {
        height: 100%;
        width: 100%;
        layout: vertical;
    }
    
    CommandDashboard .dashboard-header {
        height: 3;
        dock: top;
        background: $surface;
        padding: 0 1;
    }
    
    CommandDashboard .dashboard-content {
        height: 1fr;
        layout: horizontal;
    }
    
    CommandDashboard .command-section {
        width: 1fr;
        height: 100%;
        border: solid $primary;
        margin: 0 1;
    }
    
    CommandDashboard .reasoning-section {
        width: 1fr;
        height: 100%;
        border: solid $accent;
        margin: 0 1;
    }
    
    CommandDashboard .output-section {
        width: 100%;
        height: 40%;
        border: solid $secondary;
        margin: 1 0;
    }
    
    CommandDashboard TextArea {
        height: 1fr;
        width: 100%;
        scrollbar-size-vertical: 1;
        scrollbar-size-horizontal: 1;
    }
    
    CommandDashboard .command-area {
        background: $surface;
        color: $text;
    }
    
    CommandDashboard .reasoning-area {
        background: $panel;
        color: $text;
    }
    
    CommandDashboard .output-area {
        background: $background;
        color: $text;
    }
    
    CommandDashboard .section-title {
        text-style: bold;
        color: $accent;
        background: $surface;
        padding: 0 1;
    }
    
    CommandDashboard .status-executing {
        background: $warning 20%;
        color: $warning;
    }
    
    CommandDashboard .status-completed {
        background: $success 20%;
        color: $success;
    }
    
    CommandDashboard .status-failed {
        background: $error 20%;
        color: $error;
    }
    
    CommandDashboard .history-nav {
        height: auto;
        width: 100%;
        align: center middle;
        margin: 0 1;
    }
    """
    
    class CommandChanged(Message):
        """Message sent when current command changes."""
        
        def __init__(self, command: Optional[Command]) -> None:
            self.command = command
            super().__init__()
    
    class NavigationRequested(Message):
        """Message sent when navigation is requested."""
        
        def __init__(self, direction: str) -> None:
            """Initialize navigation message.
            
            Args:
                direction: 'prev' or 'next' for navigation direction
            """
            self.direction = direction
            super().__init__()
    
    current_command: reactive[Optional[Command]] = reactive(None)
    
    def __init__(self, **kwargs):
        """Initialize the CommandDashboard widget."""
        super().__init__(**kwargs)
        self.command_history: List[Command] = []
        self.history_index: int = -1
        self._command_area: Optional[TextArea] = None
        self._reasoning_area: Optional[TextArea] = None
        self._output_area: Optional[TextArea] = None
        self._status_label: Optional[Label] = None
        self._nav_info: Optional[Static] = None
    
    def compose(self) -> ComposeResult:
        """Compose the dashboard layout."""
        with Container(classes="dashboard-header"):
            self._status_label = Label("No command", classes="section-title")
            yield self._status_label
            
            with Horizontal(classes="history-nav"):
                yield Button("◀ Prev", id="prev-cmd", variant="default")
                self._nav_info = Static("0 / 0", classes="nav-info")
                yield self._nav_info
                yield Button("Next ▶", id="next-cmd", variant="default")
        
        with Vertical(classes="dashboard-content"):
            with Horizontal():
                with Container(classes="command-section"):
                    yield Label("Proposed Command", classes="section-title")
                    self._command_area = TextArea("", classes="command-area", read_only=True)
                    yield self._command_area
                
                with Container(classes="reasoning-section"):
                    yield Label("AI Reasoning", classes="section-title")
                    self._reasoning_area = TextArea("", classes="reasoning-area", read_only=True)
                    yield self._reasoning_area
            
            with Container(classes="output-section"):
                yield Label("Command Output", classes="section-title")
                self._output_area = TextArea("", classes="output-area", read_only=True)
                yield self._output_area
    
    def display_command(self, command: Optional[Command]) -> None:
        """Display a command in the dashboard.
        
        Args:
            command: Command to display, or None to clear
        """
        self.current_command = command
        
        if command is None:
            self._clear_display()
            return
        
        # Update command text
        if self._command_area:
            self._command_area.text = command.command_text
        
        # Update AI reasoning
        if self._reasoning_area:
            self._reasoning_area.text = command.ai_reasoning
        
        # Update command output
        if self._output_area:
            output_text = ""
            if command.result:
                output_text = f"Exit Code: {command.result.exit_code}\n\n"
                if command.result.stdout:
                    output_text += f"STDOUT:\n{command.result.stdout}\n\n"
                if command.result.stderr:
                    output_text += f"STDERR:\n{command.result.stderr}\n"
            elif command.status == CommandStatus.EXECUTING:
                output_text = "Command is executing..."
            
            self._output_area.text = output_text
        
        # Update status
        self._update_status_display(command)
        self._update_navigation_info()
    
    def _clear_display(self) -> None:
        """Clear all dashboard content."""
        if self._command_area:
            self._command_area.text = ""
        if self._reasoning_area:
            self._reasoning_area.text = ""
        if self._output_area:
            self._output_area.text = ""
        if self._status_label:
            self._status_label.update("No command")
            self._status_label.remove_class("status-executing", "status-completed", "status-failed")
    
    def _update_status_display(self, command: Command) -> None:
        """Update the status label and styling.
        
        Args:
            command: Command to show status for
        """
        if not self._status_label:
            return
        
        # Remove existing status classes
        self._status_label.remove_class("status-executing", "status-completed", "status-failed")
        
        # Update text and add appropriate class
        status_text = f"Command Status: {command.status.value.title()}"
        
        if command.status == CommandStatus.EXECUTING:
            self._status_label.add_class("status-executing")
        elif command.status == CommandStatus.COMPLETED:
            self._status_label.add_class("status-completed")
        elif command.status == CommandStatus.FAILED:
            self._status_label.add_class("status-failed")
        
        self._status_label.update(status_text)
    
    def update_command_history(self, commands: List[Command]) -> None:
        """Update the command history list.
        
        Args:
            commands: List of commands to use as history
        """
        self.command_history = commands
        
        # Reset index if history is empty
        if not commands:
            self.history_index = -1
        # Ensure index is within bounds
        elif self.history_index >= len(commands):
            self.history_index = len(commands) - 1
        # Set to latest command if no specific selection
        elif self.history_index < 0 and commands:
            self.history_index = len(commands) - 1
        
        self._update_navigation_info()
        
        # Display current command
        current = self.get_current_command()
        self.display_command(current)
    
    def _update_navigation_info(self) -> None:
        """Update the navigation info display."""
        if not self._nav_info:
            return
        
        if not self.command_history:
            self._nav_info.update("0 / 0")
        else:
            current_num = self.history_index + 1 if self.history_index >= 0 else 0
            total = len(self.command_history)
            self._nav_info.update(f"{current_num} / {total}")
    
    def get_current_command(self) -> Optional[Command]:
        """Get the currently displayed command.
        
        Returns:
            Current command or None if no command selected
        """
        if not self.command_history or self.history_index < 0 or self.history_index >= len(self.command_history):
            return None
        
        return self.command_history[self.history_index]
    
    def navigate_to_previous(self) -> bool:
        """Navigate to the previous command in history.
        
        Returns:
            True if navigation occurred, False if at beginning
        """
        if not self.command_history or self.history_index <= 0:
            return False
        
        self.history_index -= 1
        current = self.get_current_command()
        self.display_command(current)
        return True
    
    def navigate_to_next(self) -> bool:
        """Navigate to the next command in history.
        
        Returns:
            True if navigation occurred, False if at end
        """
        if not self.command_history or self.history_index >= len(self.command_history) - 1:
            return False
        
        self.history_index += 1
        current = self.get_current_command()
        self.display_command(current)
        return True
    
    def navigate_to_latest(self) -> None:
        """Navigate to the most recent command."""
        if self.command_history:
            self.history_index = len(self.command_history) - 1
            current = self.get_current_command()
            self.display_command(current)
    
    def append_output(self, text: str) -> None:
        """Append text to the command output area.
        
        Args:
            text: Text to append to output
        """
        if self._output_area:
            current_text = self._output_area.text
            self._output_area.text = current_text + text
            # Scroll to bottom
            self._output_area.scroll_end()
    
    def clear_output(self) -> None:
        """Clear the command output area."""
        if self._output_area:
            self._output_area.text = ""
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.
        
        Args:
            event: Button press event
        """
        if event.button.id == "prev-cmd":
            if self.navigate_to_previous():
                await self.post_message(self.NavigationRequested("prev"))
        elif event.button.id == "next-cmd":
            if self.navigate_to_next():
                await self.post_message(self.NavigationRequested("next"))
    
    async def on_key(self, event: Key) -> None:
        """Handle key events for navigation.
        
        Args:
            event: Key event
        """
        # Command history navigation
        if event.key == "ctrl+left" or event.key == "ctrl+h":
            if self.navigate_to_previous():
                await self.post_message(self.NavigationRequested("prev"))
                event.prevent_default()
        
        elif event.key == "ctrl+right" or event.key == "ctrl+l":
            if self.navigate_to_next():
                await self.post_message(self.NavigationRequested("next"))
                event.prevent_default()
        
        elif event.key == "ctrl+end":
            self.navigate_to_latest()
            await self.post_message(self.NavigationRequested("latest"))
            event.prevent_default()
    
    def get_command_count(self) -> int:
        """Get the number of commands in history.
        
        Returns:
            Number of commands in history
        """
        return len(self.command_history)
    
    def get_history_position(self) -> tuple[int, int]:
        """Get current position in command history.
        
        Returns:
            Tuple of (current_index, total_count)
        """
        return (self.history_index + 1 if self.history_index >= 0 else 0, len(self.command_history))