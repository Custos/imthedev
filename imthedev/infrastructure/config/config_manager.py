"""Configuration management system for imthedev.

This module provides centralized configuration management with support for:
- TOML configuration files
- Environment variable overrides
- Type-safe configuration with validation
- Default values with sensible fallbacks
"""

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DatabaseConfig:
    """Database configuration settings."""

    path: str = "imthedev.db"
    """Path to SQLite database file"""

    timeout: int = 30
    """Database connection timeout in seconds"""

    backup_enabled: bool = True
    """Whether to enable automatic database backups"""

    backup_interval_hours: int = 24
    """Interval between automatic backups in hours"""


@dataclass
class StorageConfig:
    """Storage configuration settings."""

    context_dir: str = field(
        default_factory=lambda: str(Path.home() / ".imthedev" / "contexts")
    )
    """Directory for storing project context files"""

    backup_dir: str = field(
        default_factory=lambda: str(Path.home() / ".imthedev" / "backups")
    )
    """Directory for storing backups"""

    max_context_history: int = 100
    """Maximum number of commands to keep in context history"""

    compress_backups: bool = True
    """Whether to compress backup files"""


@dataclass
class AIConfig:
    """AI provider configuration settings."""

    default_model: str = "claude"
    """Default AI model to use"""

    claude_api_key: str | None = None
    """Claude API key (loaded from environment)"""

    openai_api_key: str | None = None
    """OpenAI API key (loaded from environment)"""

    request_timeout: int = 30
    """AI request timeout in seconds"""

    max_retries: int = 3
    """Maximum number of retry attempts for failed requests"""

    retry_delay: float = 1.0
    """Delay between retry attempts in seconds"""


@dataclass
class UIConfig:
    """User interface configuration settings."""

    theme: str = "dark"
    """UI theme (dark, light, auto)"""

    autopilot_enabled: bool = False
    """Whether autopilot mode is enabled by default"""

    show_ai_reasoning: bool = True
    """Whether to show AI reasoning in the UI"""

    command_confirmation: bool = True
    """Whether to require confirmation before executing commands"""

    max_log_lines: int = 1000
    """Maximum number of log lines to keep in memory"""


@dataclass
class SecurityConfig:
    """Security configuration settings."""

    require_approval: bool = True
    """Whether commands require explicit approval"""

    dangerous_commands: list[str] = field(
        default_factory=lambda: [
            "rm",
            "rmdir",
            "del",
            "format",
            "fdisk",
            "mkfs",
            "dd",
            "chmod 777",
            "chown",
            "sudo rm",
            "sudo chmod",
        ]
    )
    """List of command patterns considered dangerous"""

    allowed_directories: list[str] = field(default_factory=list)
    """List of directories where commands are allowed (empty = all allowed)"""

    blocked_directories: list[str] = field(
        default_factory=lambda: ["/etc", "/boot", "/sys", "/proc", "/dev"]
    )
    """List of directories where commands are blocked"""

    api_key_encryption: bool = True
    """Whether to encrypt API keys in storage"""


@dataclass
class LoggingConfig:
    """Logging configuration settings."""

    level: str = "INFO"
    """Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"""

    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    """Log message format string"""

    file_path: str | None = field(
        default_factory=lambda: str(Path.home() / ".imthedev" / "logs" / "imthedev.log")
    )
    """Path to log file (None to disable file logging)"""

    max_file_size: int = 10 * 1024 * 1024  # 10MB
    """Maximum log file size in bytes"""

    backup_count: int = 5
    """Number of log file backups to keep"""

    console_enabled: bool = True
    """Whether to enable console logging"""


@dataclass
class AppConfig:
    """Complete application configuration.

    This dataclass contains all configuration settings organized by domain.
    Settings can be loaded from TOML files and overridden by environment variables.
    """

    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    """Database configuration settings"""

    storage: StorageConfig = field(default_factory=StorageConfig)
    """Storage configuration settings"""

    ai: AIConfig = field(default_factory=AIConfig)
    """AI provider configuration settings"""

    ui: UIConfig = field(default_factory=UIConfig)
    """User interface configuration settings"""

    security: SecurityConfig = field(default_factory=SecurityConfig)
    """Security configuration settings"""

    logging: LoggingConfig = field(default_factory=LoggingConfig)
    """Logging configuration settings"""

    # Global settings
    debug: bool = False
    """Enable debug mode"""

    config_file: str = field(
        default_factory=lambda: str(Path.home() / ".imthedev" / "config.toml")
    )
    """Path to configuration file"""

    def expand_paths(self) -> None:
        """Expand user paths (~) in configuration values."""
        # Expand database path
        self.database.path = os.path.expanduser(self.database.path)

        # Expand storage paths
        self.storage.context_dir = os.path.expanduser(self.storage.context_dir)
        self.storage.backup_dir = os.path.expanduser(self.storage.backup_dir)

        # Expand logging path
        if self.logging.file_path:
            self.logging.file_path = os.path.expanduser(self.logging.file_path)

        # Expand config file path
        self.config_file = os.path.expanduser(self.config_file)

    def validate(self) -> list[str]:
        """Validate configuration settings.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Validate AI configuration
        if not self.ai.claude_api_key and not self.ai.openai_api_key:
            errors.append("At least one AI API key must be configured")

        if self.ai.default_model not in [
            "claude",
            "claude-instant",
            "gpt-4",
            "gpt-3.5-turbo",
        ]:
            errors.append(f"Invalid default AI model: {self.ai.default_model}")

        # Validate UI configuration
        if self.ui.theme not in ["dark", "light", "auto"]:
            errors.append(f"Invalid UI theme: {self.ui.theme}")

        # Validate logging configuration
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.logging.level not in valid_levels:
            errors.append(f"Invalid logging level: {self.logging.level}")

        # Validate numeric ranges
        if self.database.timeout <= 0:
            errors.append("Database timeout must be positive")

        if self.storage.max_context_history <= 0:
            errors.append("Max context history must be positive")

        if self.ai.request_timeout <= 0:
            errors.append("AI request timeout must be positive")

        if self.ai.max_retries < 0:
            errors.append("AI max retries must be non-negative")

        return errors


class ConfigManager:
    """Configuration manager for loading and managing application settings.

    The ConfigManager loads configuration from multiple sources in order of precedence:
    1. Environment variables (highest precedence)
    2. TOML configuration file
    3. Default values (lowest precedence)

    Environment variables use the pattern: IMTHEDEV_<SECTION>_<SETTING>
    For example: IMTHEDEV_AI_CLAUDE_API_KEY, IMTHEDEV_DATABASE_PATH
    """

    def __init__(self, config_file: str | None = None) -> None:
        """Initialize the configuration manager.

        Args:
            config_file: Path to TOML configuration file (uses default if None)
        """
        self._config_file = config_file
        self._config: AppConfig | None = None

    def load_config(self) -> AppConfig:
        """Load configuration from all sources.

        Returns:
            Complete application configuration

        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Start with default configuration
        config = AppConfig()

        # Determine config file path
        config_file_path = self._config_file or config.config_file
        config_file_path = str(Path(config_file_path).expanduser())

        # Load from TOML file if it exists
        if os.path.exists(config_file_path):
            try:
                config = self._load_from_toml(config_file_path, config)
            except Exception as e:
                raise ConfigurationError(
                    f"Failed to load config file {config_file_path}: {e}"
                ) from e

        # Override with environment variables
        config = self._load_from_environment(config)

        # Expand user paths
        config.expand_paths()

        # Validate configuration
        validation_errors = config.validate()
        if validation_errors:
            raise ConfigurationError(
                f"Configuration validation failed: {'; '.join(validation_errors)}"
            )

        self._config = config
        return config

    def get_config(self) -> AppConfig:
        """Get the current configuration.

        Returns:
            Current application configuration

        Raises:
            ConfigurationError: If configuration has not been loaded
        """
        if self._config is None:
            raise ConfigurationError(
                "Configuration has not been loaded. Call load_config() first."
            )
        return self._config

    def create_default_config_file(self, path: str | None = None) -> str:
        """Create a default configuration file.

        Args:
            path: Path where to create the config file (uses default if None)

        Returns:
            Path to the created configuration file
        """
        config_path = path or os.path.expanduser("~/.imthedev/config.toml")
        config_dir = os.path.dirname(config_path)

        # Create config directory if it doesn't exist
        os.makedirs(config_dir, exist_ok=True)

        # Generate default TOML content
        toml_content = self._generate_default_toml()

        # Write to file
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(toml_content)

        return config_path

    def _load_from_toml(self, file_path: str, base_config: AppConfig) -> AppConfig:
        """Load configuration from TOML file.

        Args:
            file_path: Path to TOML file
            base_config: Base configuration to update

        Returns:
            Updated configuration
        """
        with open(file_path, "rb") as f:
            toml_data = tomllib.load(f)

        # Update configuration sections
        if "database" in toml_data:
            self._update_config_section(base_config.database, toml_data["database"])

        if "storage" in toml_data:
            self._update_config_section(base_config.storage, toml_data["storage"])

        if "ai" in toml_data:
            self._update_config_section(base_config.ai, toml_data["ai"])

        if "ui" in toml_data:
            self._update_config_section(base_config.ui, toml_data["ui"])

        if "security" in toml_data:
            self._update_config_section(base_config.security, toml_data["security"])

        if "logging" in toml_data:
            self._update_config_section(base_config.logging, toml_data["logging"])

        # Update global settings
        if "debug" in toml_data:
            base_config.debug = toml_data["debug"]

        return base_config

    def _load_from_environment(self, base_config: AppConfig) -> AppConfig:
        """Load configuration overrides from environment variables.

        Args:
            base_config: Base configuration to update

        Returns:
            Updated configuration
        """
        env_mappings = {
            # Database settings
            "IMTHEDEV_DATABASE_PATH": ("database", "path"),
            "IMTHEDEV_DATABASE_TIMEOUT": ("database", "timeout", int),
            "IMTHEDEV_DATABASE_BACKUP_ENABLED": ("database", "backup_enabled", bool),
            # Storage settings
            "IMTHEDEV_STORAGE_CONTEXT_DIR": ("storage", "context_dir"),
            "IMTHEDEV_STORAGE_BACKUP_DIR": ("storage", "backup_dir"),
            "IMTHEDEV_STORAGE_MAX_CONTEXT_HISTORY": (
                "storage",
                "max_context_history",
                int,
            ),
            # AI settings
            "IMTHEDEV_AI_DEFAULT_MODEL": ("ai", "default_model"),
            "IMTHEDEV_AI_CLAUDE_API_KEY": ("ai", "claude_api_key"),
            "IMTHEDEV_AI_OPENAI_API_KEY": ("ai", "openai_api_key"),
            "IMTHEDEV_AI_REQUEST_TIMEOUT": ("ai", "request_timeout", int),
            "IMTHEDEV_AI_MAX_RETRIES": ("ai", "max_retries", int),
            # Alternative API key names (common environment variable names)
            "CLAUDE_API_KEY": ("ai", "claude_api_key"),
            "OPENAI_API_KEY": ("ai", "openai_api_key"),
            "ANTHROPIC_API_KEY": ("ai", "claude_api_key"),
            # UI settings
            "IMTHEDEV_UI_THEME": ("ui", "theme"),
            "IMTHEDEV_UI_AUTOPILOT_ENABLED": ("ui", "autopilot_enabled", bool),
            "IMTHEDEV_UI_SHOW_AI_REASONING": ("ui", "show_ai_reasoning", bool),
            # Security settings
            "IMTHEDEV_SECURITY_REQUIRE_APPROVAL": (
                "security",
                "require_approval",
                bool,
            ),
            # Logging settings
            "IMTHEDEV_LOGGING_LEVEL": ("logging", "level"),
            "IMTHEDEV_LOGGING_FILE_PATH": ("logging", "file_path"),
            # Global settings
            "IMTHEDEV_DEBUG": ("debug", None, bool),
        }

        for env_var, mapping in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                self._apply_env_setting(base_config, mapping, value)

        return base_config

    def _update_config_section(
        self, config_section: object, toml_section: dict[str, Any]
    ) -> None:
        """Update a configuration section with values from TOML.

        Args:
            config_section: Configuration section object to update
            toml_section: Dictionary of values from TOML
        """
        for key, value in toml_section.items():
            if hasattr(config_section, key):
                setattr(config_section, key, value)

    def _apply_env_setting(self, config: AppConfig, mapping: tuple[Any, ...], value: str) -> None:
        """Apply an environment variable setting to configuration.

        Args:
            config: Configuration object to update
            mapping: Tuple describing where to apply the setting
            value: String value from environment variable
        """
        if len(mapping) == 3 and mapping[1] is None:
            # Global setting
            field_name, _, converter = mapping
            converted_value = self._convert_value(value, converter)
            setattr(config, field_name, converted_value)
        else:
            # Section setting
            section_name, field_name = mapping[:2]
            converter = mapping[2] if len(mapping) > 2 else str
            section = getattr(config, section_name)
            converted_value = self._convert_value(value, converter)
            setattr(section, field_name, converted_value)

    def _convert_value(self, value: str, converter: type[Any]) -> Any:
        """Convert string value to appropriate type.

        Args:
            value: String value to convert
            converter: Type to convert to (bool, int, or str)

        Returns:
            Converted value
        """
        if converter is bool:
            return value.lower() in ("true", "1", "yes", "on")
        elif converter is int:
            return int(value)
        else:
            return value

    def _generate_default_toml(self) -> str:
        """Generate default TOML configuration content.

        Returns:
            Default TOML configuration as string
        """
        return """# imthedev Configuration File
# This file contains configuration settings for the imthedev application.
# Settings can be overridden by environment variables using the pattern:
# IMTHEDEV_<SECTION>_<SETTING> (e.g., IMTHEDEV_AI_CLAUDE_API_KEY)

# ============================================================================
# IMPORTANT: API KEY CONFIGURATION REQUIRED!
# ============================================================================
# You MUST configure at least one AI API key to use imthedev.
#
# Choose one of these methods:
#
# Option 1: Environment Variables (Recommended)
#   export CLAUDE_API_KEY='your-claude-api-key-here'
#   export OPENAI_API_KEY='your-openai-api-key-here'
#
# Option 2: Configuration File
#   Uncomment and set the API keys below in the [ai] section
#
# To get API keys:
#   - Claude: https://console.anthropic.com/
#   - OpenAI: https://platform.openai.com/api-keys
# ============================================================================

# Global settings
debug = false

[database]
# SQLite database configuration
path = "~/.imthedev/imthedev.db"
timeout = 30
backup_enabled = true
backup_interval_hours = 24

[storage]
# File storage configuration
context_dir = "~/.imthedev/contexts"
backup_dir = "~/.imthedev/backups"
max_context_history = 100
compress_backups = true

[ai]
# AI provider configuration
# REQUIRED: At least one API key must be configured!
default_model = "claude"  # Options: claude, claude-instant, gpt-4, gpt-3.5-turbo

# Uncomment ONE OR BOTH of the following lines and add your API key:
# claude_api_key = "sk-ant-..."  # Get from https://console.anthropic.com/
# openai_api_key = "sk-..."      # Get from https://platform.openai.com/api-keys

# Note: Using environment variables is more secure than storing keys in this file:
#   export CLAUDE_API_KEY='your-key-here'
#   export OPENAI_API_KEY='your-key-here'

request_timeout = 30
max_retries = 3
retry_delay = 1.0

[ui]
# User interface configuration
theme = "dark"  # Options: dark, light, auto
autopilot_enabled = false
show_ai_reasoning = true
command_confirmation = true
max_log_lines = 1000

[security]
# Security configuration
require_approval = true
dangerous_commands = [
    "rm", "rmdir", "del", "format", "fdisk", "mkfs",
    "dd", "chmod 777", "chown", "sudo rm", "sudo chmod"
]
allowed_directories = []  # Empty = all allowed
blocked_directories = ["/etc", "/boot", "/sys", "/proc", "/dev"]
api_key_encryption = true

[logging]
# Logging configuration
level = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
file_path = "~/.imthedev/logs/imthedev.log"
max_file_size = 10485760  # 10MB in bytes
backup_count = 5
console_enabled = true
"""


class ConfigurationError(Exception):
    """Exception raised for configuration-related errors."""

    pass
