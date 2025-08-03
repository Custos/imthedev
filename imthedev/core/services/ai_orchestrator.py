"""AI orchestration implementation for Gemini model support.

This module provides the core AI integration functionality that orchestrates
interactions with Google's Gemini AI models through a unified interface.
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, cast

from imthedev.core.domain import Command, ProjectContext
from imthedev.core.events import Event, EventBus, EventTypes
from imthedev.core.interfaces import AIModel, AIOrchestrator, CommandAnalysis


def build_context_prompt(context: ProjectContext) -> str:
    """Build a context prompt from project context.

    Args:
        context: Project context to build prompt from

    Returns:
        Formatted context prompt string
    """
    lines = []

    # Add recent command history
    if context.history:
        lines.append("Recent Commands:")
        for cmd in context.history[-5:]:  # Last 5 commands
            lines.append(f"- {cmd.command_text} ({cmd.status.value})")

    # Add current state
    if context.current_state:
        lines.append("\nCurrent State:")
        for key, value in context.current_state.items():
            lines.append(f"- {key}: {value}")

    # Add AI memory
    if context.ai_memory:
        lines.append(f"\nAI Memory:\n{context.ai_memory}")

    return "\n".join(lines)

logger = logging.getLogger(__name__)


class AIProviderError(Exception):
    """Raised when AI provider encounters an error."""

    pass


class InvalidModelError(Exception):
    """Raised when an unsupported AI model is requested."""

    pass


class AIAdapter(ABC):
    """Abstract base class for AI provider adapters.

    Each AI provider must implement this interface to integrate with the orchestrator.
    """

    @abstractmethod
    async def generate_command(
        self, context: ProjectContext, objective: str
    ) -> tuple[str, str]:
        """Generate a command based on context and objective.

        Args:
            context: Current project context including history
            objective: What the user wants to achieve

        Returns:
            Tuple of (command_text, ai_reasoning)

        Raises:
            AIProviderError: If generation fails
        """
        pass

    @abstractmethod
    async def analyze_result(
        self, command: Command, output: str, context: ProjectContext
    ) -> CommandAnalysis:
        """Analyze command execution results.

        Args:
            command: The executed command
            output: Output from command execution
            context: Current project context

        Returns:
            Analysis with success assessment and recommendations

        Raises:
            AIProviderError: If analysis fails
        """
        pass

    @abstractmethod
    async def estimate_tokens(self, context: ProjectContext, objective: str) -> int:
        """Estimate token usage for a command generation.

        Args:
            context: Current project context
            objective: The objective to achieve

        Returns:
            Estimated number of tokens
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this adapter is available for use.

        Returns:
            True if the adapter can be used (e.g., API key is configured)
        """
        pass


class MockAIAdapter(AIAdapter):
    """Mock adapter for testing purposes."""

    def __init__(self, should_fail: bool = False) -> None:
        """Initialize mock adapter.

        Args:
            should_fail: If True, all operations will raise AIProviderError
        """
        self._should_fail = should_fail
        self._call_count = 0

    async def generate_command(
        self, context: ProjectContext, objective: str
    ) -> tuple[str, str]:
        """Generate a mock command."""
        del context  # Currently unused
        self._call_count += 1

        if self._should_fail:
            raise AIProviderError("Mock AI provider error")

        # Generate predictable commands based on objective
        if "test" in objective.lower():
            return "pytest", "Running tests based on objective"
        elif "build" in objective.lower():
            return "python -m build", "Building project based on objective"
        else:
            return f"echo 'Executing: {objective}'", f"Mock command for: {objective}"

    async def analyze_result(
        self, command: Command, output: str, context: ProjectContext
    ) -> CommandAnalysis:
        """Analyze with mock logic."""
        del context, output  # Currently unused
        if self._should_fail:
            raise AIProviderError("Mock AI provider error")

        # Simple analysis based on exit code
        success = command.result.exit_code == 0 if command.result else True

        return CommandAnalysis(
            success=success,
            next_action="Continue with next task" if success else "Fix the error",
            error_diagnosis=None
            if success
            else "Command failed with non-zero exit code",
            state_updates={"last_command": command.command_text},
        )

    async def estimate_tokens(self, context: ProjectContext, objective: str) -> int:
        """Estimate with mock logic."""
        del context, objective  # Currently unused
        return 100  # Fixed estimate for testing

    def is_available(self) -> bool:
        """Mock adapter is always available."""
        return True


class AIOrchestratorImpl(AIOrchestrator):
    """Implementation of AI orchestration with Gemini model support.

    This orchestrator uses the Adapter Pattern to support Gemini AI models
    through a unified interface. It manages model selection, error handling,
    and event notifications.
    """

    def __init__(self, event_bus: EventBus) -> None:
        """Initialize the AI orchestrator.

        Args:
            event_bus: Event bus for publishing AI-related events
        """
        self._event_bus = event_bus
        self._adapters: dict[str, AIAdapter] = {}
        self._initialize_adapters()

    def _initialize_adapters(self) -> None:
        """Initialize available AI adapters."""
        # Initialize Gemini adapters
        gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if gemini_key:
            try:
                from imthedev.core.services.gemini_adapter import GeminiAdapter
                
                # Initialize all Gemini model variants
                self._adapters[AIModel.GEMINI_FLASH] = GeminiAdapter(
                    api_key=gemini_key, model_name="gemini-2.5-flash"
                )
                self._adapters[AIModel.GEMINI_PRO] = GeminiAdapter(
                    api_key=gemini_key, model_name="gemini-2.5-pro"
                )
                self._adapters[AIModel.GEMINI_FLASH_8B] = GeminiAdapter(
                    api_key=gemini_key, model_name="gemini-2.5-flash-8b"
                )
                
                # Add convenience aliases
                self._adapters["gemini-2.5-flash"] = self._adapters[AIModel.GEMINI_FLASH]
                self._adapters["gemini-2.5-pro"] = self._adapters[AIModel.GEMINI_PRO]
                self._adapters["gemini-2.5-flash-8b"] = self._adapters[AIModel.GEMINI_FLASH_8B]
                
                logger.info(f"Initialized Gemini adapters for models: gemini-2.5-flash, gemini-2.5-pro, gemini-2.5-flash-8b")
            except ImportError:
                logger.error("GeminiAdapter not available - Please install google-generativeai package")
        else:
            logger.warning("No Gemini API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable.")

    async def generate_command(
        self, context: ProjectContext, objective: str, model: str = AIModel.GEMINI_FLASH
    ) -> tuple[str, str]:
        """Generate a command based on context and objective.

        Args:
            context: Current project context including history
            objective: What the user wants to achieve
            model: AI model to use for generation (defaults to Gemini Flash)

        Returns:
            Tuple of (command_text, ai_reasoning)

        Raises:
            AIProviderError: If AI service is unavailable
            InvalidModelError: If the specified model is not supported
        """
        adapter = self._get_adapter(model)

        try:
            # Publish event for command generation start
            await self._event_bus.publish(
                Event(
                    type=EventTypes.AI_GENERATION_STARTED,
                    payload={
                        "model": model,
                        "objective": objective,
                        "context_size": len(context.history),
                    },
                )
            )

            # Generate command
            command_text, reasoning = await adapter.generate_command(context, objective)

            # Publish success event
            await self._event_bus.publish(
                Event(
                    type=EventTypes.AI_GENERATION_COMPLETED,
                    payload={
                        "model": model,
                        "command": command_text,
                        "reasoning": reasoning,
                    },
                )
            )

            return command_text, reasoning

        except Exception as e:
            # Publish failure event
            await self._event_bus.publish(
                Event(
                    type=EventTypes.AI_GENERATION_FAILED,
                    payload={
                        "model": model,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
            )
            raise

    async def analyze_result(
        self, command: Command, output: str, context: ProjectContext
    ) -> CommandAnalysis:
        """Analyze command execution results and suggest next steps.

        Args:
            command: The executed command
            output: Output from command execution
            context: Current project context

        Returns:
            Analysis with success assessment and recommendations

        Raises:
            AIProviderError: If AI service is unavailable
        """
        # Use the same model that generated the command, or default
        model = context.metadata.get("last_ai_model", AIModel.GEMINI_FLASH)
        adapter = self._get_adapter(model)

        try:
            # Analyze the result
            analysis = await adapter.analyze_result(command, output, context)

            # Publish analysis event
            await self._event_bus.publish(
                Event(
                    type=EventTypes.AI_ANALYSIS_COMPLETED,
                    payload={
                        "model": model,
                        "command_id": str(command.id),
                        "success": analysis.success,
                        "has_next_action": analysis.next_action is not None,
                    },
                )
            )

            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze command result: {e}")
            raise

    def get_available_models(self) -> list[str]:
        """Get list of available AI models.

        Returns:
            List of model identifiers that can be used
        """
        return [
            model_id
            for model_id, adapter in self._adapters.items()
            if adapter.is_available()
        ]

    async def estimate_tokens(self, context: ProjectContext, objective: str) -> int:
        """Estimate token usage for a command generation.

        Args:
            context: Current project context
            objective: The objective to achieve

        Returns:
            Estimated number of tokens
        """
        # Use default model for estimation
        model = context.metadata.get("last_ai_model", AIModel.GEMINI_FLASH)
        adapter = self._get_adapter(model)

        return await adapter.estimate_tokens(context, objective)

    def _get_adapter(self, model: str) -> AIAdapter:
        """Get the adapter for a specific model.

        Args:
            model: Model identifier

        Returns:
            Configured adapter for the model

        Raises:
            InvalidModelError: If model is not supported or unavailable
        """
        if model not in self._adapters:
            raise InvalidModelError(
                f"Model {model} is not supported or unavailable. "
                f"Available models: {', '.join(self.get_available_models())}"
            )

        return self._adapters[model]

    def register_adapter(self, model_id: str, adapter: AIAdapter) -> None:
        """Register a custom adapter for a model.

        This method allows for runtime registration of adapters,
        useful for testing or adding custom AI providers.

        Args:
            model_id: Identifier for the model
            adapter: Adapter instance to register
        """
        self._adapters[model_id] = adapter
        logger.info(f"Registered adapter for model: {model_id}")