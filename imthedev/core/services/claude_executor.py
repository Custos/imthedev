"""Claude Code executor service for SuperClaude command execution.

This service manages the execution of SuperClaude commands through the
Claude Code CLI with SCF (SuperClaude Framework) enhancements.
"""

import asyncio
import json
import logging
import os
import re
import shlex
from pathlib import Path
from typing import AsyncIterator, Optional

from imthedev.core.orchestration.models import (
    ExecutionMetadata,
    ExecutionResult,
    TestResults,
)
from imthedev.infrastructure.events import (
    ExecutionComplete,
    ExecutionFailed,
    ExecutionProgress,
    ExecutionStarted,
    FileCreated,
    FileModified,
    MetadataExtracted,
    OutputStreaming,
    TestExecuted,
    orchestration_bus,
)

logger = logging.getLogger(__name__)


class ClaudeCodeExecutor:
    """Manages Claude Code terminal execution with SCF support.
    
    This service executes SuperClaude commands through the Claude Code CLI,
    captures real-time output, and extracts SCF-enhanced metadata.
    """
    
    def __init__(
        self,
        claude_binary: str = "claude",
        working_directory: Optional[Path] = None,
        timeout: float = 300.0
    ) -> None:
        """Initialize the Claude Code executor.
        
        Args:
            claude_binary: Path to Claude Code CLI binary
            working_directory: Working directory for command execution
            timeout: Default timeout for command execution in seconds
        """
        self.claude_binary = claude_binary
        self.working_directory = working_directory or Path.cwd()
        self.default_timeout = timeout
        self.current_process: Optional[asyncio.subprocess.Process] = None
        self.execution_id = None
    
    async def execute_command(
        self,
        command: str,
        timeout: Optional[float] = None
    ) -> AsyncIterator[str]:
        """Stream execution of a SuperClaude command.
        
        Args:
            command: SC command to execute
            timeout: Optional timeout override
            
        Yields:
            Output lines from Claude Code
        """
        from uuid import uuid4
        
        self.execution_id = uuid4()
        timeout = timeout or self.default_timeout
        
        logger.info(f"Executing SC command: {command}")
        
        # Validate command
        if not await self.validate_command(command):
            raise ValueError(f"Invalid SC command: {command}")
        
        # Emit execution started event
        await orchestration_bus.emit(
            ExecutionStarted(
                execution_id=self.execution_id,
                command=command,
                working_directory=str(self.working_directory),
                environment=dict(os.environ),
                timeout=timeout,
            )
        )
        
        # Prepare command for subprocess
        full_command = self._prepare_command(command)
        
        try:
            # Start the subprocess
            self.current_process = await asyncio.create_subprocess_shell(
                full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_directory,
            )
            
            # Stream output
            start_time = asyncio.get_event_loop().time()
            
            async for line in self._stream_output():
                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    await self._kill_process()
                    raise asyncio.TimeoutError(f"Command timed out after {timeout}s")
                
                # Emit streaming event
                await orchestration_bus.emit(
                    OutputStreaming(
                        execution_id=self.execution_id,
                        command=command,
                        output_type="stdout",
                        content=line,
                        timestamp_offset=elapsed,
                    )
                )
                
                # Parse for special events
                await self._parse_output_events(line)
                
                yield line
            
            # Wait for process to complete
            return_code = await self.current_process.wait()
            
            # Create execution result
            execution_time = asyncio.get_event_loop().time() - start_time
            
            logger.info(f"Command completed with code {return_code} in {execution_time:.2f}s")
            
        except asyncio.CancelledError:
            await self._kill_process()
            raise
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            await self._emit_failure(command, str(e))
            raise
        finally:
            self.current_process = None
    
    async def validate_command(self, command: str) -> bool:
        """Check if a SuperClaude command is valid.
        
        Args:
            command: Command to validate
            
        Returns:
            True if command is valid
        """
        # Basic SC command pattern validation
        sc_pattern = r"^/sc:\w+|^sc:\w+"
        if not re.match(sc_pattern, command.strip()):
            logger.warning(f"Command doesn't match SC pattern: {command}")
            return False
        
        # Extract command type
        command_type = self._extract_command_type(command)
        
        # Validate known command types
        valid_commands = [
            "analyze", "implement", "test", "improve", "build",
            "document", "git", "workflow", "task", "spawn",
            "help", "index", "load", "cleanup", "estimate"
        ]
        
        if command_type not in valid_commands:
            logger.warning(f"Unknown SC command type: {command_type}")
            return False
        
        # Validate flags (basic check)
        if "--" in command:
            flags = re.findall(r"--[\w-]+", command)
            for flag in flags:
                if not self._is_valid_flag(flag):
                    logger.warning(f"Invalid flag: {flag}")
                    return False
        
        return True
    
    async def get_execution_result(self) -> ExecutionResult:
        """Get the complete execution result after command finishes.
        
        Returns:
            Execution result with all details
        """
        if not self.execution_id:
            raise RuntimeError("No execution in progress")
        
        # Collect all output (this would be aggregated during streaming in real impl)
        stdout = ""
        stderr = ""
        files_created = []
        files_modified = []
        test_results = None
        
        # For now, create a basic result
        result = ExecutionResult(
            execution_id=self.execution_id,
            command="",  # Would be stored during execution
            exit_code=0,
            stdout=stdout,
            stderr=stderr,
            execution_time=0.0,
            files_created=files_created,
            files_modified=files_modified,
            tests_run=test_results,
        )
        
        # Emit completion event
        await orchestration_bus.emit(
            ExecutionComplete(
                execution_id=self.execution_id,
                command=result.command,
                exit_code=result.exit_code,
                total_output=result.stdout,
                error_output=result.stderr,
                execution_time=result.execution_time,
                files_created=result.files_created,
                files_modified=result.files_modified,
            )
        )
        
        return result
    
    async def extract_metadata(self, output: str) -> ExecutionMetadata:
        """Parse SCF-enhanced output for metadata.
        
        Args:
            output: Command output to parse
            
        Returns:
            Extracted metadata
        """
        metadata = ExecutionMetadata()
        
        # Parse SCF version
        version_match = re.search(r"SCF Version: ([\d.]+)", output)
        if version_match:
            metadata.scf_version = version_match.group(1)
        
        # Parse personas used
        persona_matches = re.findall(r"--persona-(\w+)", output)
        metadata.personas_used = list(set(persona_matches))
        
        # Parse flags
        flag_matches = re.findall(r"--([\w-]+)", output)
        metadata.flags_used = list(set(flag_matches))
        
        # Parse MCP servers
        if "--seq" in output or "--sequential" in output:
            metadata.mcp_servers_used.append("Sequential")
        if "--c7" in output or "--context7" in output:
            metadata.mcp_servers_used.append("Context7")
        if "--magic" in output:
            metadata.mcp_servers_used.append("Magic")
        if "--play" in output or "--playwright" in output:
            metadata.mcp_servers_used.append("Playwright")
        
        # Parse thinking depth
        if "--ultrathink" in output:
            metadata.thinking_depth = "ultrathink"
        elif "--think-hard" in output:
            metadata.thinking_depth = "think-hard"
        elif "--think" in output:
            metadata.thinking_depth = "think"
        else:
            metadata.thinking_depth = "standard"
        
        # Parse performance metrics if present
        perf_pattern = r"(\w+):\s*([\d.]+)(ms|s|%)"
        for match in re.finditer(perf_pattern, output):
            metric_name = match.group(1).lower()
            value = float(match.group(2))
            unit = match.group(3)
            
            # Normalize to standard units
            if unit == "s":
                value *= 1000  # Convert to ms
            elif unit == "%":
                value /= 100  # Convert to ratio
            
            metadata.performance_metrics[metric_name] = value
        
        # Emit metadata event
        await orchestration_bus.emit(
            MetadataExtracted(
                execution_id=self.execution_id,
                command="",
                scf_version=metadata.scf_version,
                personas_used=metadata.personas_used,
                flags_used=metadata.flags_used,
                mcp_servers_used=metadata.mcp_servers_used,
                performance_metrics=metadata.performance_metrics,
            )
        )
        
        return metadata
    
    async def cancel_execution(self) -> None:
        """Cancel the current execution if running."""
        if self.current_process:
            logger.info("Cancelling execution")
            await self._kill_process()
    
    def _prepare_command(self, command: str) -> str:
        """Prepare command for subprocess execution.
        
        Args:
            command: SC command
            
        Returns:
            Full command with Claude Code CLI
        """
        # Remove /sc: prefix if present
        if command.startswith("/sc:"):
            command = command[4:]
        elif command.startswith("sc:"):
            command = command[3:]
        
        # Build full command
        full_command = f"{self.claude_binary} {command}"
        
        # Add SCF environment hint
        full_command = f"SCF_ENABLED=1 {full_command}"
        
        return full_command
    
    def _extract_command_type(self, command: str) -> str:
        """Extract command type from SC command.
        
        Args:
            command: SC command
            
        Returns:
            Command type
        """
        match = re.match(r"/?sc:(\w+)", command)
        if match:
            return match.group(1)
        return ""
    
    def _is_valid_flag(self, flag: str) -> bool:
        """Check if a flag is valid for SC commands.
        
        Args:
            flag: Flag to validate
            
        Returns:
            True if valid
        """
        valid_flags = {
            # Thinking flags
            "--think", "--think-hard", "--ultrathink",
            # Persona flags
            "--persona-architect", "--persona-frontend", "--persona-backend",
            "--persona-analyzer", "--persona-security", "--persona-mentor",
            "--persona-refactorer", "--persona-performance", "--persona-qa",
            "--persona-devops", "--persona-scribe",
            # MCP flags
            "--seq", "--sequential", "--c7", "--context7",
            "--magic", "--play", "--playwright", "--all-mcp", "--no-mcp",
            # Other flags
            "--with-tests", "--safe-mode", "--validate", "--uc",
            "--verbose", "--answer-only", "--introspect",
            "--delegate", "--parallel", "--loop", "--iterations",
        }
        
        # Check exact match or prefix match for parameterized flags
        return flag in valid_flags or any(flag.startswith(f) for f in [
            "--persona-scribe=", "--iterations=", "--concurrency=",
            "--scope=", "--focus=", "--output=", "--strategy=",
        ])
    
    async def _stream_output(self) -> AsyncIterator[str]:
        """Stream output from the subprocess.
        
        Yields:
            Output lines
        """
        if not self.current_process or not self.current_process.stdout:
            return
        
        while True:
            line = await self.current_process.stdout.readline()
            if not line:
                break
            
            decoded_line = line.decode("utf-8", errors="replace").rstrip()
            yield decoded_line
    
    async def _parse_output_events(self, line: str) -> None:
        """Parse output line for special events.
        
        Args:
            line: Output line to parse
        """
        # Check for file creation
        if "Created:" in line or "Creating" in line:
            match = re.search(r"(?:Created|Creating):\s*(.+)", line)
            if match:
                file_path = Path(match.group(1).strip())
                await orchestration_bus.emit(
                    FileCreated(
                        execution_id=self.execution_id,
                        command="",
                        file_path=file_path,
                    )
                )
        
        # Check for file modification
        if "Modified:" in line or "Updating" in line:
            match = re.search(r"(?:Modified|Updating):\s*(.+)", line)
            if match:
                file_path = Path(match.group(1).strip())
                await orchestration_bus.emit(
                    FileModified(
                        execution_id=self.execution_id,
                        command="",
                        file_path=file_path,
                    )
                )
        
        # Check for test results
        if "tests passed" in line.lower() or "test results" in line.lower():
            test_results = self._parse_test_results(line)
            if test_results:
                await orchestration_bus.emit(
                    TestExecuted(
                        execution_id=self.execution_id,
                        command="",
                        test_suite=test_results.test_suite,
                        tests_passed=test_results.tests_passed,
                        tests_failed=test_results.tests_failed,
                        tests_skipped=test_results.tests_skipped,
                        coverage_percentage=test_results.coverage_percentage,
                    )
                )
        
        # Check for progress updates
        if "Progress:" in line or "%" in line:
            progress = self._parse_progress(line)
            if progress:
                await orchestration_bus.emit(
                    ExecutionProgress(
                        execution_id=self.execution_id,
                        command="",
                        progress_message=progress[0],
                        percentage=progress[1],
                        current_operation=progress[2],
                    )
                )
    
    def _parse_test_results(self, line: str) -> Optional[TestResults]:
        """Parse test results from output line.
        
        Args:
            line: Output line
            
        Returns:
            Test results or None
        """
        # Pattern: "12 passed, 2 failed, 1 skipped"
        match = re.search(r"(\d+)\s*passed.*?(\d+)\s*failed.*?(\d+)\s*skipped", line)
        if match:
            return TestResults(
                test_suite="",
                tests_passed=int(match.group(1)),
                tests_failed=int(match.group(2)),
                tests_skipped=int(match.group(3)),
            )
        
        # Pattern: "Tests: 12/14 passing (85.7%)"
        match = re.search(r"Tests?:\s*(\d+)/(\d+)\s*passing\s*\(?([\d.]+)%", line)
        if match:
            passed = int(match.group(1))
            total = int(match.group(2))
            return TestResults(
                test_suite="",
                tests_passed=passed,
                tests_failed=total - passed,
                coverage_percentage=float(match.group(3)),
            )
        
        return None
    
    def _parse_progress(self, line: str) -> Optional[tuple[str, float, str]]:
        """Parse progress information from output line.
        
        Args:
            line: Output line
            
        Returns:
            Tuple of (message, percentage, operation) or None
        """
        # Pattern: "Progress: 75% - Building components"
        match = re.search(r"Progress:\s*([\d.]+)%\s*-?\s*(.+)", line)
        if match:
            return (
                line,
                float(match.group(1)),
                match.group(2).strip()
            )
        
        # Pattern: "[45%] Analyzing files"
        match = re.search(r"\[([\d.]+)%\]\s*(.+)", line)
        if match:
            return (
                line,
                float(match.group(1)),
                match.group(2).strip()
            )
        
        return None
    
    async def _kill_process(self) -> None:
        """Kill the current subprocess."""
        if self.current_process:
            try:
                self.current_process.terminate()
                await asyncio.wait_for(self.current_process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.current_process.kill()
                await self.current_process.wait()
    
    async def _emit_failure(self, command: str, error: str) -> None:
        """Emit execution failure event.
        
        Args:
            command: Failed command
            error: Error message
        """
        await orchestration_bus.emit(
            ExecutionFailed(
                execution_id=self.execution_id,
                command=command,
                error_message=error,
                error_type="execution",
            )
        )