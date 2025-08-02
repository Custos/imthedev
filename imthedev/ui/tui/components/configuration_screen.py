"""Configuration screen component for viewing and editing application settings.

This module provides a comprehensive configuration interface with tabbed sections,
real-time validation, and keyboard-friendly navigation for managing all application
settings through the TUI.
"""

from pathlib import Path
from typing import Any, Callable

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.validation import Number, ValidationResult, Validator
from textual.widgets import (
    Button,
    Input,
    Label,
    Select,
    Static,
    Switch,
    TabbedContent,
    TabPane,
)

from imthedev.infrastructure.config import AppConfig


class PathValidator(Validator):
    """Validator for filesystem paths."""

    def validate(self, value: str) -> ValidationResult:
        """Validate that the path is valid."""
        if not value:
            return self.failure("Path cannot be empty")
        
        try:
            path = Path(value).expanduser()
            # Check if parent directory exists for files
            if "." in Path(value).name:  # Likely a file
                if not path.parent.exists():
                    return self.failure("Parent directory does not exist")
            return self.success()
        except Exception:
            return self.failure("Invalid path")


class APIKeyValidator(Validator):
    """Validator for API keys."""

    def validate(self, value: str) -> ValidationResult:
        """Validate API key format."""
        if not value:
            return self.success()  # Empty is OK (not required)
        
        if len(value) < 20:
            return self.failure("API key seems too short")
        
        if " " in value:
            return self.failure("API key cannot contain spaces")
        
        return self.success()


class ConfigurationScreen(Container):
    """Configuration screen for managing application settings.
    
    Provides a tabbed interface for editing different configuration sections
    with validation, keyboard navigation, and persistence support.
    
    Attributes:
        config: Current application configuration
        on_save: Callback when configuration is saved
        on_cancel: Callback when changes are cancelled
    """
    
    # CSS classes for styling
    DEFAULT_CSS = """
    ConfigurationScreen {
        padding: 1;
    }
    
    .config-header {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    
    .config-section {
        padding: 1;
        margin-bottom: 1;
    }
    
    .config-field {
        margin-bottom: 1;
    }
    
    .config-label {
        margin-bottom: 0;
        color: $text-muted;
    }
    
    .config-input {
        width: 100%;
    }
    
    .config-buttons {
        dock: bottom;
        height: 3;
        align: center middle;
    }
    
    .success-message {
        color: $success;
        text-style: italic;
    }
    
    .error-message {
        color: $error;
        text-style: italic;
    }
    """
    
    # Messages
    class ConfigSaved(Message):
        """Emitted when configuration is saved."""
        
        def __init__(self, config: AppConfig) -> None:
            super().__init__()
            self.config = config
    
    class ConfigCancelled(Message):
        """Emitted when configuration changes are cancelled."""
        pass
    
    def __init__(
        self,
        config: AppConfig,
        on_save: Callable[[AppConfig], None] | None = None,
        on_cancel: Callable[[], None] | None = None,
        **kwargs: Any
    ) -> None:
        """Initialize the configuration screen.
        
        Args:
            config: Current application configuration
            on_save: Optional callback when configuration is saved
            on_cancel: Optional callback when changes are cancelled
            **kwargs: Additional arguments for Container
        """
        super().__init__(**kwargs)
        self.config = config
        self.on_save = on_save
        self.on_cancel = on_cancel
        self.modified_config = self._copy_config(config)
        self.status_message = reactive("")
    
    def _copy_config(self, config: AppConfig) -> AppConfig:
        """Create a deep copy of the configuration."""
        # Create a new config with same values
        import copy
        return copy.deepcopy(config)
    
    def compose(self) -> ComposeResult:
        """Compose the configuration screen layout."""
        yield Static("[bold]Configuration Settings[/bold]", classes="config-header")
        
        # Status message area
        yield Static("", id="status-message")
        
        # Tabbed content for different sections
        with TabbedContent():
            with TabPane("Database", id="database-tab"):
                yield from self._compose_database_section()
            
            with TabPane("Storage", id="storage-tab"):
                yield from self._compose_storage_section()
            
            with TabPane("AI", id="ai-tab"):
                yield from self._compose_ai_section()
            
            with TabPane("UI", id="ui-tab"):
                yield from self._compose_ui_section()
            
            with TabPane("Security", id="security-tab"):
                yield from self._compose_security_section()
            
            with TabPane("Logging", id="logging-tab"):
                yield from self._compose_logging_section()
        
        # Action buttons
        with Horizontal(classes="config-buttons"):
            yield Button("Save", variant="primary", id="save-button")
            yield Button("Reset", variant="warning", id="reset-button")
            yield Button("Cancel", variant="default", id="cancel-button")
    
    def _compose_database_section(self) -> ComposeResult:
        """Compose the database configuration section."""
        with ScrollableContainer(classes="config-section"):
            # Database path
            yield Label("Database Path:", classes="config-label")
            yield Input(
                value=self.config.database.path,
                placeholder="Path to SQLite database",
                id="db-path",
                validators=[PathValidator()],
                classes="config-input"
            )
            
            # Timeout
            yield Label("Connection Timeout (seconds):", classes="config-label")
            yield Input(
                value=str(self.config.database.timeout),
                placeholder="30",
                id="db-timeout",
                validators=[Number(minimum=1, maximum=300)],
                classes="config-input"
            )
            
            # Backup settings
            yield Label("Enable Automatic Backups:", classes="config-label")
            yield Switch(
                value=self.config.database.backup_enabled,
                id="db-backup-enabled"
            )
            
            yield Label("Backup Interval (hours):", classes="config-label")
            yield Input(
                value=str(self.config.database.backup_interval_hours),
                placeholder="24",
                id="db-backup-interval",
                validators=[Number(minimum=1, maximum=168)],
                classes="config-input"
            )
    
    def _compose_storage_section(self) -> ComposeResult:
        """Compose the storage configuration section."""
        with ScrollableContainer(classes="config-section"):
            # Context directory
            yield Label("Context Directory:", classes="config-label")
            yield Input(
                value=self.config.storage.context_dir,
                placeholder="~/.imthedev/contexts",
                id="storage-context-dir",
                validators=[PathValidator()],
                classes="config-input"
            )
            
            # Backup directory
            yield Label("Backup Directory:", classes="config-label")
            yield Input(
                value=self.config.storage.backup_dir,
                placeholder="~/.imthedev/backups",
                id="storage-backup-dir",
                validators=[PathValidator()],
                classes="config-input"
            )
            
            # Max context history
            yield Label("Max Context History:", classes="config-label")
            yield Input(
                value=str(self.config.storage.max_context_history),
                placeholder="100",
                id="storage-max-history",
                validators=[Number(minimum=10, maximum=1000)],
                classes="config-input"
            )
            
            # Compress backups
            yield Label("Compress Backups:", classes="config-label")
            yield Switch(
                value=self.config.storage.compress_backups,
                id="storage-compress"
            )
    
    def _compose_ai_section(self) -> ComposeResult:
        """Compose the AI configuration section."""
        with ScrollableContainer(classes="config-section"):
            # Default model
            yield Label("Default AI Model:", classes="config-label")
            yield Select(
                [(line, line) for line in ["claude", "gpt-4", "gpt-3.5-turbo"]],
                value=self.config.ai.default_model,
                id="ai-model"
            )
            
            # Claude API key
            yield Label("Claude API Key (leave empty to use env var):", classes="config-label")
            yield Input(
                value=self.config.ai.claude_api_key or "",
                placeholder="sk-ant-...",
                password=True,
                id="ai-claude-key",
                validators=[APIKeyValidator()],
                classes="config-input"
            )
            
            # OpenAI API key
            yield Label("OpenAI API Key (leave empty to use env var):", classes="config-label")
            yield Input(
                value=self.config.ai.openai_api_key or "",
                placeholder="sk-...",
                password=True,
                id="ai-openai-key",
                validators=[APIKeyValidator()],
                classes="config-input"
            )
            
            # Request timeout
            yield Label("Request Timeout (seconds):", classes="config-label")
            yield Input(
                value=str(self.config.ai.request_timeout),
                placeholder="30",
                id="ai-timeout",
                validators=[Number(minimum=5, maximum=120)],
                classes="config-input"
            )
            
            # Max retries
            yield Label("Max Retries:", classes="config-label")
            yield Input(
                value=str(self.config.ai.max_retries),
                placeholder="3",
                id="ai-retries",
                validators=[Number(minimum=0, maximum=10)],
                classes="config-input"
            )
    
    def _compose_ui_section(self) -> ComposeResult:
        """Compose the UI configuration section."""
        with ScrollableContainer(classes="config-section"):
            # Theme
            yield Label("Theme:", classes="config-label")
            yield Select(
                [(theme, theme) for theme in ["dark", "light", "auto"]],
                value=self.config.ui.theme,
                id="ui-theme"
            )
            
            # Autopilot
            yield Label("Enable Autopilot by Default:", classes="config-label")
            yield Switch(
                value=self.config.ui.autopilot_enabled,
                id="ui-autopilot"
            )
            
            # Show AI reasoning
            yield Label("Show AI Reasoning:", classes="config-label")
            yield Switch(
                value=self.config.ui.show_ai_reasoning,
                id="ui-reasoning"
            )
            
            # Command confirmation
            yield Label("Require Command Confirmation:", classes="config-label")
            yield Switch(
                value=self.config.ui.command_confirmation,
                id="ui-confirmation"
            )
            
            # Max log lines
            yield Label("Max Log Lines:", classes="config-label")
            yield Input(
                value=str(self.config.ui.max_log_lines),
                placeholder="1000",
                id="ui-log-lines",
                validators=[Number(minimum=100, maximum=10000)],
                classes="config-input"
            )
    
    def _compose_security_section(self) -> ComposeResult:
        """Compose the security configuration section."""
        with ScrollableContainer(classes="config-section"):
            # Require approval
            yield Label("Require Command Approval:", classes="config-label")
            yield Switch(
                value=self.config.security.require_approval,
                id="security-approval"
            )
            
            # API key encryption
            yield Label("Encrypt API Keys:", classes="config-label")
            yield Switch(
                value=self.config.security.api_key_encryption,
                id="security-encryption"
            )
            
            # Dangerous commands (simplified for now)
            yield Label("Dangerous Commands (comma-separated):", classes="config-label")
            yield Input(
                value=", ".join(self.config.security.dangerous_commands[:5]),
                placeholder="rm, rmdir, del, format, fdisk",
                id="security-dangerous",
                classes="config-input"
            )
            
            # Blocked directories
            yield Label("Blocked Directories (comma-separated):", classes="config-label")
            yield Input(
                value=", ".join(self.config.security.blocked_directories),
                placeholder="/etc, /boot, /sys",
                id="security-blocked",
                classes="config-input"
            )
    
    def _compose_logging_section(self) -> ComposeResult:
        """Compose the logging configuration section."""
        with ScrollableContainer(classes="config-section"):
            # Log level
            yield Label("Log Level:", classes="config-label")
            yield Select(
                [(level, level) for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]],
                value=self.config.logging.level,
                id="logging-level"
            )
            
            # Log file path
            yield Label("Log File Path:", classes="config-label")
            yield Input(
                value=self.config.logging.file_path or "",
                placeholder="~/.imthedev/logs/imthedev.log",
                id="logging-path",
                validators=[PathValidator()],
                classes="config-input"
            )
            
            # Console logging
            yield Label("Enable Console Logging:", classes="config-label")
            yield Switch(
                value=self.config.logging.console_enabled,
                id="logging-console"
            )
            
            # Max file size
            yield Label("Max Log File Size (MB):", classes="config-label")
            yield Input(
                value=str(self.config.logging.max_file_size // (1024 * 1024)),
                placeholder="10",
                id="logging-size",
                validators=[Number(minimum=1, maximum=100)],
                classes="config-input"
            )
    
    @on(Button.Pressed, "#save-button")
    async def handle_save(self, event: Button.Pressed) -> None:
        """Handle save button press."""
        # Collect all values and update modified_config
        self._collect_values()
        
        # Validate all inputs
        if not self._validate_all():
            self._show_status("Validation errors found. Please check your inputs.", error=True)
            return
        
        # Call save callback if provided
        if self.on_save:
            self.on_save(self.modified_config)
        
        # Emit save message
        self.post_message(self.ConfigSaved(self.modified_config))
        self._show_status("Configuration saved successfully!", error=False)
    
    @on(Button.Pressed, "#reset-button")
    def handle_reset(self, event: Button.Pressed) -> None:
        """Handle reset button press."""
        # Reset to original config
        self.modified_config = self._copy_config(self.config)
        self._update_ui_from_config()
        self._show_status("Configuration reset to original values.", error=False)
    
    @on(Button.Pressed, "#cancel-button")
    def handle_cancel(self, event: Button.Pressed) -> None:
        """Handle cancel button press."""
        if self.on_cancel:
            self.on_cancel()
        
        self.post_message(self.ConfigCancelled())
    
    def _collect_values(self) -> None:
        """Collect values from UI inputs into modified_config."""
        # Database section
        if db_path := self.query_one("#db-path", Input):
            self.modified_config.database.path = db_path.value
        if db_timeout := self.query_one("#db-timeout", Input):
            self.modified_config.database.timeout = int(db_timeout.value or "30")
        if db_backup := self.query_one("#db-backup-enabled", Switch):
            self.modified_config.database.backup_enabled = db_backup.value
        if db_interval := self.query_one("#db-backup-interval", Input):
            self.modified_config.database.backup_interval_hours = int(db_interval.value or "24")
        
        # Storage section
        if context_dir := self.query_one("#storage-context-dir", Input):
            self.modified_config.storage.context_dir = context_dir.value
        if backup_dir := self.query_one("#storage-backup-dir", Input):
            self.modified_config.storage.backup_dir = backup_dir.value
        if max_history := self.query_one("#storage-max-history", Input):
            self.modified_config.storage.max_context_history = int(max_history.value or "100")
        if compress := self.query_one("#storage-compress", Switch):
            self.modified_config.storage.compress_backups = compress.value
        
        # AI section
        if ai_model := self.query_one("#ai-model", Select):
            self.modified_config.ai.default_model = ai_model.value
        if claude_key := self.query_one("#ai-claude-key", Input):
            self.modified_config.ai.claude_api_key = claude_key.value or None
        if openai_key := self.query_one("#ai-openai-key", Input):
            self.modified_config.ai.openai_api_key = openai_key.value or None
        if ai_timeout := self.query_one("#ai-timeout", Input):
            self.modified_config.ai.request_timeout = int(ai_timeout.value or "30")
        if ai_retries := self.query_one("#ai-retries", Input):
            self.modified_config.ai.max_retries = int(ai_retries.value or "3")
        
        # UI section
        if theme := self.query_one("#ui-theme", Select):
            self.modified_config.ui.theme = theme.value
        if autopilot := self.query_one("#ui-autopilot", Switch):
            self.modified_config.ui.autopilot_enabled = autopilot.value
        if reasoning := self.query_one("#ui-reasoning", Switch):
            self.modified_config.ui.show_ai_reasoning = reasoning.value
        if confirmation := self.query_one("#ui-confirmation", Switch):
            self.modified_config.ui.command_confirmation = confirmation.value
        if log_lines := self.query_one("#ui-log-lines", Input):
            self.modified_config.ui.max_log_lines = int(log_lines.value or "1000")
        
        # Security section
        if approval := self.query_one("#security-approval", Switch):
            self.modified_config.security.require_approval = approval.value
        if encryption := self.query_one("#security-encryption", Switch):
            self.modified_config.security.api_key_encryption = encryption.value
        if dangerous := self.query_one("#security-dangerous", Input):
            self.modified_config.security.dangerous_commands = [
                cmd.strip() for cmd in dangerous.value.split(",") if cmd.strip()
            ]
        if blocked := self.query_one("#security-blocked", Input):
            self.modified_config.security.blocked_directories = [
                dir.strip() for dir in blocked.value.split(",") if dir.strip()
            ]
        
        # Logging section
        if level := self.query_one("#logging-level", Select):
            self.modified_config.logging.level = level.value
        if log_path := self.query_one("#logging-path", Input):
            self.modified_config.logging.file_path = log_path.value or None
        if console := self.query_one("#logging-console", Switch):
            self.modified_config.logging.console_enabled = console.value
        if size := self.query_one("#logging-size", Input):
            self.modified_config.logging.max_file_size = int(size.value or "10") * 1024 * 1024
    
    def _validate_all(self) -> bool:
        """Validate all input fields.
        
        Returns:
            True if all inputs are valid, False otherwise
        """
        # Check all Input widgets for validation
        all_valid = True
        for input_widget in self.query(Input):
            if input_widget.validators:
                result = input_widget.validate(input_widget.value)
                if not result.is_valid:
                    all_valid = False
        
        return all_valid
    
    def _update_ui_from_config(self) -> None:
        """Update UI elements from the current configuration."""
        # This would update all input fields with config values
        # Implementation depends on specific needs
        pass
    
    def _show_status(self, message: str, error: bool = False) -> None:
        """Show a status message.
        
        Args:
            message: Message to display
            error: Whether this is an error message
        """
        status = self.query_one("#status-message", Static)
        status.update(message)
        if error:
            status.add_class("error-message")
            status.remove_class("success-message")
        else:
            status.add_class("success-message")
            status.remove_class("error-message")