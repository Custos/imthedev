"""Tests for the ProjectSelector TUI component.

This module contains comprehensive tests for the ProjectSelector widget including
ListView integration, project display, keyboard navigation, and selection events.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from imthedev.core.domain import Project, ProjectSettings, ProjectContext
from imthedev.ui.tui.components.project_selector import ProjectSelector


class TestProjectSelector:
    """Test suite for ProjectSelector component."""
    
    @pytest.fixture
    def sample_projects(self):
        """Create sample projects for testing."""
        return [
            Project(
                id=uuid4(),
                name="Test Project 1",
                path=Path("/home/user/project1"),
                created_at=datetime(2024, 1, 1, 10, 0, 0),
                context=ProjectContext(),
                settings=ProjectSettings()
            ),
            Project(
                id=uuid4(),
                name="Test Project 2",
                path=Path("/home/user/project2"),
                created_at=datetime(2024, 1, 2, 11, 30, 0),
                context=ProjectContext(),
                settings=ProjectSettings()
            ),
            Project(
                id=uuid4(),
                name="Another Project",
                path=Path("/home/user/another"),
                created_at=datetime(2024, 1, 3, 14, 15, 0),
                context=ProjectContext(),
                settings=ProjectSettings()
            )
        ]
    
    def test_initialization(self):
        """Test ProjectSelector initialization."""
        selector = ProjectSelector()
        
        assert selector.projects == []
        assert selector.project_list is None
        assert selector.get_project_count() == 0
    
    def test_compose_method(self):
        """Test that compose method creates ListView."""
        selector = ProjectSelector()
        
        # Call compose and check it returns a generator
        composed = selector.compose()
        widgets = list(composed)
        
        assert len(widgets) == 1
        # Check that project_list is set after compose
        assert selector.project_list is not None
    
    def test_update_projects_empty_list(self):
        """Test updating with empty project list."""
        selector = ProjectSelector()
        # Set up project_list as if compose was called
        selector.project_list = MagicMock()
        
        with patch.object(selector, 'refresh') as mock_refresh:
            selector.update_projects([])
        
            assert selector.projects == []
            selector.project_list.clear.assert_called_once()
            selector.project_list.append.assert_not_called()
            # Should still refresh to update display
            mock_refresh.assert_called_once()
    
    def test_update_projects_with_data(self, sample_projects):
        """Test updating with project data."""
        selector = ProjectSelector()
        # Mock the ListView
        mock_list_view = MagicMock()
        mock_list_view.children = [MagicMock(), MagicMock(), MagicMock()]  # Mock 3 children
        selector.project_list = mock_list_view
        
        # Mock refresh method
        with patch.object(selector, 'refresh') as mock_refresh:
            selector.update_projects(sample_projects)
        
            assert selector.projects == sample_projects
            assert selector.get_project_count() == 3
            
            # Verify ListView operations
            mock_list_view.clear.assert_called_once()
            assert mock_list_view.append.call_count == 3
            # Should select first item
            assert mock_list_view.index == 0
            # Should refresh display
            mock_refresh.assert_called_once()
    
    def test_update_projects_no_list_view(self, sample_projects):
        """Test updating projects when ListView is not initialized."""
        selector = ProjectSelector()
        # project_list is None
        
        selector.update_projects(sample_projects)
        
        # Should still update projects list
        assert selector.projects == sample_projects
        assert selector.get_project_count() == 3
    
    def test_create_project_item(self, sample_projects):
        """Test creation of project list items."""
        selector = ProjectSelector()
        project = sample_projects[0]
        
        with patch('imthedev.ui.tui.components.project_selector.ListItem') as mock_list_item, \
             patch('imthedev.ui.tui.components.project_selector.Label') as mock_label:
            
            mock_label_instance = MagicMock()
            mock_label.return_value = mock_label_instance
            mock_list_item_instance = MagicMock()
            mock_list_item.return_value = mock_list_item_instance
            
            result = selector._create_project_item(project)
            
            # Verify Label was created with project info
            mock_label.assert_called_once()
            label_text = mock_label.call_args[0][0]
            assert "Test Project 1" in label_text
            assert "/home/user/project1" in label_text
            assert "2024-01-01 10:00" in label_text
            
            # Verify ListItem was created with label and ID
            mock_list_item.assert_called_once_with(
                mock_label_instance, 
                id=f"project-{project.id}"
            )
            
            assert result == mock_list_item_instance
    
    def test_get_current_project_no_projects(self):
        """Test getting current project when no projects loaded."""
        selector = ProjectSelector()
        
        result = selector.get_current_project()
        assert result is None
    
    def test_get_current_project_no_list_view(self, sample_projects):
        """Test getting current project when ListView not initialized."""
        selector = ProjectSelector()
        selector.projects = sample_projects
        
        result = selector.get_current_project()
        assert result is None
    
    def test_get_current_project_no_selection(self, sample_projects):
        """Test getting current project when no item selected."""
        selector = ProjectSelector()
        selector.projects = sample_projects
        mock_list_view = MagicMock()
        mock_list_view.index = None
        selector.project_list = mock_list_view
        
        result = selector.get_current_project()
        assert result is None
    
    def test_get_current_project_valid_selection(self, sample_projects):
        """Test getting current project with valid selection."""
        selector = ProjectSelector()
        selector.projects = sample_projects
        mock_list_view = MagicMock()
        mock_list_view.index = 1  # Select second project
        selector.project_list = mock_list_view
        
        result = selector.get_current_project()
        assert result == sample_projects[1]
        assert result.name == "Test Project 2"
    
    def test_get_current_project_invalid_index(self, sample_projects):
        """Test getting current project with invalid index."""
        selector = ProjectSelector()
        selector.projects = sample_projects
        mock_list_view = MagicMock()
        mock_list_view.index = 5  # Out of bounds
        selector.project_list = mock_list_view
        
        result = selector.get_current_project()
        assert result is None
    
    def test_select_project_by_id(self, sample_projects):
        """Test selecting project by ID."""
        selector = ProjectSelector()
        selector.projects = sample_projects
        mock_list_view = MagicMock()
        selector.project_list = mock_list_view
        
        target_project = sample_projects[2]
        selector.select_project(str(target_project.id))
        
        assert mock_list_view.index == 2
    
    def test_select_project_invalid_id(self, sample_projects):
        """Test selecting project by non-existent ID."""
        selector = ProjectSelector()
        selector.projects = sample_projects
        mock_list_view = MagicMock()
        mock_list_view.index = 0  # Initial value
        selector.project_list = mock_list_view
        
        selector.select_project("non-existent-id")
        
        # Index should remain unchanged
        assert mock_list_view.index == 0
    
    def test_select_project_no_projects(self):
        """Test selecting project when no projects loaded."""
        selector = ProjectSelector()
        mock_list_view = MagicMock()
        selector.project_list = mock_list_view
        
        selector.select_project("some-id")
        
        # Should not change index
        assert not hasattr(mock_list_view, 'index') or mock_list_view.index is None
    
    @pytest.mark.asyncio
    async def test_on_list_view_selected(self, sample_projects):
        """Test ListView selection event handling."""
        selector = ProjectSelector()
        selector.projects = sample_projects
        mock_list_view = MagicMock()
        mock_list_view.index = 1
        selector.project_list = mock_list_view
        
        # Mock the event
        mock_event = MagicMock()
        mock_event.list_view = mock_list_view
        
        with patch.object(selector, 'post_message', new_callable=AsyncMock) as mock_post:
            await selector.on_list_view_selected(mock_event)
            
            # Should post ProjectSelected message
            mock_post.assert_called_once()
            message = mock_post.call_args[0][0]
            assert isinstance(message, ProjectSelector.ProjectSelected)
            assert message.project == sample_projects[1]
    
    @pytest.mark.asyncio
    async def test_on_list_view_selected_wrong_list(self):
        """Test ListView selection event from different ListView."""
        selector = ProjectSelector()
        mock_list_view = MagicMock()
        selector.project_list = mock_list_view
        
        # Mock event from different ListView
        mock_event = MagicMock()
        mock_event.list_view = MagicMock()  # Different ListView
        
        with patch.object(selector, 'post_message', new_callable=AsyncMock) as mock_post:
            await selector.on_list_view_selected(mock_event)
            
            # Should not post message
            mock_post.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_on_list_view_selected_no_project(self):
        """Test ListView selection event when no project selected."""
        selector = ProjectSelector()
        mock_list_view = MagicMock()
        mock_list_view.index = None
        selector.project_list = mock_list_view
        
        mock_event = MagicMock()
        mock_event.list_view = mock_list_view
        
        with patch.object(selector, 'post_message', new_callable=AsyncMock) as mock_post:
            await selector.on_list_view_selected(mock_event)
            
            # Should not post message
            mock_post.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_on_key_enter(self, sample_projects):
        """Test Enter key handling."""
        selector = ProjectSelector()
        selector.projects = sample_projects
        mock_list_view = MagicMock()
        mock_list_view.index = 0
        selector.project_list = mock_list_view
        
        # Create key event
        mock_event = MagicMock()
        mock_event.key = "enter"
        
        with patch.object(selector, 'post_message', new_callable=AsyncMock) as mock_post:
            await selector.on_key(mock_event)
            
            # Should post ProjectSelected message
            mock_post.assert_called_once()
            message = mock_post.call_args[0][0]
            assert isinstance(message, ProjectSelector.ProjectSelected)
            assert message.project == sample_projects[0]
            
            # Should prevent default
            mock_event.prevent_default.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_on_key_enter_no_project(self):
        """Test Enter key handling when no project selected."""
        selector = ProjectSelector()
        mock_list_view = MagicMock()
        mock_list_view.index = None
        selector.project_list = mock_list_view
        
        mock_event = MagicMock()
        mock_event.key = "enter"
        
        with patch.object(selector, 'post_message', new_callable=AsyncMock) as mock_post:
            await selector.on_key(mock_event)
            
            # Should not post message
            mock_post.assert_not_called()
            mock_event.prevent_default.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_on_key_navigation_keys(self, sample_projects):
        """Test navigation key handling."""
        selector = ProjectSelector()
        selector.projects = sample_projects
        mock_list_view = MagicMock()
        selector.project_list = mock_list_view
        
        navigation_keys = ["up", "down", "page_up", "page_down", "home", "end"]
        
        for key in navigation_keys:
            mock_event = MagicMock()
            mock_event.key = key
            
            await selector.on_key(mock_event)
            
            # Should forward to ListView
            mock_list_view.on_key.assert_called_with(mock_event)
    
    @pytest.mark.asyncio
    async def test_on_key_other_keys(self, sample_projects):
        """Test handling of non-navigation keys."""
        selector = ProjectSelector()
        selector.projects = sample_projects
        mock_list_view = MagicMock()
        selector.project_list = mock_list_view
        
        mock_event = MagicMock()
        mock_event.key = "space"
        
        await selector.on_key(mock_event)
        
        # Should not forward to ListView
        mock_list_view.on_key.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_on_key_no_projects(self):
        """Test key handling when no projects loaded."""
        selector = ProjectSelector()
        mock_list_view = MagicMock()
        selector.project_list = mock_list_view
        
        mock_event = MagicMock()
        mock_event.key = "enter"
        
        with patch.object(selector, 'post_message', new_callable=AsyncMock) as mock_post:
            await selector.on_key(mock_event)
            
            # Should not process key
            mock_post.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_on_key_no_list_view(self, sample_projects):
        """Test key handling when ListView not initialized."""
        selector = ProjectSelector()
        selector.projects = sample_projects
        # project_list is None
        
        mock_event = MagicMock()
        mock_event.key = "enter"
        
        with patch.object(selector, 'post_message', new_callable=AsyncMock) as mock_post:
            await selector.on_key(mock_event)
            
            # Should not process key
            mock_post.assert_not_called()
    
    def test_clear_selection(self):
        """Test clearing selection."""
        selector = ProjectSelector()
        mock_list_view = MagicMock()
        mock_list_view.index = 2
        selector.project_list = mock_list_view
        
        selector.clear_selection()
        
        assert mock_list_view.index is None
    
    def test_clear_selection_no_list_view(self):
        """Test clearing selection when ListView not initialized."""
        selector = ProjectSelector()
        # Should not raise exception
        selector.clear_selection()
    
    def test_refresh_display(self):
        """Test refreshing display."""
        selector = ProjectSelector()
        mock_list_view = MagicMock()
        selector.project_list = mock_list_view
        
        selector.refresh_display()
        
        mock_list_view.refresh.assert_called_once()
    
    def test_refresh_display_no_list_view(self):
        """Test refreshing display when ListView not initialized."""
        selector = ProjectSelector()
        # Should not raise exception
        selector.refresh_display()
    
    def test_update_projects_triggers_visual_refresh(self, sample_projects):
        """Test that update_projects triggers a visual refresh of the component."""
        selector = ProjectSelector()
        mock_list_view = MagicMock()
        selector.project_list = mock_list_view
        
        # Mock the refresh method to verify it's called
        with patch.object(selector, 'refresh') as mock_refresh:
            selector.update_projects(sample_projects)
            
            # Verify refresh was called to update the visual display
            mock_refresh.assert_called_once()
            
            # Verify items were added
            assert mock_list_view.append.call_count == len(sample_projects)


class TestProjectSelectedMessage:
    """Test suite for ProjectSelected message."""
    
    def test_project_selected_message_creation(self):
        """Test ProjectSelected message creation."""
        project = Project(
            id=uuid4(),
            name="Test Project",
            path=Path("/test/path"),
            created_at=datetime.now(),
            context=ProjectContext(),
            settings=ProjectSettings()
        )
        
        message = ProjectSelector.ProjectSelected(project)
        
        assert message.project == project
        assert isinstance(message, ProjectSelector.ProjectSelected)


class TestProjectSelectorIntegration:
    """Integration tests for ProjectSelector component."""
    
    @pytest.fixture
    def selector_with_projects(self, sample_projects):
        """Create ProjectSelector with sample projects loaded."""
        selector = ProjectSelector()
        # Mock ListView to simulate compose being called
        mock_list_view = MagicMock()
        mock_list_view.children = [MagicMock() for _ in sample_projects]
        selector.project_list = mock_list_view
        selector.update_projects(sample_projects)
        return selector
    
    @pytest.fixture
    def sample_projects(self):
        """Create sample projects for integration testing."""
        return [
            Project(
                id=uuid4(),
                name="Frontend App",
                path=Path("/home/user/frontend"),
                created_at=datetime(2024, 1, 1, 9, 0, 0),
                context=ProjectContext(),
                settings=ProjectSettings(auto_approve=False)
            ),
            Project(
                id=uuid4(),
                name="Backend API",
                path=Path("/home/user/backend"),
                created_at=datetime(2024, 1, 2, 10, 0, 0),
                context=ProjectContext(),
                settings=ProjectSettings(auto_approve=True)
            )
        ]
    
    def test_full_project_workflow(self, selector_with_projects, sample_projects):
        """Test complete project selection workflow."""
        selector = selector_with_projects
        
        # Should have projects loaded
        assert selector.get_project_count() == 2
        
        # Should have first project selected by default
        current = selector.get_current_project()
        assert current == sample_projects[0]
        assert current.name == "Frontend App"
        
        # Should be able to select by ID
        backend_project = sample_projects[1]
        selector.select_project(str(backend_project.id))
        assert selector.project_list.index == 1
        
        # Should get correct current project
        current = selector.get_current_project()
        assert current == backend_project
        assert current.name == "Backend API"
    
    @pytest.mark.asyncio
    async def test_event_driven_selection(self, selector_with_projects, sample_projects):
        """Test event-driven project selection."""
        selector = selector_with_projects
        
        # Mock message posting
        with patch.object(selector, 'post_message', new_callable=AsyncMock) as mock_post:
            # Simulate ListView selection
            mock_event = MagicMock()
            mock_event.list_view = selector.project_list
            selector.project_list.index = 1
            
            await selector.on_list_view_selected(mock_event)
            
            # Should post correct message
            mock_post.assert_called_once()
            message = mock_post.call_args[0][0]
            assert message.project == sample_projects[1]
    
    def test_project_metadata_display(self, sample_projects):
        """Test that project metadata is properly formatted for display."""
        selector = ProjectSelector()
        project = sample_projects[0]
        
        # Test item creation
        with patch('imthedev.ui.tui.components.project_selector.ListItem') as mock_list_item, \
             patch('imthedev.ui.tui.components.project_selector.Label') as mock_label:
            
            selector._create_project_item(project)
            
            # Verify formatted display text
            label_text = mock_label.call_args[0][0]
            assert "[bold]Frontend App[/bold]" in label_text
            assert "[dim]/home/user/frontend[/dim]" in label_text
            assert "[accent]Created: 2024-01-01 09:00[/accent]" in label_text