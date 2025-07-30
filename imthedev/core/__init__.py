"""Core domain logic for imthedev application.

This package contains the business logic and domain models that are
completely independent of any UI or infrastructure concerns.
"""

from imthedev.core.domain import (
    Command,
    CommandResult,
    CommandStatus,
    Project,
    ProjectContext,
    ProjectSettings,
)
from imthedev.core.events import (
    Event,
    EventBus,
    EventHandler,
    EventPriority,
    EventTypes,
    ScopedEventBus,
)
from imthedev.core.interfaces import (
    AIModel,
    AIOrchestrator,
    ApplicationState,
    CommandAnalysis,
    CommandEngine,
    ContextService,
    ProjectService,
    StateManager,
)
from imthedev.core.services import CommandEngineImpl, StateManagerImpl

__all__ = [
    # Domain models
    "Command",
    "CommandResult",
    "CommandStatus",
    "Project",
    "ProjectContext",
    "ProjectSettings",
    # Event system
    "Event",
    "EventBus",
    "EventHandler",
    "EventPriority",
    "EventTypes",
    "ScopedEventBus",
    # Service interfaces
    "AIModel",
    "AIOrchestrator",
    "ApplicationState",
    "CommandAnalysis",
    "CommandEngine",
    "ContextService",
    "ProjectService",
    "StateManager",
    # Service implementations
    "CommandEngineImpl",
    "StateManagerImpl",
]