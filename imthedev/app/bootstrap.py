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

from imthedev.core.events import EventBus
from imthedev.core.interfaces.services import (
    AIOrchestrator,
    CommandEngine,
    StateManager,
)
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
        self.event_bus: EventBus | None = None
        self.project_repository: ProjectRepository | None = None
        self.context_repository: ContextRepository | None = None
        self.command_engine: CommandEngine | None = None
        self.ai_orchestrator: AIOrchestrator | None = None
        self.state_manager: StateManager | None = None
        self.core_facade: CoreFacade | None = None

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
                db_path=Path(self.config.database.path)
            )
            await self.project_repository.initialize()
            logger.debug("Project repository initialized")

            self.context_repository = ContextRepository(
                storage_dir=Path(self.config.storage.context_dir)
            )
            logger.debug("Context repository initialized")

            # Initialize core services
            self.ai_orchestrator = AIOrchestratorImpl(event_bus=self.event_bus)
            logger.debug("AI orchestrator initialized")

            self.command_engine = CommandEngineImpl(event_bus=self.event_bus)
            logger.debug("Command engine initialized")

            self.state_manager = StateManagerImpl(
                event_bus=self.event_bus,
                state_file_path=Path(self.config.storage.context_dir)
                / "app_state.json",
            )
            logger.debug("State manager initialized")

            # Initialize facade
            self.core_facade = CoreFacade(
                event_bus=self.event_bus,
                project_service=self.project_repository,
                context_service=self.context_repository,
                command_engine=self.command_engine,
                ai_orchestrator=self.ai_orchestrator,
                state_manager=self.state_manager,
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
            tui_app = ImTheDevApp()
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

        # Note: Core services (StateManager, CommandEngine, AIOrchestrator) don't have shutdown methods
        # They manage their resources internally without requiring explicit cleanup

        # Note: Repositories don't have cleanup methods - they use simple file/DB operations
        # that don't require explicit cleanup

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


async def bootstrap_application(config_file: str | None = None) -> ImTheDevApp:
    """Bootstrap the imthedev application with all dependencies.

    This function handles the complete application initialization process:
    1. Create default config file if needed
    2. Load and validate configuration
    3. Set up logging
    4. Create application instance
    5. Initialize all services

    Args:
        config_file: Optional path to configuration file

    Returns:
        Fully initialized ImTheDevApp instance

    Raises:
        SystemExit: If bootstrap fails critically
    """
    # Determine config file path outside try block so it's available in exception handler
    config_file_path = config_file or str(Path.home() / ".imthedev" / "config.toml")
    config_file_path = str(Path(config_file_path).expanduser())

    try:
        # Create config manager
        config_manager = ConfigManager(config_file)

        # Check if config file exists, create default if not
        if not Path(config_file_path).exists():
            print(f"Configuration file not found at {config_file_path}")
            print("Creating default configuration file...")
            created_path = config_manager.create_default_config_file(config_file_path)
            print(f"\nCreated configuration file at: {created_path}")
            print("\n" + "=" * 60)
            print("IMPORTANT: You must configure at least one AI API key!")
            print("=" * 60)
            print("\nPlease edit the configuration file and add either:")
            print("  - CLAUDE_API_KEY environment variable")
            print("  - OPENAI_API_KEY environment variable")
            print("  - Or uncomment and set the API key in the config file")
            print("\nExample:")
            print("  export CLAUDE_API_KEY='your-api-key-here'")
            print(f"  OR edit {created_path} and set ai.claude_api_key")
            print("\nThen run the application again.")
            print("=" * 60 + "\n")
            sys.exit(0)  # Exit gracefully after creating config

        # Load configuration
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
        # Check if this is a missing API key error
        error_msg = str(e)
        if "At least one AI API key must be configured" in error_msg:
            print("\n" + "=" * 60, file=sys.stderr)
            print("ERROR: No AI API key configured!", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            print(
                "\nThe application requires at least one AI API key to function.",
                file=sys.stderr,
            )
            print(
                "\nPlease configure an API key using one of these methods:",
                file=sys.stderr,
            )
            print("\n1. Environment Variable (Recommended):", file=sys.stderr)
            print("   export CLAUDE_API_KEY='your-api-key-here'", file=sys.stderr)
            print("   export OPENAI_API_KEY='your-api-key-here'", file=sys.stderr)
            print("\n2. Configuration File:", file=sys.stderr)
            print(
                f"   Edit {config_file_path} and uncomment/set the API key",
                file=sys.stderr,
            )
            print("\nTo get API keys:", file=sys.stderr)
            print("   - Claude: https://console.anthropic.com/", file=sys.stderr)
            print("   - OpenAI: https://platform.openai.com/api-keys", file=sys.stderr)
            print("=" * 60 + "\n", file=sys.stderr)
        else:
            # Log other errors normally
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
            backupCount=config.logging.backup_count,
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    logger.info(f"Logging configured: level={config.logging.level}")


async def main(config_file: str | None = None) -> None:
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
