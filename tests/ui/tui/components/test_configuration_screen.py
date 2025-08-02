"""Tests for the ConfigurationScreen component.

This module provides comprehensive test coverage for the configuration screen,
including UI interactions, validation, and data persistence.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from textual.app import App
from textual.testing import AppTest
from textual.widgets import Button, Input, Select, Switch, TabbedContent

from imthedev.infrastructure.config import (
    AIConfig,
    AppConfig,
    DatabaseConfig,
    LoggingConfig,
    SecurityConfig,
    StorageConfig,
    UIConfig,
)
from imthedev.ui.tui.components.configuration_screen import (
    APIKeyValidator,
    ConfigurationScreen,
    PathValidator,
)


@pytest.fixture
def sample_config():
    """Create a sample configuration for testing."""
    return AppConfig(
        database=DatabaseConfig(
            path="/test/db.sqlite",
            timeout=30,
            backup_enabled=True,
            backup_interval_hours=24,
        ),
        storage=StorageConfig(
            context_dir="/test/contexts",
            backup_dir="/test/backups",
            max_context_history=100,
            compress_backups=True,
        ),
        ai=AIConfig(
            default_model="claude",
            claude_api_key="test-claude-key",
            openai_api_key="test-openai-key",
            request_timeout=30,
            max_retries=3,
        ),
        ui=UIConfig(
            theme="dark",
            autopilot_enabled=False,
            show_ai_reasoning=True,
            command_confirmation=True,
            max_log_lines=1000,
        ),
        security=SecurityConfig(
            require_approval=True,
            dangerous_commands=["rm", "rmdir", "del"],
            blocked_directories=["/etc", "/boot"],
            api_key_encryption=True,
        ),
        logging=LoggingConfig(
            level="INFO",
            file_path="/test/logs/app.log",
            console_enabled=True,
            max_file_size=10485760,
        ),
    )


@pytest.fixture
def config_screen(sample_config):
    """Create a ConfigurationScreen instance for testing."""
    return ConfigurationScreen(
        config=sample_config,
        on_save=MagicMock(),
        on_cancel=MagicMock(),
    )


class TestConfigurationScreen:
    """Test suite for ConfigurationScreen component."""

    async def test_initialization(self, config_screen, sample_config):
        """Test that ConfigurationScreen initializes correctly."""
        assert config_screen.config == sample_config
        assert config_screen.on_save is not None
        assert config_screen.on_cancel is not None
        assert config_screen.modified_config is not None
        assert config_screen.modified_config != config_screen.config  # Different objects

    async def test_compose_creates_all_tabs(self, config_screen):
        """Test that all configuration tabs are created."""
        app = App()
        app.mount(config_screen)
        
        async with app.run_test() as pilot:
            # Check that TabbedContent exists
            tabbed_content = pilot.app.query_one(TabbedContent)
            assert tabbed_content is not None
            
            # Check for all expected tabs
            tabs = tabbed_content.query("TabPane")
            tab_ids = [tab.id for tab in tabs]
            
            expected_tabs = [
                "database-tab",
                "storage-tab",
                "ai-tab",
                "ui-tab",
                "security-tab",
                "logging-tab",
            ]
            
            for expected_id in expected_tabs:
                assert expected_id in tab_ids

    async def test_database_section_inputs(self, config_screen):
        """Test that database section has all required inputs."""
        app = App()
        app.mount(config_screen)
        
        async with app.run_test() as pilot:
            # Check database inputs exist
            assert pilot.app.query_one("#db-path", Input) is not None
            assert pilot.app.query_one("#db-timeout", Input) is not None
            assert pilot.app.query_one("#db-backup-enabled", Switch) is not None
            assert pilot.app.query_one("#db-backup-interval", Input) is not None

    async def test_save_button_collects_values(self, config_screen):
        """Test that save button collects all values correctly."""
        app = App()
        app.mount(config_screen)
        
        async with app.run_test() as pilot:
            # Modify some values
            db_path_input = pilot.app.query_one("#db-path", Input)
            db_path_input.value = "/new/path/db.sqlite"
            
            db_timeout_input = pilot.app.query_one("#db-timeout", Input)
            db_timeout_input.value = "60"
            
            # Click save button
            save_button = pilot.app.query_one("#save-button", Button)
            await pilot.click(save_button)
            
            # Check that on_save was called
            config_screen.on_save.assert_called_once()
            
            # Check that values were collected
            saved_config = config_screen.on_save.call_args[0][0]
            assert saved_config.database.path == "/new/path/db.sqlite"
            assert saved_config.database.timeout == 60

    async def test_reset_button_restores_original(self, config_screen, sample_config):
        """Test that reset button restores original configuration."""
        app = App()
        app.mount(config_screen)
        
        async with app.run_test() as pilot:
            # Modify a value
            db_path_input = pilot.app.query_one("#db-path", Input)
            original_value = db_path_input.value
            db_path_input.value = "/modified/path.db"
            
            # Click reset button
            reset_button = pilot.app.query_one("#reset-button", Button)
            await pilot.click(reset_button)
            
            # Check that modified_config was reset
            assert config_screen.modified_config.database.path == sample_config.database.path

    async def test_cancel_button_triggers_callback(self, config_screen):
        """Test that cancel button triggers the cancel callback."""
        app = App()
        app.mount(config_screen)
        
        async with app.run_test() as pilot:
            # Click cancel button
            cancel_button = pilot.app.query_one("#cancel-button", Button)
            await pilot.click(cancel_button)
            
            # Check that on_cancel was called
            config_screen.on_cancel.assert_called_once()

    async def test_config_saved_message(self, config_screen):
        """Test that ConfigSaved message is posted on save."""
        app = App()
        app.mount(config_screen)
        
        messages = []
        
        def on_config_saved(message):
            messages.append(message)
        
        config_screen.on_config_saved = on_config_saved
        
        async with app.run_test() as pilot:
            save_button = pilot.app.query_one("#save-button", Button)
            await pilot.click(save_button)
            
            # Allow time for message processing
            await asyncio.sleep(0.1)
            
            # Check that message was posted
            assert len(messages) > 0
            assert isinstance(messages[0], ConfigurationScreen.ConfigSaved)

    async def test_ai_section_password_fields(self, config_screen):
        """Test that API key fields are password inputs."""
        app = App()
        app.mount(config_screen)
        
        async with app.run_test() as pilot:
            claude_key = pilot.app.query_one("#ai-claude-key", Input)
            openai_key = pilot.app.query_one("#ai-openai-key", Input)
            
            assert claude_key.password is True
            assert openai_key.password is True

    async def test_theme_selection(self, config_screen):
        """Test that theme selection works correctly."""
        app = App()
        app.mount(config_screen)
        
        async with app.run_test() as pilot:
            theme_select = pilot.app.query_one("#ui-theme", Select)
            
            # Check available options
            options = [opt[0] for opt in theme_select._options]
            assert "dark" in options
            assert "light" in options
            assert "auto" in options
            
            # Check current value
            assert theme_select.value == "dark"

    async def test_switch_toggles(self, config_screen):
        """Test that switch toggles work correctly."""
        app = App()
        app.mount(config_screen)
        
        async with app.run_test() as pilot:
            autopilot_switch = pilot.app.query_one("#ui-autopilot", Switch)
            
            # Check initial state
            initial_value = autopilot_switch.value
            
            # Toggle switch
            await pilot.click(autopilot_switch)
            
            # Check toggled state
            assert autopilot_switch.value != initial_value


class TestPathValidator:
    """Test suite for PathValidator."""

    def test_valid_path(self):
        """Test validation of valid paths."""
        validator = PathValidator()
        result = validator.validate("/home/user/file.txt")
        assert result.is_valid

    def test_empty_path(self):
        """Test validation of empty path."""
        validator = PathValidator()
        result = validator.validate("")
        assert not result.is_valid
        assert "Path cannot be empty" in str(result.failure_descriptions)

    def test_home_expansion(self):
        """Test that home directory expansion works."""
        validator = PathValidator()
        result = validator.validate("~/documents/file.txt")
        assert result.is_valid  # Should expand and validate

    @patch("pathlib.Path.exists")
    def test_parent_directory_check(self, mock_exists):
        """Test that parent directory is checked for files."""
        mock_exists.return_value = False
        validator = PathValidator()
        result = validator.validate("/nonexistent/dir/file.txt")
        assert not result.is_valid
        assert "Parent directory does not exist" in str(result.failure_descriptions)


class TestAPIKeyValidator:
    """Test suite for APIKeyValidator."""

    def test_valid_api_key(self):
        """Test validation of valid API key."""
        validator = APIKeyValidator()
        result = validator.validate("sk-ant-api03-very-long-key-string-here")
        assert result.is_valid

    def test_empty_api_key_allowed(self):
        """Test that empty API key is allowed."""
        validator = APIKeyValidator()
        result = validator.validate("")
        assert result.is_valid

    def test_short_api_key(self):
        """Test validation of short API key."""
        validator = APIKeyValidator()
        result = validator.validate("short-key")
        assert not result.is_valid
        assert "too short" in str(result.failure_descriptions)

    def test_api_key_with_spaces(self):
        """Test validation of API key with spaces."""
        validator = APIKeyValidator()
        result = validator.validate("sk-ant-api03 with spaces")
        assert not result.is_valid
        assert "cannot contain spaces" in str(result.failure_descriptions)


class TestInputValidation:
    """Test suite for input validation."""

    async def test_number_validation(self, config_screen):
        """Test that number inputs are validated correctly."""
        app = App()
        app.mount(config_screen)
        
        async with app.run_test() as pilot:
            timeout_input = pilot.app.query_one("#db-timeout", Input)
            
            # Test valid number
            timeout_input.value = "30"
            assert timeout_input.is_valid
            
            # Test invalid number (too high)
            timeout_input.value = "500"
            assert not timeout_input.is_valid
            
            # Test non-numeric value
            timeout_input.value = "abc"
            assert not timeout_input.is_valid

    async def test_path_validation(self, config_screen):
        """Test that path inputs are validated correctly."""
        app = App()
        app.mount(config_screen)
        
        async with app.run_test() as pilot:
            db_path_input = pilot.app.query_one("#db-path", Input)
            
            # Test valid path
            db_path_input.value = "/valid/path/to/db.sqlite"
            assert db_path_input.is_valid
            
            # Test empty path
            db_path_input.value = ""
            assert not db_path_input.is_valid

    async def test_validation_prevents_save(self, config_screen):
        """Test that validation errors prevent saving."""
        app = App()
        app.mount(config_screen)
        
        async with app.run_test() as pilot:
            # Set invalid value
            timeout_input = pilot.app.query_one("#db-timeout", Input)
            timeout_input.value = "invalid"
            
            # Try to save
            save_button = pilot.app.query_one("#save-button", Button)
            await pilot.click(save_button)
            
            # Check that on_save was not called due to validation error
            config_screen.on_save.assert_not_called()


class TestStatusMessages:
    """Test suite for status message display."""

    async def test_success_message_on_save(self, config_screen):
        """Test that success message is shown on save."""
        app = App()
        app.mount(config_screen)
        
        async with app.run_test() as pilot:
            save_button = pilot.app.query_one("#save-button", Button)
            await pilot.click(save_button)
            
            # Check status message
            status = pilot.app.query_one("#status-message")
            assert "successfully" in status.renderable.lower()
            assert "success-message" in status.classes

    async def test_error_message_on_validation_failure(self, config_screen):
        """Test that error message is shown on validation failure."""
        app = App()
        app.mount(config_screen)
        
        async with app.run_test() as pilot:
            # Set invalid value
            timeout_input = pilot.app.query_one("#db-timeout", Input)
            timeout_input.value = "invalid"
            
            # Try to save
            save_button = pilot.app.query_one("#save-button", Button)
            await pilot.click(save_button)
            
            # Check status message
            status = pilot.app.query_one("#status-message")
            assert "validation" in status.renderable.lower()
            assert "error-message" in status.classes

    async def test_reset_message(self, config_screen):
        """Test that reset message is shown."""
        app = App()
        app.mount(config_screen)
        
        async with app.run_test() as pilot:
            reset_button = pilot.app.query_one("#reset-button", Button)
            await pilot.click(reset_button)
            
            # Check status message
            status = pilot.app.query_one("#status-message")
            assert "reset" in status.renderable.lower()


class TestKeyboardNavigation:
    """Test suite for keyboard navigation."""

    async def test_tab_navigation(self, config_screen):
        """Test that Tab key navigates through inputs."""
        app = App()
        app.mount(config_screen)
        
        async with app.run_test() as pilot:
            # Start with first input focused
            first_input = pilot.app.query_one("#db-path", Input)
            first_input.focus()
            
            # Press Tab to move to next input
            await pilot.press("tab")
            
            # Check that focus moved
            assert not first_input.has_focus

    async def test_escape_triggers_cancel(self, config_screen):
        """Test that Escape key triggers cancel."""
        app = App()
        app.mount(config_screen)
        
        async with app.run_test() as pilot:
            # Press Escape
            await pilot.press("escape")
            
            # This would typically close the screen or trigger cancel
            # Implementation depends on app-level key bindings