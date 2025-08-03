"""Tests for ProjectSelector CRUD operations."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from textual.app import App
from textual.pilot import Pilot

from imthedev.core.domain import Project
from imthedev.ui.tui.components.project_selector import ProjectSelector


class TestProjectSelectorCRUD:
    """Test suite for ProjectSelector CRUD operations."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def sample_projects(self, temp_dir):
        """Create sample projects for testing."""
        return [
            Project.create("Project 1", temp_dir / "project1"),
            Project.create("Project 2", temp_dir / "project2"),
            Project.create("Project 3", temp_dir / "project3"),
        ]
    
    @pytest.fixture
    async def selector_app(self, sample_projects):
        """Create a test app with ProjectSelector."""
        class TestApp(App):
            def compose(self):
                selector = ProjectSelector()
                selector.update_projects(sample_projects)
                yield selector
        
        app = TestApp()
        async with app.run_test() as pilot:
            yield pilot
    
    def test_initial_state(self):
        """Test ProjectSelector initial state."""
        selector = ProjectSelector()
        
        assert selector.projects == []
        assert selector.project_list is None
        assert selector.dialog_container is None
        assert selector.editing_project is None
        assert selector.persistence is not None
    
    def test_update_projects(self, sample_projects):
        """Test updating projects in the selector."""
        selector = ProjectSelector()
        selector.update_projects(sample_projects)
        
        assert len(selector.projects) == 3
        assert selector.projects[0].name == "Project 1"
        assert selector.projects[1].name == "Project 2"
        assert selector.projects[2].name == "Project 3"
    
    def test_update_projects_removes_duplicates(self, sample_projects):
        """Test that update_projects removes duplicate projects."""
        selector = ProjectSelector()
        
        # Add duplicate project
        duplicate_projects = sample_projects + [sample_projects[1]]
        selector.update_projects(duplicate_projects)
        
        # Should only have 3 unique projects
        assert len(selector.projects) == 3
    
    def test_get_current_project(self, sample_projects):
        """Test getting the currently selected project."""
        selector = ProjectSelector()
        selector.update_projects(sample_projects)
        
        # Mock the project_list
        selector.project_list = Mock()
        selector.project_list.index = 1
        
        current = selector.get_current_project()
        assert current == sample_projects[1]
    
    def test_get_current_project_no_selection(self):
        """Test getting current project when nothing is selected."""
        selector = ProjectSelector()
        selector.project_list = Mock()
        selector.project_list.index = None
        
        current = selector.get_current_project()
        assert current is None
    
    def test_select_project(self, sample_projects):
        """Test selecting a project by ID."""
        selector = ProjectSelector()
        selector.update_projects(sample_projects)
        selector.project_list = Mock()
        
        # Select the second project
        project_id = str(sample_projects[1].id)
        selector.select_project(project_id)
        
        assert selector.project_list.index == 1
    
    def test_get_project_count(self, sample_projects):
        """Test getting the project count."""
        selector = ProjectSelector()
        
        assert selector.get_project_count() == 0
        
        selector.update_projects(sample_projects)
        assert selector.get_project_count() == 3
    
    @pytest.mark.asyncio
    async def test_action_new_project(self, selector_app: Pilot):
        """Test the new project action."""
        selector = selector_app.app.query_one(ProjectSelector)
        
        # Trigger new project action
        selector.action_new_project()
        
        # Check that dialog was created
        assert selector.dialog_container is not None
        
        # Check for input fields
        assert selector_app.app.query_one("#project-name-input") is not None
        assert selector_app.app.query_one("#project-path-input") is not None
    
    @pytest.mark.asyncio
    async def test_action_rename_project(self, selector_app: Pilot, sample_projects):
        """Test the rename project action."""
        selector = selector_app.app.query_one(ProjectSelector)
        
        # Mock current project selection
        with patch.object(selector, 'get_current_project', return_value=sample_projects[0]):
            selector.action_rename_project()
        
        # Check that dialog was created
        assert selector.dialog_container is not None
        assert selector.editing_project == sample_projects[0]
        
        # Check for rename input
        assert selector_app.app.query_one("#rename-input") is not None
    
    @pytest.mark.asyncio
    async def test_action_delete_project(self, selector_app: Pilot, sample_projects):
        """Test the delete project action."""
        selector = selector_app.app.query_one(ProjectSelector)
        
        # Mock current project selection
        with patch.object(selector, 'get_current_project', return_value=sample_projects[0]):
            selector.action_delete_project()
        
        # Check that confirmation dialog was created
        assert selector.dialog_container is not None
        assert selector.editing_project == sample_projects[0]
        
        # Check for delete confirmation button
        assert selector_app.app.query_one("#delete-confirm") is not None
    
    def test_close_dialog(self):
        """Test closing a dialog."""
        selector = ProjectSelector()
        selector.project_list = Mock()
        
        # Create a mock dialog
        selector.dialog_container = Mock()
        selector.editing_project = Mock()
        
        # Close the dialog
        selector.close_dialog()
        
        # Check that dialog was removed
        selector.dialog_container.remove.assert_called_once()
        assert selector.dialog_container is None
        assert selector.editing_project is None
        selector.project_list.focus.assert_called_once()
    
    @patch('imthedev.ui.tui.components.project_selector.ProjectPersistenceService')
    def test_load_projects_from_disk(self, mock_persistence_class, temp_dir):
        """Test loading projects from disk."""
        # Setup mock persistence service
        mock_persistence = Mock()
        mock_persistence_class.return_value = mock_persistence
        
        # Mock project data
        mock_project_data = [
            {
                "id": "12345678-1234-5678-1234-567812345678",
                "name": "Loaded Project",
                "path": str(temp_dir / "loaded_project"),
                "created_at": "2024-01-01T00:00:00",
                "settings": {
                    "auto_approve": False,
                    "default_ai_model": "claude",
                    "command_timeout": 300,
                    "environment_vars": {}
                }
            }
        ]
        mock_persistence.list_all_projects.return_value = mock_project_data
        
        # Create selector and load projects
        selector = ProjectSelector()
        selector.load_projects_from_disk([temp_dir])
        
        # Verify projects were loaded
        assert len(selector.projects) == 1
        assert selector.projects[0].name == "Loaded Project"
    
    def test_project_created_message(self, sample_projects):
        """Test ProjectCreated message."""
        project = sample_projects[0]
        message = ProjectSelector.ProjectCreated(project)
        
        assert message.project == project
    
    def test_project_updated_message(self, sample_projects):
        """Test ProjectUpdated message."""
        project = sample_projects[0]
        message = ProjectSelector.ProjectUpdated(project)
        
        assert message.project == project
    
    def test_project_deleted_message(self):
        """Test ProjectDeleted message."""
        project_id = "test-id"
        message = ProjectSelector.ProjectDeleted(project_id)
        
        assert message.project_id == project_id