"""Command dashboard component for imthedev TUI.

This module provides a widget for displaying AI-generated commands and their history.
Fully featured with Gemini-first model selection, AI reasoning, and autopilot mode.
Compatible with Textual v5.0.1.
"""

import os
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Static


class CommandDashboard(Widget):
    """Widget for displaying and managing AI-generated commands.

    This component provides:
    - Gemini as the default model for command generation
    - Simple model selection via keyboard shortcuts
    - AI reasoning display
    - Command history with model tracking
    - Autopilot mode toggle
    - Full backward compatibility with existing app.py structure
    """

    # Allow this widget to be focused for keyboard navigation
    can_focus = True
    
    # Reactive properties for state management
    selected_model = reactive("gemini-2.5-pro")
    autopilot_enabled = reactive(False)

    # Define key bindings for command operations
    BINDINGS = [
        ("ctrl+enter", "submit_command", "Submit Command"),
        ("ctrl+g", "generate_command", "Generate with AI"),
        ("escape", "clear_command", "Clear Command"),
        ("ctrl+1", "select_gemini_flash", "Gemini Flash"),
        ("ctrl+2", "select_gemini_pro", "Gemini Pro"),
        ("ctrl+3", "select_claude", "Claude"),
        ("ctrl+4", "select_gpt4", "GPT-4"),
        ("up", "previous_command", "Previous Command"),
        ("down", "next_command", "Next Command"),
        ("a", "toggle_autopilot", "Toggle Autopilot"),
    ]
    
    # Available AI models with metadata
    AI_MODELS = {
        "gemini-2.5-flash": {
            "name": "Gemini 2.5 Flash",
            "provider": "Google",
            "description": "Fast and efficient for quick responses",
            "icon": "⚡",
            "color": "cyan",
        },
        "gemini-2.5-pro": {
            "name": "Gemini 2.5 Pro",
            "provider": "Google",
            "description": "Advanced reasoning for complex tasks",
            "icon": "🚀",
            "color": "blue",
        },
        "gemini-2.5-flash-8b": {
            "name": "Gemini Flash 8B",
            "provider": "Google", 
            "description": "Lightweight for simple operations",
            "icon": "💨",
            "color": "green",
        },
        "claude": {
            "name": "Claude 3 Opus",
            "provider": "Anthropic",
            "description": "Sophisticated analysis and coding",
            "icon": "🧠",
            "color": "magenta",
        },
        "gpt-4": {
            "name": "GPT-4",
            "provider": "OpenAI",
            "description": "Advanced GPT model",
            "icon": "🤖",
            "color": "yellow",
        },
    }

    class CommandGenerated(Message):
        """Message sent when AI generates a command."""
        
        def __init__(self, command: str, reasoning: str, model: str) -> None:
            self.command = command
            self.reasoning = reasoning
            self.model = model
            super().__init__()
    
    class CommandSubmitted(Message):
        """Message sent when a command is submitted for execution."""
        
        def __init__(self, command: str, command_id: str, model: str) -> None:
            self.command = command
            self.command_id = command_id
            self.model = model
            super().__init__()

    class CommandCleared(Message):
        """Message sent when command input is cleared."""

        pass

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the CommandDashboard widget."""
        super().__init__(**kwargs)
        self.command_history: list[tuple[str, str, str, str, datetime]] = []
        # (id, command, status, model, timestamp)
        self.current_command: Optional[str] = None
        self.current_reasoning: Optional[str] = None
        self.command_input: Optional[Input] = None
        self.objective_input: Optional[Input] = None
        self.model_display: Optional[Static] = None
        self.history_container: Optional[ScrollableContainer] = None
        self.reasoning_display: Optional[Static] = None
        self.autopilot_display: Optional[Static] = None
        self.history_index: int = -1
        
        # Check available models based on API keys
        self.available_models = self._get_available_models()
        
        # Set default to Gemini if available
        if "gemini-2.5-pro" in self.available_models:
            self.selected_model = "gemini-2.5-pro"
        elif "gemini-2.5-flash" in self.available_models:
            self.selected_model = "gemini-2.5-flash"
        elif self.available_models:
            self.selected_model = self.available_models[0]
    
    def _get_available_models(self) -> list[str]:
        """Determine which models are available based on API keys."""
        available = []
        
        # Check for Gemini models (prioritized)
        if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
            available.extend(["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-8b"])
        
        # Check for Claude models
        if os.environ.get("CLAUDE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"):
            available.append("claude")
        
        # Check for OpenAI models
        if os.environ.get("OPENAI_API_KEY"):
            available.append("gpt-4")
        
        return available

    def compose(self) -> ComposeResult:
        """Compose the enhanced widget layout."""
        with Vertical(id="command-dashboard-container"):
            # Header with model and autopilot status
            with Horizontal(id="dashboard-header"):
                yield Label("[bold]AI Command Generation[/bold]", id="dashboard-title")
                
                # Model display
                model_info = self.AI_MODELS.get(self.selected_model, {"name": "Unknown", "icon": "?"})
                self.model_display = Static(
                    f"Model: {model_info['icon']} {model_info['name']} [dim](Ctrl+1-4 to switch)[/dim]",
                    id="model-display"
                )
                yield self.model_display
                
                # Autopilot status
                self.autopilot_display = Static(
                    f"Autopilot: {'[green]ON[/green]' if self.autopilot_enabled else '[red]OFF[/red]'} [dim](A to toggle)[/dim]",
                    id="autopilot-display"
                )
                yield self.autopilot_display
            
            # Objective input area
            yield Label("[bold]Objective:[/bold]", id="objective-label")
            self.objective_input = Input(
                placeholder="What do you want to accomplish? (e.g., 'Set up Docker for Node.js app')",
                id="objective-input"
            )
            yield self.objective_input
            
            # AI-generated command display
            with Vertical(id="command-section"):
                yield Label("[bold]Generated Command:[/bold]", id="command-label")
                yield Static(
                    "No command generated yet. Enter an objective and press Ctrl+G",
                    id="current-command-display"
                )
                
                # Command edit input
                yield Label("[bold]Edit Command:[/bold]", id="edit-label")
                self.command_input = Input(
                    placeholder="Command will appear here for editing...",
                    id="command-input"
                )
                yield self.command_input
            
            # AI reasoning display
            with Vertical(id="reasoning-section"):
                yield Label("[bold]AI Reasoning:[/bold]", id="reasoning-label")
                self.reasoning_display = Static(
                    "AI explanation will appear here...",
                    id="reasoning-display"
                )
                yield self.reasoning_display
            
            # Action buttons
            with Horizontal(id="action-buttons"):
                yield Button("Generate [Ctrl+G]", variant="primary", id="generate-btn")
                yield Button("Execute [Ctrl+Enter]", variant="success", id="execute-btn")
                yield Button("Clear [Esc]", variant="warning", id="clear-btn")

            # Command history
            yield Label("[bold]Command History:[/bold]", id="history-label")
            with ScrollableContainer(id="command-history-scroll"):
                self.history_container = ScrollableContainer(
                    id="command-history-container"
                )
                yield self.history_container

    def on_mount(self) -> None:
        """Initialize the dashboard when mounted."""
        # Set focus to objective input
        if self.objective_input:
            self.objective_input.focus()
        
        # Add sample history for demonstration
        if not self.command_history:
            sample_commands = [
                (
                    str(uuid4()),
                    "npm init -y",
                    "completed",
                    "gemini-2.5-flash",
                    datetime.now()
                ),
                (
                    str(uuid4()),
                    "npm install express cors dotenv",
                    "completed",
                    "gemini-2.5-pro",
                    datetime.now()
                ),
            ]
            
            for cmd_id, command, status, model, timestamp in sample_commands:
                self.add_to_history(cmd_id, command, status, model, timestamp)
        
        self.log(f"CommandDashboard initialized with model: {self.selected_model}")

    def update_current_command(self, command: str) -> None:
        """Update the currently proposed command.

        Args:
            command: The command to display
        """
        self.current_command = command
        
        # Update command display with model-specific styling
        model_info = self.AI_MODELS.get(self.selected_model, {"color": "white"})
        color = model_info['color']
        
        current_display = self.query_one("#current-command-display", Static)
        current_display.update(f"[{color}]$ {command}[/{color}]")

        # Also update the input field
        if self.command_input:
            self.command_input.value = command

    def add_to_history(
        self,
        command_id: str,
        command: str,
        status: str,
        model: str,
        timestamp: datetime
    ) -> None:
        """Add a command to the history with model information.
        
        Args:
            command_id: Unique ID for the command
            command: The command text
            status: Status of the command (completed, failed, cancelled, pending)
            model: AI model that generated the command
            timestamp: When the command was executed
        """
        self.command_history.append((command_id, command, status, model, timestamp))

        if self.history_container:
            # Create history entry with model indicator
            time_str = timestamp.strftime("%H:%M:%S")
            status_color = {
                "completed": "green",
                "failed": "red",
                "cancelled": "yellow",
                "pending": "blue"
            }.get(status, "white")

            model_info = self.AI_MODELS.get(model, {"icon": "?", "color": "white"})

            history_entry = Static(
                f"[dim]{time_str}[/dim] {model_info['icon']} [{status_color}]{status}[/{status_color}] [dim]{model}[/dim] {command}",
                id=f"history-{command_id}",
            )

            self.history_container.mount(history_entry)
            self.history_container.scroll_end()

    # Backward compatibility method for existing code
    def add_to_history_legacy(
        self, command_id: str, command: str, status: str, timestamp: datetime
    ) -> None:
        """Legacy method for backward compatibility with 4-parameter signature."""
        self.add_to_history(command_id, command, status, self.selected_model, timestamp)

    def action_submit_command(self) -> None:
        """Submit the command for execution."""
        if self.command_input and self.command_input.value.strip():
            command = self.command_input.value.strip()
            command_id = str(uuid4())
            
            self.log(f"Submitting command via {self.selected_model}: {command}")
            self.post_message(self.CommandSubmitted(command, command_id, self.selected_model))
            
            # Add to history
            self.add_to_history(
                command_id,
                command,
                "pending",
                self.selected_model,
                datetime.now()
            )
            
            # Clear inputs
            if self.objective_input:
                self.objective_input.value = ""
            if self.command_input:
                self.command_input.value = ""
            
            # Clear displays
            command_display = self.query_one("#current-command-display", Static)
            command_display.update("No command generated yet. Enter an objective and press Ctrl+G")
            
            if self.reasoning_display:
                self.reasoning_display.update("AI explanation will appear here...")

    def action_clear_command(self) -> None:
        """Clear all inputs and displays."""
        if self.objective_input:
            self.objective_input.value = ""
        if self.command_input:
            self.command_input.value = ""
        
        self.current_command = None
        self.current_reasoning = None
        
        # Reset displays
        command_display = self.query_one("#current-command-display", Static)
        command_display.update("No command generated yet. Enter an objective and press Ctrl+G")
        
        if self.reasoning_display:
            self.reasoning_display.update("AI explanation will appear here...")
        
        self.log("Dashboard cleared")
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
            _, command, _, model, _ = self.command_history[self.history_index]
            if self.command_input:
                self.command_input.value = command
            
            # Also switch to that model
            if model in self.available_models:
                self._switch_model(model)

    def action_next_command(self) -> None:
        """Navigate to next command in history."""
        if not self.command_history:
            return

        if self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            _, command, _, model, _ = self.command_history[self.history_index]
            if self.command_input:
                self.command_input.value = command
            
            # Switch to that model
            if model in self.available_models:
                self._switch_model(model)
        else:
            self.history_index = -1
            if self.command_input:
                self.command_input.value = ""

    def update_command_status(self, command_id: str, status: str) -> None:
        """Update the status of a command in history.
        
        Args:
            command_id: ID of the command to update
            status: New status (completed, failed, cancelled, pending)
        """
        # Update in our history list
        for i, (cmd_id, cmd, _, model, timestamp) in enumerate(self.command_history):
            if cmd_id == command_id:
                self.command_history[i] = (cmd_id, cmd, status, model, timestamp)
                break

        # Update visual display
        try:
            history_entry = self.query_one(f"#history-{command_id}", Static)
            time_str = timestamp.strftime("%H:%M:%S")
            status_color = {
                "completed": "green",
                "failed": "red",
                "cancelled": "yellow",
                "pending": "blue"
            }.get(status, "white")

            model_info = self.AI_MODELS.get(model, {"icon": "?", "color": "white"})

            history_entry.update(
                f"[dim]{time_str}[/dim] {model_info['icon']} [{status_color}]{status}[/{status_color}] [dim]{model}[/dim] {cmd}"
            )
        except Exception:
            pass  # Entry might not be visible
    
    # New methods for enhanced functionality
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "generate-btn":
            self.action_generate_command()
        elif event.button.id == "execute-btn":
            self.action_submit_command()
        elif event.button.id == "clear-btn":
            self.action_clear_command()
    
    def action_generate_command(self) -> None:
        """Generate a command using the selected AI model."""
        if not self.objective_input or not self.objective_input.value.strip():
            self.log("Please enter an objective first")
            return
        
        objective = self.objective_input.value.strip()
        model = self.selected_model
        model_info = self.AI_MODELS.get(model, {"name": "Unknown", "icon": "?"})
        
        # Simulate AI command generation
        if "docker" in objective.lower():
            command = "docker init --language node && docker-compose up -d"
            reasoning = f"Using {model_info['name']} to set up Docker with best practices."
        elif "test" in objective.lower():
            command = "npm test -- --coverage --watchAll=false"
            reasoning = f"{model_info['name']} suggests running tests with coverage."
        else:
            command = f"echo 'Executing: {objective}'"
            reasoning = f"{model_info['name']} is processing: {objective}"
        
        # Update displays
        self.update_generated_command(command, reasoning)
        
        # Post message
        self.post_message(self.CommandGenerated(command, reasoning, model))
        
        # If autopilot is enabled, auto-execute
        if self.autopilot_enabled:
            self.action_submit_command()
    
    def update_generated_command(self, command: str, reasoning: str) -> None:
        """Update the generated command and reasoning displays."""
        self.current_command = command
        self.current_reasoning = reasoning
        
        # Update command display
        model_info = self.AI_MODELS.get(self.selected_model, {"color": "white"})
        color = model_info['color']
        
        command_display = self.query_one("#current-command-display", Static)
        command_display.update(f"[{color}]$ {command}[/{color}]")
        
        # Update command input
        if self.command_input:
            self.command_input.value = command
        
        # Update reasoning display
        if self.reasoning_display:
            self.reasoning_display.update(
                f"[dim]{model_info.get('icon', '?')} {model_info.get('name', 'Unknown')}:[/dim] {reasoning}"
            )
    
    def action_select_gemini_flash(self) -> None:
        """Select Gemini Flash model."""
        if "gemini-2.5-flash" in self.available_models:
            self._switch_model("gemini-2.5-flash")
    
    def action_select_gemini_pro(self) -> None:
        """Select Gemini Pro model."""
        if "gemini-2.5-pro" in self.available_models:
            self._switch_model("gemini-2.5-pro")
    
    def action_select_claude(self) -> None:
        """Select Claude model."""
        if "claude" in self.available_models:
            self._switch_model("claude")
    
    def action_select_gpt4(self) -> None:
        """Select GPT-4 model."""
        if "gpt-4" in self.available_models:
            self._switch_model("gpt-4")
    
    def _switch_model(self, model: str) -> None:
        """Switch to a different AI model."""
        self.selected_model = model
        model_info = self.AI_MODELS.get(model, {"name": "Unknown", "icon": "?"})
        
        # Update model display
        if self.model_display:
            self.model_display.update(
                f"Model: {model_info['icon']} {model_info['name']} [dim](Ctrl+1-4 to switch)[/dim]"
            )
        
        self.log(f"Switched to {model_info['name']} ({model_info.get('provider', 'Unknown')})")
    
    def action_toggle_autopilot(self) -> None:
        """Toggle autopilot mode."""
        self.autopilot_enabled = not self.autopilot_enabled
        
        # Update display
        if self.autopilot_display:
            self.autopilot_display.update(
                f"Autopilot: {'[green]ON[/green]' if self.autopilot_enabled else '[red]OFF[/red]'} [dim](A to toggle)[/dim]"
            )
        
        self.log(f"Autopilot {'enabled' if self.autopilot_enabled else 'disabled'}")