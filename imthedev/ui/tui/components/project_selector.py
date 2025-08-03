"""Project selector component for imthedev TUI.

This module provides a widget for displaying and selecting projects in the TUI.
Compatible with Textual v5.0.1.
"""

from pathlib import Path
from typing import Any, Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Input, Label, ListItem, ListView, Static

from imthedev.core.domain import Project
from imthedev.core.services.project_persistence import ProjectPersistenceService


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

    # Define key bindings for project selection and management
    BINDINGS = [
        ("enter", "select_project", "Select Project"),
        ("n", "new_project", "New Project"),
        ("f2", "rename_project", "Rename Project"),
        ("delete", "delete_project", "Delete Project"),
        ("r", "refresh_projects", "Refresh List"),
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
    
    ProjectSelector .dialog-overlay {
        align: center middle;
        background: $surface 90%;
        layer: overlay;
    }
    
    ProjectSelector .dialog-box {
        border: double $primary;
        background: $panel;
        padding: 1 2;
        width: 60;
        height: auto;
    }
    
    ProjectSelector .dialog-title {
        text-style: bold;
        margin-bottom: 1;
    }
    
    ProjectSelector .dialog-buttons {
        margin-top: 1;
        align: center middle;
    }
    
    ProjectSelector .dialog-buttons Button {
        margin: 0 1;
    }
    """

    class ProjectSelected(Message):
        """Message sent when a project is selected."""

        def __init__(self, project: Project) -> None:
            self.project = project
            super().__init__()
    
    class ProjectCreated(Message):
        """Message sent when a new project is created."""
        
        def __init__(self, project: Project) -> None:
            self.project = project
            super().__init__()
    
    class ProjectUpdated(Message):
        """Message sent when a project is updated."""
        
        def __init__(self, project: Project) -> None:
            self.project = project
            super().__init__()
    
    class ProjectDeleted(Message):
        """Message sent when a project is deleted."""
        
        def __init__(self, project_id: str) -> None:
            self.project_id = project_id
            super().__init__()

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the ProjectSelector widget."""
        super().__init__(**kwargs)
        self.projects: list[Project] = []
        self.project_list: ListView | None = None
        self.persistence = ProjectPersistenceService()
        self.dialog_container: Optional[Container] = None
        self.editing_project: Optional[Project] = None

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        with Container():
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
    
    # ============== CRUD Operations ==============
    
    def action_new_project(self) -> None:
        """Show dialog to create a new project."""
        self.show_create_dialog()
    
    def action_rename_project(self) -> None:
        """Show dialog to rename the current project."""
        current_project = self.get_current_project()
        if current_project:
            self.show_rename_dialog(current_project)
    
    def action_delete_project(self) -> None:
        """Show confirmation dialog to delete the current project."""
        current_project = self.get_current_project()
        if current_project:
            self.show_delete_confirmation(current_project)
    
    def action_refresh_projects(self) -> None:
        """Refresh the project list from disk."""
        self.load_projects_from_disk()
    
    def show_create_dialog(self) -> None:
        """Display the create project dialog."""
        if self.dialog_container:
            return  # Dialog already open
        
        self.dialog_container = Container(
            Vertical(
                Static("Create New Project", classes="dialog-title"),
                Label("Project Name:"),
                Input(placeholder="Enter project name", id="project-name-input"),
                Label("Project Path:"),
                Input(placeholder="Enter project path", id="project-path-input"),
                Horizontal(
                    Button("Create", variant="primary", id="create-confirm"),
                    Button("Cancel", variant="default", id="create-cancel"),
                    classes="dialog-buttons"
                ),
                classes="dialog-box"
            ),
            classes="dialog-overlay"
        )
        self.mount(self.dialog_container)
        
        # Focus the name input
        name_input = self.query_one("#project-name-input", Input)
        name_input.focus()
    
    def show_rename_dialog(self, project: Project) -> None:
        """Display the rename project dialog."""
        if self.dialog_container:
            return  # Dialog already open
        
        self.editing_project = project
        self.dialog_container = Container(
            Vertical(
                Static(f"Rename Project: {project.name}", classes="dialog-title"),
                Label("New Name:"),
                Input(value=project.name, id="rename-input"),
                Horizontal(
                    Button("Rename", variant="primary", id="rename-confirm"),
                    Button("Cancel", variant="default", id="rename-cancel"),
                    classes="dialog-buttons"
                ),
                classes="dialog-box"
            ),
            classes="dialog-overlay"
        )
        self.mount(self.dialog_container)
        
        # Focus and select all text in the input
        rename_input = self.query_one("#rename-input", Input)
        rename_input.focus()
    
    def show_delete_confirmation(self, project: Project) -> None:
        """Display the delete confirmation dialog."""
        if self.dialog_container:
            return  # Dialog already open
        
        self.editing_project = project
        self.dialog_container = Container(
            Vertical(
                Static("Delete Project", classes="dialog-title"),
                Label(f"Are you sure you want to delete '{project.name}'?"),
                Label("[dim]This will remove the .imthedev directory[/dim]"),
                Horizontal(
                    Button("Delete", variant="error", id="delete-confirm"),
                    Button("Cancel", variant="default", id="delete-cancel"),
                    classes="dialog-buttons"
                ),
                classes="dialog-box"
            ),
            classes="dialog-overlay"
        )
        self.mount(self.dialog_container)
    
    def close_dialog(self) -> None:
        """Close any open dialog."""
        if self.dialog_container:
            self.dialog_container.remove()
            self.dialog_container = None
            self.editing_project = None
            self.project_list.focus()
    
    # ============== Button Handlers ==============
    
    @on(Button.Pressed, "#create-confirm")
    def handle_create_confirm(self) -> None:
        """Handle create project confirmation."""
        name_input = self.query_one("#project-name-input", Input)
        path_input = self.query_one("#project-path-input", Input)
        
        name = name_input.value.strip()
        path = path_input.value.strip()
        
        if name and path:
            # Create the project
            project_path = Path(path).expanduser().resolve()
            new_project = Project.create(name, project_path)
            
            # Initialize project directory
            try:
                project_path.mkdir(parents=True, exist_ok=True)
                self.persistence.initialize_project_directory(new_project)
                
                # Add to list and update display
                self.projects.append(new_project)
                self.update_projects(self.projects)
                
                # Post creation message
                self.post_message(self.ProjectCreated(new_project))
                
                # Select the new project
                self.select_project(str(new_project.id))
            except OSError as e:
                # TODO: Show error message
                pass
        
        self.close_dialog()
    
    @on(Button.Pressed, "#create-cancel")
    def handle_create_cancel(self) -> None:
        """Handle create project cancellation."""
        self.close_dialog()
    
    @on(Button.Pressed, "#rename-confirm")
    def handle_rename_confirm(self) -> None:
        """Handle rename project confirmation."""
        if not self.editing_project:
            self.close_dialog()
            return
        
        rename_input = self.query_one("#rename-input", Input)
        new_name = rename_input.value.strip()
        
        if new_name and new_name != self.editing_project.name:
            # Update project name
            self.persistence.rename_project(self.editing_project, new_name)
            
            # Update display
            self.update_projects(self.projects)
            
            # Post update message
            self.post_message(self.ProjectUpdated(self.editing_project))
        
        self.close_dialog()
    
    @on(Button.Pressed, "#rename-cancel")
    def handle_rename_cancel(self) -> None:
        """Handle rename project cancellation."""
        self.close_dialog()
    
    @on(Button.Pressed, "#delete-confirm")
    def handle_delete_confirm(self) -> None:
        """Handle delete project confirmation."""
        if not self.editing_project:
            self.close_dialog()
            return
        
        # Delete project data
        self.persistence.delete_project_data(self.editing_project.path)
        
        # Remove from list
        project_id = str(self.editing_project.id)
        self.projects = [p for p in self.projects if str(p.id) != project_id]
        self.update_projects(self.projects)
        
        # Post deletion message
        self.post_message(self.ProjectDeleted(project_id))
        
        self.close_dialog()
    
    @on(Button.Pressed, "#delete-cancel")
    def handle_delete_cancel(self) -> None:
        """Handle delete project cancellation."""
        self.close_dialog()
    
    def load_projects_from_disk(self, base_paths: Optional[list[Path]] = None) -> None:
        """Load all projects from disk.
        
        Args:
            base_paths: Optional list of paths to scan for projects.
                       Defaults to user home and common project directories.
        """
        if base_paths is None:
            base_paths = [
                Path.home() / "projects",
                Path.home() / "code",
                Path.home() / "dev",
                Path.home() / "workspace",
            ]
        
        # Load project metadata from disk
        project_data = self.persistence.list_all_projects(base_paths)
        
        # Convert to Project objects
        from datetime import datetime
        from uuid import UUID
        
        projects = []
        for data in project_data:
            project = Project(
                id=UUID(data["id"]),
                name=data["name"],
                path=Path(data["path"]),
                created_at=datetime.fromisoformat(data["created_at"]),
                context=ProjectContext(),  # Will be loaded when project is selected
                settings=ProjectSettings(
                    auto_approve=data["settings"].get("auto_approve", False),
                    default_ai_model=data["settings"].get("default_ai_model", "claude"),
                    command_timeout=data["settings"].get("command_timeout", 300),
                    environment_vars=data["settings"].get("environment_vars", {}),
                )
            )
            projects.append(project)
        
        # Update display
        self.update_projects(projects)
