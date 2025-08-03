"""Feedback loop and learning events.

Events related to analysis, learning, and pattern recognition.
"""

from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from .orchestration_bus import OrchestrationEvent


@dataclass(frozen=True)
class FeedbackEvent(OrchestrationEvent):
    """Base class for feedback and learning events."""
    
    session_id: UUID = field(default=UUID("00000000-0000-0000-0000-000000000000"))


@dataclass(frozen=True)
class FeedbackCycleStarted(FeedbackEvent):
    """Event emitted when feedback analysis begins."""
    
    execution_id: UUID = field(default=UUID("00000000-0000-0000-0000-000000000000"))
    objective_id: UUID = field(default=UUID("00000000-0000-0000-0000-000000000000"))


@dataclass(frozen=True)
class PatternDetected(FeedbackEvent):
    """Event emitted when a pattern is recognized."""
    
    pattern_name: str = ""
    pattern_type: str = ""  # success, failure, optimization
    trigger_conditions: list[str] = field(default_factory=list)
    command_sequence: list[str] = field(default_factory=list)
    success_rate: float = 0.0
    occurrences: int = 0


@dataclass(frozen=True)
class LearningCaptured(FeedbackEvent):
    """Event emitted when learning is extracted."""
    
    learning_type: str = ""  # technique, anti-pattern, optimization
    description: str = ""
    context: str = ""
    applicability_score: float = 0.0
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PatternApplied(FeedbackEvent):
    """Event emitted when a learned pattern is applied."""
    
    pattern_id: str = ""
    pattern_name: str = ""
    confidence: float = 0.0
    adjustments_made: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ContextUpdated(FeedbackEvent):
    """Event emitted when orchestration context is updated."""
    
    context_type: str = ""  # command_history, file_changes, test_results
    added_items: int = 0
    removed_items: int = 0
    total_context_size: int = 0


@dataclass(frozen=True)
class MetricsCalculated(FeedbackEvent):
    """Event emitted when performance metrics are calculated."""
    
    success_rate: float = 0.0
    average_steps_to_complete: float = 0.0
    average_execution_time: float = 0.0
    pattern_reuse_rate: float = 0.0
    user_intervention_rate: float = 0.0
    custom_metrics: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class FeedbackCycleComplete(FeedbackEvent):
    """Event emitted when feedback cycle completes."""
    
    cycle_duration: float = 0.0
    patterns_identified: int = 0
    learnings_captured: int = 0
    context_updates: int = 0
    next_action_determined: bool = False