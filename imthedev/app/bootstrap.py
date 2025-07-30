"""Application bootstrap and dependency injection for imthedev.

This module provides the core application bootstrap functionality including:
- Dependency injection container and service initialization
- Configuration loading and validation
- Component lifecycle management
- Error handling and recovery
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from imthedev.core.events import EventBus
from imthedev.core.interfaces.services import AIOrchestrator, CommandEngine, StateManager
from imthedev.core.services import (
    AIOrchestratorImpl,
    CommandEngineImpl,
    StateManagerImpl,
)
from imthedev.infrastructure.config import AppConfig, ConfigManager
from imthedev.infrastructure.persistence import ContextRepository, ProjectRepository
from imthedev.ui.tui.facade import CoreFacade

logger = logging.getLogger(__name__)


class ImTheDevApp:
    """Main application class that manages the application lifecycle.
    
    This class serves as the root container for all application services
    and manages their initialization, configuration, and cleanup.
    
    Attributes:
        config: Application configuration
        event_bus: Central event bus for communication
        project_repository: Repository for project data
        context_repository: Repository for context data
        command_engine: Engine for command management
        ai_orchestrator: Orchestrator for AI interactions
        state_manager: Manager for application state
        core_facade: Facade for UI-core communication
    """
    
    def __init__(self, config: AppConfig) -> None:
        """Initialize the application with configuration.
        
        Args:
            config: Validated application configuration
        """
        self.config = config
        self._initialized = False
        
        # Core services (initialized in bootstrap)
        self.event_bus: Optional[EventBus] = None
        self.project_repository: Optional[ProjectRepository] = None
        self.context_repository: Optional[ContextRepository] = None
        self.command_engine: Optional[CommandEngine] = None
        self.ai_orchestrator: Optional[AIOrchestrator] = None
        self.state_manager: Optional[StateManager] = None
        self.core_facade: Optional[CoreFacade] = None
    
    async def initialize(self) -> None:
        """Initialize all application services and dependencies.
        
        This method sets up the dependency injection container and
        initializes all services in the correct order.
        
        Raises:
            RuntimeError: If initialization fails
        """
        if self._initialized:
            logger.warning("Application already initialized")
            return
        
        try:
            logger.info("Initializing imthedev application...")
            
            # Initialize event bus
            self.event_bus = EventBus("main")
            logger.debug("Event bus initialized")
            
            # Initialize repositories
            self.project_repository = ProjectRepository(
                db_path=self.config.database.path,
                timeout=self.config.database.timeout
            )
            await self.project_repository.initialize()
            logger.debug("Project repository initialized")
            
            self.context_repository = ContextRepository(
                context_dir=self.config.storage.context_dir,
                max_history=self.config.storage.max_context_history
            )
            await self.context_repository.initialize()
            logger.debug("Context repository initialized")
            
            # Initialize core services
            self.ai_orchestrator = AIOrchestratorImpl(
                event_bus=self.event_bus
            )
            logger.debug("AI orchestrator initialized")
            
            self.command_engine = CommandEngineImpl(
                event_bus=self.event_bus
            )
            logger.debug("Command engine initialized")
            
            self.state_manager = StateManagerImpl(
                event_bus=self.event_bus,
                state_file_path=Path(self.config.storage.context_dir) / "app_state.json"
            )
            logger.debug("State manager initialized")
            
            # Initialize facade
            self.core_facade = CoreFacade(
                event_bus=self.event_bus,
                project_service=self.project_repository,
                context_service=self.context_repository,
                command_engine=self.command_engine,
                ai_orchestrator=self.ai_orchestrator,
                state_manager=self.state_manager
            )
            await self.core_facade.initialize()
            logger.debug("Core facade initialized")
            
            self._initialized = True
            logger.info("Application initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize application: {e}", exc_info=True)
            await self.cleanup()
            raise RuntimeError(f"Application initialization failed: {e}") from e
    
    async def run(self) -> None:
        """Run the main application.
        
        This method starts the TUI application and manages its lifecycle.
        
        Raises:
            RuntimeError: If the application is not initialized
        """
        if not self._initialized:
            raise RuntimeError("Application must be initialized before running")
        
        try:
            logger.info("Starting imthedev TUI application...")
            
            # Import here to avoid circular imports
            from imthedev.ui.tui.app import ImTheDevApp
            
            # Create and run TUI application
            tui_app = ImTheDevApp(self.core_facade)
            await tui_app.run_async()
            
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
        except Exception as e:
            logger.error(f"Application error: {e}", exc_info=True)
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self) -> None:
        """Clean up application resources and shutdown services.
        
        This method ensures proper cleanup of all resources even if
        initialization was only partially completed.
        """
        logger.info("Cleaning up application resources...")
        
        # Cleanup in reverse order of initialization
        # Each cleanup is in its own try-catch to ensure all services are cleaned up
        if self.core_facade:
            try:
                await self.core_facade.shutdown()
                logger.debug("Core facade shutdown")
            except Exception as e:
                logger.error(f"Error shutting down core facade: {e}", exc_info=True)
        
        if self.state_manager:
            try:
                await self.state_manager.shutdown()
                logger.debug("State manager shutdown")
            except Exception as e:
                logger.error(f"Error shutting down state manager: {e}", exc_info=True)
        
        if self.command_engine:
            try:
                await self.command_engine.shutdown()
                logger.debug("Command engine shutdown")
            except Exception as e:
                logger.error(f"Error shutting down command engine: {e}", exc_info=True)
        
        if self.ai_orchestrator:
            try:
                await self.ai_orchestrator.shutdown()
                logger.debug("AI orchestrator shutdown")
            except Exception as e:
                logger.error(f"Error shutting down AI orchestrator: {e}", exc_info=True)
        
        if self.context_repository:
            try:
                await self.context_repository.cleanup()
                logger.debug("Context repository cleanup")
            except Exception as e:
                logger.error(f"Error cleaning up context repository: {e}", exc_info=True)
        
        if self.project_repository:
            try:
                await self.project_repository.cleanup()
                logger.debug("Project repository cleanup")
            except Exception as e:
                logger.error(f"Error cleaning up project repository: {e}", exc_info=True)
        
        if self.event_bus:
            try:
                # Event bus cleanup (clear handlers and history)
                self.event_bus.clear_history()
                logger.debug("Event bus cleanup")
            except Exception as e:
                logger.error(f"Error cleaning up event bus: {e}", exc_info=True)
        
        self._initialized = False
        logger.info("Application cleanup completed")
    
    def is_initialized(self) -> bool:
        """Check if the application is initialized.
        
        Returns:
            True if application is initialized
        """
        return self._initialized


async def bootstrap_application(config_file: Optional[str] = None) -> ImTheDevApp:
    """Bootstrap the imthedev application with all dependencies.
    
    This function handles the complete application initialization process:
    1. Load and validate configuration
    2. Set up logging
    3. Create application instance
    4. Initialize all services
    
    Args:
        config_file: Optional path to configuration file
        
    Returns:
        Fully initialized ImTheDevApp instance
        
    Raises:
        SystemExit: If bootstrap fails critically
    """
    try:
        # Load configuration
        config_manager = ConfigManager(config_file)
        config = config_manager.load_config()
        
        # Set up logging
        _setup_logging(config)
        
        logger.info("Starting imthedev application bootstrap...")
        logger.debug(f"Configuration loaded from: {config.config_file}")
        
        # Create application instance
        app = ImTheDevApp(config)
        
        # Initialize application
        await app.initialize()
        
        logger.info("Application bootstrap completed successfully")
        return app
        
    except Exception as e:
        # Log to stderr since logging might not be set up
        print(f"FATAL: Failed to bootstrap application: {e}", file=sys.stderr)
        if logger.handlers:  # Only if logging is set up
            logger.critical(f"Bootstrap failed: {e}", exc_info=True)
        sys.exit(1)


def _setup_logging(config: AppConfig) -> None:
    """Set up application logging based on configuration.
    
    Args:
        config: Application configuration containing logging settings
    """
    # Create log directory if file logging is enabled
    if config.logging.file_path:
        log_path = Path(config.logging.file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.logging.level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(config.logging.format)
    
    # Console handler
    if config.logging.console_enabled:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler
    if config.logging.file_path:
        from logging.handlers import RotatingFileHandler
        
        file_handler = RotatingFileHandler(
            config.logging.file_path,
            maxBytes=config.logging.max_file_size,
            backupCount=config.logging.backup_count
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    logger.info(f"Logging configured: level={config.logging.level}")


async def main(config_file: Optional[str] = None) -> None:
    """Main entry point for the imthedev application.
    
    Args:
        config_file: Optional path to configuration file
    """
    app = None
    try:
        # Bootstrap application
        app = await bootstrap_application(config_file)
        
        # Run application
        await app.run()
        
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
    except Exception as e:
        print(f"Application failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if app:
            await app.cleanup()


if __name__ == "__main__":
    # Allow running directly for development
    import sys
    config_file = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(main(config_file))