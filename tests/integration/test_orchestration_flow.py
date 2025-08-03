"""Integration tests for complete orchestration flow."""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from imthedev.core.orchestration.models import (
    OrchestrationObjective,
    OrchestrationContext,
    ExecutionResult,
    ObjectiveStatus,
)
from imthedev.core.services.gemini_orchestrator import GeminiOrchestrator
from imthedev.core.services.claude_executor import ClaudeCodeExecutor
from imthedev.infrastructure.events import (
    orchestration_bus,
    ObjectiveSubmitted,
    CommandProposed,
    CommandApproved,
    ExecutionStarted,
    ExecutionComplete,
    ResultAnalyzed,
)


class MockGeminiAdapter:
    """Mock Gemini adapter for integration testing."""
    
    def __init__(self):
        self.generate_content = AsyncMock()
        self.call_count = 0
    
    async def generate_content_sequence(self, prompt):
        """Generate different responses based on call count."""
        self.call_count += 1
        
        if self.call_count == 1:
            # Initial analysis
            return """{
                "complexity": 0.6,
                "dependencies": ["auth"],
                "risk_assessment": "Medium complexity",
                "steps": [
                    {
                        "command": "/sc:analyze --focus security",
                        "description": "Analyze security",
                        "estimated_time": 60
                    },
                    {
                        "command": "/sc:implement auth",
                        "description": "Implement auth",
                        "estimated_time": 120
                    }
                ]
            }"""
        elif self.call_count == 2:
            # First command proposal
            return """{
                "command": "/sc:analyze --focus security",
                "reasoning": "Security analysis first",
                "confidence": 0.85,
                "alternatives": [],
                "expected_outcome": "Security report"
            }"""
        elif self.call_count == 3:
            # Result analysis
            return """{
                "success": true,
                "understanding": "Analysis complete",
                "key_findings": ["No vulnerabilities"],
                "missing_elements": [],
                "next_action": "Implement auth",
                "confidence": 0.9,
                "requires_correction": false,
                "can_continue": true,
                "insights": []
            }"""
        elif self.call_count == 4:
            # Next step proposal
            return """{
                "command": "/sc:implement auth --with-tests",
                "reasoning": "Implementing authentication",
                "confidence": 0.8,
                "alternatives": [],
                "expected_outcome": "Auth module created"
            }"""
        else:
            # Final analysis - complete
            return """{
                "success": true,
                "understanding": "Auth implemented",
                "key_findings": ["Auth working"],
                "missing_elements": [],
                "next_action": "",
                "confidence": 0.95,
                "requires_correction": false,
                "can_continue": false,
                "insights": ["Pattern learned"]
            }"""


@pytest.fixture
async def orchestration_system():
    """Create a complete orchestration system for testing."""
    # Create mock Gemini adapter
    mock_adapter = MockGeminiAdapter()
    mock_adapter.generate_content = mock_adapter.generate_content_sequence
    
    # Create services
    orchestrator = GeminiOrchestrator(gemini_adapter=mock_adapter)
    executor = ClaudeCodeExecutor()
    
    # Clear event bus
    orchestration_bus.clear_history()
    
    return {
        "orchestrator": orchestrator,
        "executor": executor,
        "bus": orchestration_bus,
        "adapter": mock_adapter
    }


@pytest.mark.asyncio
async def test_complete_orchestration_cycle(orchestration_system):
    """Test a complete orchestration cycle from objective to completion."""
    orchestrator = orchestration_system["orchestrator"]
    bus = orchestration_system["bus"]
    
    # Track events
    events_received = []
    
    async def event_tracker(event):
        events_received.append(event.__class__.__name__)
    
    # Subscribe to all events
    bus.subscribe(ObjectiveSubmitted, event_tracker)
    bus.subscribe(CommandProposed, event_tracker)
    bus.subscribe(ResultAnalyzed, event_tracker)
    
    # Create objective
    objective = OrchestrationObjective(
        description="Add user authentication",
        success_criteria=["Users can log in", "Passwords are secure"]
    )
    
    # Emit objective submitted
    await bus.emit(ObjectiveSubmitted(
        objective_id=objective.id,
        objective_text=objective.description
    ))
    
    # Analyze objective
    plan = await orchestrator.analyze_objective(objective)
    assert plan.total_steps == 2
    assert plan.complexity_score == 0.6
    
    # Create context
    context = OrchestrationContext(objective_id=objective.id)
    context.total_steps = plan.total_steps
    
    # Propose first command
    context.current_step = 1
    proposal1 = await orchestrator.propose_command(context, plan.steps[0]["description"])
    assert proposal1.command == "/sc:analyze --focus security"
    assert proposal1.confidence == 0.85
    
    # Simulate execution result
    result1 = ExecutionResult(
        command=proposal1.command,
        exit_code=0,
        stdout="Security analysis complete",
        execution_time=5.0
    )
    
    # Analyze first result
    analysis1 = await orchestrator.analyze_execution_result(result1, context)
    assert analysis1.success
    assert analysis1.can_continue
    
    # Update context
    context.add_command(proposal1.command, success=True)
    context.current_step = 2
    
    # Determine next step
    proposal2 = await orchestrator.determine_next_step(analysis1, context)
    assert proposal2 is not None
    assert proposal2.command == "/sc:implement auth --with-tests"
    
    # Simulate second execution
    result2 = ExecutionResult(
        command=proposal2.command,
        exit_code=0,
        stdout="Authentication implemented",
        execution_time=10.0,
        files_created=[Path("auth.py"), Path("auth_test.py")]
    )
    
    # Analyze second result
    analysis2 = await orchestrator.analyze_execution_result(result2, context)
    assert analysis2.success
    assert not analysis2.can_continue  # Should be complete
    
    # Update context
    context.add_command(proposal2.command, success=True)
    
    # Check final state
    assert context.success_rate == 1.0
    assert len(context.command_history) == 2
    
    # Wait for events
    await asyncio.sleep(0.01)
    
    # Verify events were emitted
    assert "ObjectiveSubmitted" in events_received
    assert "CommandProposed" in events_received
    assert "ResultAnalyzed" in events_received


@pytest.mark.asyncio
async def test_error_recovery_flow(orchestration_system):
    """Test orchestration with error recovery."""
    orchestrator = orchestration_system["orchestrator"]
    
    # Create context with failed command
    context = OrchestrationContext(objective_id=uuid4())
    context.add_command("/sc:test", success=False)
    
    # Create failure analysis
    from imthedev.core.orchestration.models import GeminiAnalysis
    failure_analysis = GeminiAnalysis(
        success=False,
        understanding="Test failed due to missing dependency",
        requires_correction=True,
        can_continue=True
    )
    
    # Mock recovery response
    orchestration_system["adapter"].generate_content = AsyncMock(
        return_value="""{
            "command": "/sc:fix dependencies --validate",
            "reasoning": "Installing missing dependencies",
            "confidence": 0.7,
            "alternatives": ["/sc:install deps"],
            "expected_outcome": "Dependencies fixed"
        }"""
    )
    
    # Propose recovery
    recovery = await orchestrator.propose_recovery(failure_analysis, context)
    
    assert recovery.command == "/sc:fix dependencies --validate"
    assert "missing dependencies" in recovery.reasoning.lower()
    assert recovery.confidence == 0.7


@pytest.mark.asyncio
async def test_event_bus_integration(orchestration_system):
    """Test event bus integration between services."""
    bus = orchestration_system["bus"]
    
    # Track execution flow
    execution_flow = []
    
    async def track_execution(event):
        execution_flow.append(event.command)
    
    async def track_completion(event):
        execution_flow.append(f"Complete: {event.exit_code}")
    
    # Subscribe to events
    bus.subscribe(ExecutionStarted, track_execution)
    bus.subscribe(ExecutionComplete, track_completion)
    
    # Emit execution events
    test_id = uuid4()
    await bus.emit(ExecutionStarted(
        execution_id=test_id,
        command="/sc:test"
    ))
    
    await bus.emit(ExecutionComplete(
        execution_id=test_id,
        command="/sc:test",
        exit_code=0
    ))
    
    # Wait for processing
    await asyncio.sleep(0.01)
    
    # Verify flow
    assert "/sc:test" in execution_flow
    assert "Complete: 0" in execution_flow


@pytest.mark.asyncio
async def test_command_validation_integration(orchestration_system):
    """Test command validation between orchestrator and executor."""
    executor = orchestration_system["executor"]
    
    # Valid commands from orchestrator patterns
    valid_commands = [
        "/sc:analyze --think",
        "/sc:implement feature --persona-backend --with-tests",
        "/sc:test --comprehensive",
        "/sc:improve --performance --seq",
        "/sc:git --smart-commit"
    ]
    
    for cmd in valid_commands:
        assert await executor.validate_command(cmd), f"Should validate: {cmd}"
    
    # Invalid commands that orchestrator shouldn't generate
    invalid_commands = [
        "/sc:invalid_command",
        "sc test",  # Missing colon
        "/sc:test --invalid-flag",
    ]
    
    for cmd in invalid_commands:
        assert not await executor.validate_command(cmd), f"Should not validate: {cmd}"


@pytest.mark.asyncio
async def test_metadata_extraction_integration(orchestration_system):
    """Test SCF metadata extraction from execution output."""
    executor = orchestration_system["executor"]
    bus = orchestration_system["bus"]
    
    # Track metadata events
    metadata_events = []
    
    async def track_metadata(event):
        metadata_events.append(event)
    
    from imthedev.infrastructure.events import MetadataExtracted
    bus.subscribe(MetadataExtracted, track_metadata)
    
    # Sample SCF-enhanced output
    scf_output = """
    SCF Version: 1.5.0
    Command: /sc:implement auth --persona-backend --persona-security
    Using --think-hard for complex analysis
    MCP Servers: --seq --c7 enabled
    
    Performance Metrics:
    - Execution: 2500ms
    - Memory: 128MB
    - Cache hits: 95%
    
    Files created: auth.py, auth_test.py
    Tests: 15 passed, 0 failed
    """
    
    # Extract metadata
    metadata = await executor.extract_metadata(scf_output)
    
    # Verify extraction
    assert metadata.scf_version == "1.5.0"
    assert "backend" in metadata.personas_used
    assert "security" in metadata.personas_used
    assert metadata.thinking_depth == "think-hard"
    assert "Sequential" in metadata.mcp_servers_used
    assert "Context7" in metadata.mcp_servers_used
    assert metadata.performance_metrics["execution"] == 2500.0
    assert metadata.has_enhanced_features()
    
    # Wait for event
    await asyncio.sleep(0.01)
    
    # Verify metadata event was emitted
    assert len(metadata_events) > 0


@pytest.mark.asyncio
async def test_pattern_learning_integration(orchestration_system):
    """Test pattern learning from successful orchestrations."""
    orchestrator = orchestration_system["orchestrator"]
    
    # Add a learned pattern
    from imthedev.core.orchestration.models import Pattern
    auth_pattern = Pattern(
        name="Authentication Flow",
        trigger=r"auth|login|user.*authentication",
        command_sequence=[
            "/sc:analyze --focus security",
            "/sc:implement auth --with-tests",
            "/sc:test auth"
        ],
        success_rate=0.92,
        usage_count=5
    )
    orchestrator.patterns.append(auth_pattern)
    
    # Create similar objective
    objective = OrchestrationObjective(
        description="Setup user login system"
    )
    
    # Mock response that acknowledges pattern
    orchestration_system["adapter"].generate_content = AsyncMock(
        return_value="""{
            "complexity": 0.5,
            "dependencies": ["auth"],
            "risk_assessment": "Using proven pattern",
            "steps": [
                {
                    "command": "/sc:analyze --focus security",
                    "description": "Security analysis",
                    "estimated_time": 30
                }
            ]
        }"""
    )
    
    # Analyze with pattern
    plan = await orchestrator.analyze_objective(objective)
    
    # Verify pattern influence
    assert plan.complexity_score == 0.5  # Lower due to pattern
    assert "proven pattern" in plan.risk_assessment.lower()
    
    # Pattern should match
    assert auth_pattern.matches(objective.description)


@pytest.mark.asyncio
async def test_context_persistence_integration(orchestration_system):
    """Test context persistence across orchestration steps."""
    context = OrchestrationContext(objective_id=uuid4())
    
    # Simulate multi-step orchestration
    commands = [
        "/sc:analyze",
        "/sc:implement feature",
        "/sc:test",
        "/sc:document"
    ]
    
    files_modified = [
        Path("main.py"),
        Path("feature.py"),
        Path("test_feature.py"),
        Path("README.md")
    ]
    
    # Execute steps
    for i, cmd in enumerate(commands):
        # Add command
        success = i != 1  # Fail second command
        context.add_command(cmd, success=success)
        
        # Add file changes
        if i < len(files_modified):
            context.add_file_change(files_modified[i], "created" if i % 2 == 0 else "modified")
        
        # Update progress
        context.current_step = i + 1
        context.total_steps = len(commands)
    
    # Add test results
    from imthedev.core.orchestration.models import TestResults
    context.add_test_result(TestResults(
        tests_passed=10,
        tests_failed=1,
        coverage_percentage=85.0
    ))
    
    # Add learned pattern
    context.add_learned_pattern("Use --with-tests for better coverage")
    
    # Verify context state
    assert len(context.command_history) == 4
    assert len(context.successful_commands) == 3
    assert len(context.failed_commands) == 1
    assert context.success_rate == 0.75
    assert len(context.file_changes) == 4
    assert len(context.test_results) == 1
    assert len(context.learned_patterns) == 1
    assert context.progress == 1.0