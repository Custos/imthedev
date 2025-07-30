"""Tests for the application bootstrap and ImTheDevApp implementation.

This module contains comprehensive tests for the application bootstrap functionality
including dependency injection, service initialization, and lifecycle management.
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Textual mocking is handled in conftest.py

from imthedev.app.bootstrap import ImTheDevApp, bootstrap_application, main
from imthedev.infrastructure.config import AppConfig, ConfigManager


class TestImTheDevApp:
    """Test suite for ImTheDevApp class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        config = AppConfig()
        config.database.path = ":memory:"  # Use in-memory SQLite for tests
        config.storage.context_dir = "/tmp/test_contexts"
        config.ai.claude_api_key = "test-claude-key"
        config.ai.openai_api_key = "test-openai-key"
        return config
    
    def test_app_initialization_state(self, mock_config):
        """Test that app initializes with correct state."""
        app = ImTheDevApp(mock_config)
        
        assert app.config is mock_config
        assert not app.is_initialized()
        assert app.event_bus is None
        assert app.project_repository is None
        assert app.context_repository is None
        assert app.command_engine is None
        assert app.ai_orchestrator is None
        assert app.state_manager is None
        assert app.core_facade is None
    
    @pytest.mark.asyncio
    async def test_successful_initialization(self, mock_config):
        """Test successful application initialization."""
        app = ImTheDevApp(mock_config)
        
        # Mock all the service classes to avoid actual initialization
        with patch('imthedev.app.bootstrap.EventBus') as mock_event_bus, \
             patch('imthedev.app.bootstrap.ProjectRepository') as mock_project_repo, \
             patch('imthedev.app.bootstrap.ContextRepository') as mock_context_repo, \
             patch('imthedev.app.bootstrap.AIOrchestratorImpl') as mock_ai_orchestrator, \
             patch('imthedev.app.bootstrap.CommandEngineImpl') as mock_command_engine, \
             patch('imthedev.app.bootstrap.StateManagerImpl') as mock_state_manager, \
             patch('imthedev.app.bootstrap.CoreFacade') as mock_core_facade:
            
            # Set up mocks
            mock_event_bus.return_value = MagicMock()
            mock_project_repo.return_value = AsyncMock()
            mock_context_repo.return_value = AsyncMock()
            mock_ai_orchestrator.return_value = AsyncMock()
            mock_command_engine.return_value = AsyncMock()
            mock_state_manager.return_value = AsyncMock()
            mock_core_facade.return_value = AsyncMock()
            
            await app.initialize()
            
            # Verify initialization
            assert app.is_initialized()
            assert app.event_bus is not None
            assert app.project_repository is not None
            assert app.context_repository is not None
            assert app.ai_orchestrator is not None
            assert app.command_engine is not None
            assert app.state_manager is not None
            assert app.core_facade is not None
            
            # Verify service initialization calls
            mock_project_repo.return_value.initialize.assert_called_once()
            mock_context_repo.return_value.initialize.assert_called_once()
            mock_core_facade.return_value.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialization_failure_cleanup(self, mock_config):
        """Test that initialization failure triggers cleanup."""
        app = ImTheDevApp(mock_config)
        
        with patch('imthedev.app.bootstrap.EventBus') as mock_event_bus, \
             patch('imthedev.app.bootstrap.ProjectRepository') as mock_project_repo:
            
            # Make project repository initialization fail
            mock_event_bus.return_value = MagicMock()
            mock_project_repo.return_value.initialize.side_effect = Exception("Init failed")
            
            with pytest.raises(RuntimeError, match="Application initialization failed"):
                await app.initialize()
            
            # Verify app is not marked as initialized
            assert not app.is_initialized()
    
    @pytest.mark.asyncio
    async def test_double_initialization_warning(self, mock_config):
        """Test warning on double initialization."""
        app = ImTheDevApp(mock_config)
        
        with patch('imthedev.app.bootstrap.EventBus') as mock_event_bus, \
             patch('imthedev.app.bootstrap.ProjectRepository') as mock_project_repo, \
             patch('imthedev.app.bootstrap.ContextRepository') as mock_context_repo, \
             patch('imthedev.app.bootstrap.AIOrchestratorImpl') as mock_ai_orchestrator, \
             patch('imthedev.app.bootstrap.CommandEngineImpl') as mock_command_engine, \
             patch('imthedev.app.bootstrap.StateManagerImpl') as mock_state_manager, \
             patch('imthedev.app.bootstrap.CoreFacade') as mock_core_facade, \
             patch('imthedev.app.bootstrap.logger') as mock_logger:
            
            # Set up mocks
            mock_event_bus.return_value = MagicMock()
            mock_project_repo.return_value = AsyncMock()
            mock_context_repo.return_value = AsyncMock()
            mock_ai_orchestrator.return_value = AsyncMock()
            mock_command_engine.return_value = AsyncMock()
            mock_state_manager.return_value = AsyncMock()
            mock_core_facade.return_value = AsyncMock()
            
            # First initialization
            await app.initialize()
            assert app.is_initialized()
            
            # Second initialization should warn and return early
            await app.initialize()
            mock_logger.warning.assert_called_with("Application already initialized")
    
    @pytest.mark.asyncio
    async def test_run_without_initialization(self, mock_config):
        """Test that running without initialization raises error."""
        app = ImTheDevApp(mock_config)
        
        with pytest.raises(RuntimeError, match="Application must be initialized before running"):
            await app.run()
    
    @pytest.mark.asyncio
    async def test_successful_run(self, mock_config):
        """Test successful application run."""
        app = ImTheDevApp(mock_config)
        app._initialized = True  # Mock initialization
        
        with patch('imthedev.ui.tui.app.ImTheDevApp') as mock_tui_app:
            mock_tui_instance = AsyncMock()
            mock_tui_app.return_value = mock_tui_instance
            
            # Mock cleanup to avoid actual cleanup during test
            with patch.object(app, 'cleanup', new_callable=AsyncMock):
                await app.run()
            
            # Verify TUI app was created and run
            mock_tui_app.assert_called_once()
            mock_tui_instance.run_async.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_keyboard_interrupt(self, mock_config):
        """Test handling of keyboard interrupt during run."""
        app = ImTheDevApp(mock_config)
        app._initialized = True
        
        with patch('imthedev.ui.tui.app.ImTheDevApp') as mock_tui_app, \
             patch.object(app, 'cleanup', new_callable=AsyncMock) as mock_cleanup:
            
            mock_tui_instance = AsyncMock()
            mock_tui_instance.run_async.side_effect = KeyboardInterrupt()
            mock_tui_app.return_value = mock_tui_instance
            
            await app.run()  # Should not raise
            
            # Verify cleanup was called
            mock_cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_partial_initialization(self, mock_config):
        """Test cleanup with partially initialized services."""
        app = ImTheDevApp(mock_config)
        
        # Set up partial initialization
        app.event_bus = MagicMock()
        app.project_repository = AsyncMock()
        app.context_repository = None  # Not initialized
        app.core_facade = AsyncMock()
        
        # Should not raise even with partial initialization
        await app.cleanup()
        
        # Verify cleanup calls were made for initialized services
        app.core_facade.shutdown.assert_called_once()
        app.project_repository.cleanup.assert_called_once()
        
        # Verify app is marked as not initialized
        assert not app.is_initialized()
    
    @pytest.mark.asyncio
    async def test_cleanup_with_errors(self, mock_config):
        """Test cleanup handles service errors gracefully."""
        app = ImTheDevApp(mock_config)
        
        # Set up services that will fail during cleanup
        app.core_facade = AsyncMock()
        app.core_facade.shutdown.side_effect = Exception("Cleanup failed")
        app.project_repository = AsyncMock()
        
        # Should not raise despite errors
        await app.cleanup()
        
        # Verify all cleanups were attempted
        app.core_facade.shutdown.assert_called_once()
        app.project_repository.cleanup.assert_called_once()


class TestBootstrapApplication:
    """Test suite for bootstrap_application function."""
    
    @pytest.mark.asyncio
    async def test_successful_bootstrap(self):
        """Test successful application bootstrap."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write('''
debug = false

[ai]
claude_api_key = "test-key"

[database]
path = ":memory:"

[storage]
context_dir = "/tmp/test"
            ''')
            config_file = f.name
        
        try:
            with patch('imthedev.app.bootstrap.ImTheDevApp') as mock_app_class:
                mock_app = AsyncMock()
                mock_app_class.return_value = mock_app
                
                result = await bootstrap_application(config_file)
                
                # Verify app was created and initialized
                mock_app_class.assert_called_once()
                mock_app.initialize.assert_called_once()
                assert result is mock_app
        finally:
            Path(config_file).unlink()
    
    @pytest.mark.asyncio
    async def test_bootstrap_with_config_error(self):
        """Test bootstrap failure due to configuration error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write('''
[ai]
default_model = "invalid-model"
            ''')
            config_file = f.name
        
        try:
            with pytest.raises(SystemExit):
                await bootstrap_application(config_file)
        finally:
            Path(config_file).unlink()
    
    @pytest.mark.asyncio
    async def test_bootstrap_with_initialization_error(self):
        """Test bootstrap failure during app initialization."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write('''
[ai]
claude_api_key = "test-key"
            ''')
            config_file = f.name
        
        try:
            with patch('imthedev.app.bootstrap.ImTheDevApp') as mock_app_class:
                mock_app = AsyncMock()
                mock_app.initialize.side_effect = Exception("Init failed")
                mock_app_class.return_value = mock_app
                
                with pytest.raises(SystemExit):
                    await bootstrap_application(config_file)
        finally:
            Path(config_file).unlink()
    
    @pytest.mark.asyncio
    async def test_bootstrap_default_config(self):
        """Test bootstrap with default configuration file."""
        with patch('imthedev.app.bootstrap.Path') as mock_path:
            # Mock that config file exists
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path.return_value = mock_path_instance
            
            with patch('imthedev.app.bootstrap.ConfigManager') as mock_config_manager:
                mock_manager = MagicMock()
                mock_config = AppConfig()
                mock_config.ai.claude_api_key = "test-key"
                mock_manager.load_config.return_value = mock_config
                mock_config_manager.return_value = mock_manager
                
                with patch('imthedev.app.bootstrap.ImTheDevApp') as mock_app_class:
                    mock_app = AsyncMock()
                    mock_app_class.return_value = mock_app
                    
                    result = await bootstrap_application()
                    
                    # Verify ConfigManager was called with None (default config)
                    mock_config_manager.assert_called_once_with(None)
                    assert result is mock_app
    
    @pytest.mark.asyncio
    async def test_bootstrap_creates_config_if_missing(self):
        """Test bootstrap creates default config file when missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / ".imthedev" / "config.toml"
            
            # Make sure the config doesn't exist
            assert not config_path.exists()
            
            with patch('imthedev.app.bootstrap.ConfigManager') as mock_config_manager:
                mock_manager = MagicMock()
                mock_manager.create_default_config_file.return_value = str(config_path)
                mock_config_manager.return_value = mock_manager
                
                with patch('sys.exit') as mock_exit:
                    # Make sys.exit raise SystemExit to simulate real behavior
                    mock_exit.side_effect = SystemExit
                    
                    with pytest.raises(SystemExit):
                        await bootstrap_application(str(config_path))
                    
                    # Verify config file creation was attempted
                    mock_manager.create_default_config_file.assert_called_once_with(str(config_path))
                    
                    # Verify graceful exit after creating config (should be first call)
                    assert mock_exit.call_args_list[0] == ((0,), {})
    
    @pytest.mark.asyncio
    async def test_bootstrap_api_key_error_message(self):
        """Test bootstrap shows helpful error for missing API keys."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write('''
[ai]
# No API keys configured
            ''')
            config_file = f.name
        
        try:
            with patch('sys.exit') as mock_exit:
                with patch('builtins.print') as mock_print:
                    await bootstrap_application(config_file)
                    
                    # Verify helpful error message was printed
                    printed_messages = ' '.join(str(call[0][0]) for call in mock_print.call_args_list if call[0])
                    assert "ERROR: No AI API key configured!" in printed_messages
                    assert "CLAUDE_API_KEY" in printed_messages
                    assert "OPENAI_API_KEY" in printed_messages
                    assert "https://console.anthropic.com/" in printed_messages
                    
                    # Verify exit with error
                    mock_exit.assert_called_once_with(1)
        finally:
            Path(config_file).unlink()


class TestMain:
    """Test suite for main function."""
    
    @pytest.mark.asyncio
    async def test_successful_main(self):
        """Test successful main execution."""
        with patch('imthedev.app.bootstrap.bootstrap_application') as mock_bootstrap:
            mock_app = AsyncMock()
            mock_bootstrap.return_value = mock_app
            
            await main()
            
            # Verify bootstrap and run were called
            mock_bootstrap.assert_called_once_with(None)
            mock_app.run.assert_called_once()
            mock_app.cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_main_with_config_file(self):
        """Test main with config file argument."""
        with patch('imthedev.app.bootstrap.bootstrap_application') as mock_bootstrap:
            mock_app = AsyncMock()
            mock_bootstrap.return_value = mock_app
            
            await main("/path/to/config.toml")
            
            # Verify bootstrap was called with config file
            mock_bootstrap.assert_called_once_with("/path/to/config.toml")
    
    @pytest.mark.asyncio
    async def test_main_keyboard_interrupt(self):
        """Test main handles keyboard interrupt."""
        with patch('imthedev.app.bootstrap.bootstrap_application') as mock_bootstrap:
            mock_app = AsyncMock()
            mock_app.run.side_effect = KeyboardInterrupt()
            mock_bootstrap.return_value = mock_app
            
            # Should not raise
            await main()
            
            # Verify cleanup was still called
            mock_app.cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_main_bootstrap_failure(self):
        """Test main handles bootstrap failure."""
        with patch('imthedev.app.bootstrap.bootstrap_application') as mock_bootstrap:
            mock_bootstrap.side_effect = SystemExit(1)
            
            with pytest.raises(SystemExit):
                await main()
    
    @pytest.mark.asyncio
    async def test_main_run_failure(self):
        """Test main handles runtime failure."""
        with patch('imthedev.app.bootstrap.bootstrap_application') as mock_bootstrap, \
             patch('sys.exit') as mock_exit:
            
            mock_app = AsyncMock()
            mock_app.run.side_effect = Exception("Runtime error")
            mock_bootstrap.return_value = mock_app
            
            await main()
            
            # Verify cleanup was called and exit was called
            mock_app.cleanup.assert_called_once()
            mock_exit.assert_called_once_with(1)


class TestLoggingSetup:
    """Test suite for logging setup functionality."""
    
    def test_logging_setup_console_only(self):
        """Test logging setup with console only."""
        config = AppConfig()
        config.logging.console_enabled = True
        config.logging.file_path = None
        config.logging.level = "INFO"
        
        from imthedev.app.bootstrap import _setup_logging
        
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            _setup_logging(config)
            
            # Verify logger was configured
            mock_logger.setLevel.assert_called_once_with(logging.INFO)
            mock_logger.handlers.clear.assert_called_once()
            assert mock_logger.addHandler.call_count == 1  # Console handler only
    
    def test_logging_setup_file_and_console(self):
        """Test logging setup with file and console handlers."""
        config = AppConfig()
        config.logging.console_enabled = True
        config.logging.file_path = "/tmp/test.log"
        config.logging.level = "DEBUG"
        config.logging.max_file_size = 1024
        config.logging.backup_count = 3
        
        from imthedev.app.bootstrap import _setup_logging
        
        with patch('logging.getLogger') as mock_get_logger, \
             patch('pathlib.Path.mkdir') as mock_mkdir, \
             patch('logging.handlers.RotatingFileHandler') as mock_file_handler:
            
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            mock_handler = MagicMock()
            mock_file_handler.return_value = mock_handler
            
            _setup_logging(config)
            
            # Verify directory creation
            mock_mkdir.assert_called_once()
            
            # Verify file handler creation
            mock_file_handler.assert_called_once_with(
                "/tmp/test.log",
                maxBytes=1024,
                backupCount=3
            )
            
            # Verify both handlers were added
            assert mock_logger.addHandler.call_count == 2  # Console + file
    
    def test_logging_setup_creates_log_directory(self):
        """Test that logging setup creates log directory."""
        config = AppConfig()
        config.logging.file_path = "/tmp/logs/app.log"
        
        from imthedev.app.bootstrap import _setup_logging
        
        with patch('logging.getLogger') as mock_get_logger, \
             patch('imthedev.app.bootstrap.Path') as mock_path, \
             patch('logging.handlers.RotatingFileHandler') as mock_file_handler:
            
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            mock_log_path = MagicMock()
            mock_path.return_value = mock_log_path
            
            _setup_logging(config)
            
            # Verify path handling
            mock_path.assert_called_once_with("/tmp/logs/app.log")
            mock_log_path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)