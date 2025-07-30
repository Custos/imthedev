"""SQLite-based implementation of ProjectService interface.

This module implements the ProjectService interface using aiosqlite for
persistent storage of project metadata and settings.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import UUID

import aiosqlite

from imthedev.core.domain import Project, ProjectContext, ProjectSettings
from imthedev.core.interfaces.services import ProjectService


class ProjectRepository(ProjectService):
    """SQLite-based repository for project data.
    
    This class implements the ProjectService interface using SQLite for
    persistent storage of project metadata and settings. The database
    schema is designed for atomic operations and data integrity.
    
    Attributes:
        db_path: Path to the SQLite database file
        _current_project_id: Cached ID of the currently selected project
    """
    
    def __init__(self, db_path: Path) -> None:
        """Initialize the repository with database path.
        
        Args:
            db_path: Path to SQLite database file (will be created if not exists)
        """
        self.db_path = db_path
        self._current_project_id: Optional[UUID] = None
    
    async def initialize(self) -> None:
        """Initialize the database schema.
        
        Creates the projects table if it doesn't exist and sets up
        necessary indexes for performance.
        
        Raises:
            DatabaseError: If database initialization fails
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    settings TEXT NOT NULL DEFAULT '{}',
                    is_current BOOLEAN DEFAULT 0
                )
            """)
            
            # Create index for faster path lookups
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_projects_path ON projects(path)
            """)
            
            # Create index for current project lookups
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_projects_current ON projects(is_current) 
                WHERE is_current = 1
            """)
            
            await db.commit()
    
    async def create_project(
        self,
        name: str,
        path: str,
        settings: Optional[ProjectSettings] = None
    ) -> Project:
        """Create a new project with the specified configuration.
        
        Args:
            name: Human-readable project name
            path: Filesystem path to project root
            settings: Optional project-specific settings
            
        Returns:
            Newly created Project instance
            
        Raises:
            ProjectExistsError: If a project already exists at the path
            InvalidPathError: If the path is not valid or accessible
        """
        project_path = Path(path)
        
        # Validate path exists and is accessible
        if not project_path.exists():
            raise ValueError(f"Path does not exist: {path}")
        
        if not project_path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")
        
        # Create project with default context and settings
        project = Project.create(
            name=name,
            path=project_path,
            settings=settings or ProjectSettings()
        )
        
        # Store in database
        settings_json = json.dumps({
            "auto_approve": project.settings.auto_approve,
            "default_ai_model": project.settings.default_ai_model,
            "command_timeout": project.settings.command_timeout,
            "environment_vars": project.settings.environment_vars
        })
        
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("""
                    INSERT INTO projects (id, name, path, created_at, settings, is_current)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    str(project.id),
                    project.name,
                    str(project.path),
                    project.created_at.isoformat(),
                    settings_json,
                    0  # Not current by default
                ))
                await db.commit()
            except aiosqlite.IntegrityError as e:
                if "UNIQUE constraint failed: projects.path" in str(e):
                    raise ValueError(f"Project already exists at path: {path}")
                raise
        
        return project
    
    async def get_project(self, project_id: UUID) -> Optional[Project]:
        """Retrieve a project by its ID.
        
        Args:
            project_id: Unique identifier of the project
            
        Returns:
            Project instance if found, None otherwise
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT id, name, path, created_at, settings
                FROM projects 
                WHERE id = ?
            """, (str(project_id),)) as cursor:
                row = await cursor.fetchone()
        
        if not row:
            return None
        
        return self._row_to_project(row)
    
    async def list_projects(self) -> List[Project]:
        """List all available projects.
        
        Returns:
            List of all projects ordered by creation date (newest first)
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT id, name, path, created_at, settings
                FROM projects 
                ORDER BY created_at DESC
            """) as cursor:
                rows = await cursor.fetchall()
        
        projects = []
        for row in rows:
            projects.append(self._row_to_project(row))
        
        return projects
    
    async def update_project(self, project: Project) -> None:
        """Update an existing project's metadata and settings.
        
        Args:
            project: Project instance with updated values
            
        Raises:
            ProjectNotFoundError: If the project doesn't exist
        """
        settings_json = json.dumps({
            "auto_approve": project.settings.auto_approve,
            "default_ai_model": project.settings.default_ai_model,
            "command_timeout": project.settings.command_timeout,
            "environment_vars": project.settings.environment_vars
        })
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                UPDATE projects 
                SET name = ?, path = ?, settings = ?
                WHERE id = ?
            """, (
                project.name,
                str(project.path),
                settings_json,
                str(project.id)
            ))
            
            if cursor.rowcount == 0:
                raise ValueError(f"Project not found: {project.id}")
            
            await db.commit()
    
    async def delete_project(self, project_id: UUID) -> None:
        """Delete a project and all associated data.
        
        Args:
            project_id: ID of the project to delete
            
        Raises:
            ProjectNotFoundError: If the project doesn't exist
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM projects WHERE id = ?
            """, (str(project_id),))
            
            if cursor.rowcount == 0:
                raise ValueError(f"Project not found: {project_id}")
            
            await db.commit()
        
        # Clear current project if it was deleted
        if self._current_project_id == project_id:
            self._current_project_id = None
    
    async def get_current_project(self) -> Optional[Project]:
        """Get the currently selected project.
        
        Returns:
            Currently selected project or None if no project is selected
        """
        # First check cached value
        if self._current_project_id:
            project = await self.get_project(self._current_project_id)
            if project:
                return project
            else:
                # Cache is stale, clear it
                self._current_project_id = None
        
        # Check database for current project
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT id, name, path, created_at, settings
                FROM projects 
                WHERE is_current = 1
                LIMIT 1
            """) as cursor:
                row = await cursor.fetchone()
        
        if not row:
            return None
        
        project = self._row_to_project(row)
        self._current_project_id = project.id
        return project
    
    async def set_current_project(self, project_id: UUID) -> None:
        """Set the current active project.
        
        Args:
            project_id: ID of the project to make current
            
        Raises:
            ProjectNotFoundError: If the project doesn't exist
        """
        async with aiosqlite.connect(self.db_path) as db:
            # First verify project exists
            async with db.execute("""
                SELECT 1 FROM projects WHERE id = ?
            """, (str(project_id),)) as cursor:
                if not await cursor.fetchone():
                    raise ValueError(f"Project not found: {project_id}")
            
            # Clear current project flag from all projects
            await db.execute("UPDATE projects SET is_current = 0")
            
            # Set the new current project
            await db.execute("""
                UPDATE projects SET is_current = 1 WHERE id = ?
            """, (str(project_id),))
            
            await db.commit()
        
        # Update cache
        self._current_project_id = project_id
    
    def _row_to_project(self, row: tuple) -> Project:
        """Convert database row to Project instance.
        
        Args:
            row: Database row tuple (id, name, path, created_at, settings)
            
        Returns:
            Project instance
        """
        project_id, name, path, created_at_str, settings_json = row
        
        # Parse settings JSON
        settings_data = json.loads(settings_json)
        settings = ProjectSettings(
            auto_approve=settings_data.get("auto_approve", False),
            default_ai_model=settings_data.get("default_ai_model", "claude"),
            command_timeout=settings_data.get("command_timeout", 300),
            environment_vars=settings_data.get("environment_vars", {})
        )
        
        # Parse datetime
        created_at = datetime.fromisoformat(created_at_str)
        
        return Project(
            id=UUID(project_id),
            name=name,
            path=Path(path),
            created_at=created_at,
            context=ProjectContext(),  # Context loaded separately by ContextRepository
            settings=settings
        )