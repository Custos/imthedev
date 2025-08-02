"""Event type definitions for the imthedev event system.

This module defines all event types used throughout the application,
organized by domain and lifecycle stage.
"""

from typing import Final


class EventTypes:
    """Central registry of all event types in the system.

    Event naming convention: <domain>.<entity>.<action>
    Examples: project.created, command.approved, state.autopilot.toggled
    """

    # Project Events
    PROJECT_CREATED: Final[str] = "project.created"
    PROJECT_UPDATED: Final[str] = "project.updated"
    PROJECT_DELETED: Final[str] = "project.deleted"
    PROJECT_SELECTED: Final[str] = "project.selected"
    PROJECT_DESELECTED: Final[str] = "project.deselected"

    # Context Events
    CONTEXT_SAVED: Final[str] = "context.saved"
    CONTEXT_LOADED: Final[str] = "context.loaded"
    CONTEXT_UPDATED: Final[str] = "context.updated"
    CONTEXT_CLEARED: Final[str] = "context.cleared"

    # Command Lifecycle Events
    COMMAND_PROPOSED: Final[str] = "command.proposed"
    COMMAND_APPROVED: Final[str] = "command.approved"
    COMMAND_REJECTED: Final[str] = "command.rejected"
    COMMAND_EXECUTING: Final[str] = "command.executing"
    COMMAND_COMPLETED: Final[str] = "command.completed"
    COMMAND_FAILED: Final[str] = "command.failed"
    COMMAND_CANCELLED: Final[str] = "command.cancelled"

    # AI Events
    AI_GENERATION_STARTED: Final[str] = "ai.generation.started"
    AI_GENERATION_COMPLETED: Final[str] = "ai.generation.completed"
    AI_GENERATION_FAILED: Final[str] = "ai.generation.failed"
    AI_ANALYSIS_STARTED: Final[str] = "ai.analysis.started"
    AI_ANALYSIS_COMPLETED: Final[str] = "ai.analysis.completed"
    AI_MODEL_CHANGED: Final[str] = "ai.model.changed"

    # State Management Events
    STATE_UPDATED: Final[str] = "state.updated"
    STATE_AUTOPILOT_ENABLED: Final[str] = "state.autopilot.enabled"
    STATE_AUTOPILOT_DISABLED: Final[str] = "state.autopilot.disabled"
    STATE_MODEL_CHANGED: Final[str] = "state.model.changed"
    STATE_PERSISTED: Final[str] = "state.persisted"
    STATE_RESTORED: Final[str] = "state.restored"

    # UI Events (for UI layer to emit)
    UI_READY: Final[str] = "ui.ready"
    UI_PROJECT_LIST_REQUESTED: Final[str] = "ui.project.list.requested"
    UI_PROJECT_CREATE_REQUESTED: Final[str] = "ui.project.create.requested"
    UI_PROJECT_SELECT_REQUESTED: Final[str] = "ui.project.select.requested"
    UI_COMMAND_APPROVE_REQUESTED: Final[str] = "ui.command.approve.requested"
    UI_COMMAND_REJECT_REQUESTED: Final[str] = "ui.command.reject.requested"
    UI_AUTOPILOT_TOGGLE_REQUESTED: Final[str] = "ui.autopilot.toggle.requested"
    UI_MODEL_CHANGE_REQUESTED: Final[str] = "ui.model.change.requested"

    # System Events
    SYSTEM_STARTUP: Final[str] = "system.startup"
    SYSTEM_READY: Final[str] = "system.ready"
    SYSTEM_SHUTDOWN_REQUESTED: Final[str] = "system.shutdown.requested"
    SYSTEM_SHUTDOWN: Final[str] = "system.shutdown"
    SYSTEM_ERROR: Final[str] = "system.error"
    SYSTEM_WARNING: Final[str] = "system.warning"

    # Storage Events
    STORAGE_SAVE_STARTED: Final[str] = "storage.save.started"
    STORAGE_SAVE_COMPLETED: Final[str] = "storage.save.completed"
    STORAGE_SAVE_FAILED: Final[str] = "storage.save.failed"
    STORAGE_LOAD_STARTED: Final[str] = "storage.load.started"
    STORAGE_LOAD_COMPLETED: Final[str] = "storage.load.completed"
    STORAGE_LOAD_FAILED: Final[str] = "storage.load.failed"

    @classmethod
    def all_events(cls) -> list[str]:
        """Get a list of all defined event types.

        Returns:
            List of all event type strings
        """
        return [
            value
            for name, value in cls.__dict__.items()
            if isinstance(value, str) and not name.startswith("_")
        ]

    @classmethod
    def is_valid_event(cls, event_type: str) -> bool:
        """Check if an event type is valid.

        Args:
            event_type: Event type string to validate

        Returns:
            True if the event type is defined
        """
        return event_type in cls.all_events()

    @classmethod
    def get_domain(cls, event_type: str) -> str:
        """Extract domain from event type.

        Args:
            event_type: Event type string (e.g., "project.created")

        Returns:
            Domain part of the event (e.g., "project")
        """
        return event_type.split(".")[0] if "." in event_type else event_type

    @classmethod
    def get_events_by_domain(cls, domain: str) -> list[str]:
        """Get all events for a specific domain.

        Args:
            domain: Domain to filter by (e.g., "project", "command")

        Returns:
            List of event types for the domain
        """
        return [event for event in cls.all_events() if event.startswith(f"{domain}.")]


class EventPriority:
    """Event priority levels for processing order."""

    CRITICAL: Final[int] = 0  # Highest priority
    HIGH: Final[int] = 1
    NORMAL: Final[int] = 2
    LOW: Final[int] = 3  # Lowest priority

    @classmethod
    def get_priority(cls, event_type: str) -> int:
        """Get priority for an event type.

        Args:
            event_type: Event type to get priority for

        Returns:
            Priority level (lower number = higher priority)
        """
        # Critical events that need immediate processing
        if event_type in [
            EventTypes.SYSTEM_ERROR,
            EventTypes.SYSTEM_SHUTDOWN_REQUESTED,
            EventTypes.COMMAND_FAILED,
        ]:
            return cls.CRITICAL

        # High priority user actions
        elif event_type in [
            EventTypes.UI_COMMAND_APPROVE_REQUESTED,
            EventTypes.UI_COMMAND_REJECT_REQUESTED,
            EventTypes.COMMAND_EXECUTING,
        ]:
            return cls.HIGH

        # Low priority background events
        elif event_type in [
            EventTypes.STORAGE_SAVE_STARTED,
            EventTypes.STATE_PERSISTED,
            EventTypes.CONTEXT_SAVED,
        ]:
            return cls.LOW

        # Default to normal priority
        else:
            return cls.NORMAL
