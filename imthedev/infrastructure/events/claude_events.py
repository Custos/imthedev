"""Claude Code executor-specific events.

Events related to Claude Code command execution and output streaming.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from uuid import UUID

from .orchestration_bus import OrchestrationEvent


@dataclass(frozen=True)
class ClaudeEvent(OrchestrationEvent):
    """Base class for Claude Code executor events."""
    
    execution_id: UUID = field(default=UUID("00000000-0000-0000-0000-000000000000"))
    command: str = ""


@dataclass(frozen=True)
class ExecutionStarted(ClaudeEvent):
    """Event emitted when Claude Code starts executing."""
    
    working_directory: str = ""
    environment: dict[str, str] = field(default_factory=dict)
    timeout: float = 300.0


@dataclass(frozen=True)
class OutputStreaming(ClaudeEvent):
    """Event emitted for real-time output streaming."""
    
    output_type: str = "stdout"  # stdout, stderr
    content: str = ""
    timestamp_offset: float = 0.0  # Seconds since execution start


@dataclass(frozen=True)
class ExecutionProgress(ClaudeEvent):
    """Event emitted for execution progress updates."""
    
    progress_message: str = ""
    percentage: float = 0.0
    current_operation: str = ""


@dataclass(frozen=True)
class FileCreated(ClaudeEvent):
    """Event emitted when Claude Code creates a file."""
    
    file_path: Path = field(default=Path())
    file_size: int = 0
    file_type: str = ""


@dataclass(frozen=True)
class FileModified(ClaudeEvent):
    """Event emitted when Claude Code modifies a file."""
    
    file_path: Path = field(default=Path())
    lines_added: int = 0
    lines_removed: int = 0
    lines_modified: int = 0


@dataclass(frozen=True)
class TestExecuted(ClaudeEvent):
    """Event emitted when Claude Code runs tests."""
    
    test_suite: str = ""
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0
    coverage_percentage: float = 0.0


@dataclass(frozen=True)
class ExecutionComplete(ClaudeEvent):
    """Event emitted when Claude Code execution completes."""
    
    exit_code: int = 0
    total_output: str = ""
    error_output: str = ""
    execution_time: float = 0.0
    files_created: list[Path] = field(default_factory=list)
    files_modified: list[Path] = field(default_factory=list)
    
    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return self.exit_code == 0


@dataclass(frozen=True)
class ExecutionFailed(ClaudeEvent):
    """Event emitted when Claude Code execution fails."""
    
    error_message: str = ""
    error_type: str = ""  # timeout, syntax, runtime, etc.
    stack_trace: Optional[str] = None
    recovery_suggestions: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MetadataExtracted(ClaudeEvent):
    """Event emitted when SCF metadata is extracted from output."""
    
    scf_version: str = ""
    personas_used: list[str] = field(default_factory=list)
    flags_used: list[str] = field(default_factory=list)
    mcp_servers_used: list[str] = field(default_factory=list)
    performance_metrics: dict[str, float] = field(default_factory=dict)