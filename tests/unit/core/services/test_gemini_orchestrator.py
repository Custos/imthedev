"""Unit tests for Gemini orchestrator service."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from imthedev.core.orchestration.models import (
    OrchestrationObjective,
    OrchestrationContext,
    ExecutionResult,
    Pattern,
)
from imthedev.core.services.gemini_orchestrator import GeminiOrchestrator


class MockGeminiAdapter:
    """Mock Gemini adapter for testing."""
    
    def __init__(self):
        self.generate_content = AsyncMock()


@pytest.fixture
def mock_gemini_adapter():
    """Create a mock Gemini adapter."""
    return MockGeminiAdapter()


@pytest.fixture
def orchestrator(mock_gemini_adapter):
    """Create a Gemini orchestrator with mock adapter."""
    return GeminiOrchestrator(gemini_adapter=mock_gemini_adapter)


@pytest.mark.asyncio
async def test_analyze_objective(orchestrator, mock_gemini_adapter):
    """Test analyzing an objective."""
    objective = OrchestrationObjective(
        description="Add user authentication",
        success_criteria=["Login works", "Passwords hashed"]
    )
    
    # Mock Gemini response
    mock_response = json.dumps({
        "complexity": 0.7,
        "dependencies": ["bcrypt", "jwt"],
        "risk_assessment": "Medium complexity with security considerations",
        "steps": [
            {
                "command": "/sc:analyze --focus security",
                "description": "Analyze security requirements",
                "estimated_time": 60.0
            },
            {
                "command": "/sc:implement auth --with-tests",
                "description": "Implement authentication",
                "estimated_time": 180.0
            }
        ]
    })
    mock_gemini_adapter.generate_content.return_value = mock_response
    
    # Analyze objective
    plan = await orchestrator.analyze_objective(objective)
    
    # Verify plan
    assert plan.objective_id == objective.id
    assert plan.complexity_score == 0.7
    assert "bcrypt" in plan.dependencies
    assert plan.total_steps == 2
    assert plan.estimated_total_time == 240.0
    
    # Verify Gemini was called
    mock_gemini_adapter.generate_content.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_objective_with_pattern(orchestrator, mock_gemini_adapter):
    """Test analyzing objective with matching pattern."""
    # Add a pattern
    pattern = Pattern(
        name="Auth Pattern",
        trigger="authentication",
        command_sequence=["/sc:implement auth"],
        success_rate=0.95
    )
    orchestrator.patterns.append(pattern)
    
    objective = OrchestrationObjective(
        description="Add authentication system"
    )
    
    mock_response = json.dumps({
        "complexity": 0.5,
        "dependencies": [],
        "risk_assessment": "Using proven pattern",
        "steps": []
    })
    mock_gemini_adapter.generate_content.return_value = mock_response
    
    await orchestrator.analyze_objective(objective)
    
    # Verify pattern context was included in prompt
    call_args = mock_gemini_adapter.generate_content.call_args[0][0]
    assert "Auth Pattern" in call_args
    assert "95.0%" in call_args


@pytest.mark.asyncio
async def test_propose_command(orchestrator, mock_gemini_adapter):
    """Test proposing a SuperClaude command."""
    context = OrchestrationContext(objective_id=uuid4())
    context.add_command("/sc:analyze", success=True)
    
    # Mock response
    mock_response = json.dumps({
        "command": "/sc:implement feature --with-tests",
        "reasoning": "Implementing based on analysis",
        "confidence": 0.85,
        "alternatives": ["/sc:build feature", "/sc:create feature"],
        "expected_outcome": "Feature implementation with tests",
        "estimated_duration": 120.0
    })
    mock_gemini_adapter.generate_content.return_value = mock_response
    
    # Propose command
    proposal = await orchestrator.propose_command(context, "Implement feature")
    
    # Verify proposal
    assert proposal.command == "/sc:implement feature --with-tests"
    assert proposal.confidence == 0.85
    assert len(proposal.alternatives) == 2
    assert proposal.is_high_confidence()


@pytest.mark.asyncio
async def test_analyze_execution_result_success(orchestrator, mock_gemini_adapter):
    """Test analyzing successful execution result."""
    result = ExecutionResult(
        command="/sc:test",
        exit_code=0,
        stdout="All tests passed",
        execution_time=5.0
    )
    context = OrchestrationContext(objective_id=uuid4())
    
    # Mock response
    mock_response = json.dumps({
        "success": True,
        "understanding": "Tests executed successfully",
        "key_findings": ["All tests passing", "Good coverage"],
        "missing_elements": [],
        "next_action": "Deploy to staging",
        "confidence": 0.9,
        "requires_correction": False,
        "can_continue": True,
        "insights": ["Test-first approach working well"]
    })
    mock_gemini_adapter.generate_content.return_value = mock_response
    
    # Analyze result
    analysis = await orchestrator.analyze_execution_result(result, context)
    
    # Verify analysis
    assert analysis.success
    assert analysis.execution_id == result.execution_id
    assert "All tests passing" in analysis.key_findings
    assert analysis.can_continue
    assert not analysis.requires_correction
    assert analysis.is_actionable()


@pytest.mark.asyncio
async def test_analyze_execution_result_failure(orchestrator, mock_gemini_adapter):
    """Test analyzing failed execution result."""
    result = ExecutionResult(
        command="/sc:test",
        exit_code=1,
        stderr="Test failed: ImportError"
    )
    context = OrchestrationContext(objective_id=uuid4())
    
    # Mock response
    mock_response = json.dumps({
        "success": False,
        "understanding": "Import error in tests",
        "key_findings": ["Missing dependency"],
        "missing_elements": ["pytest module"],
        "next_action": "Install missing dependencies",
        "confidence": 0.8,
        "requires_correction": True,
        "can_continue": True,
        "insights": []
    })
    mock_gemini_adapter.generate_content.return_value = mock_response
    
    # Analyze result
    analysis = await orchestrator.analyze_execution_result(result, context)
    
    # Verify analysis
    assert not analysis.success
    assert analysis.requires_correction
    assert "pytest module" in analysis.missing_elements


@pytest.mark.asyncio
async def test_determine_next_step_continue(orchestrator, mock_gemini_adapter):
    """Test determining next step when can continue."""
    from imthedev.core.orchestration.models import GeminiAnalysis
    
    analysis = GeminiAnalysis(
        success=True,
        can_continue=True,
        next_action="Add documentation"
    )
    context = OrchestrationContext(objective_id=uuid4())
    context.current_step = 2
    context.total_steps = 5
    
    # Mock response
    mock_response = json.dumps({
        "command": "/sc:document --comprehensive",
        "reasoning": "Adding documentation as suggested",
        "confidence": 0.75,
        "alternatives": [],
        "expected_outcome": "Complete documentation"
    })
    mock_gemini_adapter.generate_content.return_value = mock_response
    
    # Determine next step
    proposal = await orchestrator.determine_next_step(analysis, context)
    
    # Verify proposal
    assert proposal is not None
    assert proposal.command == "/sc:document --comprehensive"


@pytest.mark.asyncio
async def test_determine_next_step_complete(orchestrator, mock_gemini_adapter):
    """Test determining next step when objective is complete."""
    from imthedev.core.orchestration.models import GeminiAnalysis
    
    analysis = GeminiAnalysis(
        success=True,
        can_continue=False
    )
    context = OrchestrationContext(objective_id=uuid4())
    
    # Determine next step
    proposal = await orchestrator.determine_next_step(analysis, context)
    
    # Should return None when complete
    assert proposal is None


@pytest.mark.asyncio
async def test_propose_recovery(orchestrator, mock_gemini_adapter):
    """Test proposing recovery strategy."""
    from imthedev.core.orchestration.models import GeminiAnalysis
    
    analysis = GeminiAnalysis(
        success=False,
        understanding="Database connection failed",
        requires_correction=True
    )
    context = OrchestrationContext(objective_id=uuid4())
    context.add_command("/sc:test db", success=False)
    
    # Mock response
    mock_response = json.dumps({
        "command": "/sc:fix database --validate",
        "reasoning": "Fixing database connection issue",
        "confidence": 0.7,
        "alternatives": ["/sc:restart services"],
        "expected_outcome": "Database connection restored"
    })
    mock_gemini_adapter.generate_content.return_value = mock_response
    
    # Propose recovery
    proposal = await orchestrator.propose_recovery(analysis, context)
    
    # Verify recovery proposal
    assert proposal.command == "/sc:fix database --validate"
    assert "database connection" in proposal.reasoning.lower()


@pytest.mark.asyncio
async def test_error_handling_in_analyze(orchestrator, mock_gemini_adapter):
    """Test error handling when Gemini fails."""
    objective = OrchestrationObjective(description="Test")
    
    # Make Gemini fail
    mock_gemini_adapter.generate_content.side_effect = Exception("API Error")
    
    # Should raise the error
    with pytest.raises(Exception) as exc_info:
        await orchestrator.analyze_objective(objective)
    
    assert "API Error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_json_parse_error_fallback(orchestrator, mock_gemini_adapter):
    """Test fallback when JSON parsing fails."""
    context = OrchestrationContext()
    
    # Return invalid JSON
    mock_gemini_adapter.generate_content.return_value = "Not valid JSON"
    
    # Should return fallback proposal
    proposal = await orchestrator.propose_command(context)
    
    assert proposal.command == "/sc:help"
    assert proposal.reasoning == "Parse error"