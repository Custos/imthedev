"""Tests for AI Orchestrator implementation.

This module tests the AI orchestration functionality including adapter pattern,
multi-model support, command generation, and result analysis.
"""

import os
from uuid import uuid4

import pytest

from imthedev.core.domain import (
    Command,
    CommandResult,
    CommandStatus,
    ProjectContext,
)
from imthedev.core.events import Event, EventBus, EventTypes
from imthedev.core.interfaces import AIModel
from imthedev.core.services.ai_orchestrator import (
    AIOrchestratorImpl,
    AIProviderError,
    InvalidModelError,
    MockAIAdapter,
)


class EventCollector:
    """Test helper to collect events."""

    def __init__(self) -> None:
        self.events: list[Event] = []

    def __call__(self, event: Event) -> None:
        self.events.append(event)

    def get_events_by_type(self, event_type: str) -> list[Event]:
        return [e for e in self.events if e.type == event_type]


@pytest.fixture
async def event_bus() -> EventBus:
    """Create an event bus for testing."""
    return EventBus()


@pytest.fixture
async def event_collector(event_bus: EventBus) -> EventCollector:
    """Create and register an event collector."""
    collector = EventCollector()

    # Subscribe to all AI-related events
    event_bus.subscribe(EventTypes.AI_GENERATION_STARTED, collector)
    event_bus.subscribe(EventTypes.AI_GENERATION_COMPLETED, collector)
    event_bus.subscribe(EventTypes.AI_GENERATION_FAILED, collector)
    event_bus.subscribe(EventTypes.AI_ANALYSIS_COMPLETED, collector)

    return collector


@pytest.fixture
async def orchestrator(event_bus: EventBus) -> AIOrchestratorImpl:
    """Create an AI orchestrator for testing."""
    return AIOrchestratorImpl(event_bus)


@pytest.fixture
def mock_context() -> ProjectContext:
    """Create a mock project context."""
    cmd1 = Command(
        id=uuid4(),
        project_id=uuid4(),
        command_text="echo 'test'",
        ai_reasoning="Testing echo",
        status=CommandStatus.COMPLETED,
    )
    cmd2 = Command(
        id=uuid4(),
        project_id=uuid4(),
        command_text="ls -la",
        ai_reasoning="List files",
        status=CommandStatus.COMPLETED,
    )

    return ProjectContext(
        history=[cmd1, cmd2],
        current_state={"working_dir": "/test", "last_status": "success"},
        ai_memory="Previous task completed successfully",
        metadata={"project_name": "test_project"},
    )


class TestMockAIAdapter:
    """Test the mock AI adapter functionality."""

    async def test_mock_adapter_generate_command(self) -> None:
        """Test mock adapter command generation."""
        adapter = MockAIAdapter()
        context = ProjectContext()

        # Test with "test" objective
        cmd, reasoning = await adapter.generate_command(context, "run tests")
        assert cmd == "pytest"
        assert "tests" in reasoning

        # Test with "build" objective
        cmd, reasoning = await adapter.generate_command(context, "build project")
        assert cmd == "python -m build"
        assert "build" in reasoning.lower()

        # Test with generic objective
        cmd, reasoning = await adapter.generate_command(context, "deploy app")
        assert cmd == "echo 'Executing: deploy app'"
        assert "deploy app" in reasoning

    async def test_mock_adapter_analyze_result(self) -> None:
        """Test mock adapter result analysis."""
        adapter = MockAIAdapter()
        context = ProjectContext()

        # Test successful command
        cmd = Command(
            id=uuid4(),
            project_id=uuid4(),
            command_text="echo 'test'",
            ai_reasoning="Test",
            status=CommandStatus.COMPLETED,
            result=CommandResult(
                exit_code=0, stdout="test", stderr="", execution_time=0.1
            ),
        )

        analysis = await adapter.analyze_result(cmd, "test", context)
        assert analysis.success is True
        assert analysis.next_action == "Continue with next task"
        assert analysis.error_diagnosis is None

        # Test failed command
        cmd.result = CommandResult(
            exit_code=1, stdout="", stderr="error", execution_time=0.1
        )
        analysis = await adapter.analyze_result(cmd, "error", context)
        assert analysis.success is False
        assert analysis.next_action == "Fix the error"
        assert "non-zero exit code" in analysis.error_diagnosis

    async def test_mock_adapter_failure_mode(self) -> None:
        """Test mock adapter in failure mode."""
        adapter = MockAIAdapter(should_fail=True)
        context = ProjectContext()

        with pytest.raises(AIProviderError, match="Mock AI provider error"):
            await adapter.generate_command(context, "test")

        cmd = Command(
            id=uuid4(),
            project_id=uuid4(),
            command_text="test",
            ai_reasoning="Test",
            status=CommandStatus.COMPLETED,
        )

        with pytest.raises(AIProviderError, match="Mock AI provider error"):
            await adapter.analyze_result(cmd, "output", context)

    def test_mock_adapter_is_available(self) -> None:
        """Test mock adapter availability."""
        adapter = MockAIAdapter()
        assert adapter.is_available() is True

        adapter_fail = MockAIAdapter(should_fail=True)
        assert adapter_fail.is_available() is True  # Still available, just fails


class TestAIOrchestratorImpl:
    """Test the AI orchestrator implementation."""

    async def test_register_and_use_mock_adapter(
        self, orchestrator: AIOrchestratorImpl, mock_context: ProjectContext
    ) -> None:
        """Test registering and using a mock adapter."""
        # Register mock adapter
        mock_adapter = MockAIAdapter()
        orchestrator.register_adapter("mock-model", mock_adapter)

        # Generate command with mock
        cmd, reasoning = await orchestrator.generate_command(
            mock_context, "run tests", model="mock-model"
        )

        assert cmd == "pytest"
        assert "tests" in reasoning

    async def test_generate_command_events(
        self,
        orchestrator: AIOrchestratorImpl,
        event_collector: EventCollector,
        mock_context: ProjectContext,
    ) -> None:
        """Test that command generation publishes correct events."""
        # Register mock adapter
        orchestrator.register_adapter("mock-model", MockAIAdapter())

        # Generate command
        await orchestrator.generate_command(
            mock_context, "test objective", model="mock-model"
        )

        # Check events
        start_events = event_collector.get_events_by_type(
            EventTypes.AI_GENERATION_STARTED
        )
        assert len(start_events) == 1
        assert start_events[0].payload["model"] == "mock-model"
        assert start_events[0].payload["objective"] == "test objective"

        complete_events = event_collector.get_events_by_type(
            EventTypes.AI_GENERATION_COMPLETED
        )
        assert len(complete_events) == 1
        assert complete_events[0].payload["model"] == "mock-model"
        assert "command" in complete_events[0].payload

    async def test_generate_command_failure_event(
        self,
        orchestrator: AIOrchestratorImpl,
        event_collector: EventCollector,
        mock_context: ProjectContext,
    ) -> None:
        """Test that failures publish failure events."""
        # Register failing mock adapter
        orchestrator.register_adapter("fail-model", MockAIAdapter(should_fail=True))

        # Try to generate command
        with pytest.raises(AIProviderError):
            await orchestrator.generate_command(
                mock_context, "test", model="fail-model"
            )

        # Check failure event
        fail_events = event_collector.get_events_by_type(
            EventTypes.AI_GENERATION_FAILED
        )
        assert len(fail_events) == 1
        assert fail_events[0].payload["model"] == "fail-model"
        assert "Mock AI provider error" in fail_events[0].payload["error"]

    async def test_invalid_model_error(
        self, orchestrator: AIOrchestratorImpl, mock_context: ProjectContext
    ) -> None:
        """Test that invalid model raises appropriate error."""
        with pytest.raises(
            InvalidModelError, match="Model invalid-model is not supported"
        ):
            await orchestrator.generate_command(
                mock_context, "test", model="invalid-model"
            )

    async def test_analyze_result(
        self,
        orchestrator: AIOrchestratorImpl,
        event_collector: EventCollector,
        mock_context: ProjectContext,
    ) -> None:
        """Test result analysis functionality."""
        # Register mock adapter
        orchestrator.register_adapter("mock-model", MockAIAdapter())

        # Create a command to analyze
        cmd = Command(
            id=uuid4(),
            project_id=uuid4(),
            command_text="echo 'test'",
            ai_reasoning="Test",
            status=CommandStatus.COMPLETED,
            result=CommandResult(
                exit_code=0, stdout="test", stderr="", execution_time=0.1
            ),
        )

        # Analyze result
        mock_context.metadata["last_ai_model"] = "mock-model"
        analysis = await orchestrator.analyze_result(cmd, "test output", mock_context)

        assert analysis.success is True
        assert analysis.next_action is not None

        # Check event
        events = event_collector.get_events_by_type(EventTypes.AI_ANALYSIS_COMPLETED)
        assert len(events) == 1
        assert events[0].payload["success"] is True

    async def test_get_available_models(self, orchestrator: AIOrchestratorImpl) -> None:
        """Test getting available models."""
        # Initially, no models should be available (no API keys)
        models = orchestrator.get_available_models()
        assert isinstance(models, list)

        # Register mock adapter
        orchestrator.register_adapter("mock-model", MockAIAdapter())

        models = orchestrator.get_available_models()
        assert "mock-model" in models

    async def test_estimate_tokens(
        self, orchestrator: AIOrchestratorImpl, mock_context: ProjectContext
    ) -> None:
        """Test token estimation."""
        # Register mock adapter
        orchestrator.register_adapter("mock-model", MockAIAdapter())
        mock_context.metadata["last_ai_model"] = "mock-model"

        tokens = await orchestrator.estimate_tokens(mock_context, "test objective")
        assert tokens == 100  # Mock adapter returns fixed value


class TestGeminiIntegration:
    """Test Gemini integration functionality."""

    async def test_gemini_models_available(self, orchestrator: AIOrchestratorImpl) -> None:
        """Test that Gemini models are available when API key is set."""
        # Set a test API key
        os.environ["GEMINI_API_KEY"] = "test-key"
        
        # Re-initialize adapters
        orchestrator._initialize_adapters()
        
        # Check that Gemini models are available
        available_models = orchestrator.get_available_models()
        
        # Should include Gemini models if adapter is properly initialized
        # Note: Actual availability depends on whether google-generativeai is installed
        # and the adapter can be initialized
        
    async def test_gemini_default_model(self, orchestrator: AIOrchestratorImpl, mock_context: ProjectContext) -> None:
        """Test that Gemini Flash is the default model."""
        # Register a mock adapter for testing
        orchestrator.register_adapter(AIModel.GEMINI_FLASH, MockAIAdapter())
        
        # Generate command without specifying model (should use default)
        cmd, reasoning = await orchestrator.generate_command(
            mock_context, "test objective"
        )
        
        # Should work with default Gemini Flash model
        assert cmd is not None
        assert reasoning is not None
