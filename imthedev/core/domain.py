"""Core domain models for the imthedev application.

This module defines the fundamental data structures used throughout the application,
following Domain-Driven Design principles with rich domain models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4


class CommandStatus(Enum):
    """Represents the lifecycle status of a command."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CommandResult:
    """Represents the result of an executed command."""

    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Command:
    """Represents a command proposed by the AI for execution.

    Attributes:
        id: Unique identifier for the command
        project_id: ID of the project this command belongs to
        command_text: The actual command to be executed
        ai_reasoning: AI's explanation for why this command is proposed
        status: Current status in the command lifecycle
        result: Execution result if command has been executed
        timestamp: When the command was created
    """

    id: UUID
    project_id: UUID
    command_text: str
    ai_reasoning: str
    status: CommandStatus
    result: CommandResult | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ProjectContext:
    """Maintains the execution context and history for a project.

    Attributes:
        history: List of all commands executed in this project
        current_state: Key-value store of current project state
        ai_memory: Persistent memory/context for AI conversations
        metadata: Additional project-specific metadata
    """

    history: list[Command] = field(default_factory=list)
    current_state: dict[str, Any] = field(default_factory=dict)
    ai_memory: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProjectSettings:
    """Configuration settings for a project.

    Attributes:
        auto_approve: Whether to automatically approve AI commands
        default_ai_model: Preferred AI model for this project
        command_timeout: Maximum execution time for commands in seconds
        environment_vars: Project-specific environment variables
    """

    auto_approve: bool = False
    default_ai_model: str = "gemini-2.5-pro"
    command_timeout: int = 300
    environment_vars: dict[str, str] = field(default_factory=dict)


@dataclass
class Project:
    """Represents an AI-driven project managed by imthedev.

    Attributes:
        id: Unique identifier for the project
        name: Human-readable project name
        path: Filesystem path to the project root
        created_at: When the project was created
        context: Project execution context and history
        settings: Project-specific configuration
    """

    id: UUID
    name: str
    path: Path
    created_at: datetime
    context: ProjectContext
    settings: ProjectSettings

    def __post_init__(self) -> None:
        """Ensure path is a Path object."""
        if isinstance(self.path, str):
            self.path = Path(self.path)

    @classmethod
    def create(
        cls, name: str, path: Path, settings: ProjectSettings | None = None
    ) -> "Project":
        """Factory method to create a new project with defaults.

        Args:
            name: Human-readable project name
            path: Filesystem path to project root
            settings: Optional project settings, uses defaults if not provided

        Returns:
            New Project instance with generated ID and timestamp
        """
        return cls(
            id=uuid4(),
            name=name,
            path=path,
            created_at=datetime.now(),
            context=ProjectContext(),
            settings=settings or ProjectSettings(),
        )
