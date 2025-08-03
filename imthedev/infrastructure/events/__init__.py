"""Event system for dual-AI orchestration.

This package provides the event-driven communication infrastructure
for the orchestration system.
"""

from .orchestration_bus import OrchestrationEvent, OrchestrationEventBus, orchestration_bus
from .command_events import (
    CommandEvent,
    CommandProposed,
    CommandApproved,
    CommandRejected,
    CommandModified,
    CommandValidated,
)
from .gemini_events import (
    GeminiEvent,
    ObjectiveSubmitted,
    ObjectiveAnalyzed,
    PlanGenerated,
    ResultAnalyzed,
    NextStepProposed,
    ObjectiveCompleted,
    RecoveryProposed,
)
from .claude_events import (
    ClaudeEvent,
    ExecutionStarted,
    OutputStreaming,
    ExecutionProgress,
    FileCreated,
    FileModified,
    TestExecuted,
    ExecutionComplete,
    ExecutionFailed,
    MetadataExtracted,
)
from .feedback_events import (
    FeedbackEvent,
    FeedbackCycleStarted,
    PatternDetected,
    LearningCaptured,
    PatternApplied,
    ContextUpdated,
    MetricsCalculated,
    FeedbackCycleComplete,
)

__all__ = [
    # Bus
    "OrchestrationEvent",
    "OrchestrationEventBus",
    "orchestration_bus",
    # Command events
    "CommandEvent",
    "CommandProposed",
    "CommandApproved",
    "CommandRejected",
    "CommandModified",
    "CommandValidated",
    # Gemini events
    "GeminiEvent",
    "ObjectiveSubmitted",
    "ObjectiveAnalyzed",
    "PlanGenerated",
    "ResultAnalyzed",
    "NextStepProposed",
    "ObjectiveCompleted",
    "RecoveryProposed",
    # Claude events
    "ClaudeEvent",
    "ExecutionStarted",
    "OutputStreaming",
    "ExecutionProgress",
    "FileCreated",
    "FileModified",
    "TestExecuted",
    "ExecutionComplete",
    "ExecutionFailed",
    "MetadataExtracted",
    # Feedback events
    "FeedbackEvent",
    "FeedbackCycleStarted",
    "PatternDetected",
    "LearningCaptured",
    "PatternApplied",
    "ContextUpdated",
    "MetricsCalculated",
    "FeedbackCycleComplete",
]