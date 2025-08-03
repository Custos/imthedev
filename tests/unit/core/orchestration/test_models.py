"""Unit tests for orchestration data models."""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from imthedev.core.orchestration.models import (
    ObjectiveStatus,
    StepStatus,
    OrchestrationObjective,
    CommandProposal,
    OrchestrationStep,
    TestResults,
    ExecutionResult,
    GeminiAnalysis,
    OrchestrationPlan,
    ExecutionMetadata,
    OrchestrationContext,
    Pattern,
)


def test_orchestration_objective_creation():
    """Test creating an orchestration objective."""
    objective = OrchestrationObjective(
        description="Add user authentication",
        success_criteria=["Login works", "Passwords are hashed"]
    )
    
    assert objective.id is not None
    assert objective.description == "Add user authentication"
    assert len(objective.success_criteria) == 2
    assert objective.status == ObjectiveStatus.PENDING
    assert objective.created_at is not None


def test_objective_status_updates():
    """Test updating objective status."""
    objective = OrchestrationObjective()
    
    assert objective.status == ObjectiveStatus.PENDING
    
    objective.update_status(ObjectiveStatus.IN_PROGRESS)
    assert objective.status == ObjectiveStatus.IN_PROGRESS
    assert objective.updated_at > objective.created_at
    
    objective.update_status(ObjectiveStatus.COMPLETED)
    assert objective.is_complete()


def test_objective_success_criteria():
    """Test adding success criteria."""
    objective = OrchestrationObjective()
    
    objective.add_success_criterion("Tests pass")
    objective.add_success_criterion("Documentation complete")
    
    assert len(objective.success_criteria) == 2
    assert "Tests pass" in objective.success_criteria


def test_command_proposal_confidence():
    """Test command proposal confidence checking."""
    low_confidence = CommandProposal(confidence=0.3)
    assert not low_confidence.is_high_confidence()
    
    high_confidence = CommandProposal(confidence=0.85)
    assert high_confidence.is_high_confidence()


def test_orchestration_step_lifecycle():
    """Test orchestration step state transitions."""
    step = OrchestrationStep(
        objective_id=uuid4(),
        step_number=1,
        command="/sc:test",
        reasoning="Running tests"
    )
    
    assert step.status == StepStatus.PENDING
    
    # Approve step
    step.approve()
    assert step.status == StepStatus.APPROVED
    
    # Start execution
    step.start_execution()
    assert step.status == StepStatus.EXECUTING
    assert step.started_at is not None
    
    # Complete execution
    result = ExecutionResult(command="/sc:test", exit_code=0)
    step.complete_execution(result)
    assert step.status == StepStatus.COMPLETED
    assert step.result == result
    assert step.completed_at is not None
    assert step.duration is not None


def test_step_rejection():
    """Test rejecting an orchestration step."""
    step = OrchestrationStep()
    step.reject()
    assert step.status == StepStatus.REJECTED


def test_step_failure():
    """Test failing an orchestration step."""
    step = OrchestrationStep()
    step.start_execution()
    step.fail_execution("Command not found")
    assert step.status == StepStatus.FAILED
    assert step.completed_at is not None


def test_test_results_calculations():
    """Test TestResults calculations."""
    results = TestResults(
        test_suite="unit",
        tests_passed=10,
        tests_failed=2,
        tests_skipped=1,
        coverage_percentage=85.5
    )
    
    assert results.total_tests == 13
    assert results.success_rate == pytest.approx(10/13)


def test_execution_result_properties():
    """Test ExecutionResult properties."""
    result = ExecutionResult(
        command="/sc:implement feature",
        exit_code=0,
        stdout="Feature implemented",
        stderr="",
        files_created=[Path("new.py")],
        files_modified=[Path("existing.py"), Path("config.json")]
    )
    
    assert result.success
    assert result.has_output
    assert result.file_changes_count == 3


def test_execution_result_failure():
    """Test ExecutionResult failure detection."""
    result = ExecutionResult(exit_code=1)
    assert not result.success


def test_gemini_analysis_methods():
    """Test GeminiAnalysis helper methods."""
    analysis = GeminiAnalysis()
    
    analysis.add_finding("Authentication implemented")
    analysis.add_finding("Tests passing")
    assert len(analysis.key_findings) == 2
    
    analysis.add_missing_element("Documentation")
    assert "Documentation" in analysis.missing_elements
    
    analysis.next_action = "Add documentation"
    analysis.can_continue = True
    assert analysis.is_actionable()


def test_orchestration_plan_management():
    """Test OrchestrationPlan step management."""
    plan = OrchestrationPlan(objective_id=uuid4())
    
    # Add steps
    plan.add_step("/sc:analyze", "Analyze codebase", 60.0)
    plan.add_step("/sc:implement", "Implement feature", 180.0)
    plan.add_step("/sc:test", "Run tests", 120.0)
    
    assert plan.total_steps == 3
    assert plan.estimated_total_time == 360.0
    
    # Get specific step
    step2 = plan.get_step(2)
    assert step2["command"] == "/sc:implement"
    assert step2["step_number"] == 2
    
    # Invalid step number
    assert plan.get_step(0) is None
    assert plan.get_step(10) is None


def test_execution_metadata_enhancement_detection():
    """Test ExecutionMetadata SCF enhancement detection."""
    # Basic metadata without enhancements
    basic = ExecutionMetadata()
    assert not basic.has_enhanced_features()
    
    # Enhanced with personas
    with_persona = ExecutionMetadata(personas_used=["backend"])
    assert with_persona.has_enhanced_features()
    
    # Enhanced with MCP servers
    with_mcp = ExecutionMetadata(mcp_servers_used=["Sequential"])
    assert with_mcp.has_enhanced_features()
    
    # Enhanced with thinking depth
    with_thinking = ExecutionMetadata(thinking_depth="ultrathink")
    assert with_thinking.has_enhanced_features()


def test_orchestration_context_tracking():
    """Test OrchestrationContext state tracking."""
    context = OrchestrationContext(objective_id=uuid4())
    
    # Add commands
    context.add_command("/sc:test1", success=True)
    context.add_command("/sc:test2", success=False)
    context.add_command("/sc:test3", success=True)
    
    assert len(context.command_history) == 3
    assert len(context.successful_commands) == 2
    assert len(context.failed_commands) == 1
    assert context.success_rate == pytest.approx(2/3)
    
    # Add file changes
    context.add_file_change(Path("file1.py"), "created")
    context.add_file_change(Path("file1.py"), "modified")
    context.add_file_change(Path("file2.py"), "created")
    
    assert len(context.file_changes) == 2
    assert len(context.file_changes[Path("file1.py")]) == 2
    
    # Add test results
    test_result = TestResults(tests_passed=10, tests_failed=2)
    context.add_test_result(test_result)
    assert len(context.test_results) == 1
    
    # Add learned pattern
    context.add_learned_pattern("Use --with-tests for better results")
    context.add_learned_pattern("Use --with-tests for better results")  # Duplicate
    assert len(context.learned_patterns) == 1


def test_context_progress_calculation():
    """Test OrchestrationContext progress tracking."""
    context = OrchestrationContext()
    
    # No steps
    assert context.progress == 0.0
    
    # Set steps
    context.current_step = 3
    context.total_steps = 10
    assert context.progress == 0.3
    
    # Complete
    context.current_step = 10
    assert context.progress == 1.0


def test_pattern_matching():
    """Test Pattern matching against objectives."""
    pattern = Pattern(
        name="Authentication Flow",
        trigger=r"auth|login|user.*authentication",
        command_sequence=["/sc:analyze security", "/sc:implement auth"],
        success_rate=0.95
    )
    
    # Should match
    assert pattern.matches("Add user authentication")
    assert pattern.matches("Implement login system")
    assert pattern.matches("Setup auth module")
    
    # Should not match
    assert not pattern.matches("Add payment processing")
    assert not pattern.matches("Optimize performance")


def test_pattern_usage_tracking():
    """Test Pattern usage tracking."""
    pattern = Pattern(name="Test Pattern", success_rate=0.9)
    
    assert pattern.usage_count == 0
    assert pattern.last_used is None
    
    # Use pattern
    pattern.use()
    assert pattern.usage_count == 1
    assert pattern.last_used is not None
    
    # Use again
    first_use = pattern.last_used
    pattern.use()
    assert pattern.usage_count == 2
    assert pattern.last_used >= first_use


def test_pattern_reliability_score():
    """Test Pattern reliability score calculation."""
    # New pattern with high success rate
    new_pattern = Pattern(success_rate=1.0, usage_count=0)
    assert new_pattern.reliability_score == 0.7  # 1.0 * 0.7 + 0 * 0.3
    
    # Used pattern with moderate success
    used_pattern = Pattern(success_rate=0.8, usage_count=5)
    assert used_pattern.reliability_score == pytest.approx(0.8 * 0.7 + 0.5 * 0.3)
    
    # Heavily used pattern
    veteran_pattern = Pattern(success_rate=0.9, usage_count=20)
    assert veteran_pattern.reliability_score == pytest.approx(0.9 * 0.7 + 1.0 * 0.3)