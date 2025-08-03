"""Tests for the ConfigManager and AppConfig implementation.

This module contains comprehensive tests for the configuration management system
including TOML file loading, environment variable overrides, and validation.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from imthedev.infrastructure.config import AppConfig, ConfigManager
from imthedev.infrastructure.config.config_manager import (
    AIConfig,
    ConfigurationError,
    DatabaseConfig,
    LoggingConfig,
    SecurityConfig,
    StorageConfig,
    UIConfig,
)


class TestAppConfig:
    """Test suite for AppConfig dataclass."""

    def test_default_configuration(self) -> None:
        """Test that default configuration is created correctly."""
        config = AppConfig()

        # Test default values
        assert config.debug is False
        # Config file should use Path.home() now
        expected_config_file = str(Path.home() / ".imthedev" / "config.toml")
        assert config.config_file == expected_config_file

        # Test nested configurations have defaults
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.storage, StorageConfig)
        assert isinstance(config.ai, AIConfig)
        assert isinstance(config.ui, UIConfig)
        assert isinstance(config.security, SecurityConfig)
        assert isinstance(config.logging, LoggingConfig)

        # Test specific defaults
        assert config.database.path == "imthedev.db"
        assert config.ai.default_model == "gemini-2.5-flash"
        assert config.ui.theme == "dark"
        assert config.logging.level == "INFO"

        # Test paths use Path.home() instead of ~
        expected_context_dir = str(Path.home() / ".imthedev" / "contexts")
        expected_backup_dir = str(Path.home() / ".imthedev" / "backups")
        expected_log_path = str(Path.home() / ".imthedev" / "logs" / "imthedev.log")

        assert config.storage.context_dir == expected_context_dir
        assert config.storage.backup_dir == expected_backup_dir
        assert config.logging.file_path == expected_log_path

    def test_expand_paths(self) -> None:
        """Test path expansion functionality."""
        config = AppConfig()

        # Set paths with ~ to test expansion (simulating paths from TOML/env)
        config.database.path = "~/test/db.sqlite"
        config.storage.context_dir = "~/test/contexts"
        config.storage.backup_dir = "~/test/backups"
        config.logging.file_path = "~/test/logs/app.log"
        config.config_file = "~/test/config.toml"

        # Expand paths
        config.expand_paths()

        # Verify paths are expanded using Path.expanduser()
        str(Path.home())
        assert config.database.path == str(Path.home() / "test" / "db.sqlite")
        assert config.storage.context_dir == str(Path.home() / "test" / "contexts")
        assert config.storage.backup_dir == str(Path.home() / "test" / "backups")
        assert config.logging.file_path == str(
            Path.home() / "test" / "logs" / "app.log"
        )
        assert config.config_file == str(Path.home() / "test" / "config.toml")

    def test_validation_success(self) -> None:
        """Test successful configuration validation."""
        config = AppConfig()
        config.ai.gemini_api_key = "test-key"

        errors = config.validate()
        assert errors == []

    def test_validation_no_api_keys(self) -> None:
        """Test validation failure when no API keys are provided."""
        config = AppConfig()

        errors = config.validate()
        assert "Gemini API key must be configured" in errors

    def test_validation_invalid_model(self) -> None:
        """Test validation failure for invalid AI model."""
        config = AppConfig()
        config.ai.gemini_api_key = "test-key"
        config.ai.default_model = "invalid-model"

        errors = config.validate()
        assert any("Invalid default AI model" in error for error in errors)

    def test_validation_invalid_theme(self) -> None:
        """Test validation failure for invalid UI theme."""
        config = AppConfig()
        config.ai.gemini_api_key = "test-key"
        config.ui.theme = "invalid-theme"

        errors = config.validate()
        assert any("Invalid UI theme" in error for error in errors)

    def test_validation_invalid_logging_level(self) -> None:
        """Test validation failure for invalid logging level."""
        config = AppConfig()
        config.ai.gemini_api_key = "test-key"
        config.logging.level = "INVALID"

        errors = config.validate()
        assert any("Invalid logging level" in error for error in errors)

    def test_validation_negative_values(self) -> None:
        """Test validation failure for negative numeric values."""
        config = AppConfig()
        config.ai.gemini_api_key = "test-key"
        config.database.timeout = -1
        config.storage.max_context_history = 0
        config.ai.request_timeout = -5
        config.ai.max_retries = -1

        errors = config.validate()
        assert any("Database timeout must be positive" in error for error in errors)
        assert any("Max context history must be positive" in error for error in errors)
        assert any("AI request timeout must be positive" in error for error in errors)
        assert any("AI max retries must be non-negative" in error for error in errors)


class TestConfigManager:
    """Test suite for ConfigManager."""

    def test_load_default_config(self) -> None:
        """Test loading default configuration when no file exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "nonexistent.toml"

            # Mock API key to pass validation
            with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
                manager = ConfigManager(str(config_file))
                config = manager.load_config()

                assert isinstance(config, AppConfig)
                assert config.debug is False
                assert config.ai.default_model == "gemini-2.5-flash"

    def test_load_config_from_toml_file(self) -> None:
        """Test loading configuration from TOML file."""
        toml_content = """
debug = true

[database]
path = "/custom/db.sqlite"
timeout = 60

[storage]
context_dir = "~/custom/contexts"
backup_dir = "~/custom/backups"

[ai]
default_model = "gemini-2.5-pro"
request_timeout = 45

[ui]
theme = "light"
autopilot_enabled = true

[logging]
level = "DEBUG"
file_path = "~/custom/logs/app.log"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            config_file = f.name

        try:
            # Mock API key to pass validation
            with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
                manager = ConfigManager(config_file)
                config = manager.load_config()

                # Test that TOML values override defaults
                assert config.debug is True
                assert config.database.path == "/custom/db.sqlite"
                assert config.database.timeout == 60
                assert config.ai.default_model == "gemini-2.5-pro"
                assert config.ai.request_timeout == 45
                assert config.ui.theme == "light"
                assert config.ui.autopilot_enabled is True
                assert config.logging.level == "DEBUG"

                # Test that paths with ~ are properly expanded
                expected_context_dir = str(Path.home() / "custom" / "contexts")
                expected_backup_dir = str(Path.home() / "custom" / "backups")
                expected_log_path = str(Path.home() / "custom" / "logs" / "app.log")

                assert config.storage.context_dir == expected_context_dir
                assert config.storage.backup_dir == expected_backup_dir
                assert config.logging.file_path == expected_log_path

        finally:
            os.unlink(config_file)

    def test_environment_variable_overrides(self) -> None:
        """Test that environment variables override TOML and defaults."""
        env_vars = {
            "IMTHEDEV_DEBUG": "true",
            "IMTHEDEV_DATABASE_PATH": "/env/db.sqlite",
            "IMTHEDEV_DATABASE_TIMEOUT": "120",
            "IMTHEDEV_AI_DEFAULT_MODEL": "gemini-2.5-flash-8b",
            "IMTHEDEV_AI_REQUEST_TIMEOUT": "90",
            "GEMINI_API_KEY": "env-gemini-key",
            "IMTHEDEV_UI_THEME": "auto",
            "IMTHEDEV_UI_AUTOPILOT_ENABLED": "true",
            "IMTHEDEV_LOGGING_LEVEL": "WARNING",
        }

        with patch.dict(os.environ, env_vars):
            manager = ConfigManager()
            config = manager.load_config()

            # Test environment variable overrides
            assert config.debug is True
            assert config.database.path == "/env/db.sqlite"
            assert config.database.timeout == 120
            assert config.ai.default_model == "gemini-2.5-flash-8b"
            assert config.ai.request_timeout == 90
            assert config.ai.gemini_api_key == "env-gemini-key"
            assert config.ui.theme == "auto"
            assert config.ui.autopilot_enabled is True
            assert config.logging.level == "WARNING"

    def test_boolean_environment_variables(self) -> None:
        """Test parsing of boolean environment variables."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
            ("off", False),
            ("anything_else", False),
        ]

        for env_value, expected in test_cases:
            with patch.dict(
                os.environ,
                {
                    "IMTHEDEV_DEBUG": env_value,
                    "GEMINI_API_KEY": "test-key",  # Add API key for validation
                },
            ):
                manager = ConfigManager()
                config = manager.load_config()
                assert config.debug == expected, f"Failed for env_value: {env_value}"

    def test_integer_environment_variables(self) -> None:
        """Test parsing of integer environment variables."""
        with patch.dict(
            os.environ,
            {
                "IMTHEDEV_DATABASE_TIMEOUT": "300",
                "IMTHEDEV_AI_MAX_RETRIES": "5",
                "GEMINI_API_KEY": "test-key",  # Add API key for validation
            },
        ):
            manager = ConfigManager()
            config = manager.load_config()

            assert config.database.timeout == 300
            assert config.ai.max_retries == 5

    def test_alternative_api_key_environment_variables(self) -> None:
        """Test that common API key environment variable names work."""
        env_vars = {
            "GEMINI_API_KEY": "gemini-from-standard-env",
            "GOOGLE_API_KEY": "gemini-from-google-env",
        }

        with patch.dict(os.environ, env_vars):
            manager = ConfigManager()
            config = manager.load_config()

            # GOOGLE_API_KEY should override GEMINI_API_KEY due to order in mapping
            assert config.ai.gemini_api_key == "gemini-from-google-env"

    def test_config_validation_error(self) -> None:
        """Test that validation errors raise ConfigurationError."""
        toml_content = """
[ai]
default_model = "invalid-model"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            config_file = f.name

        try:
            manager = ConfigManager(config_file)

            with pytest.raises(
                ConfigurationError, match="Configuration validation failed"
            ):
                manager.load_config()
        finally:
            os.unlink(config_file)

    def test_invalid_toml_file(self) -> None:
        """Test handling of invalid TOML file."""
        invalid_toml = """
        [database
        path = "invalid toml
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(invalid_toml)
            config_file = f.name

        try:
            manager = ConfigManager(config_file)

            with pytest.raises(ConfigurationError, match="Failed to load config file"):
                manager.load_config()
        finally:
            os.unlink(config_file)

    def test_get_config_before_load(self) -> None:
        """Test that get_config raises error before load_config is called."""
        manager = ConfigManager()

        with pytest.raises(
            ConfigurationError, match="Configuration has not been loaded"
        ):
            manager.get_config()

    def test_get_config_after_load(self) -> None:
        """Test that get_config returns loaded configuration."""
        with patch.dict(os.environ, {"CLAUDE_API_KEY": "test-key"}):
            manager = ConfigManager()
            original_config = manager.load_config()
            retrieved_config = manager.get_config()

            assert retrieved_config is original_config

    def test_create_default_config_file(self) -> None:
        """Test creation of default configuration file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.toml"
            manager = ConfigManager()

            created_path = manager.create_default_config_file(str(config_path))

            assert created_path == str(config_path)
            assert config_path.exists()

            # Verify the file contains expected content
            content = config_path.read_text()
            assert "# imthedev Configuration File" in content
            assert "[database]" in content
            assert "[ai]" in content
            assert "[ui]" in content
            assert "[security]" in content
            assert "[logging]" in content

    def test_create_default_config_file_creates_directory(self) -> None:
        """Test that creating config file creates parent directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "nested" / "dir" / "config.toml"
            manager = ConfigManager()

            created_path = manager.create_default_config_file(str(config_path))

            assert created_path == str(config_path)
            assert config_path.exists()
            assert config_path.parent.exists()

    def test_path_robustness_with_path_home(self) -> None:
        """Test that using Path.home() is more robust than '~'."""
        config = AppConfig()

        # Verify defaults use absolute paths
        assert Path(config.storage.context_dir).is_absolute()
        assert Path(config.storage.backup_dir).is_absolute()
        assert Path(config.logging.file_path).is_absolute()
        assert Path(config.config_file).is_absolute()

        # Verify paths don't contain '~'
        assert "~" not in config.storage.context_dir
        assert "~" not in config.storage.backup_dir
        assert "~" not in config.logging.file_path
        assert "~" not in config.config_file

    def test_toml_and_env_precedence(self) -> None:
        """Test that environment variables take precedence over TOML file."""
        toml_content = """
[database]
timeout = 30

[ai]
default_model = "gemini-2.5-flash"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            config_file = f.name

        try:
            # Environment variables should override TOML values
            env_vars = {
                "IMTHEDEV_DATABASE_TIMEOUT": "60",
                "IMTHEDEV_AI_DEFAULT_MODEL": "gemini-2.5-pro",
                "GEMINI_API_KEY": "test-key",  # Add API key for validation
            }

            with patch.dict(os.environ, env_vars):
                manager = ConfigManager(config_file)
                config = manager.load_config()

                # Environment variables should take precedence
                assert config.database.timeout == 60  # From env, not 30 from TOML
                assert (
                    config.ai.default_model == "gemini-2.5-pro"
                )  # From env, not 'gemini-2.5-flash' from TOML
        finally:
            os.unlink(config_file)

    def test_partial_toml_config(self) -> None:
        """Test that partial TOML config merges with defaults."""
        toml_content = """
debug = true

[ai]
default_model = "gemini-2.5-pro"

[ui]
theme = "light"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            config_file = f.name

        try:
            with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
                manager = ConfigManager(config_file)
                config = manager.load_config()

                # Specified values should be from TOML
                assert config.debug is True
                assert config.ai.default_model == "gemini-2.5-pro"
                assert config.ui.theme == "light"

                # Unspecified values should be defaults
                assert config.database.timeout == 30  # Default
                assert config.ai.request_timeout == 30  # Default
                assert config.ui.autopilot_enabled is False  # Default
                assert config.logging.level == "INFO"  # Default
        finally:
            os.unlink(config_file)


class TestConfigurationSections:
    """Test individual configuration section classes."""

    def test_database_config_defaults(self) -> None:
        """Test DatabaseConfig default values."""
        config = DatabaseConfig()

        assert config.path == "imthedev.db"
        assert config.timeout == 30
        assert config.backup_enabled is True
        assert config.backup_interval_hours == 24

    def test_storage_config_defaults(self) -> None:
        """Test StorageConfig default values."""
        config = StorageConfig()

        # Paths should now use Path.home() instead of ~
        expected_context_dir = str(Path.home() / ".imthedev" / "contexts")
        expected_backup_dir = str(Path.home() / ".imthedev" / "backups")

        assert config.context_dir == expected_context_dir
        assert config.backup_dir == expected_backup_dir
        assert config.max_context_history == 100
        assert config.compress_backups is True

    def test_ai_config_defaults(self) -> None:
        """Test AIConfig default values."""
        config = AIConfig()

        assert config.default_model == "gemini-2.5-flash"
        assert config.gemini_api_key is None
        assert config.request_timeout == 30
        assert config.max_retries == 3
        assert config.retry_delay == 1.0

    def test_ui_config_defaults(self) -> None:
        """Test UIConfig default values."""
        config = UIConfig()

        assert config.theme == "dark"
        assert config.autopilot_enabled is False
        assert config.show_ai_reasoning is True
        assert config.command_confirmation is True
        assert config.max_log_lines == 1000

    def test_security_config_defaults(self) -> None:
        """Test SecurityConfig default values."""
        config = SecurityConfig()

        assert config.require_approval is True
        assert len(config.dangerous_commands) > 0
        assert "rm" in config.dangerous_commands
        assert "sudo rm" in config.dangerous_commands
        assert config.allowed_directories == []
        assert "/etc" in config.blocked_directories
        assert config.api_key_encryption is True

    def test_logging_config_defaults(self) -> None:
        """Test LoggingConfig default values."""
        config = LoggingConfig()

        # Path should now use Path.home() instead of ~
        expected_log_path = str(Path.home() / ".imthedev" / "logs" / "imthedev.log")

        assert config.level == "INFO"
        assert "%(asctime)s" in config.format
        assert config.file_path == expected_log_path
        assert config.max_file_size == 10 * 1024 * 1024  # 10MB
        assert config.backup_count == 5
        assert config.console_enabled is True
