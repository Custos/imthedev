"""Data models for the orchestration system.

Core domain models representing objectives, steps, results, and analysis
in the dual-AI orchestration workflow.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4


class ObjectiveStatus(Enum):
    """Status of an orchestration objective."""
    
    PENDING = "pending"
    ANALYZING = "analyzing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    """Status of an orchestration step."""
    
    PENDING = "pending"
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class OrchestrationObjective:
    """High-level goal from user for orchestration.
    
    Represents what the user wants to achieve through the
    dual-AI orchestration system.
    """
    
    id: UUID = field(default_factory=uuid4)
    description: str = ""
    success_criteria: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    status: ObjectiveStatus = ObjectiveStatus.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def add_success_criterion(self, criterion: str) -> None:
        """Add a success criterion to the objective."""
        self.success_criteria.append(criterion)
        self.updated_at = datetime.now()
    
    def update_status(self, status: ObjectiveStatus) -> None:
        """Update the objective status."""
        self.status = status
        self.updated_at = datetime.now()
    
    def is_complete(self) -> bool:
        """Check if objective is complete."""
        return self.status in (ObjectiveStatus.COMPLETED, ObjectiveStatus.FAILED, ObjectiveStatus.CANCELLED)


@dataclass
class CommandProposal:
    """Proposed SuperClaude command from Gemini."""
    
    command: str = ""
    reasoning: str = ""
    confidence: float = 0.0
    alternatives: list[str] = field(default_factory=list)
    expected_outcome: str = ""
    estimated_duration: float = 0.0
    required_capabilities: list[str] = field(default_factory=list)
    
    def is_high_confidence(self) -> bool:
        """Check if this is a high-confidence proposal."""
        return self.confidence >= 0.8


@dataclass
class OrchestrationStep:
    """Single step in the orchestration process.
    
    Represents one SC command execution cycle in the orchestration.
    """
    
    id: UUID = field(default_factory=uuid4)
    objective_id: UUID = field(default=UUID("00000000-0000-0000-0000-000000000000"))
    step_number: int = 0
    command: str = ""
    reasoning: str = ""
    status: StepStatus = StepStatus.PENDING
    proposal: Optional[CommandProposal] = None
    result: Optional["ExecutionResult"] = None
    analysis: Optional["GeminiAnalysis"] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def approve(self) -> None:
        """Approve this step for execution."""
        self.status = StepStatus.APPROVED
    
    def reject(self) -> None:
        """Reject this step."""
        self.status = StepStatus.REJECTED
    
    def start_execution(self) -> None:
        """Mark step as executing."""
        self.status = StepStatus.EXECUTING
        self.started_at = datetime.now()
    
    def complete_execution(self, result: "ExecutionResult") -> None:
        """Mark step as completed with result."""
        self.status = StepStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now()
    
    def fail_execution(self, error: str) -> None:
        """Mark step as failed."""
        self.status = StepStatus.FAILED
        self.completed_at = datetime.now()
    
    @property
    def duration(self) -> Optional[float]:
        """Get execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class TestResults:
    """Test execution results from Claude Code."""
    
    test_suite: str = ""
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0
    coverage_percentage: float = 0.0
    failed_tests: list[str] = field(default_factory=list)
    
    @property
    def total_tests(self) -> int:
        """Get total number of tests."""
        return self.tests_passed + self.tests_failed + self.tests_skipped
    
    @property
    def success_rate(self) -> float:
        """Get test success rate."""
        if self.total_tests == 0:
            return 0.0
        return self.tests_passed / self.total_tests


@dataclass
class ExecutionResult:
    """Result from Claude Code command execution."""
    
    execution_id: UUID = field(default_factory=uuid4)
    command: str = ""
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    execution_time: float = 0.0
    files_created: list[Path] = field(default_factory=list)
    files_modified: list[Path] = field(default_factory=list)
    tests_run: Optional[TestResults] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return self.exit_code == 0
    
    @property
    def has_output(self) -> bool:
        """Check if execution produced output."""
        return bool(self.stdout or self.stderr)
    
    @property
    def file_changes_count(self) -> int:
        """Get total number of file changes."""
        return len(self.files_created) + len(self.files_modified)


@dataclass
class GeminiAnalysis:
    """Gemini's analysis of execution results."""
    
    execution_id: UUID = field(default=UUID("00000000-0000-0000-0000-000000000000"))
    success: bool = False
    understanding: str = ""
    key_findings: list[str] = field(default_factory=list)
    missing_elements: list[str] = field(default_factory=list)
    next_action: str = ""
    confidence: float = 0.0
    requires_correction: bool = False
    can_continue: bool = True
    learned_insights: list[str] = field(default_factory=list)
    
    def add_finding(self, finding: str) -> None:
        """Add a key finding from the analysis."""
        self.key_findings.append(finding)
    
    def add_missing_element(self, element: str) -> None:
        """Add a missing element identified."""
        self.missing_elements.append(element)
    
    def is_actionable(self) -> bool:
        """Check if analysis suggests actionable next steps."""
        return bool(self.next_action) and self.can_continue


@dataclass
class OrchestrationPlan:
    """Execution plan generated by Gemini for an objective."""
    
    objective_id: UUID = field(default=UUID("00000000-0000-0000-0000-000000000000"))
    steps: list[dict[str, Any]] = field(default_factory=list)
    estimated_total_time: float = 0.0
    complexity_score: float = 0.0
    dependencies: list[str] = field(default_factory=list)
    risk_assessment: str = ""
    parallel_opportunities: list[list[int]] = field(default_factory=list)
    
    def add_step(self, command: str, description: str, estimated_time: float = 0.0) -> None:
        """Add a step to the plan."""
        self.steps.append({
            "command": command,
            "description": description,
            "estimated_time": estimated_time,
            "step_number": len(self.steps) + 1
        })
        self.estimated_total_time += estimated_time
    
    @property
    def total_steps(self) -> int:
        """Get total number of steps in plan."""
        return len(self.steps)
    
    def get_step(self, step_number: int) -> Optional[dict[str, Any]]:
        """Get a specific step by number."""
        if 0 < step_number <= len(self.steps):
            return self.steps[step_number - 1]
        return None


@dataclass
class ExecutionMetadata:
    """Metadata extracted from SCF-enhanced Claude Code output."""
    
    scf_version: str = ""
    command_type: str = ""
    personas_used: list[str] = field(default_factory=list)
    flags_used: list[str] = field(default_factory=list)
    mcp_servers_used: list[str] = field(default_factory=list)
    thinking_depth: str = ""  # standard, think, think-hard, ultrathink
    performance_metrics: dict[str, float] = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    def has_enhanced_features(self) -> bool:
        """Check if SCF enhanced features were used."""
        return bool(self.personas_used or self.mcp_servers_used or self.thinking_depth)


@dataclass
class OrchestrationContext:
    """Context maintained across orchestration cycles."""
    
    objective_id: UUID = field(default=UUID("00000000-0000-0000-0000-000000000000"))
    command_history: list[str] = field(default_factory=list)
    successful_commands: list[str] = field(default_factory=list)
    failed_commands: list[str] = field(default_factory=list)
    file_changes: dict[Path, list[str]] = field(default_factory=dict)
    test_results: list[TestResults] = field(default_factory=list)
    learned_patterns: list[str] = field(default_factory=list)
    current_step: int = 0
    total_steps: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def add_command(self, command: str, success: bool = True) -> None:
        """Add a command to history."""
        self.command_history.append(command)
        if success:
            self.successful_commands.append(command)
        else:
            self.failed_commands.append(command)
    
    def add_file_change(self, file_path: Path, change_type: str) -> None:
        """Add a file change to context."""
        if file_path not in self.file_changes:
            self.file_changes[file_path] = []
        self.file_changes[file_path].append(change_type)
    
    def add_test_result(self, result: TestResults) -> None:
        """Add test results to context."""
        self.test_results.append(result)
    
    def add_learned_pattern(self, pattern: str) -> None:
        """Add a learned pattern."""
        if pattern not in self.learned_patterns:
            self.learned_patterns.append(pattern)
    
    @property
    def success_rate(self) -> float:
        """Calculate command success rate."""
        total = len(self.command_history)
        if total == 0:
            return 0.0
        return len(self.successful_commands) / total
    
    @property
    def progress(self) -> float:
        """Calculate progress percentage."""
        if self.total_steps == 0:
            return 0.0
        return self.current_step / self.total_steps


@dataclass
class Pattern:
    """Learned pattern from successful orchestrations."""
    
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    trigger: str = ""  # Regex or keyword trigger
    command_sequence: list[str] = field(default_factory=list)
    success_rate: float = 0.0
    usage_count: int = 0
    context_requirements: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    tags: list[str] = field(default_factory=list)
    
    def matches(self, objective: str) -> bool:
        """Check if pattern matches an objective."""
        import re
        return bool(re.search(self.trigger, objective, re.IGNORECASE))
    
    def use(self) -> None:
        """Mark pattern as used."""
        self.usage_count += 1
        self.last_used = datetime.now()
    
    @property
    def reliability_score(self) -> float:
        """Calculate pattern reliability score."""
        # Combine success rate with usage count for reliability
        usage_factor = min(self.usage_count / 10, 1.0)  # Cap at 10 uses
        return self.success_rate * 0.7 + usage_factor * 0.3