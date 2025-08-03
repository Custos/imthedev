"""Gemini orchestrator service for AI-driven command generation.

This service manages Gemini's role as the orchestrator, analyzing objectives,
proposing SuperClaude commands, and interpreting execution results.
"""

import asyncio
import json
import logging
import re
from typing import AsyncIterator, Optional

from imthedev.core.orchestration.models import (
    CommandProposal,
    GeminiAnalysis,
    OrchestrationContext,
    OrchestrationObjective,
    OrchestrationPlan,
    Pattern,
)
from imthedev.infrastructure.events import (
    CommandProposed,
    NextStepProposed,
    ObjectiveAnalyzed,
    PlanGenerated,
    RecoveryProposed,
    ResultAnalyzed,
    orchestration_bus,
)

logger = logging.getLogger(__name__)


class GeminiOrchestrator:
    """Manages Gemini's orchestration logic for dual-AI coordination.
    
    This service coordinates with Gemini to:
    - Analyze user objectives
    - Generate execution plans
    - Propose SuperClaude commands
    - Interpret execution results
    - Determine next steps
    """
    
    def __init__(self, gemini_adapter: Optional["GeminiAdapter"] = None) -> None:
        """Initialize the Gemini orchestrator.
        
        Args:
            gemini_adapter: Optional Gemini API adapter for testing
        """
        self.gemini_adapter = gemini_adapter
        self.context_manager: Optional[OrchestrationContext] = None
        self.patterns: list[Pattern] = []
        self._init_gemini()
    
    def _init_gemini(self) -> None:
        """Initialize Gemini adapter if not provided."""
        if not self.gemini_adapter:
            from imthedev.core.services.gemini_adapter import GeminiAdapter
            self.gemini_adapter = GeminiAdapter()
    
    async def analyze_objective(
        self, objective: OrchestrationObjective
    ) -> OrchestrationPlan:
        """Analyze an objective and generate execution plan.
        
        Args:
            objective: The user's objective to analyze
            
        Returns:
            Orchestration plan with steps
        """
        logger.info(f"Analyzing objective: {objective.description}")
        
        # Check for matching patterns first
        matching_pattern = self._find_matching_pattern(objective.description)
        
        prompt = self._build_analysis_prompt(objective, matching_pattern)
        
        try:
            response = await self.gemini_adapter.generate_content(prompt)
            plan = self._parse_plan_response(response, objective)
            
            # Emit analysis event
            await orchestration_bus.emit(
                ObjectiveAnalyzed(
                    objective_id=objective.id,
                    analysis=plan.risk_assessment,
                    estimated_steps=plan.total_steps,
                    complexity_score=plan.complexity_score,
                    suggested_approach="Pattern-based" if matching_pattern else "Discovery",
                    required_capabilities=plan.dependencies,
                )
            )
            
            # Emit plan generated event
            await orchestration_bus.emit(
                PlanGenerated(
                    objective_id=objective.id,
                    plan_steps=plan.steps,
                    total_estimated_time=plan.estimated_total_time,
                    dependencies=plan.dependencies,
                    risk_assessment=plan.risk_assessment,
                )
            )
            
            return plan
            
        except Exception as e:
            logger.error(f"Failed to analyze objective: {e}")
            raise
    
    async def propose_command(
        self, context: OrchestrationContext, step_description: str = ""
    ) -> CommandProposal:
        """Generate next SuperClaude command based on context.
        
        Args:
            context: Current orchestration context
            step_description: Optional description of the step
            
        Returns:
            Proposed command with reasoning
        """
        logger.info(f"Proposing command for step {context.current_step}")
        
        prompt = self._build_command_prompt(context, step_description)
        
        try:
            response = await self.gemini_adapter.generate_content(prompt)
            proposal = self._parse_command_response(response)
            
            # Emit command proposed event
            await orchestration_bus.emit(
                CommandProposed(
                    command_text=proposal.command,
                    reasoning=proposal.reasoning,
                    confidence=proposal.confidence,
                    alternatives=proposal.alternatives,
                    context_used=self._summarize_context(context),
                )
            )
            
            return proposal
            
        except Exception as e:
            logger.error(f"Failed to propose command: {e}")
            raise
    
    async def analyze_execution_result(
        self, result: "ExecutionResult", context: OrchestrationContext
    ) -> GeminiAnalysis:
        """Analyze Claude Code execution results.
        
        Args:
            result: Execution result from Claude Code
            context: Current orchestration context
            
        Returns:
            Analysis of the execution
        """
        logger.info(f"Analyzing execution result for: {result.command}")
        
        prompt = self._build_analysis_prompt_for_result(result, context)
        
        try:
            response = await self.gemini_adapter.generate_content(prompt)
            analysis = self._parse_analysis_response(response, result)
            
            # Emit result analyzed event
            await orchestration_bus.emit(
                ResultAnalyzed(
                    objective_id=context.objective_id,
                    execution_id=result.execution_id,
                    success=analysis.success,
                    understanding=analysis.understanding,
                    missing_elements=analysis.missing_elements,
                    next_action=analysis.next_action,
                    confidence=analysis.confidence,
                )
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze result: {e}")
            raise
    
    async def determine_next_step(
        self, analysis: GeminiAnalysis, context: OrchestrationContext
    ) -> Optional[CommandProposal]:
        """Determine next orchestration step based on analysis.
        
        Args:
            analysis: Analysis of previous execution
            context: Current orchestration context
            
        Returns:
            Next command proposal or None if complete
        """
        logger.info("Determining next orchestration step")
        
        # Check if objective is complete
        if not analysis.can_continue or context.current_step >= context.total_steps:
            logger.info("Objective appears complete or cannot continue")
            return None
        
        # Generate recovery if needed
        if analysis.requires_correction:
            return await self.propose_recovery(analysis, context)
        
        # Propose next step
        prompt = self._build_next_step_prompt(analysis, context)
        
        try:
            response = await self.gemini_adapter.generate_content(prompt)
            proposal = self._parse_command_response(response)
            
            # Emit next step event
            await orchestration_bus.emit(
                NextStepProposed(
                    objective_id=context.objective_id,
                    step_number=context.current_step + 1,
                    next_command=proposal.command,
                    reasoning=proposal.reasoning,
                    alternatives=proposal.alternatives,
                    expected_outcome=proposal.expected_outcome,
                )
            )
            
            return proposal
            
        except Exception as e:
            logger.error(f"Failed to determine next step: {e}")
            return None
    
    async def propose_recovery(
        self, analysis: GeminiAnalysis, context: OrchestrationContext
    ) -> CommandProposal:
        """Propose recovery strategy for failed execution.
        
        Args:
            analysis: Analysis showing failure
            context: Current orchestration context
            
        Returns:
            Recovery command proposal
        """
        logger.info("Proposing recovery strategy")
        
        prompt = self._build_recovery_prompt(analysis, context)
        
        try:
            response = await self.gemini_adapter.generate_content(prompt)
            proposal = self._parse_command_response(response)
            
            # Emit recovery event
            await orchestration_bus.emit(
                RecoveryProposed(
                    objective_id=context.objective_id,
                    error_context=analysis.understanding,
                    recovery_strategy=proposal.reasoning,
                    recovery_commands=[proposal.command] + proposal.alternatives,
                    success_probability=proposal.confidence,
                )
            )
            
            return proposal
            
        except Exception as e:
            logger.error(f"Failed to propose recovery: {e}")
            raise
    
    def _find_matching_pattern(self, objective: str) -> Optional[Pattern]:
        """Find a pattern matching the objective.
        
        Args:
            objective: Objective description
            
        Returns:
            Matching pattern or None
        """
        for pattern in sorted(self.patterns, key=lambda p: p.reliability_score, reverse=True):
            if pattern.matches(objective):
                logger.info(f"Found matching pattern: {pattern.name}")
                return pattern
        return None
    
    def _build_analysis_prompt(
        self, objective: OrchestrationObjective, pattern: Optional[Pattern] = None
    ) -> str:
        """Build prompt for objective analysis.
        
        Args:
            objective: Objective to analyze
            pattern: Optional matching pattern
            
        Returns:
            Prompt for Gemini
        """
        pattern_context = ""
        if pattern:
            pattern_context = f"""
            I found a similar pattern that worked before:
            Pattern: {pattern.name}
            Commands used: {', '.join(pattern.command_sequence)}
            Success rate: {pattern.success_rate:.1%}
            """
        
        return f"""
        Analyze this development objective and create an execution plan using SuperClaude commands.
        
        Objective: {objective.description}
        Success Criteria:
        {chr(10).join(f"- {c}" for c in objective.success_criteria)}
        
        {pattern_context}
        
        Please provide:
        1. Complexity assessment (0-1 score)
        2. Required capabilities and dependencies
        3. Step-by-step plan with SC commands
        4. Risk assessment
        5. Estimated time for each step
        
        Focus on using SuperClaude Framework commands like:
        - /sc:analyze - for analysis and understanding
        - /sc:implement - for creating features
        - /sc:test - for testing
        - /sc:improve - for optimization
        
        Include appropriate flags like --think, --persona-backend, --with-tests, etc.
        
        Respond in JSON format.
        """
    
    def _build_command_prompt(
        self, context: OrchestrationContext, step_description: str
    ) -> str:
        """Build prompt for command generation.
        
        Args:
            context: Current context
            step_description: Step description
            
        Returns:
            Prompt for Gemini
        """
        history = "\n".join(context.command_history[-5:]) if context.command_history else "None"
        files = ", ".join(str(p) for p in list(context.file_changes.keys())[-10:])
        
        return f"""
        Generate the next SuperClaude command for this orchestration step.
        
        Current Step: {context.current_step}/{context.total_steps}
        Step Description: {step_description}
        
        Recent Command History:
        {history}
        
        Recent File Changes:
        {files or "None"}
        
        Current Success Rate: {context.success_rate:.1%}
        
        Generate a specific SC command with appropriate flags and personas.
        Consider using:
        - Thinking flags (--think, --think-hard) for complex tasks
        - Personas (--persona-backend, --persona-frontend, etc.) for specialized work
        - MCP servers (--seq, --c7, --magic) for enhanced capabilities
        - Testing flags (--with-tests) for quality assurance
        
        Provide:
        1. The exact command to run
        2. Reasoning for this command
        3. Confidence score (0-1)
        4. 2-3 alternative commands
        5. Expected outcome
        
        Respond in JSON format.
        """
    
    def _build_analysis_prompt_for_result(
        self, result: "ExecutionResult", context: OrchestrationContext
    ) -> str:
        """Build prompt for result analysis.
        
        Args:
            result: Execution result
            context: Current context
            
        Returns:
            Prompt for Gemini
        """
        output_preview = result.stdout[:1000] if result.stdout else result.stderr[:1000]
        
        return f"""
        Analyze this SuperClaude command execution result.
        
        Command Executed: {result.command}
        Exit Code: {result.exit_code}
        Execution Time: {result.execution_time:.2f}s
        Files Created: {len(result.files_created)}
        Files Modified: {len(result.files_modified)}
        
        Output Preview:
        {output_preview}
        
        Test Results: {result.tests_run.success_rate:.1%} passing if result.tests_run else "No tests run"}
        
        Context:
        - Step {context.current_step}/{context.total_steps}
        - Overall Success Rate: {context.success_rate:.1%}
        
        Analyze and provide:
        1. Was the execution successful?
        2. Your understanding of what happened
        3. Key findings from the output
        4. Any missing elements or issues
        5. Suggested next action
        6. Confidence in the analysis (0-1)
        7. Does this require correction?
        8. Can we continue to next step?
        9. Any insights learned
        
        Respond in JSON format.
        """
    
    def _build_next_step_prompt(
        self, analysis: GeminiAnalysis, context: OrchestrationContext
    ) -> str:
        """Build prompt for next step determination.
        
        Args:
            analysis: Previous analysis
            context: Current context
            
        Returns:
            Prompt for Gemini
        """
        return f"""
        Based on the previous execution analysis, propose the next SuperClaude command.
        
        Previous Analysis:
        - Success: {analysis.success}
        - Understanding: {analysis.understanding}
        - Missing Elements: {', '.join(analysis.missing_elements) or 'None'}
        - Suggested Action: {analysis.next_action}
        
        Current Progress: {context.current_step}/{context.total_steps} ({context.progress:.1%})
        
        Generate the next SC command that builds on what we've accomplished.
        Consider the missing elements and suggested action.
        
        Provide the same JSON format as before with command, reasoning, etc.
        """
    
    def _build_recovery_prompt(
        self, analysis: GeminiAnalysis, context: OrchestrationContext
    ) -> str:
        """Build prompt for recovery strategy.
        
        Args:
            analysis: Failure analysis
            context: Current context
            
        Returns:
            Prompt for Gemini
        """
        failed_command = context.failed_commands[-1] if context.failed_commands else "Unknown"
        
        return f"""
        The previous command failed and needs recovery.
        
        Failed Command: {failed_command}
        Failure Analysis: {analysis.understanding}
        Missing Elements: {', '.join(analysis.missing_elements)}
        
        Recent Successful Commands:
        {chr(10).join(context.successful_commands[-3:])}
        
        Propose a recovery strategy using SuperClaude commands.
        Consider:
        - Rolling back changes if needed
        - Fixing the specific issues identified
        - Alternative approaches to achieve the goal
        - Using --safe-mode or --validate flags
        
        Provide the recovery command in the standard JSON format.
        """
    
    def _parse_plan_response(
        self, response: str, objective: OrchestrationObjective
    ) -> OrchestrationPlan:
        """Parse Gemini's plan response.
        
        Args:
            response: JSON response from Gemini
            objective: Related objective
            
        Returns:
            Orchestration plan
        """
        try:
            data = json.loads(response)
            plan = OrchestrationPlan(objective_id=objective.id)
            
            plan.complexity_score = data.get("complexity", 0.5)
            plan.dependencies = data.get("dependencies", [])
            plan.risk_assessment = data.get("risk_assessment", "")
            
            for step in data.get("steps", []):
                plan.add_step(
                    command=step.get("command", ""),
                    description=step.get("description", ""),
                    estimated_time=step.get("estimated_time", 60.0)
                )
            
            return plan
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse plan response: {e}")
            # Return a basic plan
            plan = OrchestrationPlan(objective_id=objective.id)
            plan.add_step("/sc:analyze .", "Initial analysis", 60.0)
            return plan
    
    def _parse_command_response(self, response: str) -> CommandProposal:
        """Parse Gemini's command response.
        
        Args:
            response: JSON response from Gemini
            
        Returns:
            Command proposal
        """
        try:
            data = json.loads(response)
            return CommandProposal(
                command=data.get("command", ""),
                reasoning=data.get("reasoning", ""),
                confidence=data.get("confidence", 0.5),
                alternatives=data.get("alternatives", []),
                expected_outcome=data.get("expected_outcome", ""),
                estimated_duration=data.get("estimated_duration", 60.0)
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse command response: {e}")
            return CommandProposal(command="/sc:help", reasoning="Parse error")
    
    def _parse_analysis_response(
        self, response: str, result: "ExecutionResult"
    ) -> GeminiAnalysis:
        """Parse Gemini's analysis response.
        
        Args:
            response: JSON response from Gemini
            result: Related execution result
            
        Returns:
            Gemini analysis
        """
        try:
            data = json.loads(response)
            analysis = GeminiAnalysis(execution_id=result.execution_id)
            
            analysis.success = data.get("success", False)
            analysis.understanding = data.get("understanding", "")
            analysis.key_findings = data.get("key_findings", [])
            analysis.missing_elements = data.get("missing_elements", [])
            analysis.next_action = data.get("next_action", "")
            analysis.confidence = data.get("confidence", 0.5)
            analysis.requires_correction = data.get("requires_correction", False)
            analysis.can_continue = data.get("can_continue", True)
            analysis.learned_insights = data.get("insights", [])
            
            return analysis
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse analysis response: {e}")
            return GeminiAnalysis(
                execution_id=result.execution_id,
                success=result.success,
                understanding="Parse error in analysis"
            )
    
    def _summarize_context(self, context: OrchestrationContext) -> str:
        """Summarize context for event metadata.
        
        Args:
            context: Context to summarize
            
        Returns:
            Context summary string
        """
        return (
            f"Step {context.current_step}/{context.total_steps}, "
            f"{len(context.command_history)} commands, "
            f"{len(context.file_changes)} files changed, "
            f"{context.success_rate:.1%} success rate"
        )