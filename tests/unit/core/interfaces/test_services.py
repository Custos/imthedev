"""Unit tests for service interface contracts and mock implementations."""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
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
from imthedev.core.interfaces import (
    AIModel,
    AIOrchestrator,
    ApplicationState,
    CommandAnalysis,
    CommandEngine,
    ContextService,
    ProjectService,
    StateManager,
)


class MockProjectService:
    """Mock implementation of ProjectService for testing."""
    
    def __init__(self):
        self.projects: Dict[UUID, Project] = {}
        self.current_project_id: Optional[UUID] = None
    
    async def create_project(
        self,
        name: str,
        path: str,
        settings: Optional[ProjectSettings] = None
    ) -> Project:
        project = Project.create(name, Path(path), settings)
        self.projects[project.id] = project
        return project
    
    async def get_project(self, project_id: UUID) -> Optional[Project]:
        return self.projects.get(project_id)
    
    async def list_projects(self) -> List[Project]:
        return sorted(
            self.projects.values(),
            key=lambda p: p.created_at
        )
    
    async def update_project(self, project: Project) -> None:
        if project.id not in self.projects:
            raise ValueError(f"Project {project.id} not found")
        self.projects[project.id] = project
    
    async def delete_project(self, project_id: UUID) -> None:
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        del self.projects[project_id]
        if self.current_project_id == project_id:
            self.current_project_id = None
    
    async def get_current_project(self) -> Optional[Project]:
        if self.current_project_id:
            return self.projects.get(self.current_project_id)
        return None
    
    async def set_current_project(self, project_id: UUID) -> None:
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        self.current_project_id = project_id


class MockContextService:
    """Mock implementation of ContextService for testing."""
    
    def __init__(self):
        self.contexts: Dict[UUID, ProjectContext] = {}
    
    async def save_context(
        self,
        project_id: UUID,
        context: ProjectContext
    ) -> None:
        self.contexts[project_id] = context
    
    async def load_context(self, project_id: UUID) -> ProjectContext:
        if project_id not in self.contexts:
            raise ValueError(f"Context for project {project_id} not found")
        return self.contexts[project_id]
    
    async def append_command(
        self,
        project_id: UUID,
        command: Command
    ) -> None:
        if project_id not in self.contexts:
            self.contexts[project_id] = ProjectContext()
        self.contexts[project_id].history.append(command)
    
    async def get_command_history(
        self,
        project_id: UUID,
        limit: int = 50,
        status_filter: Optional[CommandStatus] = None
    ) -> List[Command]:
        if project_id not in self.contexts:
            return []
        
        history = self.contexts[project_id].history
        if status_filter:
            history = [cmd for cmd in history if cmd.status == status_filter]
        
        return sorted(history, key=lambda c: c.timestamp, reverse=True)[:limit]
    
    async def update_command_status(
        self,
        project_id: UUID,
        command_id: UUID,
        status: CommandStatus
    ) -> None:
        if project_id not in self.contexts:
            raise ValueError(f"Project {project_id} not found")
        
        for cmd in self.contexts[project_id].history:
            if cmd.id == command_id:
                cmd.status = status
                return
        
        raise ValueError(f"Command {command_id} not found")


class MockAIOrchestrator:
    """Mock implementation of AIOrchestrator for testing."""
    
    def __init__(self):
        self.available_models = [
            AIModel.CLAUDE,
            AIModel.CLAUDE_INSTANT,
            AIModel.GPT4,
            AIModel.GPT35_TURBO
        ]
    
    async def generate_command(
        self,
        context: ProjectContext,
        objective: str,
        model: str = AIModel.CLAUDE
    ) -> tuple[str, str]:
        # Simple mock logic for testing
        if "git" in objective.lower():
            return "git init", "Initialize a new git repository"
        elif "create" in objective.lower() and "file" in objective.lower():
            return "touch README.md", "Create a new README file"
        else:
            return "echo 'Task completed'", "Execute the requested task"
    
    async def analyze_result(
        self,
        command: Command,
        output: str,
        context: ProjectContext
    ) -> CommandAnalysis:
        success = "error" not in output.lower()
        return CommandAnalysis(
            success=success,
            next_action="Continue with next task" if success else None,
            error_diagnosis="Command failed" if not success else None
        )
    
    def get_available_models(self) -> List[str]:
        return self.available_models
    
    async def estimate_tokens(
        self,
        context: ProjectContext,
        objective: str
    ) -> int:
        # Simple estimation based on context size
        base_tokens = 100
        history_tokens = len(context.history) * 50
        objective_tokens = len(objective.split()) * 2
        return base_tokens + history_tokens + objective_tokens


class MockCommandEngine:
    """Mock implementation of CommandEngine for testing."""
    
    def __init__(self):
        self.pending_commands: Dict[UUID, Command] = {}
        self.all_commands: Dict[UUID, Command] = {}
    
    async def propose_command(
        self,
        project_id: UUID,
        command_text: str,
        ai_reasoning: str
    ) -> Command:
        command = Command(
            id=uuid4(),
            project_id=project_id,
            command_text=command_text,
            ai_reasoning=ai_reasoning,
            status=CommandStatus.PROPOSED
        )
        self.pending_commands[command.id] = command
        self.all_commands[command.id] = command
        return command
    
    async def approve_command(self, command_id: UUID) -> None:
        if command_id not in self.pending_commands:
            raise ValueError(f"Command {command_id} not found or not pending")
        
        command = self.pending_commands[command_id]
        if command.status != CommandStatus.PROPOSED:
            raise ValueError(f"Command {command_id} is not in PROPOSED state")
        
        command.status = CommandStatus.APPROVED
        del self.pending_commands[command_id]
    
    async def reject_command(self, command_id: UUID) -> None:
        if command_id not in self.pending_commands:
            raise ValueError(f"Command {command_id} not found or not pending")
        
        command = self.pending_commands[command_id]
        if command.status != CommandStatus.PROPOSED:
            raise ValueError(f"Command {command_id} is not in PROPOSED state")
        
        command.status = CommandStatus.REJECTED
        del self.pending_commands[command_id]
    
    async def execute_command(self, command_id: UUID) -> None:
        if command_id not in self.all_commands:
            raise ValueError(f"Command {command_id} not found")
        
        command = self.all_commands[command_id]
        if command.status != CommandStatus.APPROVED:
            raise ValueError(f"Command {command_id} is not APPROVED")
        
        command.status = CommandStatus.EXECUTING
        # Simulate execution
        command.status = CommandStatus.COMPLETED
        command.result = CommandResult(
            exit_code=0,
            stdout="Command executed successfully",
            stderr="",
            execution_time=1.0
        )
    
    def get_pending_commands(self) -> Dict[UUID, Command]:
        return self.pending_commands.copy()
    
    async def cancel_execution(self, command_id: UUID) -> None:
        if command_id not in self.all_commands:
            raise ValueError(f"Command {command_id} not found")
        
        command = self.all_commands[command_id]
        if command.status != CommandStatus.EXECUTING:
            raise ValueError(f"Command {command_id} is not EXECUTING")
        
        command.status = CommandStatus.FAILED


class MockStateManager:
    """Mock implementation of StateManager for testing."""
    
    def __init__(self):
        self.state = ApplicationState()
        self.subscribers = []
    
    def get_state(self) -> ApplicationState:
        return self.state
    
    async def update_state(self, updates: Dict[str, any]) -> None:
        for key, value in updates.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
            else:
                raise ValueError(f"Invalid state field: {key}")
        
        # Notify subscribers
        for callback in self.subscribers:
            callback(self.state)
    
    async def toggle_autopilot(self) -> bool:
        self.state.autopilot_enabled = not self.state.autopilot_enabled
        for callback in self.subscribers:
            callback(self.state)
        return self.state.autopilot_enabled
    
    async def set_ai_model(self, model: str) -> None:
        valid_models = [
            AIModel.CLAUDE,
            AIModel.CLAUDE_INSTANT,
            AIModel.GPT4,
            AIModel.GPT35_TURBO
        ]
        if model not in valid_models:
            raise ValueError(f"Invalid model: {model}")
        
        self.state.selected_ai_model = model
        for callback in self.subscribers:
            callback(self.state)
    
    def subscribe(self, callback: callable) -> None:
        self.subscribers.append(callback)
    
    def unsubscribe(self, callback: callable) -> None:
        if callback in self.subscribers:
            self.subscribers.remove(callback)


class TestServiceInterfaces:
    """Test that mock implementations satisfy protocol interfaces."""
    
    def test_project_service_protocol(self):
        """Test that MockProjectService implements ProjectService protocol."""
        service = MockProjectService()
        # This will pass type checking if the mock implements the protocol
        assert isinstance(service, object)  # Basic runtime check
        
        # Verify all required methods exist
        assert hasattr(service, 'create_project')
        assert hasattr(service, 'get_project')
        assert hasattr(service, 'list_projects')
        assert hasattr(service, 'update_project')
        assert hasattr(service, 'delete_project')
        assert hasattr(service, 'get_current_project')
        assert hasattr(service, 'set_current_project')
    
    def test_context_service_protocol(self):
        """Test that MockContextService implements ContextService protocol."""
        service = MockContextService()
        
        assert hasattr(service, 'save_context')
        assert hasattr(service, 'load_context')
        assert hasattr(service, 'append_command')
        assert hasattr(service, 'get_command_history')
        assert hasattr(service, 'update_command_status')
    
    def test_ai_orchestrator_protocol(self):
        """Test that MockAIOrchestrator implements AIOrchestrator protocol."""
        service = MockAIOrchestrator()
        
        assert hasattr(service, 'generate_command')
        assert hasattr(service, 'analyze_result')
        assert hasattr(service, 'get_available_models')
        assert hasattr(service, 'estimate_tokens')
    
    def test_command_engine_protocol(self):
        """Test that MockCommandEngine implements CommandEngine protocol."""
        service = MockCommandEngine()
        
        assert hasattr(service, 'propose_command')
        assert hasattr(service, 'approve_command')
        assert hasattr(service, 'reject_command')
        assert hasattr(service, 'execute_command')
        assert hasattr(service, 'get_pending_commands')
        assert hasattr(service, 'cancel_execution')
    
    def test_state_manager_protocol(self):
        """Test that MockStateManager implements StateManager protocol."""
        service = MockStateManager()
        
        assert hasattr(service, 'get_state')
        assert hasattr(service, 'update_state')
        assert hasattr(service, 'toggle_autopilot')
        assert hasattr(service, 'set_ai_model')
        assert hasattr(service, 'subscribe')
        assert hasattr(service, 'unsubscribe')


class TestMockImplementations:
    """Test the behavior of mock implementations."""
    
    @pytest.mark.asyncio
    async def test_project_service_workflow(self):
        """Test complete project service workflow."""
        service = MockProjectService()
        
        # Create project
        project = await service.create_project("Test", "/tmp/test")
        assert project.name == "Test"
        assert str(project.path) == "/tmp/test"
        
        # Get project
        retrieved = await service.get_project(project.id)
        assert retrieved == project
        
        # List projects
        projects = await service.list_projects()
        assert len(projects) == 1
        assert projects[0] == project
        
        # Set current project
        await service.set_current_project(project.id)
        current = await service.get_current_project()
        assert current == project
        
        # Update project
        project.name = "Updated Test"
        await service.update_project(project)
        retrieved = await service.get_project(project.id)
        assert retrieved.name == "Updated Test"
        
        # Delete project
        await service.delete_project(project.id)
        projects = await service.list_projects()
        assert len(projects) == 0
    
    @pytest.mark.asyncio
    async def test_command_engine_workflow(self):
        """Test complete command engine workflow."""
        engine = MockCommandEngine()
        project_id = uuid4()
        
        # Propose command
        command = await engine.propose_command(
            project_id,
            "git init",
            "Initialize repository"
        )
        assert command.status == CommandStatus.PROPOSED
        
        # Check pending commands
        pending = engine.get_pending_commands()
        assert len(pending) == 1
        assert command.id in pending
        
        # Approve command
        await engine.approve_command(command.id)
        assert command.status == CommandStatus.APPROVED
        
        # Execute command
        await engine.execute_command(command.id)
        assert command.status == CommandStatus.COMPLETED
        assert command.result is not None
        assert command.result.exit_code == 0
    
    @pytest.mark.asyncio
    async def test_state_manager_subscriptions(self):
        """Test state manager subscription mechanism."""
        manager = MockStateManager()
        state_changes = []
        
        def callback(state: ApplicationState):
            state_changes.append(state.autopilot_enabled)
        
        # Subscribe
        manager.subscribe(callback)
        
        # Toggle autopilot
        await manager.toggle_autopilot()
        assert len(state_changes) == 1
        assert state_changes[0] is True
        
        # Toggle again
        await manager.toggle_autopilot()
        assert len(state_changes) == 2
        assert state_changes[1] is False
        
        # Unsubscribe
        manager.unsubscribe(callback)
        await manager.toggle_autopilot()
        assert len(state_changes) == 2  # No new updates


class TestAIIntegration:
    """Test AI orchestrator integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_command_generation(self):
        """Test AI command generation."""
        orchestrator = MockAIOrchestrator()
        context = ProjectContext()
        
        # Test git-related objective
        cmd_text, reasoning = await orchestrator.generate_command(
            context,
            "Initialize a git repository"
        )
        assert cmd_text == "git init"
        assert "repository" in reasoning.lower()
        
        # Test file creation objective
        cmd_text, reasoning = await orchestrator.generate_command(
            context,
            "Create a new README file"
        )
        assert "touch" in cmd_text or "README" in cmd_text
    
    @pytest.mark.asyncio
    async def test_result_analysis(self):
        """Test AI result analysis."""
        orchestrator = MockAIOrchestrator()
        command = Command(
            id=uuid4(),
            project_id=uuid4(),
            command_text="git init",
            ai_reasoning="Initialize repository",
            status=CommandStatus.COMPLETED
        )
        
        # Successful analysis
        analysis = await orchestrator.analyze_result(
            command,
            "Initialized empty Git repository",
            ProjectContext()
        )
        assert analysis.success is True
        assert analysis.next_action is not None
        
        # Failed analysis
        analysis = await orchestrator.analyze_result(
            command,
            "Error: permission denied",
            ProjectContext()
        )
        assert analysis.success is False
        assert analysis.error_diagnosis is not None