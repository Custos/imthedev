"""Core service interfaces for the imthedev application.

This module defines the protocol interfaces that establish contracts between
different layers of the application. These protocols ensure loose coupling
and enable easy testing through mock implementations.
"""

from collections.abc import Callable
from typing import Any, Protocol
from uuid import UUID

from imthedev.core.domain import (
    Command,
    CommandStatus,
    Project,
    ProjectContext,
    ProjectSettings,
)


class AIModel:
    """Enumeration of supported AI models."""

    GEMINI_FLASH = "gemini-2.5-flash"
    GEMINI_PRO = "gemini-2.5-pro"
    GEMINI_FLASH_8B = "gemini-2.5-flash-8b"


class CommandAnalysis:
    """Analysis result from AI after command execution."""

    def __init__(
        self,
        success: bool,
        next_action: str | None = None,
        error_diagnosis: str | None = None,
        state_updates: dict[str, Any] | None = None,
    ):
        self.success = success
        self.next_action = next_action
        self.error_diagnosis = error_diagnosis
        self.state_updates = state_updates or {}


class ProjectService(Protocol):
    """Service for managing projects and their lifecycle."""

    async def create_project(
        self, name: str, path: str, settings: ProjectSettings | None = None
    ) -> Project:
        """Create a new project with the specified configuration.

        Args:
            name: Human-readable project name
            path: Filesystem path to project root
            settings: Optional project-specific settings

        Returns:
            Newly created Project instance

        Raises:
            ProjectExistsError: If a project already exists at the path
            InvalidPathError: If the path is not valid or accessible
        """
        ...

    async def get_project(self, project_id: UUID) -> Project | None:
        """Retrieve a project by its ID.

        Args:
            project_id: Unique identifier of the project

        Returns:
            Project instance if found, None otherwise
        """
        ...

    async def list_projects(self) -> list[Project]:
        """List all available projects.

        Returns:
            List of all projects ordered by creation date
        """
        ...

    async def update_project(self, project: Project) -> None:
        """Update an existing project's metadata and settings.

        Args:
            project: Project instance with updated values

        Raises:
            ProjectNotFoundError: If the project doesn't exist
        """
        ...

    async def delete_project(self, project_id: UUID) -> None:
        """Delete a project and all associated data.

        Args:
            project_id: ID of the project to delete

        Raises:
            ProjectNotFoundError: If the project doesn't exist
        """
        ...

    async def get_current_project(self) -> Project | None:
        """Get the currently selected project.

        Returns:
            Currently selected project or None if no project is selected
        """
        ...

    async def set_current_project(self, project_id: UUID) -> None:
        """Set the current active project.

        Args:
            project_id: ID of the project to make current

        Raises:
            ProjectNotFoundError: If the project doesn't exist
        """
        ...


class ContextService(Protocol):
    """Service for managing project context and command history."""

    async def save_context(self, project_id: UUID, context: ProjectContext) -> None:
        """Save or update the context for a project.

        Args:
            project_id: ID of the project
            context: Context to save

        Raises:
            ProjectNotFoundError: If the project doesn't exist
            StorageError: If context cannot be persisted
        """
        ...

    async def load_context(self, project_id: UUID) -> ProjectContext:
        """Load the context for a project.

        Args:
            project_id: ID of the project

        Returns:
            Project context with full history and state

        Raises:
            ProjectNotFoundError: If the project doesn't exist
            ContextNotFoundError: If no context exists for the project
        """
        ...

    async def append_command(self, project_id: UUID, command: Command) -> None:
        """Append a command to the project's history.

        Args:
            project_id: ID of the project
            command: Command to append to history

        Raises:
            ProjectNotFoundError: If the project doesn't exist
        """
        ...

    async def get_command_history(
        self,
        project_id: UUID,
        limit: int = 50,
        status_filter: CommandStatus | None = None,
    ) -> list[Command]:
        """Retrieve command history for a project.

        Args:
            project_id: ID of the project
            limit: Maximum number of commands to return
            status_filter: Optional filter by command status

        Returns:
            List of commands ordered by timestamp (newest first)

        Raises:
            ProjectNotFoundError: If the project doesn't exist
        """
        ...

    async def update_command_status(
        self, project_id: UUID, command_id: UUID, status: CommandStatus
    ) -> None:
        """Update the status of a command in history.

        Args:
            project_id: ID of the project
            command_id: ID of the command to update
            status: New status for the command

        Raises:
            ProjectNotFoundError: If the project doesn't exist
            CommandNotFoundError: If the command doesn't exist
        """
        ...


class AIOrchestrator(Protocol):
    """Service for orchestrating AI interactions and command generation."""

    async def generate_command(
        self, context: ProjectContext, objective: str, model: str = AIModel.GEMINI_FLASH
    ) -> tuple[str, str]:
        """Generate a command based on context and objective.

        Args:
            context: Current project context including history
            objective: What the user wants to achieve
            model: AI model to use for generation

        Returns:
            Tuple of (command_text, ai_reasoning)

        Raises:
            AIProviderError: If AI service is unavailable
            InvalidModelError: If the specified model is not supported
        """
        ...

    async def analyze_result(
        self, command: Command, output: str, context: ProjectContext
    ) -> CommandAnalysis:
        """Analyze command execution results and suggest next steps.

        Args:
            command: The executed command
            output: Output from command execution
            context: Current project context

        Returns:
            Analysis with success assessment and recommendations

        Raises:
            AIProviderError: If AI service is unavailable
        """
        ...

    def get_available_models(self) -> list[str]:
        """Get list of available AI models.

        Returns:
            List of model identifiers that can be used
        """
        ...

    async def estimate_tokens(self, context: ProjectContext, objective: str) -> int:
        """Estimate token usage for a command generation.

        Args:
            context: Current project context
            objective: The objective to achieve

        Returns:
            Estimated number of tokens
        """
        ...


class CommandEngine(Protocol):
    """Service for managing command lifecycle and execution."""

    async def propose_command(
        self, project_id: UUID, command_text: str, ai_reasoning: str
    ) -> Command:
        """Propose a new command for approval.

        Args:
            project_id: ID of the project
            command_text: The command to execute
            ai_reasoning: AI's explanation for the command

        Returns:
            Proposed command with PROPOSED status

        Raises:
            ProjectNotFoundError: If the project doesn't exist
        """
        ...

    async def approve_command(self, command_id: UUID) -> None:
        """Approve a proposed command for execution.

        Args:
            command_id: ID of the command to approve

        Raises:
            CommandNotFoundError: If the command doesn't exist
            InvalidStateError: If command is not in PROPOSED state
        """
        ...

    async def reject_command(self, command_id: UUID) -> None:
        """Reject a proposed command.

        Args:
            command_id: ID of the command to reject

        Raises:
            CommandNotFoundError: If the command doesn't exist
            InvalidStateError: If command is not in PROPOSED state
        """
        ...

    async def execute_command(self, command_id: UUID) -> None:
        """Execute an approved command.

        Args:
            command_id: ID of the command to execute

        Raises:
            CommandNotFoundError: If the command doesn't exist
            InvalidStateError: If command is not APPROVED
            ExecutionError: If command execution fails
        """
        ...

    def get_pending_commands(self) -> dict[UUID, Command]:
        """Get all commands awaiting approval.

        Returns:
            Dictionary mapping command IDs to Command instances
        """
        ...

    async def cancel_execution(self, command_id: UUID) -> None:
        """Cancel a currently executing command.

        Args:
            command_id: ID of the command to cancel

        Raises:
            CommandNotFoundError: If the command doesn't exist
            InvalidStateError: If command is not EXECUTING
        """
        ...


class ApplicationState:
    """Represents the global application state."""

    def __init__(
        self,
        current_project_id: UUID | None = None,
        autopilot_enabled: bool = False,
        selected_ai_model: str = AIModel.GEMINI_FLASH,
        ui_preferences: dict[str, Any] | None = None,
    ):
        self.current_project_id = current_project_id
        self.autopilot_enabled = autopilot_enabled
        self.selected_ai_model = selected_ai_model
        self.ui_preferences = ui_preferences or {}


class StateManager(Protocol):
    """Service for managing application state and settings."""

    def get_state(self) -> ApplicationState:
        """Get the current application state.

        Returns:
            Current application state
        """
        ...

    async def update_state(self, updates: dict[str, Any]) -> None:
        """Update application state with partial updates.

        Args:
            updates: Dictionary of state fields to update

        Raises:
            InvalidStateError: If updates contain invalid fields
        """
        ...

    async def toggle_autopilot(self) -> bool:
        """Toggle autopilot mode on/off.

        Returns:
            New autopilot state (True if enabled)
        """
        ...

    async def set_ai_model(self, model: str) -> None:
        """Set the active AI model.

        Args:
            model: Model identifier to use

        Raises:
            InvalidModelError: If model is not supported
        """
        ...

    def subscribe(self, callback: Callable[[ApplicationState], None]) -> None:
        """Subscribe to state changes.

        Args:
            callback: Function to call when state changes
                     Signature: callback(state: ApplicationState) -> None
        """
        ...

    def unsubscribe(self, callback: Callable[[ApplicationState], None]) -> None:
        """Unsubscribe from state changes.

        Args:
            callback: Previously subscribed callback to remove
        """
        ...
