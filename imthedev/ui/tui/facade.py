"""Core-UI integration facade for the TUI application.

This module provides the CoreFacade class which acts as the single point
of contact between the UI layer and the core business logic layer. It
orchestrates core services and handles event-driven communication.
"""

from collections.abc import Callable
from typing import Any
from uuid import UUID

from imthedev.core import (
    AIOrchestrator,
    Command,
    CommandEngine,
    ContextService,
    Event,
    EventBus,
    EventTypes,
    Project,
    ProjectService,
    ProjectSettings,
    StateManager,
)


class CoreFacade:
    """Facade that provides a simplified interface for UI interaction with core services.

    This class encapsulates all core services and provides a clean API for the UI
    layer. It handles event subscriptions, service orchestration, and state management.

    Attributes:
        event_bus: Central event bus for communication
        project_service: Service for project management
        context_service: Service for context management
        command_engine: Engine for command lifecycle management
        ai_orchestrator: Orchestrator for AI interactions
        state_manager: Manager for application state
    """

    def __init__(
        self,
        event_bus: EventBus,
        project_service: ProjectService,
        context_service: ContextService,
        command_engine: CommandEngine,
        ai_orchestrator: AIOrchestrator,
        state_manager: StateManager,
    ) -> None:
        """Initialize the facade with core services.

        Args:
            event_bus: Event bus for pub/sub communication
            project_service: Service for project operations
            context_service: Service for context operations
            command_engine: Engine for command management
            ai_orchestrator: Orchestrator for AI operations
            state_manager: Manager for application state
        """
        self.event_bus = event_bus
        self.project_service = project_service
        self.context_service = context_service
        self.command_engine = command_engine
        self.ai_orchestrator = ai_orchestrator
        self.state_manager = state_manager

        # UI event handler callbacks
        self._ui_event_handlers: dict[str, list[Callable[..., None]]] = {}

        # Subscribe to core events
        self._subscribe_to_core_events()

    def _subscribe_to_core_events(self) -> None:
        """Subscribe to relevant core events for UI updates."""
        # Project events
        self.event_bus.subscribe(
            EventTypes.PROJECT_CREATED, self._handle_project_created
        )
        self.event_bus.subscribe(
            EventTypes.PROJECT_SELECTED, self._handle_project_selected
        )
        self.event_bus.subscribe(
            EventTypes.PROJECT_DELETED, self._handle_project_deleted
        )

        # Command events
        self.event_bus.subscribe(
            EventTypes.COMMAND_PROPOSED, self._handle_command_proposed
        )
        self.event_bus.subscribe(
            EventTypes.COMMAND_APPROVED, self._handle_command_approved
        )
        self.event_bus.subscribe(
            EventTypes.COMMAND_REJECTED, self._handle_command_rejected
        )
        self.event_bus.subscribe(
            EventTypes.COMMAND_EXECUTING, self._handle_command_executing
        )
        self.event_bus.subscribe(
            EventTypes.COMMAND_COMPLETED, self._handle_command_completed
        )
        self.event_bus.subscribe(EventTypes.COMMAND_FAILED, self._handle_command_failed)

        # State events
        self.event_bus.subscribe(
            EventTypes.STATE_AUTOPILOT_ENABLED, self._handle_autopilot_enabled
        )
        self.event_bus.subscribe(
            EventTypes.STATE_AUTOPILOT_DISABLED, self._handle_autopilot_disabled
        )
        self.event_bus.subscribe(
            EventTypes.STATE_MODEL_CHANGED, self._handle_model_changed
        )

    # UI Event Registration

    def on_ui_event(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """Register a handler for UI events.

        Args:
            event_type: Type of event to handle
            handler: Callback function to handle the event
        """
        if event_type not in self._ui_event_handlers:
            self._ui_event_handlers[event_type] = []
        self._ui_event_handlers[event_type].append(handler)

    def _emit_ui_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Emit an event to registered UI handlers.

        Args:
            event_type: Type of event to emit
            payload: Event payload data
        """
        if event_type in self._ui_event_handlers:
            event = Event(type=event_type, payload=payload)
            for handler in self._ui_event_handlers[event_type]:
                handler(event)

    # Project Operations

    async def get_projects(self) -> list[Project]:
        """Get all available projects.

        Returns:
            List of projects
        """
        return await self.project_service.list_projects()

    async def create_project(
        self, name: str, path: str, settings: ProjectSettings | None = None
    ) -> Project:
        """Create a new project.

        Args:
            name: Project name
            path: Project path
            settings: Optional project settings

        Returns:
            Created project
        """
        project = await self.project_service.create_project(name, path, settings)
        return project

    async def select_project(self, project_id: UUID) -> None:
        """Select a project as current.

        Args:
            project_id: ID of project to select
        """
        await self.project_service.set_current_project(project_id)
        # Load project context
        await self.context_service.load_context(project_id)
        # Update state
        await self.state_manager.update_state({"current_project_id": project_id})

    async def get_current_project(self) -> Project | None:
        """Get the currently selected project.

        Returns:
            Current project or None
        """
        return await self.project_service.get_current_project()

    # Command Operations

    async def propose_command(self, objective: str) -> Command:
        """Request AI to propose a command for the given objective.

        Args:
            objective: What the user wants to accomplish

        Returns:
            Proposed command
        """
        # Get current project
        project = await self.get_current_project()
        if not project:
            raise ValueError("No project selected")

        # Get project context
        context = await self.context_service.load_context(project.id)

        # Generate command with AI
        command_text, reasoning = await self.ai_orchestrator.generate_command(
            context, objective
        )

        # Propose command through engine
        command = await self.command_engine.propose_command(
            project.id, command_text, reasoning
        )

        return command

    async def approve_command(self, command_id: UUID) -> None:
        """Approve a proposed command.

        Args:
            command_id: ID of command to approve
        """
        await self.command_engine.approve_command(command_id)

    async def reject_command(self, command_id: UUID) -> None:
        """Reject a proposed command.

        Args:
            command_id: ID of command to reject
        """
        await self.command_engine.reject_command(command_id)

    async def get_pending_commands(self) -> list[Command]:
        """Get all pending commands awaiting approval.

        Returns:
            List of pending commands
        """
        pending_dict = self.command_engine.get_pending_commands()
        return list(pending_dict.values())

    # State Operations

    async def toggle_autopilot(self) -> bool:
        """Toggle autopilot mode.

        Returns:
            New autopilot state
        """
        current_state = self.state_manager.get_state()
        new_state = not current_state.autopilot_enabled
        await self.state_manager.update_state({"autopilot_enabled": new_state})
        return new_state

    async def get_autopilot_status(self) -> bool:
        """Get current autopilot status.

        Returns:
            True if autopilot is enabled
        """
        state = self.state_manager.get_state()
        return state.autopilot_enabled

    async def set_ai_model(self, model: str) -> None:
        """Set the AI model to use.

        Args:
            model: Model identifier
        """
        await self.state_manager.update_state({"selected_ai_model": model})

    async def get_current_model(self) -> str:
        """Get the currently selected AI model.

        Returns:
            Current model identifier
        """
        state = self.state_manager.get_state()
        return state.selected_ai_model

    async def get_available_models(self) -> list[str]:
        """Get list of available AI models.

        Returns:
            List of model identifiers
        """
        return self.ai_orchestrator.get_available_models()

    # Core Event Handlers

    def _handle_project_created(self, event: Event) -> None:
        """Handle project created event."""
        self._emit_ui_event("ui.project.created", event.payload)

    def _handle_project_selected(self, event: Event) -> None:
        """Handle project selected event."""
        self._emit_ui_event("ui.project.selected", event.payload)

    def _handle_project_deleted(self, event: Event) -> None:
        """Handle project deleted event."""
        self._emit_ui_event("ui.project.deleted", event.payload)

    def _handle_command_proposed(self, event: Event) -> None:
        """Handle command proposed event."""
        self._emit_ui_event("ui.command.proposed", event.payload)

    def _handle_command_approved(self, event: Event) -> None:
        """Handle command approved event."""
        self._emit_ui_event("ui.command.approved", event.payload)

    def _handle_command_rejected(self, event: Event) -> None:
        """Handle command rejected event."""
        self._emit_ui_event("ui.command.rejected", event.payload)

    def _handle_command_executing(self, event: Event) -> None:
        """Handle command executing event."""
        self._emit_ui_event("ui.command.executing", event.payload)

    def _handle_command_completed(self, event: Event) -> None:
        """Handle command completed event."""
        self._emit_ui_event("ui.command.completed", event.payload)

    def _handle_command_failed(self, event: Event) -> None:
        """Handle command failed event."""
        self._emit_ui_event("ui.command.failed", event.payload)

    def _handle_autopilot_enabled(self, event: Event) -> None:
        """Handle autopilot enabled event."""
        self._emit_ui_event("ui.autopilot.enabled", event.payload)

    def _handle_autopilot_disabled(self, event: Event) -> None:
        """Handle autopilot disabled event."""
        self._emit_ui_event("ui.autopilot.disabled", event.payload)

    def _handle_model_changed(self, event: Event) -> None:
        """Handle model changed event."""
        self._emit_ui_event("ui.model.changed", event.payload)

    # Lifecycle Methods

    async def initialize(self) -> None:
        """Initialize the facade and core services."""
        # Restore state
        state = self.state_manager.get_state()

        # If there's a current project, load its context
        if state.current_project_id:
            try:
                await self.context_service.load_context(
                    state.current_project_id
                )
            except Exception:
                # If loading fails, clear the current project
                await self.state_manager.update_state({"current_project_id": None})

    async def shutdown(self) -> None:
        """Shutdown the facade and cleanup resources."""
        # Persist state
        self.state_manager.get_state()  # This triggers persistence

        # Clear handlers
        self._ui_event_handlers.clear()
