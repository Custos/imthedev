"""Core service interfaces for dependency inversion and testing.

This package defines protocol interfaces that establish contracts between
different components of the application, ensuring loose coupling and
enabling easy testing through mock implementations.
"""

from imthedev.core.interfaces.services import (
    AIModel,
    AIOrchestrator,
    ApplicationState,
    CommandAnalysis,
    CommandEngine,
    ContextService,
    ProjectService,
    StateManager,
)

__all__ = [
    "AIModel",
    "AIOrchestrator",
    "ApplicationState",
    "CommandAnalysis",
    "CommandEngine",
    "ContextService",
    "ProjectService",
    "StateManager",
]
