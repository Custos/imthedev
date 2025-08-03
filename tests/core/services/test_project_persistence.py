"""Tests for the project persistence service."""

import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest

from imthedev.core.domain import Project, ProjectContext, ProjectSettings
from imthedev.core.services.project_persistence import ProjectPersistenceService


class TestProjectPersistenceService:
    """Test suite for ProjectPersistenceService."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def service(self):
        """Create a ProjectPersistenceService instance."""
        return ProjectPersistenceService()
    
    @pytest.fixture
    def sample_project(self, temp_dir):
        """Create a sample project for testing."""
        return Project.create(
            name="Test Project",
            path=temp_dir / "test_project"
        )
    
    def test_initialize_project_directory(self, service, sample_project):
        """Test project directory initialization."""
        # Initialize the project directory
        service.initialize_project_directory(sample_project)
        
        # Check that the .imthedev directory was created
        imthedev_dir = sample_project.path / ".imthedev"
        assert imthedev_dir.exists()
        assert imthedev_dir.is_dir()
        
        # Check that subdirectories were created
        commands_dir = imthedev_dir / "commands"
        assert commands_dir.exists()
        assert commands_dir.is_dir()
        
        # Check that project.json was created
        project_file = imthedev_dir / "project.json"
        assert project_file.exists()
        
        # Check that context.json was created
        context_file = imthedev_dir / "context.json"
        assert context_file.exists()
    
    def test_save_and_load_project_metadata(self, service, sample_project):
        """Test saving and loading project metadata."""
        # Create the .imthedev directory
        imthedev_dir = sample_project.path / ".imthedev"
        imthedev_dir.mkdir(parents=True, exist_ok=True)
        
        # Save project metadata
        service.save_project_metadata(sample_project)
        
        # Load project metadata
        metadata = service.load_project_metadata(sample_project.path)
        
        assert metadata is not None
        assert metadata["id"] == str(sample_project.id)
        assert metadata["name"] == sample_project.name
        assert metadata["path"] == str(sample_project.path)
        assert metadata["settings"]["auto_approve"] == sample_project.settings.auto_approve
        assert metadata["settings"]["default_ai_model"] == sample_project.settings.default_ai_model
    
    def test_save_and_load_project_context(self, service, sample_project):
        """Test saving and loading project context."""
        # Create the .imthedev directory
        imthedev_dir = sample_project.path / ".imthedev"
        imthedev_dir.mkdir(parents=True, exist_ok=True)
        
        # Add some data to the context
        sample_project.context.ai_memory = "Test memory"
        sample_project.context.current_state = {"key": "value"}
        sample_project.context.metadata = {"meta": "data"}
        
        # Save project context
        service.save_project_context(sample_project)
        
        # Load project context
        context_data = service.load_project_context(sample_project.path)
        
        assert context_data is not None
        assert context_data["ai_memory"] == "Test memory"
        assert context_data["current_state"]["key"] == "value"
        assert context_data["metadata"]["meta"] == "data"
    
    def test_rename_project(self, service, sample_project):
        """Test renaming a project."""
        # Initialize the project
        service.initialize_project_directory(sample_project)
        
        # Rename the project
        new_name = "Renamed Project"
        service.rename_project(sample_project, new_name)
        
        # Check that the name was updated
        assert sample_project.name == new_name
        
        # Load metadata and verify the name was persisted
        metadata = service.load_project_metadata(sample_project.path)
        assert metadata["name"] == new_name
    
    def test_delete_project_data(self, service, sample_project):
        """Test deleting project data."""
        # Initialize the project
        service.initialize_project_directory(sample_project)
        
        # Verify .imthedev directory exists
        imthedev_dir = sample_project.path / ".imthedev"
        assert imthedev_dir.exists()
        
        # Delete project data
        result = service.delete_project_data(sample_project.path)
        assert result is True
        
        # Verify .imthedev directory was deleted
        assert not imthedev_dir.exists()
    
    def test_delete_nonexistent_project_data(self, service, temp_dir):
        """Test deleting data for a project that doesn't exist."""
        nonexistent_path = temp_dir / "nonexistent"
        result = service.delete_project_data(nonexistent_path)
        assert result is True  # Should return True even if nothing to delete
    
    def test_project_exists(self, service, sample_project):
        """Test checking if a project exists."""
        # Initially should not exist
        assert not service.project_exists(sample_project.path)
        
        # Initialize the project
        service.initialize_project_directory(sample_project)
        
        # Now should exist
        assert service.project_exists(sample_project.path)
    
    def test_log_command(self, service, sample_project):
        """Test logging a command."""
        # Initialize the project
        service.initialize_project_directory(sample_project)
        
        # Log a command
        command_text = "git status"
        result = "On branch main"
        service.log_command(sample_project, command_text, result)
        
        # Check that log file was created
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = sample_project.path / ".imthedev" / "commands" / f"{today}.log"
        assert log_file.exists()
        
        # Check log contents
        log_contents = log_file.read_text()
        assert command_text in log_contents
        assert result in log_contents
    
    def test_list_all_projects(self, service, temp_dir):
        """Test listing all projects from disk."""
        # Create multiple project directories
        project1_path = temp_dir / "project1"
        project2_path = temp_dir / "project2"
        project3_path = temp_dir / "project3"  # This one won't be initialized
        
        # Create and initialize first two projects
        project1 = Project.create("Project 1", project1_path)
        project2 = Project.create("Project 2", project2_path)
        
        service.initialize_project_directory(project1)
        service.initialize_project_directory(project2)
        
        # Create third directory without initialization
        project3_path.mkdir(parents=True, exist_ok=True)
        
        # List all projects
        projects = service.list_all_projects([temp_dir])
        
        # Should find exactly 2 initialized projects
        assert len(projects) == 2
        
        project_names = [p["name"] for p in projects]
        assert "Project 1" in project_names
        assert "Project 2" in project_names
    
    def test_list_projects_empty_directory(self, service, temp_dir):
        """Test listing projects from an empty directory."""
        projects = service.list_all_projects([temp_dir])
        assert len(projects) == 0
    
    def test_list_projects_nonexistent_directory(self, service, temp_dir):
        """Test listing projects from a nonexistent directory."""
        nonexistent = temp_dir / "does_not_exist"
        projects = service.list_all_projects([nonexistent])
        assert len(projects) == 0
    
    def test_load_corrupted_metadata(self, service, sample_project):
        """Test loading corrupted metadata file."""
        # Create .imthedev directory
        imthedev_dir = sample_project.path / ".imthedev"
        imthedev_dir.mkdir(parents=True, exist_ok=True)
        
        # Write corrupted JSON
        metadata_file = imthedev_dir / "project.json"
        metadata_file.write_text("{ corrupted json }")
        
        # Should return None for corrupted file
        metadata = service.load_project_metadata(sample_project.path)
        assert metadata is None
    
    def test_load_corrupted_context(self, service, sample_project):
        """Test loading corrupted context file."""
        # Create .imthedev directory
        imthedev_dir = sample_project.path / ".imthedev"
        imthedev_dir.mkdir(parents=True, exist_ok=True)
        
        # Write corrupted JSON
        context_file = imthedev_dir / "context.json"
        context_file.write_text("{ corrupted json }")
        
        # Should return None for corrupted file
        context = service.load_project_context(sample_project.path)
        assert context is None