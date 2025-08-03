"""Google Gemini AI adapter implementation for imthedev.

This module provides integration with Google's Gemini 2.5 models (Flash and Pro)
through the AIAdapter interface, enabling multi-model AI support in the application.
"""

import json
import logging
import os
from typing import Any, Optional

from imthedev.core.domain import Command, CommandAnalysis, ProjectContext
from imthedev.core.services.ai_orchestrator import AIAdapter, AIProviderError

logger = logging.getLogger(__name__)


class GeminiAdapter(AIAdapter):
    """Adapter for Google's Gemini 2.5 models.
    
    Supports both Gemini 2.5 Flash (fast, efficient) and Gemini 2.5 Pro (advanced)
    models with full async support and comprehensive error handling.
    
    Attributes:
        api_key: Google AI API key for authentication
        model_name: Specific Gemini model to use
        client: Google genai client instance
    """
    
    # Supported Gemini models
    SUPPORTED_MODELS = {
        "gemini-2.5-flash": {
            "name": "gemini-2.5-flash",
            "description": "Fast and efficient model for quick responses",
            "max_tokens": 8192,
            "cost_per_1k_tokens": 0.00025,  # Approximate pricing
        },
        "gemini-2.5-pro": {
            "name": "gemini-2.5-pro",
            "description": "Advanced model for complex reasoning",
            "max_tokens": 32768,
            "cost_per_1k_tokens": 0.00125,  # Approximate pricing
        },
        "gemini-2.5-flash-8b": {
            "name": "gemini-2.5-flash-8b",
            "description": "Lightweight model for simple tasks",
            "max_tokens": 8192,
            "cost_per_1k_tokens": 0.00015,  # Approximate pricing
        },
    }
    
    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "gemini-2.5-flash"
    ) -> None:
        """Initialize Gemini adapter.
        
        Args:
            api_key: API key for Google AI. If None, will try to read from environment.
            model_name: Specific Gemini model version to use
        
        Raises:
            ValueError: If unsupported model is specified
        """
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        
        if model_name not in self.SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported model: {model_name}. "
                f"Supported models: {list(self.SUPPORTED_MODELS.keys())}"
            )
        
        self._model_name = model_name
        self._model_config = self.SUPPORTED_MODELS[model_name]
        self._client: Any = None
        
        if self._api_key:
            try:
                # Import Google AI SDK
                from google import genai
                from google.genai import types
                
                # Configure client with API key
                self._client = genai.Client(api_key=self._api_key)
                logger.info(f"Gemini adapter initialized with model: {model_name}")
            except ImportError:
                logger.warning(
                    "Google AI SDK not installed. Install with: pip install google-genai"
                )
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
    
    def is_available(self) -> bool:
        """Check if this adapter is available for use.
        
        Returns:
            True if the adapter can be used (API key configured and client initialized)
        """
        return bool(self._api_key and self._client)
    
    async def generate_command(
        self, context: ProjectContext, objective: str
    ) -> tuple[str, str]:
        """Generate a command based on context and objective using Gemini.
        
        Args:
            context: Current project context including history
            objective: What the user wants to achieve
        
        Returns:
            Tuple of (command_text, ai_reasoning)
        
        Raises:
            AIProviderError: If generation fails
        """
        if not self.is_available():
            raise AIProviderError("Gemini adapter is not available (missing API key or client)")
        
        try:
            # Build context prompt
            context_prompt = self._build_context_prompt(context)
            
            # Create the prompt for Gemini
            prompt = self._create_command_generation_prompt(context_prompt, objective)
            
            # Generate response using Gemini
            response = await self._generate_async(prompt)
            
            # Parse the response to extract command and reasoning
            command_text, reasoning = self._parse_command_response(response)
            
            logger.debug(f"Generated command: {command_text}")
            return command_text, reasoning
            
        except Exception as e:
            logger.error(f"Failed to generate command with Gemini: {e}")
            raise AIProviderError(f"Gemini command generation failed: {str(e)}") from e
    
    async def analyze_result(
        self, command: Command, output: str, context: ProjectContext
    ) -> CommandAnalysis:
        """Analyze command execution results using Gemini.
        
        Args:
            command: The executed command
            output: Output from command execution
            context: Current project context
        
        Returns:
            Analysis with success assessment and recommendations
        
        Raises:
            AIProviderError: If analysis fails
        """
        if not self.is_available():
            raise AIProviderError("Gemini adapter is not available")
        
        try:
            # Create analysis prompt
            prompt = self._create_analysis_prompt(command, output, context)
            
            # Generate analysis using Gemini
            response = await self._generate_async(prompt)
            
            # Parse the analysis response
            analysis = self._parse_analysis_response(response)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze result with Gemini: {e}")
            raise AIProviderError(f"Gemini analysis failed: {str(e)}") from e
    
    async def estimate_tokens(self, context: ProjectContext, objective: str) -> int:
        """Estimate token usage for a command generation.
        
        Uses approximate token counting based on character count.
        Gemini uses a similar tokenization to other models (~4 chars per token).
        
        Args:
            context: Current project context
            objective: The objective to achieve
        
        Returns:
            Estimated number of tokens
        """
        # Build the full prompt
        context_prompt = self._build_context_prompt(context)
        prompt = self._create_command_generation_prompt(context_prompt, objective)
        
        # Approximate token count (1 token ≈ 4 characters)
        char_count = len(prompt)
        estimated_tokens = char_count // 4
        
        # Add buffer for response tokens
        estimated_tokens += 500  # Typical response size
        
        return estimated_tokens
    
    async def _generate_async(self, prompt: str) -> str:
        """Make an async request to Gemini API.
        
        Args:
            prompt: The prompt to send to Gemini
        
        Returns:
            Generated response text
        
        Raises:
            Exception: If API call fails
        """
        import asyncio
        
        # Gemini SDK might not have native async support yet,
        # so we run the sync version in an executor
        loop = asyncio.get_event_loop()
        
        def _sync_generate():
            response = self._client.models.generate_content(
                model=self._model_name,
                contents=prompt,
                config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": self._model_config["max_tokens"],
                }
            )
            return response.text
        
        # Run in executor for non-blocking operation
        result = await loop.run_in_executor(None, _sync_generate)
        return result
    
    def _build_context_prompt(self, context: ProjectContext) -> str:
        """Build a context prompt from project context.
        
        Args:
            context: Project context to build prompt from
        
        Returns:
            Formatted context prompt string
        """
        lines = []
        
        # Add recent command history
        if context.history:
            lines.append("Recent Command History:")
            for cmd in context.history[-5:]:  # Last 5 commands
                lines.append(f"  - Command: {cmd.command_text}")
                lines.append(f"    Status: {cmd.status.value}")
                if cmd.result:
                    lines.append(f"    Exit Code: {cmd.result.exit_code}")
        
        # Add current state
        if context.current_state:
            lines.append("\nCurrent Project State:")
            for key, value in context.current_state.items():
                lines.append(f"  - {key}: {value}")
        
        # Add AI memory/context
        if context.ai_memory:
            lines.append(f"\nPrevious Context:\n{context.ai_memory}")
        
        return "\n".join(lines)
    
    def _create_command_generation_prompt(self, context: str, objective: str) -> str:
        """Create a prompt for command generation.
        
        Args:
            context: Formatted context information
            objective: User's objective
        
        Returns:
            Complete prompt for Gemini
        """
        return f"""You are an AI assistant helping with software development tasks.
        
Based on the following context and objective, generate a shell command that will help achieve the goal.

CONTEXT:
{context}

OBJECTIVE: {objective}

Please provide:
1. A single shell command that will help achieve the objective
2. Clear reasoning explaining why this command is appropriate

Format your response as:
COMMAND: [the actual command to execute]
REASONING: [explanation of why this command helps achieve the objective]

Important guidelines:
- Generate safe, non-destructive commands
- Consider the current state and recent command history
- Provide commands that move towards the objective incrementally
- Explain your reasoning clearly
"""
    
    def _create_analysis_prompt(
        self, command: Command, output: str, context: ProjectContext
    ) -> str:
        """Create a prompt for result analysis.
        
        Args:
            command: Executed command
            output: Command output
            context: Project context
        
        Returns:
            Complete analysis prompt
        """
        context_str = self._build_context_prompt(context)
        
        return f"""Analyze the following command execution result:

COMMAND EXECUTED: {command.command_text}
COMMAND OUTPUT:
{output}

CONTEXT:
{context_str}

Please analyze this result and provide:
1. Whether the command succeeded or failed
2. What was accomplished
3. Suggested next steps

Format your response as:
SUCCESS: [true/false]
SUMMARY: [brief summary of what happened]
NEXT_STEPS: [recommended actions to take next]
"""
    
    def _parse_command_response(self, response: str) -> tuple[str, str]:
        """Parse Gemini's response to extract command and reasoning.
        
        Args:
            response: Raw response from Gemini
        
        Returns:
            Tuple of (command_text, reasoning)
        """
        lines = response.strip().split('\n')
        command_text = ""
        reasoning = ""
        
        for i, line in enumerate(lines):
            if line.startswith("COMMAND:"):
                command_text = line.replace("COMMAND:", "").strip()
            elif line.startswith("REASONING:"):
                # Join all remaining lines as reasoning
                reasoning_lines = lines[i:]
                reasoning = " ".join(reasoning_lines).replace("REASONING:", "").strip()
                break
        
        # Fallback if format is unexpected
        if not command_text:
            # Try to find something that looks like a command
            for line in lines:
                if any(cmd in line for cmd in ["git", "npm", "python", "cd", "ls", "mkdir"]):
                    command_text = line.strip()
                    break
            
            if not command_text:
                command_text = "echo 'Unable to generate command'"
        
        if not reasoning:
            reasoning = "Generated command based on the provided objective and context."
        
        return command_text, reasoning
    
    def _parse_analysis_response(self, response: str) -> CommandAnalysis:
        """Parse Gemini's analysis response.
        
        Args:
            response: Raw analysis response from Gemini
        
        Returns:
            CommandAnalysis object
        """
        lines = response.strip().split('\n')
        success = False
        summary = ""
        next_steps = []
        
        for i, line in enumerate(lines):
            if line.startswith("SUCCESS:"):
                success_str = line.replace("SUCCESS:", "").strip().lower()
                success = success_str in ["true", "yes", "1"]
            elif line.startswith("SUMMARY:"):
                summary = line.replace("SUMMARY:", "").strip()
            elif line.startswith("NEXT_STEPS:"):
                # Parse remaining lines as next steps
                for j in range(i + 1, len(lines)):
                    step = lines[j].strip()
                    if step and not step.startswith(("SUCCESS:", "SUMMARY:")):
                        next_steps.append(step.lstrip("- •"))
        
        # Fallback values
        if not summary:
            summary = "Command execution completed" if success else "Command execution failed"
        
        if not next_steps:
            next_steps = ["Continue with the next task"] if success else ["Review and fix the error"]
        
        return CommandAnalysis(
            success=success,
            confidence=0.8 if success else 0.3,
            issues_found=[],
            suggestions=next_steps,
            next_command=None
        )
    
    def get_model_info(self) -> dict[str, Any]:
        """Get information about the current model configuration.
        
        Returns:
            Dictionary with model information
        """
        return {
            "provider": "Google Gemini",
            "model": self._model_name,
            "description": self._model_config["description"],
            "max_tokens": self._model_config["max_tokens"],
            "available": self.is_available(),
        }