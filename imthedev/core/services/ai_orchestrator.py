"""AI orchestration implementation with adapter pattern for multi-model support.

This module provides the core AI integration functionality that orchestrates
interactions with multiple AI providers through a unified interface.
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

    Each AI provider (Claude, OpenAI, etc.) must implement this interface
    to integrate with the orchestrator.
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


class ClaudeAdapter(AIAdapter):
    """Adapter for Anthropic's Claude models."""

    def __init__(
        self, api_key: str | None = None, model_name: str = "claude-3-opus-20240229"
    ) -> None:
        """Initialize Claude adapter.

        Args:
            api_key: API key for Anthropic. If None, will try to read from environment.
            model_name: Specific Claude model version to use
        """
        self._api_key = api_key or os.environ.get("CLAUDE_API_KEY", "")
        self._model_name = model_name
        self._client = None

        if self._api_key:
            try:
                import anthropic

                self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
            except ImportError:
                logger.warning(
                    "anthropic package not installed. Claude adapter will be unavailable."
                )
            except Exception as e:
                logger.error(f"Failed to initialize Claude client: {e}")

    async def generate_command(
        self, context: ProjectContext, objective: str
    ) -> tuple[str, str]:
        """Generate a command using Claude."""
        if not self._client:
            raise AIProviderError("Claude client not initialized")

        try:
            # Build context for Claude
            context_text = self._build_context_prompt(context)

            prompt = f"""You are an AI assistant helping with software development tasks.

Project Context:
{context_text}

Current Objective: {objective}

Based on the context and objective, generate a single shell command that would help achieve the goal.
Respond in JSON format with exactly two fields:
- "command": The exact command to execute
- "reasoning": A brief explanation of why this command helps achieve the objective

Important:
- Generate only ONE command at a time
- Make the command specific and executable
- Consider the project's current state and history
"""

            response = await self._client.messages.create(
                model=self._model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.7,
            )

            # Parse response - extract text from TextBlock
            content_block = response.content[0]
            if hasattr(content_block, 'text'):
                result = json.loads(content_block.text)
                return result["command"], result["reasoning"]
            else:
                raise AIProviderError(f"Unexpected response type: {type(content_block)}")

        except json.JSONDecodeError as e:
            raise AIProviderError(f"Failed to parse Claude response: {e}") from e
        except Exception as e:
            raise AIProviderError(f"Claude API error: {e}") from e

    async def analyze_result(
        self, command: Command, output: str, context: ProjectContext
    ) -> CommandAnalysis:
        """Analyze command results using Claude."""
        del context  # Currently unused
        if not self._client:
            raise AIProviderError("Claude client not initialized")

        try:
            prompt = f"""Analyze the following command execution result:

Command: {command.command_text}
Exit Code: {command.result.exit_code if command.result else 'N/A'}
Output:
{output}

Based on the output, determine:
1. Was the command successful?
2. What should be the next action (if any)?
3. If there was an error, what is the diagnosis?
4. Are there any state updates needed?

Respond in JSON format with these fields:
- "success": boolean
- "next_action": string or null
- "error_diagnosis": string or null
- "state_updates": object or null
"""

            response = await self._client.messages.create(
                model=self._model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.3,
            )

            content_block = response.content[0]
            if hasattr(content_block, 'text'):
                result = json.loads(content_block.text)
            else:
                raise AIProviderError(f"Unexpected response type: {type(content_block)}")
            return CommandAnalysis(
                success=result["success"],
                next_action=result.get("next_action"),
                error_diagnosis=result.get("error_diagnosis"),
                state_updates=result.get("state_updates", {}),
            )

        except json.JSONDecodeError as e:
            raise AIProviderError(f"Failed to parse Claude response: {e}") from e
        except Exception as e:
            raise AIProviderError(f"Claude API error: {e}") from e

    async def estimate_tokens(self, context: ProjectContext, objective: str) -> int:
        """Estimate token usage for Claude."""
        # Rough estimation based on context size
        context_text = self._build_context_prompt(context)
        total_chars = len(context_text) + len(objective) + 500  # Buffer for prompt

        # Claude uses approximately 1 token per 4 characters
        return total_chars // 4

    def is_available(self) -> bool:
        """Check if Claude adapter is available."""
        return bool(self._api_key and self._client is not None)

    def _build_context_prompt(self, context: ProjectContext) -> str:
        """Build a context prompt from project context."""
        return build_context_prompt(context)


class OpenAIAdapter(AIAdapter):
    """Adapter for OpenAI's GPT models."""

    def __init__(self, api_key: str | None = None, model_name: str = "gpt-4") -> None:
        """Initialize OpenAI adapter.

        Args:
            api_key: API key for OpenAI. If None, will try to read from environment.
            model_name: Specific GPT model to use
        """
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._model_name = model_name
        self._client = None

        if self._api_key:
            try:
                import openai

                self._client = openai.AsyncOpenAI(api_key=self._api_key)
            except ImportError:
                logger.warning(
                    "openai package not installed. OpenAI adapter will be unavailable."
                )
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")

    async def generate_command(
        self, context: ProjectContext, objective: str
    ) -> tuple[str, str]:
        """Generate a command using GPT."""
        if not self._client:
            raise AIProviderError("OpenAI client not initialized")

        try:
            # Build context for GPT
            context_text = self._build_context_prompt(context)

            messages = [
                {
                    "role": "system",
                    "content": "You are an AI assistant helping with software development tasks. Always respond in valid JSON format.",
                },
                {
                    "role": "user",
                    "content": f"""Project Context:
{context_text}

Current Objective: {objective}

Generate a single shell command that would help achieve the goal.
Respond in JSON format with exactly two fields:
- "command": The exact command to execute
- "reasoning": A brief explanation of why this command helps achieve the objective""",
                },
            ]

            response = await self._client.chat.completions.create(  # type: ignore[call-overload]
                model=self._model_name,
                messages=messages,
                max_tokens=1000,
                temperature=0.7,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            return result["command"], result["reasoning"]

        except json.JSONDecodeError as e:
            raise AIProviderError(f"Failed to parse OpenAI response: {e}") from e
        except Exception as e:
            raise AIProviderError(f"OpenAI API error: {e}") from e

    async def analyze_result(
        self, command: Command, output: str, context: ProjectContext
    ) -> CommandAnalysis:
        """Analyze command results using GPT."""
        del context  # Currently unused
        if not self._client:
            raise AIProviderError("OpenAI client not initialized")

        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are an AI assistant analyzing command execution results. Always respond in valid JSON format.",
                },
                {
                    "role": "user",
                    "content": f"""Analyze this command execution:

Command: {command.command_text}
Exit Code: {command.result.exit_code if command.result else 'N/A'}
Output:
{output}

Respond in JSON with:
- "success": boolean
- "next_action": string or null
- "error_diagnosis": string or null
- "state_updates": object or null""",
                },
            ]

            response = await self._client.chat.completions.create(  # type: ignore[call-overload]
                model=self._model_name,
                messages=messages,
                max_tokens=1000,
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            return CommandAnalysis(
                success=result["success"],
                next_action=result.get("next_action"),
                error_diagnosis=result.get("error_diagnosis"),
                state_updates=result.get("state_updates", {}),
            )

        except json.JSONDecodeError as e:
            raise AIProviderError(f"Failed to parse OpenAI response: {e}") from e
        except Exception as e:
            raise AIProviderError(f"OpenAI API error: {e}") from e

    async def estimate_tokens(self, context: ProjectContext, objective: str) -> int:
        """Estimate token usage for GPT."""
        # Similar estimation to Claude
        context_text = self._build_context_prompt(context)
        total_chars = len(context_text) + len(objective) + 500

        # GPT uses approximately 1 token per 4 characters
        return total_chars // 4

    def is_available(self) -> bool:
        """Check if OpenAI adapter is available."""
        return bool(self._api_key and self._client is not None)

    def _build_context_prompt(self, context: ProjectContext) -> str:
        """Build a context prompt from project context."""
        return build_context_prompt(context)


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
    """Implementation of AI orchestration with multi-model support.

    This orchestrator uses the Adapter Pattern to support multiple AI providers
    through a unified interface. It manages model selection, error handling,
    and event notifications.
    """

    # Registry of adapter classes by model identifier
    ADAPTER_REGISTRY: dict[str, type[AIAdapter]] = {
        AIModel.CLAUDE: ClaudeAdapter,
        AIModel.CLAUDE_INSTANT: ClaudeAdapter,
        AIModel.GPT4: OpenAIAdapter,
        AIModel.GPT35_TURBO: OpenAIAdapter,
    }
    
    # Note: Gemini adapters will be registered dynamically to avoid import issues

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
        # Initialize Claude adapters
        claude_key = os.environ.get("CLAUDE_API_KEY")
        if claude_key:
            self._adapters[AIModel.CLAUDE] = ClaudeAdapter(
                api_key=claude_key, model_name="claude-3-opus-20240229"
            )
            self._adapters[AIModel.CLAUDE_INSTANT] = ClaudeAdapter(
                api_key=claude_key, model_name="claude-3-sonnet-20240229"
            )

        # Initialize OpenAI adapters
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            self._adapters[AIModel.GPT4] = OpenAIAdapter(
                api_key=openai_key, model_name="gpt-4"
            )
            self._adapters[AIModel.GPT35_TURBO] = OpenAIAdapter(
                api_key=openai_key, model_name="gpt-3.5-turbo"
            )
        
        # Initialize Gemini adapters
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            try:
                from imthedev.core.services.gemini_adapter import GeminiAdapter
                
                self._adapters[AIModel.GEMINI_FLASH] = GeminiAdapter(
                    api_key=gemini_key, model_name="gemini-2.5-flash"
                )
                self._adapters[AIModel.GEMINI_PRO] = GeminiAdapter(
                    api_key=gemini_key, model_name="gemini-2.5-pro"
                )
                self._adapters[AIModel.GEMINI_FLASH_8B] = GeminiAdapter(
                    api_key=gemini_key, model_name="gemini-2.5-flash-8b"
                )
            except ImportError:
                logger.warning("GeminiAdapter not available - Google AI SDK may not be installed")

        logger.info(f"Initialized adapters for models: {list(self._adapters.keys())}")

    async def generate_command(
        self, context: ProjectContext, objective: str, model: str = AIModel.CLAUDE
    ) -> tuple[str, str]:
        """Generate a command based on context and objective.

        Args:
            context: Current project context including history
            objective: What the user wants to achieve
            model: AI model to use for generation

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
        model = context.metadata.get("last_ai_model", AIModel.CLAUDE)
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
        model = context.metadata.get("last_ai_model", AIModel.CLAUDE)
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
            # Try to create adapter on demand
            if model in self.ADAPTER_REGISTRY:
                adapter_class = self.ADAPTER_REGISTRY[model]
                adapter = adapter_class()
                if adapter.is_available():
                    self._adapters[model] = adapter
                else:
                    raise InvalidModelError(
                        f"Model {model} is not available. Check API key configuration."
                    )
            else:
                raise InvalidModelError(
                    f"Model {model} is not supported. "
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
