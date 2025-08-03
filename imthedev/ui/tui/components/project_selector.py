"""Project selector component for imthedev TUI.

This module provides a widget for displaying and selecting projects in the TUI.
Compatible with Textual v5.0.1.
"""

from typing import Any

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, ListItem, ListView

from imthedev.core.domain import Project


class ProjectSelector(Widget):
    """Widget for selecting and managing projects.

    This component displays a list of available projects and allows users
    to navigate and select them using keyboard controls.

    Attributes:
        projects: List of available projects
        project_list: ListView widget for displaying projects
    """

    # Allow this widget to be focused so it can handle selection
    can_focus = True

    # Define key bindings for project selection
    BINDINGS = [
        ("enter", "select_project", "Select Project"),
    ]

    DEFAULT_CSS = """
    ProjectSelector {
        border: solid $primary;
        height: 100%;
        width: 100%;
    }

    ProjectSelector > ListView {
        height: 100%;
        width: 100%;
        scrollbar-size-vertical: 1;
        scrollbar-color: $accent;
    }

    ProjectSelector > ListView > ListItem {
        padding: 0 1;
        height: 3;
    }

    ProjectSelector > ListView > ListItem.--highlight {
        background: $primary 20%;
    }

    ProjectSelector .project-name {
        text-style: bold;
        color: $text;
    }

    ProjectSelector .project-path {
        color: $text-muted;
        text-style: italic;
    }

    ProjectSelector .project-date {
        color: $accent;
    }
    """

    class ProjectSelected(Message):
        """Message sent when a project is selected."""

        def __init__(self, project: Project) -> None:
            self.project = project
            super().__init__()

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the ProjectSelector widget."""
        super().__init__(**kwargs)
        self.projects: list[Project] = []
        self.project_list: ListView | None = None

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        self.project_list = ListView()
        yield self.project_list

    def update_projects(self, projects: list[Project]) -> None:
        """Update the project list with new projects.

        Args:
            projects: List of projects to display
        """
        # Remove any duplicate projects (by ID) to prevent DuplicateIds error
        seen_ids = set()
        unique_projects = []
        for project in projects:
            if project.id not in seen_ids:
                seen_ids.add(project.id)
                unique_projects.append(project)
        
        self.projects = unique_projects

        if self.project_list is None:
            return

        # Clear existing items by removing all children
        self.project_list.clear()

        # Create ListItems for each project with unique widget IDs
        items = []
        for i, project in enumerate(unique_projects):
            project_item = self._create_project_item(project)
            # Ensure unique widget ID even if project IDs somehow collide
            # Use index as fallback to guarantee uniqueness
            if project_item.id in [item.id for item in items]:
                project_item.id = f"project-{project.id}-{i}"
            items.append(project_item)

        # Add all items at once
        if items:
            for item in items:
                self.project_list.append(item)
            # Select first item if available
            self.project_list.index = 0

        # Force refresh to update display
        self.refresh()

    def _create_project_item(self, project: Project) -> ListItem:
        """Create a ListItem for a project.

        Args:
            project: Project to create item for

        Returns:
            ListItem widget configured for the project
        """
        # Format creation date
        created_date = project.created_at.strftime("%Y-%m-%d %H:%M")

        # Create project display with name, path, and date
        project_display = Label(
            f"[bold]{project.name}[/bold]\n"
            f"[dim]{project.path}[/dim]\n"
            f"[accent]Created: {created_date}[/accent]"
        )

        return ListItem(project_display, id=f"project-{project.id}")

    def get_current_project(self) -> Project | None:
        """Get the currently selected project.

        Returns:
            Currently selected project or None if no selection
        """
        if not self.projects or self.project_list is None:
            return None

        current_index = self.project_list.index
        if current_index is None or current_index >= len(self.projects):
            return None

        return self.projects[current_index]

    def select_project(self, project_id: str) -> None:
        """Select a project by its ID.

        Args:
            project_id: ID of the project to select
        """
        if not self.projects or self.project_list is None:
            return

        for index, project in enumerate(self.projects):
            if str(project.id) == project_id:
                self.project_list.index = index
                break

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle ListView selection events.

        Args:
            event: The selection event
        """
        # Only handle events from our own ListView
        if event.list_view != self.project_list:
            return

        # Get the currently selected project and post selection message
        current_project = self.get_current_project()
        if current_project:
            self.post_message(self.ProjectSelected(current_project))

    def action_select_project(self) -> None:
        """Action to select the currently highlighted project."""
        if self.project_list is None or not self.projects:
            return

        current_project = self.get_current_project()
        if current_project:
            self.post_message(self.ProjectSelected(current_project))

    def clear_selection(self) -> None:
        """Clear the current selection."""
        if self.project_list:
            self.project_list.index = None

    def refresh_display(self) -> None:
        """Refresh the project display."""
        if self.project_list:
            self.project_list.refresh()

    def get_project_count(self) -> int:
        """Get the number of projects in the list.

        Returns:
            Number of projects currently displayed
        """
        return len(self.projects)
