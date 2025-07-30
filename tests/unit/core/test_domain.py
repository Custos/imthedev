"""Unit tests for core domain models."""

from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from imthedev.core.domain import (
    Command,
    CommandResult,
    CommandStatus,
    Project,
    ProjectContext,
    ProjectSettings,
)


class TestCommandStatus:
    """Test the CommandStatus enum."""
    
    def test_command_status_values(self):
        """Test that all expected status values exist."""
        assert CommandStatus.PROPOSED.value == "proposed"
        assert CommandStatus.APPROVED.value == "approved"
        assert CommandStatus.REJECTED.value == "rejected"
        assert CommandStatus.EXECUTING.value == "executing"
        assert CommandStatus.COMPLETED.value == "completed"
        assert CommandStatus.FAILED.value == "failed"
    
    def test_command_status_members(self):
        """Test that we can iterate over status values."""
        statuses = list(CommandStatus)
        assert len(statuses) == 6
        assert CommandStatus.PROPOSED in statuses


class TestCommandResult:
    """Test the CommandResult dataclass."""
    
    def test_command_result_creation(self):
        """Test creating a CommandResult with all fields."""
        result = CommandResult(
            exit_code=0,
            stdout="Success output",
            stderr="",
            execution_time=1.5
        )
        
        assert result.exit_code == 0
        assert result.stdout == "Success output"
        assert result.stderr == ""
        assert result.execution_time == 1.5
        assert isinstance(result.timestamp, datetime)
    
    def test_command_result_with_error(self):
        """Test creating a CommandResult for a failed command."""
        result = CommandResult(
            exit_code=1,
            stdout="",
            stderr="Error: Command not found",
            execution_time=0.1
        )
        
        assert result.exit_code == 1
        assert result.stderr == "Error: Command not found"


class TestCommand:
    """Test the Command dataclass."""
    
    def test_command_creation(self):
        """Test creating a Command with required fields."""
        project_id = uuid4()
        command = Command(
            id=uuid4(),
            project_id=project_id,
            command_text="git init",
            ai_reasoning="Initialize a new git repository",
            status=CommandStatus.PROPOSED
        )
        
        assert isinstance(command.id, UUID)
        assert command.project_id == project_id
        assert command.command_text == "git init"
        assert command.ai_reasoning == "Initialize a new git repository"
        assert command.status == CommandStatus.PROPOSED
        assert command.result is None
        assert isinstance(command.timestamp, datetime)
    
    def test_command_with_result(self):
        """Test creating a Command with an execution result."""
        result = CommandResult(
            exit_code=0,
            stdout="Initialized empty Git repository",
            stderr="",
            execution_time=0.5
        )
        
        command = Command(
            id=uuid4(),
            project_id=uuid4(),
            command_text="git init",
            ai_reasoning="Initialize repository",
            status=CommandStatus.COMPLETED,
            result=result
        )
        
        assert command.status == CommandStatus.COMPLETED
        assert command.result == result
        assert command.result.exit_code == 0


class TestProjectContext:
    """Test the ProjectContext dataclass."""
    
    def test_project_context_creation_defaults(self):
        """Test creating a ProjectContext with default values."""
        context = ProjectContext()
        
        assert context.history == []
        assert context.current_state == {}
        assert context.ai_memory == ""
        assert context.metadata == {}
    
    def test_project_context_with_history(self):
        """Test creating a ProjectContext with command history."""
        commands = [
            Command(
                id=uuid4(),
                project_id=uuid4(),
                command_text="mkdir src",
                ai_reasoning="Create source directory",
                status=CommandStatus.COMPLETED
            )
        ]
        
        context = ProjectContext(
            history=commands,
            current_state={"initialized": True},
            ai_memory="Previous conversation context",
            metadata={"version": "1.0"}
        )
        
        assert len(context.history) == 1
        assert context.history[0].command_text == "mkdir src"
        assert context.current_state["initialized"] is True
        assert context.ai_memory == "Previous conversation context"
        assert context.metadata["version"] == "1.0"


class TestProjectSettings:
    """Test the ProjectSettings dataclass."""
    
    def test_project_settings_defaults(self):
        """Test creating ProjectSettings with default values."""
        settings = ProjectSettings()
        
        assert settings.auto_approve is False
        assert settings.default_ai_model == "claude"
        assert settings.command_timeout == 300
        assert settings.environment_vars == {}
    
    def test_project_settings_custom(self):
        """Test creating ProjectSettings with custom values."""
        settings = ProjectSettings(
            auto_approve=True,
            default_ai_model="gpt-4",
            command_timeout=600,
            environment_vars={"API_KEY": "test-key"}
        )
        
        assert settings.auto_approve is True
        assert settings.default_ai_model == "gpt-4"
        assert settings.command_timeout == 600
        assert settings.environment_vars["API_KEY"] == "test-key"


class TestProject:
    """Test the Project dataclass."""
    
    def test_project_creation(self):
        """Test creating a Project with all required fields."""
        project_id = uuid4()
        path = Path("/home/user/projects/test")
        context = ProjectContext()
        settings = ProjectSettings()
        
        project = Project(
            id=project_id,
            name="Test Project",
            path=path,
            created_at=datetime.now(),
            context=context,
            settings=settings
        )
        
        assert project.id == project_id
        assert project.name == "Test Project"
        assert project.path == path
        assert isinstance(project.created_at, datetime)
        assert project.context == context
        assert project.settings == settings
    
    def test_project_path_conversion(self):
        """Test that string paths are converted to Path objects."""
        project = Project(
            id=uuid4(),
            name="Test",
            path="/home/user/project",  # String path
            created_at=datetime.now(),
            context=ProjectContext(),
            settings=ProjectSettings()
        )
        
        assert isinstance(project.path, Path)
        assert str(project.path) == "/home/user/project"
    
    def test_project_create_factory(self):
        """Test the Project.create factory method."""
        path = Path("/home/user/new-project")
        project = Project.create(
            name="New Project",
            path=path
        )
        
        assert isinstance(project.id, UUID)
        assert project.name == "New Project"
        assert project.path == path
        assert isinstance(project.created_at, datetime)
        assert isinstance(project.context, ProjectContext)
        assert isinstance(project.settings, ProjectSettings)
        assert project.settings.auto_approve is False  # Default
    
    def test_project_create_with_settings(self):
        """Test Project.create with custom settings."""
        custom_settings = ProjectSettings(
            auto_approve=True,
            default_ai_model="gpt-4"
        )
        
        project = Project.create(
            name="Custom Project",
            path=Path("/tmp/custom"),
            settings=custom_settings
        )
        
        assert project.settings == custom_settings
        assert project.settings.auto_approve is True
        assert project.settings.default_ai_model == "gpt-4"


class TestDomainModelIntegration:
    """Integration tests for domain models working together."""
    
    def test_project_with_command_history(self):
        """Test a project with a full command history."""
        project = Project.create(
            name="Integration Test",
            path=Path("/tmp/integration")
        )
        
        # Add commands to history
        command1 = Command(
            id=uuid4(),
            project_id=project.id,
            command_text="git init",
            ai_reasoning="Initialize repository",
            status=CommandStatus.COMPLETED,
            result=CommandResult(0, "Initialized", "", 0.5)
        )
        
        command2 = Command(
            id=uuid4(),
            project_id=project.id,
            command_text="echo 'Hello World' > README.md",
            ai_reasoning="Create README file",
            status=CommandStatus.PROPOSED
        )
        
        project.context.history.extend([command1, command2])
        
        assert len(project.context.history) == 2
        assert project.context.history[0].status == CommandStatus.COMPLETED
        assert project.context.history[1].status == CommandStatus.PROPOSED
        assert project.context.history[0].result is not None
        assert project.context.history[1].result is None
    
    def test_project_state_management(self):
        """Test managing project state through context."""
        project = Project.create(
            name="State Test",
            path=Path("/tmp/state")
        )
        
        # Update project state
        project.context.current_state["git_initialized"] = True
        project.context.current_state["files_created"] = ["README.md", "src/main.py"]
        project.context.ai_memory = "User prefers TypeScript for this project"
        
        assert project.context.current_state["git_initialized"] is True
        assert len(project.context.current_state["files_created"]) == 2
        assert "TypeScript" in project.context.ai_memory