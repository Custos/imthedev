"""Unit tests for Claude Code executor service."""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from imthedev.core.services.claude_executor import ClaudeCodeExecutor
from imthedev.core.orchestration.models import TestResults


@pytest.fixture
def executor():
    """Create a Claude Code executor for testing."""
    return ClaudeCodeExecutor(
        claude_binary="claude",
        working_directory=Path("/tmp/test"),
        timeout=10.0
    )


@pytest.mark.asyncio
async def test_validate_command_valid(executor):
    """Test validating valid SC commands."""
    # Valid commands
    assert await executor.validate_command("/sc:test")
    assert await executor.validate_command("sc:implement feature")
    assert await executor.validate_command("/sc:analyze --think")
    assert await executor.validate_command("/sc:build --persona-backend --with-tests")
    
    # Valid with multiple flags
    assert await executor.validate_command(
        "/sc:implement auth --persona-security --think-hard --with-tests"
    )


@pytest.mark.asyncio
async def test_validate_command_invalid(executor):
    """Test rejecting invalid SC commands."""
    # Invalid command format
    assert not await executor.validate_command("test")
    assert not await executor.validate_command("/test")
    assert not await executor.validate_command("sc test")
    
    # Unknown command type
    assert not await executor.validate_command("/sc:unknown")
    assert not await executor.validate_command("/sc:random_command")
    
    # Invalid flags
    assert not await executor.validate_command("/sc:test --invalid-flag")
    assert not await executor.validate_command("/sc:build --not-a-real-flag")


def test_extract_command_type(executor):
    """Test extracting command type from SC commands."""
    assert executor._extract_command_type("/sc:test") == "test"
    assert executor._extract_command_type("sc:implement") == "implement"
    assert executor._extract_command_type("/sc:analyze --flags") == "analyze"
    assert executor._extract_command_type("invalid") == ""


def test_prepare_command(executor):
    """Test preparing commands for subprocess execution."""
    # Basic command
    cmd = executor._prepare_command("/sc:test")
    assert "claude" in cmd
    assert "test" in cmd
    assert "SCF_ENABLED=1" in cmd
    
    # Command with flags
    cmd = executor._prepare_command("/sc:build --with-tests")
    assert "build --with-tests" in cmd
    
    # Command without prefix
    cmd = executor._prepare_command("sc:analyze")
    assert "analyze" in cmd


def test_is_valid_flag(executor):
    """Test flag validation."""
    # Valid flags
    assert executor._is_valid_flag("--think")
    assert executor._is_valid_flag("--persona-backend")
    assert executor._is_valid_flag("--with-tests")
    assert executor._is_valid_flag("--seq")
    
    # Parameterized flags
    assert executor._is_valid_flag("--persona-scribe=en")
    assert executor._is_valid_flag("--iterations=5")
    assert executor._is_valid_flag("--scope=module")
    
    # Invalid flags
    assert not executor._is_valid_flag("--invalid")
    assert not executor._is_valid_flag("--random-flag")


def test_parse_test_results(executor):
    """Test parsing test results from output."""
    # Pattern 1: "X passed, Y failed, Z skipped"
    line1 = "Tests: 12 passed, 2 failed, 1 skipped"
    result1 = executor._parse_test_results(line1)
    assert result1.tests_passed == 12
    assert result1.tests_failed == 2
    assert result1.tests_skipped == 1
    
    # Pattern 2: "Tests: X/Y passing (Z%)"
    line2 = "Tests: 10/12 passing (83.3%)"
    result2 = executor._parse_test_results(line2)
    assert result2.tests_passed == 10
    assert result2.tests_failed == 2
    assert result2.coverage_percentage == 83.3
    
    # No match
    line3 = "Running tests now"
    result3 = executor._parse_test_results(line3)
    assert result3 is None


def test_parse_progress(executor):
    """Test parsing progress information."""
    # Pattern 1: "Progress: X% - message"
    line1 = "Progress: 75% - Building components"
    progress1 = executor._parse_progress(line1)
    assert progress1[1] == 75.0
    assert progress1[2] == "Building components"
    
    # Pattern 2: "[X%] message"
    line2 = "[45%] Analyzing files"
    progress2 = executor._parse_progress(line2)
    assert progress2[1] == 45.0
    assert progress2[2] == "Analyzing files"
    
    # No match
    line3 = "Working on task"
    progress3 = executor._parse_progress(line3)
    assert progress3 is None


@pytest.mark.asyncio
async def test_extract_metadata(executor):
    """Test extracting SCF metadata from output."""
    output = """
    SCF Version: 1.2.3
    Using --persona-backend --persona-security
    MCP: --seq --c7 enabled
    --ultrathink mode active
    Performance: execution: 1234ms, memory: 45.6%
    """
    
    metadata = await executor.extract_metadata(output)
    
    assert metadata.scf_version == "1.2.3"
    assert "backend" in metadata.personas_used
    assert "security" in metadata.personas_used
    assert "Sequential" in metadata.mcp_servers_used
    assert "Context7" in metadata.mcp_servers_used
    assert metadata.thinking_depth == "ultrathink"
    assert metadata.performance_metrics["execution"] == 1234.0
    assert metadata.has_enhanced_features()


@pytest.mark.asyncio
async def test_execute_command_mock(executor):
    """Test command execution with mocked subprocess."""
    with patch('asyncio.create_subprocess_shell') as mock_subprocess:
        # Create mock process
        mock_process = AsyncMock()
        mock_process.stdout.readline = AsyncMock()
        mock_process.stderr.readline = AsyncMock()
        mock_process.wait = AsyncMock(return_value=0)
        
        # Set up readline to return output then empty
        outputs = [
            b"Starting execution\n",
            b"Progress: 50% - Working\n",
            b"Tests: 5 passed, 0 failed, 0 skipped\n",
            b"Complete\n",
            b""  # End of output
        ]
        mock_process.stdout.readline.side_effect = outputs
        
        mock_subprocess.return_value = mock_process
        
        # Execute command
        output_lines = []
        async for line in executor.execute_command("/sc:test"):
            output_lines.append(line)
        
        # Verify output
        assert len(output_lines) == 4
        assert "Starting execution" in output_lines[0]
        assert "Progress: 50%" in output_lines[1]
        assert "Complete" in output_lines[3]
        
        # Verify subprocess was called correctly
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert "claude" in call_args
        assert "test" in call_args


@pytest.mark.asyncio
async def test_execute_command_timeout(executor):
    """Test command execution timeout."""
    executor.default_timeout = 0.01  # Very short timeout
    
    with patch('asyncio.create_subprocess_shell') as mock_subprocess:
        # Create mock process that never completes
        mock_process = AsyncMock()
        mock_process.stdout.readline = AsyncMock()
        
        # Simulate slow output
        async def slow_readline():
            await asyncio.sleep(1.0)  # Longer than timeout
            return b"output\n"
        
        mock_process.stdout.readline.side_effect = slow_readline
        mock_process.wait = AsyncMock()
        mock_subprocess.return_value = mock_process
        
        # Should timeout
        with pytest.raises(asyncio.TimeoutError):
            async for _ in executor.execute_command("/sc:test", timeout=0.01):
                pass


@pytest.mark.asyncio
async def test_cancel_execution(executor):
    """Test cancelling execution."""
    with patch('asyncio.create_subprocess_shell') as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.terminate = AsyncMock()
        mock_process.kill = AsyncMock()
        mock_process.wait = AsyncMock()
        
        mock_subprocess.return_value = mock_process
        executor.current_process = mock_process
        
        # Cancel execution
        await executor.cancel_execution()
        
        # Verify process was terminated
        mock_process.terminate.assert_called_once()


@pytest.mark.asyncio
async def test_parse_output_events(executor):
    """Test parsing special events from output."""
    executor.execution_id = uuid4()
    
    # Mock event bus
    with patch('imthedev.core.services.claude_executor.orchestration_bus') as mock_bus:
        mock_bus.emit = AsyncMock()
        
        # Test file creation detection
        await executor._parse_output_events("Created: /path/to/file.py")
        
        # Verify FileCreated event was emitted
        calls = mock_bus.emit.call_args_list
        assert any(
            "FileCreated" in str(call)
            for call in calls
        )
        
        # Test file modification detection
        await executor._parse_output_events("Modified: /path/to/config.json")
        
        # Test test results detection
        await executor._parse_output_events("Tests: 10 tests passed, 0 failed")


@pytest.mark.asyncio
async def test_get_execution_result_no_execution(executor):
    """Test getting execution result without active execution."""
    with pytest.raises(RuntimeError) as exc_info:
        await executor.get_execution_result()
    
    assert "No execution in progress" in str(exc_info.value)