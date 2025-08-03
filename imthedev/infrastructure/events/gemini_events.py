"""Gemini orchestrator-specific events.

Events related to Gemini's analysis, planning, and decision-making.
"""

from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from .orchestration_bus import OrchestrationEvent


@dataclass(frozen=True)
class GeminiEvent(OrchestrationEvent):
    """Base class for Gemini orchestrator events."""
    
    objective_id: Optional[UUID] = None
    step_number: int = 0


@dataclass(frozen=True)
class ObjectiveSubmitted(GeminiEvent):
    """Event emitted when user submits an objective."""
    
    objective_text: str = ""
    success_criteria: list[str] = field(default_factory=list)
    context: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ObjectiveAnalyzed(GeminiEvent):
    """Event emitted after Gemini analyzes an objective."""
    
    analysis: str = ""
    estimated_steps: int = 0
    complexity_score: float = 0.0
    suggested_approach: str = ""
    required_capabilities: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PlanGenerated(GeminiEvent):
    """Event emitted when Gemini generates execution plan."""
    
    plan_steps: list[dict[str, str]] = field(default_factory=list)
    total_estimated_time: float = 0.0
    dependencies: list[str] = field(default_factory=list)
    risk_assessment: str = ""


@dataclass(frozen=True)
class ResultAnalyzed(GeminiEvent):
    """Event emitted after Gemini analyzes execution results."""
    
    execution_id: UUID = field(default=UUID("00000000-0000-0000-0000-000000000000"))
    success: bool = False
    understanding: str = ""
    missing_elements: list[str] = field(default_factory=list)
    next_action: str = ""
    confidence: float = 0.0


@dataclass(frozen=True)
class NextStepProposed(GeminiEvent):
    """Event emitted when Gemini proposes next orchestration step."""
    
    next_command: str = ""
    reasoning: str = ""
    alternatives: list[str] = field(default_factory=list)
    expected_outcome: str = ""


@dataclass(frozen=True)
class ObjectiveCompleted(GeminiEvent):
    """Event emitted when objective is successfully completed."""
    
    total_steps: int = 0
    total_time: float = 0.0
    success_metrics: dict[str, float] = field(default_factory=dict)
    learned_patterns: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RecoveryProposed(GeminiEvent):
    """Event emitted when Gemini proposes error recovery."""
    
    error_context: str = ""
    recovery_strategy: str = ""
    recovery_commands: list[str] = field(default_factory=list)
    success_probability: float = 0.0