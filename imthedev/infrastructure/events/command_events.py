"""Command lifecycle events for SuperClaude command orchestration.

Events related to proposing, approving, and executing SC commands.
"""

from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from .orchestration_bus import OrchestrationEvent


@dataclass(frozen=True)
class CommandEvent(OrchestrationEvent):
    """Base class for command-related events."""
    
    command_id: UUID = field(default=UUID("00000000-0000-0000-0000-000000000000"))
    command_text: str = ""


@dataclass(frozen=True)
class CommandProposed(CommandEvent):
    """Event emitted when Gemini proposes an SC command."""
    
    reasoning: str = ""
    confidence: float = 0.0
    alternatives: list[str] = field(default_factory=list)
    context_used: str = ""


@dataclass(frozen=True)
class CommandApproved(CommandEvent):
    """Event emitted when user approves a command."""
    
    approved_by: str = "user"
    modifications: Optional[str] = None


@dataclass(frozen=True)
class CommandRejected(CommandEvent):
    """Event emitted when user rejects a command."""
    
    rejected_by: str = "user"
    reason: Optional[str] = None


@dataclass(frozen=True)
class CommandModified(CommandEvent):
    """Event emitted when user modifies a proposed command."""
    
    original_command: str = ""
    modified_command: str = ""
    modified_by: str = "user"


@dataclass(frozen=True)
class CommandValidated(CommandEvent):
    """Event emitted after command validation."""
    
    is_valid: bool = False
    validation_errors: list[str] = field(default_factory=list)
    suggested_fixes: list[str] = field(default_factory=list)