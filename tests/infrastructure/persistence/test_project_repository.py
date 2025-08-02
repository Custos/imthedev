"""Tests for the ProjectRepository SQLite implementation.

This module contains comprehensive tests for the SQLite-based
ProjectRepository that implements the ProjectService interface.
"""

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from imthedev.core.domain import ProjectSettings
from imthedev.infrastructure.persistence import ProjectRepository


class TestProjectRepository:
    """Test suite for ProjectRepository."""

    @pytest.fixture
    async def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        repo = ProjectRepository(db_path)
        await repo.initialize()

        yield repo

        # Cleanup
        if db_path.exists():
            db_path.unlink()

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary directory for testing project paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.mark.asyncio
    async def test_initialization(self, temp_db) -> None:
        """Test that repository initializes database schema correctly."""
        # Repository should be initialized without errors
        assert isinstance(temp_db, ProjectRepository)

        # Should be able to query empty projects table
        projects = await temp_db.list_projects()
        assert projects == []

    @pytest.mark.asyncio
    async def test_create_project(self, temp_db, temp_project_dir) -> None:
        """Test creating a new project."""
        # Create project
        project = await temp_db.create_project(
            name="Test Project", path=str(temp_project_dir)
        )

        # Verify project properties
        assert project.name == "Test Project"
        assert project.path == temp_project_dir
        assert project.id is not None
        assert project.created_at is not None
        assert project.settings.auto_approve is False
        assert project.settings.default_ai_model == "claude"

    @pytest.mark.asyncio
    async def test_create_project_with_settings(self, temp_db, temp_project_dir) -> None:
        """Test creating a project with custom settings."""
        settings = ProjectSettings(
            auto_approve=True,
            default_ai_model="gpt-4",
            command_timeout=600,
            environment_vars={"TEST_VAR": "test_value"},
        )

        project = await temp_db.create_project(
            name="Custom Project", path=str(temp_project_dir), settings=settings
        )

        # Verify custom settings
        assert project.settings.auto_approve is True
        assert project.settings.default_ai_model == "gpt-4"
        assert project.settings.command_timeout == 600
        assert project.settings.environment_vars == {"TEST_VAR": "test_value"}

    @pytest.mark.asyncio
    async def test_create_project_invalid_path(self, temp_db) -> None:
        """Test creating project with invalid path raises error."""
        with pytest.raises(ValueError, match="Path does not exist"):
            await temp_db.create_project(
                name="Invalid Project", path="/nonexistent/path"
            )

    @pytest.mark.asyncio
    async def test_create_project_duplicate_path(self, temp_db, temp_project_dir) -> None:
        """Test creating project with duplicate path raises error."""
        # Create first project
        await temp_db.create_project(name="First Project", path=str(temp_project_dir))

        # Try to create second project with same path
        with pytest.raises(ValueError, match="Project already exists at path"):
            await temp_db.create_project(
                name="Second Project", path=str(temp_project_dir)
            )

    @pytest.mark.asyncio
    async def test_get_project(self, temp_db, temp_project_dir) -> None:
        """Test retrieving project by ID."""
        # Create project
        created_project = await temp_db.create_project(
            name="Get Test Project", path=str(temp_project_dir)
        )

        # Retrieve project
        retrieved_project = await temp_db.get_project(created_project.id)

        # Verify retrieved project matches created project
        assert retrieved_project is not None
        assert retrieved_project.id == created_project.id
        assert retrieved_project.name == created_project.name
        assert retrieved_project.path == created_project.path
        assert retrieved_project.created_at == created_project.created_at

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, temp_db) -> None:
        """Test retrieving non-existent project returns None."""
        non_existent_id = uuid4()
        project = await temp_db.get_project(non_existent_id)
        assert project is None

    @pytest.mark.asyncio
    async def test_list_projects(self, temp_db, temp_project_dir) -> None:
        """Test listing all projects."""
        # Initially empty
        projects = await temp_db.list_projects()
        assert len(projects) == 0

        # Create multiple projects
        with tempfile.TemporaryDirectory() as temp_dir2:
            await temp_db.create_project("Project 1", str(temp_project_dir))
            await temp_db.create_project("Project 2", temp_dir2)

        # List projects
        projects = await temp_db.list_projects()
        assert len(projects) == 2

        # Should be ordered by creation date (newest first)
        project_names = [p.name for p in projects]
        assert "Project 2" in project_names
        assert "Project 1" in project_names

    @pytest.mark.asyncio
    async def test_update_project(self, temp_db, temp_project_dir) -> None:
        """Test updating project metadata and settings."""
        # Create project
        project = await temp_db.create_project(
            name="Original Name", path=str(temp_project_dir)
        )

        # Update project
        project.name = "Updated Name"
        project.settings.auto_approve = True
        project.settings.default_ai_model = "gpt-4"

        await temp_db.update_project(project)

        # Verify update
        updated_project = await temp_db.get_project(project.id)
        assert updated_project.name == "Updated Name"
        assert updated_project.settings.auto_approve is True
        assert updated_project.settings.default_ai_model == "gpt-4"

    @pytest.mark.asyncio
    async def test_update_project_not_found(self, temp_db, temp_project_dir) -> None:
        """Test updating non-existent project raises error."""
        # Create project with fake ID
        project = await temp_db.create_project("Test", str(temp_project_dir))
        project.id = uuid4()  # Change to non-existent ID

        with pytest.raises(ValueError, match="Project not found"):
            await temp_db.update_project(project)

    @pytest.mark.asyncio
    async def test_delete_project(self, temp_db, temp_project_dir) -> None:
        """Test deleting a project."""
        # Create project
        project = await temp_db.create_project("Delete Test", str(temp_project_dir))

        # Verify project exists
        assert await temp_db.get_project(project.id) is not None

        # Delete project
        await temp_db.delete_project(project.id)

        # Verify project is gone
        assert await temp_db.get_project(project.id) is None

    @pytest.mark.asyncio
    async def test_delete_project_not_found(self, temp_db) -> None:
        """Test deleting non-existent project raises error."""
        non_existent_id = uuid4()

        with pytest.raises(ValueError, match="Project not found"):
            await temp_db.delete_project(non_existent_id)

    @pytest.mark.asyncio
    async def test_current_project_management(self, temp_db, temp_project_dir) -> None:
        """Test current project get/set functionality."""
        # Initially no current project
        current = await temp_db.get_current_project()
        assert current is None

        # Create project
        with tempfile.TemporaryDirectory() as temp_dir2:
            project1 = await temp_db.create_project("Project 1", str(temp_project_dir))
            project2 = await temp_db.create_project("Project 2", temp_dir2)

        # Set current project
        await temp_db.set_current_project(project1.id)

        # Verify current project
        current = await temp_db.get_current_project()
        assert current is not None
        assert current.id == project1.id

        # Change current project
        await temp_db.set_current_project(project2.id)

        # Verify change
        current = await temp_db.get_current_project()
        assert current.id == project2.id

    @pytest.mark.asyncio
    async def test_set_current_project_not_found(self, temp_db) -> None:
        """Test setting non-existent project as current raises error."""
        non_existent_id = uuid4()

        with pytest.raises(ValueError, match="Project not found"):
            await temp_db.set_current_project(non_existent_id)

    @pytest.mark.asyncio
    async def test_delete_current_project_clears_cache(self, temp_db, temp_project_dir) -> None:
        """Test that deleting current project clears the cache."""
        # Create and set current project
        project = await temp_db.create_project("Current Test", str(temp_project_dir))
        await temp_db.set_current_project(project.id)

        # Verify it's current
        current = await temp_db.get_current_project()
        assert current.id == project.id

        # Delete the current project
        await temp_db.delete_project(project.id)

        # Verify current project is cleared
        current = await temp_db.get_current_project()
        assert current is None
