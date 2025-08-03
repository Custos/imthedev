#!/usr/bin/env python3
"""Demo script to showcase the Gemini-first CommandDashboard.

This script demonstrates the enhanced command dashboard with Gemini
as the default AI model for command generation.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from imthedev.ui.tui.components.command_dashboard import CommandDashboard


class GeminiDashboardDemo(App):
    """Demo application showcasing the Gemini-first command dashboard."""
    
    TITLE = "imthedev - Gemini-First Command Generation Demo"
    # CSS_PATH removed - using default styling
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle Dark Mode"),
        ("ctrl+s", "screenshot", "Screenshot"),
    ]
    
    def compose(self) -> ComposeResult:
        """Compose the demo application layout."""
        yield Header()
        
        with Container(id="main-container"):
            yield Static(
                "[bold cyan]Welcome to the Gemini-First Command Dashboard![/bold cyan]\n\n"
                "This demo showcases the redesigned command dashboard that prioritizes "
                "Google's Gemini models for AI-powered command generation.\n\n"
                "[yellow]Features:[/yellow]\n"
                "• Gemini 2.5 Pro as the default model\n"
                "• Visual model selector with provider icons\n"
                "• AI reasoning display with model attribution\n"
                "• Autopilot mode for automatic command execution\n"
                "• Command history with model tracking\n"
                "• Keyboard-driven interface\n\n"
                "[green]Try it out:[/green]\n"
                "1. Enter an objective (e.g., 'Set up Docker for Node.js')\n"
                "2. Press Ctrl+G to generate a command\n"
                "3. Review the AI reasoning\n"
                "4. Press Ctrl+Enter to execute or edit the command first\n",
                id="intro-text"
            )
            
            yield CommandDashboard(id="gemini-dashboard")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the demo when mounted."""
        self.log("Gemini Dashboard Demo initialized")
        self.log("Available models detected based on environment variables:")
        
        dashboard = self.query_one("#gemini-dashboard", CommandDashboard)
        for model in dashboard.available_models:
            model_info = dashboard.AI_MODELS.get(model, {})
            self.log(f"  - {model_info.get('name', model)} ({model_info.get('provider', 'Unknown')})")
        
        if not dashboard.available_models:
            self.log("⚠️  No API keys detected! Set GEMINI_API_KEY, CLAUDE_API_KEY, or OPENAI_API_KEY")
    
    def action_screenshot(self) -> None:
        """Take a screenshot of the dashboard."""
        self.save_screenshot("gemini_dashboard_demo.svg")
        self.log("Screenshot saved as gemini_dashboard_demo.svg")
    
    def on_command_dashboard_command_generated(
        self, message: CommandDashboard.CommandGenerated
    ) -> None:
        """Handle command generation events."""
        self.log(f"Command generated using {message.model}:")
        self.log(f"  Command: {message.command}")
        self.log(f"  Reasoning: {message.reasoning}")
    
    def on_command_dashboard_command_submitted(
        self, message: CommandDashboard.CommandSubmitted
    ) -> None:
        """Handle command submission events."""
        self.log(f"Command submitted for execution:")
        self.log(f"  ID: {message.command_id}")
        self.log(f"  Command: {message.command}")
        self.log(f"  Model: {message.model}")
        
        # Simulate command execution
        dashboard = self.query_one("#gemini-dashboard", CommandDashboard)
        dashboard.update_command_status(message.command_id, "completed")
        self.log(f"  Status: ✅ Completed")
    


def main():
    """Run the demo application."""
    print("\n" + "="*60)
    print("imthedev - Gemini-First Command Dashboard Demo")
    print("="*60)
    
    # Check for API keys
    has_gemini = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    has_claude = bool(os.environ.get("CLAUDE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"))
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))
    
    print("\nAPI Key Status:")
    print(f"  Gemini: {'✅ Configured' if has_gemini else '❌ Not configured'}")
    print(f"  Claude: {'✅ Configured' if has_claude else '❌ Not configured'}")
    print(f"  OpenAI: {'✅ Configured' if has_openai else '❌ Not configured'}")
    
    if not any([has_gemini, has_claude, has_openai]):
        print("\n⚠️  Warning: No API keys detected!")
        print("Set one of the following environment variables:")
        print("  - GEMINI_API_KEY (recommended)")
        print("  - CLAUDE_API_KEY")
        print("  - OPENAI_API_KEY")
        print("\nThe demo will still run but with limited functionality.\n")
    elif has_gemini:
        print("\n✨ Gemini API key detected - full functionality available!")
    
    print("\nKeyboard Shortcuts:")
    print("  Ctrl+G    - Generate command")
    print("  Ctrl+Enter - Execute command")
    print("  Ctrl+M    - Focus model selector")
    print("  A         - Toggle autopilot")
    print("  Escape    - Clear inputs")
    print("  Q         - Quit demo")
    print("\nStarting demo...\n")
    
    app = GeminiDashboardDemo()
    app.run()


if __name__ == "__main__":
    main()