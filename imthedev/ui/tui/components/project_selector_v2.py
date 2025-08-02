"""Project selector component for imthedev TUI - Version 2.

This module provides a clean, focused widget for displaying and selecting
projects using a ListView with proper key bindings.
Compatible with Textual v5.0.1.
"""

from typing import Any

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, ListItem, ListView


class ProjectSelectorV2(Widget):
    """Widget for selecting and managing projects.

    This component displays a list of available projects and allows users
    to navigate and select them using keyboard controls. It uses ListView
    for proper scrolling and selection management.

    Attributes:
        projects: List of project data (tuples of id, name, path)
        project_list: ListView widget for displaying projects
    """

    # Allow this widget to be focused for keyboard navigation
    can_focus = True

    # Define key bindings for project selection
    BINDINGS = [
        ("enter", "select_project", "Select Project"),
        ("up", "cursor_up", "Previous"),
        ("down", "cursor_down", "Next"),
    ]

    class ProjectSelected(Message):
        """Message sent when a project is selected."""

        def __init__(self, project_id: str, project_name: str) -> None:
            self.project_id = project_id
            self.project_name = project_name
            super().__init__()

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the ProjectSelectorV2 widget."""
        super().__init__(**kwargs)
        self.projects: list[tuple[str, str, str]] = []  # (id, name, path)
        self.project_list: ListView | None = None

    def compose(self) -> ComposeResult:
        """Compose the widget layout with a ListView."""
        self.project_list = ListView(id="project-list-view")
        yield self.project_list

    def on_mount(self) -> None:
        """Called when the widget is mounted. Load sample projects."""
        # Load some sample projects for testing
        sample_projects = [
            ("proj-1", "Demo Project 1", "~/projects/demo1"),
            ("proj-2", "Demo Project 2", "~/projects/demo2"),
            ("proj-3", "Demo Project 3", "~/projects/demo3"),
        ]
        self.update_projects(sample_projects)

    def update_projects(self, projects: list[tuple[str, str, str]]) -> None:
        """Update the project list with new projects.

        Args:
            projects: List of tuples containing (id, name, path)
        """
        self.projects = projects

        if self.project_list is None:
            return

        # Clear existing items
        self.project_list.clear()

        # Add new items
        for project_id, name, path in projects:
            # Create a list item with project info
            list_item = ListItem(
                Label(f"[bold]{name}[/bold]\n[dim]{path}[/dim]"),
                id=f"project-{project_id}",
            )
            self.project_list.append(list_item)

    def action_select_project(self) -> None:
        """Handle the project selection action.

        This is triggered when Enter is pressed while a project is highlighted.
        """
        if self.project_list is None:
            return

        # Get the currently selected index
        index = self.project_list.index
        if index is not None and 0 <= index < len(self.projects):
            project_id, name, path = self.projects[index]
            self.log(f"Project selected: {name} (ID: {project_id})")

            # Post a message that the app can handle
            self.post_message(self.ProjectSelected(project_id, name))

    def action_cursor_up(self) -> None:
        """Move selection up in the list."""
        if self.project_list:
            self.project_list.action_cursor_up()

    def action_cursor_down(self) -> None:
        """Move selection down in the list."""
        if self.project_list:
            self.project_list.action_cursor_down()
