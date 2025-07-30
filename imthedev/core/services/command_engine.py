"""Command engine implementation for managing command lifecycle.

This module provides the core command execution engine that handles the
complete lifecycle of commands from proposal through execution.
"""

import asyncio
import subprocess
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID, uuid4

from imthedev.core.domain import Command, CommandResult, CommandStatus
from imthedev.core.events import Event, EventBus, EventPriority, EventTypes
from imthedev.core.interfaces import CommandEngine


class CommandExecutionError(Exception):
    """Raised when command execution fails."""
    
    def __init__(self, message: str, exit_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.exit_code = exit_code


class CommandEngineImpl(CommandEngine):
    """Implementation of command execution engine with event-driven lifecycle.
    
    This engine manages the complete command lifecycle including:
    - Command proposal and queueing
    - Approval/rejection workflow
    - Command execution with async subprocess support
    - Result handling and event publishing
    
    All state changes are published through the event bus for decoupled
    communication with other system components.
    """
    
    def __init__(self, event_bus: EventBus) -> None:
        """Initialize the command engine.
        
        Args:
            event_bus: Event bus for publishing command lifecycle events
        """
        self._event_bus = event_bus
        self._pending_commands: Dict[UUID, Command] = {}
        self._executing_commands: Dict[UUID, asyncio.Task[None]] = {}
        
    async def propose_command(
        self,
        project_id: UUID,
        command_text: str,
        ai_reasoning: str
    ) -> Command:
        """Propose a new command for execution.
        
        Creates a new command in pending status and publishes a command
        proposed event. The command is added to the pending queue awaiting
        approval or rejection.
        
        Args:
            project_id: ID of the project this command belongs to
            command_text: The actual command to execute
            ai_reasoning: AI-generated reasoning for the command
            
        Returns:
            The newly created command in pending status
        """
        command = Command(
            id=UUID(str(uuid4())),
            project_id=project_id,
            command_text=command_text,
            ai_reasoning=ai_reasoning,
            status=CommandStatus.PROPOSED
        )
        
        self._pending_commands[command.id] = command
        
        # Publish command proposed event
        await self._event_bus.publish(Event(
            type=EventTypes.COMMAND_PROPOSED,
            payload={
                "command_id": str(command.id),
                "project_id": str(project_id),
                "command_text": command_text,
                "ai_reasoning": ai_reasoning
            }
        ))
        
        return command
        
    async def approve_command(self, command_id: UUID) -> None:
        """Approve a pending command for execution.
        
        Transitions the command from pending to approved status, removes it
        from the pending queue, and initiates asynchronous execution.
        
        Args:
            command_id: ID of the command to approve
            
        Raises:
            ValueError: If command not found or not in pending status
        """
        command = self._pending_commands.get(command_id)
        if not command:
            raise ValueError(f"Command {command_id} not found in pending queue")
            
        # Remove from pending and update status
        del self._pending_commands[command_id]
        command.status = CommandStatus.APPROVED
        
        # Publish approval event
        await self._event_bus.publish(Event(
            type=EventTypes.COMMAND_APPROVED,
            payload={
                "command_id": str(command_id),
                "project_id": str(command.project_id)
            }
        ))
        
        # Start execution asynchronously
        task = asyncio.create_task(self._execute_command_async(command))
        self._executing_commands[command_id] = task
        
    async def reject_command(self, command_id: UUID) -> None:
        """Reject a pending command.
        
        Transitions the command to rejected status and removes it from the
        pending queue. The command will not be executed.
        
        Args:
            command_id: ID of the command to reject
            
        Raises:
            ValueError: If command not found in pending queue
        """
        command = self._pending_commands.get(command_id)
        if not command:
            raise ValueError(f"Command {command_id} not found in pending queue")
            
        # Remove from pending and update status
        del self._pending_commands[command_id]
        command.status = CommandStatus.REJECTED
        
        # Publish rejection event
        await self._event_bus.publish(Event(
            type=EventTypes.COMMAND_REJECTED,
            payload={
                "command_id": str(command_id),
                "project_id": str(command.project_id),
                "reason": "User rejected command"
            }
        ))
        
    async def execute_command(self, command_id: UUID) -> None:
        """Execute a command immediately (used for autopilot mode).
        
        Bypasses the approval workflow and executes the command directly.
        This is typically used when autopilot mode is enabled.
        
        Args:
            command_id: ID of the command to execute
            
        Raises:
            ValueError: If command not found
        """
        command = self._pending_commands.get(command_id)
        if not command:
            # Check if already executing
            if command_id in self._executing_commands:
                return  # Already executing
            raise ValueError(f"Command {command_id} not found")
            
        # Remove from pending if present
        if command_id in self._pending_commands:
            del self._pending_commands[command_id]
            
        command.status = CommandStatus.APPROVED
        
        # Start execution
        task = asyncio.create_task(self._execute_command_async(command))
        self._executing_commands[command_id] = task
        
    def get_pending_commands(self) -> Dict[UUID, Command]:
        """Get all commands awaiting approval.
        
        Returns:
            Dictionary mapping command IDs to pending commands
        """
        return self._pending_commands.copy()
        
    async def cancel_execution(self, command_id: UUID) -> None:
        """Cancel an executing command.
        
        Attempts to cancel a currently executing command. This may not
        always be possible depending on the command's state.
        
        Args:
            command_id: ID of the command to cancel
            
        Raises:
            ValueError: If command not currently executing
        """
        task = self._executing_commands.get(command_id)
        if not task:
            raise ValueError(f"Command {command_id} is not currently executing")
            
        # Cancel the task
        task.cancel()
        
        # Publish cancellation event
        await self._event_bus.publish(Event(
            type=EventTypes.COMMAND_CANCELLED,
            payload={"command_id": str(command_id)}
        ))
        
        # Remove from executing
        del self._executing_commands[command_id]
        
    async def _execute_command_async(self, command: Command) -> None:
        """Execute a command asynchronously.
        
        Internal method that handles the actual command execution using
        asyncio subprocess. Publishes events for execution start, output,
        and completion.
        
        Args:
            command: The command to execute
        """
        command.status = CommandStatus.EXECUTING
        
        # Publish execution started event
        await self._event_bus.publish(Event(
            type=EventTypes.COMMAND_EXECUTING,
            payload={
                "command_id": str(command.id),
                "project_id": str(command.project_id),
                "command_text": command.command_text
            }
        ))
        
        try:
            # Execute command using asyncio subprocess
            process = await asyncio.create_subprocess_shell(
                command.command_text,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Collect output
            stdout, stderr = await process.communicate()
            
            # Check return code
            if process.returncode == 0:
                command.status = CommandStatus.COMPLETED
                command.result = CommandResult(
                    exit_code=0,
                    stdout=stdout.decode('utf-8'),
                    stderr=stderr.decode('utf-8'),
                    execution_time=0.0  # TODO: Calculate actual execution time
                )
                
                # Publish success event
                await self._event_bus.publish(Event(
                    type=EventTypes.COMMAND_COMPLETED,
                    payload={
                        "command_id": str(command.id),
                        "project_id": str(command.project_id),
                        "exit_code": 0,
                        "stdout": command.result.stdout,
                        "stderr": command.result.stderr
                    }
                ))
            else:
                command.status = CommandStatus.FAILED
                command.result = CommandResult(
                    exit_code=process.returncode or -1,
                    stdout=stdout.decode('utf-8'),
                    stderr=stderr.decode('utf-8'),
                    execution_time=0.0  # TODO: Calculate actual execution time
                )
                
                # Publish failure event
                await self._event_bus.publish(Event(
                    type=EventTypes.COMMAND_FAILED,
                    payload={
                        "command_id": str(command.id),
                        "project_id": str(command.project_id),
                        "exit_code": command.result.exit_code,
                        "error": command.result.stderr or "Command failed"
                    }
                ))
                
        except asyncio.CancelledError:
            # Command was cancelled
            command.status = CommandStatus.CANCELLED
            raise
            
        except Exception as e:
            # Unexpected error
            command.status = CommandStatus.FAILED
            command.result = CommandResult(
                exit_code=-1,
                stdout="",
                stderr=str(e),
                execution_time=0.0
            )
            
            # Publish error event
            await self._event_bus.publish(Event(
                type=EventTypes.COMMAND_FAILED,
                payload={
                    "command_id": str(command.id),
                    "project_id": str(command.project_id),
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            ))
            
        finally:
            # Remove from executing commands
            self._executing_commands.pop(command.id, None)