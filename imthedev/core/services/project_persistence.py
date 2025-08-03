"""Project persistence service for managing project data storage.

This module handles all file system operations for project metadata,
context, and command history storage in the .imthedev directory.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from imthedev.core.domain import Project, ProjectContext, ProjectSettings


class ProjectPersistenceService:
    """Service for persisting project data to the file system.
    
    Each project stores its data in a .imthedev directory within the project root:
    - project.json: Project metadata (name, id, created_at, settings)
    - context.json: AI context and conversation history
    - commands/: Directory containing command history logs
    """
    
    IMTHEDEV_DIR = ".imthedev"
    PROJECT_FILE = "project.json"
    CONTEXT_FILE = "context.json"
    COMMANDS_DIR = "commands"
    
    def __init__(self) -> None:
        """Initialize the project persistence service."""
        pass
    
    def initialize_project_directory(self, project: Project) -> None:
        """Initialize the .imthedev directory structure for a project.
        
        Args:
            project: The project to initialize storage for
            
        Raises:
            OSError: If directory creation fails
        """
        project_dir = Path(project.path)
        imthedev_dir = project_dir / self.IMTHEDEV_DIR
        
        # Create directory structure
        imthedev_dir.mkdir(parents=True, exist_ok=True)
        (imthedev_dir / self.COMMANDS_DIR).mkdir(exist_ok=True)
        
        # Save initial project metadata
        self.save_project_metadata(project)
        
        # Save initial empty context
        self.save_project_context(project)
    
    def save_project_metadata(self, project: Project) -> None:
        """Save project metadata to project.json.
        
        Args:
            project: The project whose metadata to save
        """
        metadata_path = Path(project.path) / self.IMTHEDEV_DIR / self.PROJECT_FILE
        
        metadata = {
            "id": str(project.id),
            "name": project.name,
            "path": str(project.path),
            "created_at": project.created_at.isoformat(),
            "settings": {
                "auto_approve": project.settings.auto_approve,
                "default_ai_model": project.settings.default_ai_model,
                "command_timeout": project.settings.command_timeout,
                "environment_vars": project.settings.environment_vars,
            }
        }
        
        # Ensure directory exists
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
    
    def load_project_metadata(self, project_path: Path) -> Optional[dict[str, Any]]:
        """Load project metadata from project.json.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Project metadata dict or None if not found
        """
        metadata_path = project_path / self.IMTHEDEV_DIR / self.PROJECT_FILE
        
        if not metadata_path.exists():
            return None
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
    
    def save_project_context(self, project: Project) -> None:
        """Save project context to context.json.
        
        Args:
            project: The project whose context to save
        """
        context_path = Path(project.path) / self.IMTHEDEV_DIR / self.CONTEXT_FILE
        
        # Convert context to serializable format
        context_data = {
            "ai_memory": project.context.ai_memory,
            "current_state": project.context.current_state,
            "metadata": project.context.metadata,
            "history": [
                {
                    "id": str(cmd.id),
                    "project_id": str(cmd.project_id),
                    "command_text": cmd.command_text,
                    "ai_reasoning": cmd.ai_reasoning,
                    "status": cmd.status.value,
                    "timestamp": cmd.timestamp.isoformat(),
                    "result": {
                        "exit_code": cmd.result.exit_code,
                        "stdout": cmd.result.stdout,
                        "stderr": cmd.result.stderr,
                        "execution_time": cmd.result.execution_time,
                        "timestamp": cmd.result.timestamp.isoformat(),
                    } if cmd.result else None
                }
                for cmd in project.context.history
            ]
        }
        
        # Ensure directory exists
        context_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(context_path, 'w', encoding='utf-8') as f:
            json.dump(context_data, f, indent=2)
    
    def load_project_context(self, project_path: Path) -> Optional[dict[str, Any]]:
        """Load project context from context.json.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Context data dict or None if not found
        """
        context_path = project_path / self.IMTHEDEV_DIR / self.CONTEXT_FILE
        
        if not context_path.exists():
            return None
        
        try:
            with open(context_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
    
    def rename_project(self, project: Project, new_name: str) -> None:
        """Rename a project and update its metadata.
        
        Args:
            project: The project to rename
            new_name: The new name for the project
        """
        project.name = new_name
        self.save_project_metadata(project)
    
    def delete_project_data(self, project_path: Path) -> bool:
        """Delete the .imthedev directory for a project.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            True if deletion was successful, False otherwise
        """
        imthedev_dir = project_path / self.IMTHEDEV_DIR
        
        if not imthedev_dir.exists():
            return True
        
        try:
            shutil.rmtree(imthedev_dir)
            return True
        except OSError:
            return False
    
    def project_exists(self, project_path: Path) -> bool:
        """Check if a project has been initialized with .imthedev directory.
        
        Args:
            project_path: Path to check
            
        Returns:
            True if .imthedev/project.json exists
        """
        metadata_path = project_path / self.IMTHEDEV_DIR / self.PROJECT_FILE
        return metadata_path.exists()
    
    def log_command(self, project: Project, command_text: str, result: Optional[str] = None) -> None:
        """Log a command execution to the project's command history.
        
        Args:
            project: The project to log the command for
            command_text: The command that was executed
            result: Optional result or output from the command
        """
        # Create log file path with today's date
        today = datetime.now().strftime("%Y-%m-%d")
        log_dir = Path(project.path) / self.IMTHEDEV_DIR / self.COMMANDS_DIR
        log_file = log_dir / f"{today}.log"
        
        # Ensure directory exists
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log entry
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {command_text}"
        if result:
            log_entry += f"\n    Result: {result}"
        log_entry += "\n"
        
        # Append to log file
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    
    def list_all_projects(self, base_paths: list[Path]) -> list[dict[str, Any]]:
        """Scan directories for projects with .imthedev directories.
        
        Args:
            base_paths: List of paths to scan for projects
            
        Returns:
            List of project metadata dictionaries
        """
        projects = []
        
        for base_path in base_paths:
            if not base_path.exists():
                continue
            
            # Look for directories with .imthedev subdirectory
            for item in base_path.iterdir():
                if item.is_dir():
                    metadata = self.load_project_metadata(item)
                    if metadata:
                        projects.append(metadata)
        
        return projects