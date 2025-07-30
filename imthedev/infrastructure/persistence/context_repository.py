"""JSON file-based implementation of ContextService interface.

This module implements the ContextService interface using JSON files for
persistent storage of project contexts and command history.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from imthedev.core.domain import Command, CommandResult, CommandStatus, ProjectContext
from imthedev.core.interfaces.services import ContextService


class ContextRepository(ContextService):
    """JSON file-based repository for project context data.
    
    This class implements the ContextService interface using JSON files for
    persistent storage of project contexts. Each project's context is stored
    in a separate JSON file for atomic operations.
    
    Attributes:
        storage_dir: Directory containing context JSON files
    """
    
    def __init__(self, storage_dir: Path) -> None:
        """Initialize the repository with storage directory.
        
        Args:
            storage_dir: Directory to store context JSON files
        """
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_context_file_path(self, project_id: UUID) -> Path:
        """Get the file path for a project's context.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Path to the context JSON file
        """
        return self.storage_dir / f"{project_id}.json"
    
    async def save_context(
        self,
        project_id: UUID,
        context: ProjectContext
    ) -> None:
        """Save or update the context for a project.
        
        Args:
            project_id: ID of the project
            context: Context to save
            
        Raises:
            StorageError: If context cannot be persisted
        """
        context_file = self._get_context_file_path(project_id)
        
        # Apply history size limit before saving
        MAX_HISTORY_SIZE = 100
        history = context.history
        if len(history) > MAX_HISTORY_SIZE:
            history = history[-MAX_HISTORY_SIZE:]
        
        # Convert context to serializable format
        context_data = {
            "history": [self._command_to_dict(cmd) for cmd in history],
            "current_state": context.current_state,
            "ai_memory": context.ai_memory,
            "metadata": context.metadata,
            "last_updated": datetime.now().isoformat()
        }
        
        try:
            # Write to temporary file first for atomic operation
            temp_file = context_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(context_data, f, indent=2, ensure_ascii=False)
            
            # Atomic move to final location
            temp_file.replace(context_file)
            
        except (OSError, json.JSONEncodeError) as e:
            # Clean up temp file if it exists
            if temp_file.exists():
                temp_file.unlink()
            raise RuntimeError(f"Failed to save context for project {project_id}: {e}")
    
    async def load_context(self, project_id: UUID) -> ProjectContext:
        """Load the context for a project.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Project context with full history and state
            
        Raises:
            ContextNotFoundError: If no context exists for the project
        """
        context_file = self._get_context_file_path(project_id)
        
        if not context_file.exists():
            # Return empty context for new projects
            return ProjectContext()
        
        try:
            with open(context_file, 'r', encoding='utf-8') as f:
                context_data = json.load(f)
            
            # Convert back to domain objects
            history = [self._dict_to_command(cmd_data) for cmd_data in context_data.get("history", [])]
            
            return ProjectContext(
                history=history,
                current_state=context_data.get("current_state", {}),
                ai_memory=context_data.get("ai_memory", ""),
                metadata=context_data.get("metadata", {})
            )
            
        except (OSError, json.JSONDecodeError, KeyError, ValueError) as e:
            raise RuntimeError(f"Failed to load context for project {project_id}: {e}")
    
    async def append_command(
        self,
        project_id: UUID,
        command: Command
    ) -> None:
        """Append a command to the project's history.
        
        Args:
            project_id: ID of the project
            command: Command to append to history
        """
        # Load existing context
        context = await self.load_context(project_id)
        
        # Append command to history
        context.history.append(command)
        
        # Keep only the last 100 commands to prevent unbounded growth
        MAX_HISTORY_SIZE = 100
        if len(context.history) > MAX_HISTORY_SIZE:
            context.history = context.history[-MAX_HISTORY_SIZE:]
        
        # Save updated context
        await self.save_context(project_id, context)
    
    async def get_command_history(
        self,
        project_id: UUID,
        limit: int = 50,
        status_filter: Optional[CommandStatus] = None
    ) -> List[Command]:
        """Retrieve command history for a project.
        
        Args:
            project_id: ID of the project
            limit: Maximum number of commands to return
            status_filter: Optional filter by command status
            
        Returns:
            List of commands ordered by timestamp (newest first)
        """
        context = await self.load_context(project_id)
        
        # Filter by status if specified
        commands = context.history
        if status_filter:
            commands = [cmd for cmd in commands if cmd.status == status_filter]
        
        # Sort by timestamp (newest first) and apply limit
        commands.sort(key=lambda cmd: cmd.timestamp, reverse=True)
        return commands[:limit]
    
    async def update_command_status(
        self,
        project_id: UUID,
        command_id: UUID,
        status: CommandStatus
    ) -> None:
        """Update the status of a command in history.
        
        Args:
            project_id: ID of the project
            command_id: ID of the command to update
            status: New status for the command
            
        Raises:
            CommandNotFoundError: If the command doesn't exist
        """
        context = await self.load_context(project_id)
        
        # Find and update the command
        command_found = False
        for command in context.history:
            if command.id == command_id:
                command.status = status
                command_found = True
                break
        
        if not command_found:
            raise ValueError(f"Command not found: {command_id}")
        
        # Save updated context
        await self.save_context(project_id, context)
    
    def _command_to_dict(self, command: Command) -> dict:
        """Convert Command to dictionary for JSON serialization.
        
        Args:
            command: Command instance to convert
            
        Returns:
            Dictionary representation of the command
        """
        data = {
            "id": str(command.id),
            "project_id": str(command.project_id),
            "command_text": command.command_text,
            "ai_reasoning": command.ai_reasoning,
            "status": command.status.value,
            "timestamp": command.timestamp.isoformat()
        }
        
        if command.result:
            data["result"] = {
                "exit_code": command.result.exit_code,
                "stdout": command.result.stdout,
                "stderr": command.result.stderr,
                "execution_time": command.result.execution_time,
                "timestamp": command.result.timestamp.isoformat()
            }
        
        return data
    
    def _dict_to_command(self, data: dict) -> Command:
        """Convert dictionary to Command instance.
        
        Args:
            data: Dictionary representation of command
            
        Returns:
            Command instance
        """
        result = None
        if "result" in data:
            result_data = data["result"]
            result = CommandResult(
                exit_code=result_data["exit_code"],
                stdout=result_data["stdout"],
                stderr=result_data["stderr"],
                execution_time=result_data["execution_time"],
                timestamp=datetime.fromisoformat(result_data["timestamp"])
            )
        
        return Command(
            id=UUID(data["id"]),
            project_id=UUID(data["project_id"]),
            command_text=data["command_text"],
            ai_reasoning=data["ai_reasoning"],
            status=CommandStatus(data["status"]),
            result=result,
            timestamp=datetime.fromisoformat(data["timestamp"])
        )