"""Tests for the ContextRepository JSON file implementation.

This module contains comprehensive tests for the JSON file-based
ContextRepository that implements the ContextService interface.
"""

import tempfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest

from imthedev.core.domain import (
    Command,
    CommandResult,
    CommandStatus,
    ProjectContext,
)
from imthedev.infrastructure.persistence import ContextRepository


class TestContextRepository:
    """Test suite for ContextRepository."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create a temporary directory for context storage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def context_repo(self, temp_storage_dir):
        """Create a ContextRepository instance."""
        return ContextRepository(temp_storage_dir)

    @pytest.fixture
    def sample_project_id(self):
        """Create a sample project ID."""
        return uuid4()

    @pytest.fixture
    def sample_command(self, sample_project_id):
        """Create a sample command."""
        return Command(
            id=uuid4(),
            project_id=sample_project_id,
            command_text="echo 'Hello World'",
            ai_reasoning="Testing command execution",
            status=CommandStatus.PROPOSED,
            timestamp=datetime.now(),
        )

    @pytest.fixture
    def sample_context(self, sample_command):
        """Create a sample project context with history."""
        return ProjectContext(
            history=[sample_command],
            current_state={"test_key": "test_value", "counter": 42},
            ai_memory="Previous conversation context",
            metadata={"version": "1.0", "tags": ["test", "sample"]},
        )

    def test_initialization(self, temp_storage_dir) -> None:
        """Test that repository initializes storage directory."""
        # Remove the directory to test creation
        temp_storage_dir.rmdir()
        assert not temp_storage_dir.exists()

        # Initialize repository
        ContextRepository(temp_storage_dir)

        # Directory should be created
        assert temp_storage_dir.exists()
        assert temp_storage_dir.is_dir()

    @pytest.mark.asyncio
    async def test_save_and_load_context(
        self, context_repo, sample_project_id, sample_context
    ):
        """Test saving and loading project context."""
        # Save context
        await context_repo.save_context(sample_project_id, sample_context)

        # Load context
        loaded_context = await context_repo.load_context(sample_project_id)

        # Verify context was loaded correctly
        assert len(loaded_context.history) == 1
        assert loaded_context.current_state == sample_context.current_state
        assert loaded_context.ai_memory == sample_context.ai_memory
        assert loaded_context.metadata == sample_context.metadata

        # Verify command in history
        loaded_command = loaded_context.history[0]
        original_command = sample_context.history[0]
        assert loaded_command.id == original_command.id
        assert loaded_command.project_id == original_command.project_id
        assert loaded_command.command_text == original_command.command_text
        assert loaded_command.ai_reasoning == original_command.ai_reasoning
        assert loaded_command.status == original_command.status

    @pytest.mark.asyncio
    async def test_load_nonexistent_context(self, context_repo) -> None:
        """Test loading context for non-existent project returns empty context."""
        project_id = uuid4()

        context = await context_repo.load_context(project_id)

        # Should return empty context
        assert isinstance(context, ProjectContext)
        assert len(context.history) == 0
        assert context.current_state == {}
        assert context.ai_memory == ""
        assert context.metadata == {}

    @pytest.mark.asyncio
    async def test_save_context_with_command_result(
        self, context_repo, sample_project_id
    ):
        """Test saving context with command that has execution result."""
        # Create command with result
        command = Command(
            id=uuid4(),
            project_id=sample_project_id,
            command_text="ls -la",
            ai_reasoning="List directory contents",
            status=CommandStatus.COMPLETED,
            result=CommandResult(
                exit_code=0,
                stdout="total 8\ndrwxr-xr-x 2 user user 4096 Jan 1 12:00 .\n",
                stderr="",
                execution_time=0.123,
                timestamp=datetime.now(),
            ),
            timestamp=datetime.now(),
        )

        context = ProjectContext(history=[command])

        # Save and load
        await context_repo.save_context(sample_project_id, context)
        loaded_context = await context_repo.load_context(sample_project_id)

        # Verify command result was preserved
        loaded_command = loaded_context.history[0]
        assert loaded_command.result is not None
        assert loaded_command.result.exit_code == 0
        assert "total 8" in loaded_command.result.stdout
        assert loaded_command.result.stderr == ""
        assert loaded_command.result.execution_time == 0.123

    @pytest.mark.asyncio
    async def test_append_command(
        self, context_repo, sample_project_id, sample_command
    ):
        """Test appending a command to existing context."""
        # Start with empty context
        initial_context = ProjectContext(
            current_state={"existing": "data"}, ai_memory="Initial memory"
        )
        await context_repo.save_context(sample_project_id, initial_context)

        # Append command
        await context_repo.append_command(sample_project_id, sample_command)

        # Load and verify
        loaded_context = await context_repo.load_context(sample_project_id)
        assert len(loaded_context.history) == 1
        assert loaded_context.history[0].id == sample_command.id
        assert loaded_context.current_state == {"existing": "data"}
        assert loaded_context.ai_memory == "Initial memory"

    @pytest.mark.asyncio
    async def test_append_command_to_new_project(
        self, context_repo, sample_project_id, sample_command
    ):
        """Test appending command to project with no existing context."""
        # Append command to new project
        await context_repo.append_command(sample_project_id, sample_command)

        # Load and verify
        loaded_context = await context_repo.load_context(sample_project_id)
        assert len(loaded_context.history) == 1
        assert loaded_context.history[0].id == sample_command.id

    @pytest.mark.asyncio
    async def test_history_size_limit(self, context_repo, sample_project_id) -> None:
        """Test that command history is limited to prevent unbounded growth."""
        # Create many commands (more than the limit of 100)
        commands = []
        for i in range(120):
            command = Command(
                id=uuid4(),
                project_id=sample_project_id,
                command_text=f"echo 'Command {i}'",
                ai_reasoning=f"Test command number {i}",
                status=CommandStatus.COMPLETED,
                timestamp=datetime.now(),
            )
            commands.append(command)

        # Create context with all commands
        context = ProjectContext(history=commands)
        await context_repo.save_context(sample_project_id, context)

        # Load context and verify history is limited
        loaded_context = await context_repo.load_context(sample_project_id)
        assert len(loaded_context.history) == 100  # Should be limited to 100

        # Should keep the most recent commands
        assert (
            loaded_context.history[0].command_text == "echo 'Command 20'"
        )  # First kept command
        assert (
            loaded_context.history[-1].command_text == "echo 'Command 119'"
        )  # Last command

    @pytest.mark.asyncio
    async def test_get_command_history(self, context_repo, sample_project_id) -> None:
        """Test retrieving command history with various filters."""
        # Create commands with different statuses
        commands = []
        statuses = [
            CommandStatus.PROPOSED,
            CommandStatus.APPROVED,
            CommandStatus.COMPLETED,
            CommandStatus.FAILED,
        ]

        for i, status in enumerate(statuses * 3):  # Create 12 commands total
            command = Command(
                id=uuid4(),
                project_id=sample_project_id,
                command_text=f"command_{i}",
                ai_reasoning=f"reason_{i}",
                status=status,
                timestamp=datetime.now(),
            )
            commands.append(command)

        # Save context
        context = ProjectContext(history=commands)
        await context_repo.save_context(sample_project_id, context)

        # Test getting all history
        all_history = await context_repo.get_command_history(sample_project_id)
        assert len(all_history) == 12

        # Test with limit
        limited_history = await context_repo.get_command_history(
            sample_project_id, limit=5
        )
        assert len(limited_history) == 5

        # Test with status filter
        completed_history = await context_repo.get_command_history(
            sample_project_id, status_filter=CommandStatus.COMPLETED
        )
        assert len(completed_history) == 3
        assert all(cmd.status == CommandStatus.COMPLETED for cmd in completed_history)

        # Test with status filter and limit
        limited_completed = await context_repo.get_command_history(
            sample_project_id, limit=2, status_filter=CommandStatus.COMPLETED
        )
        assert len(limited_completed) == 2
        assert all(cmd.status == CommandStatus.COMPLETED for cmd in limited_completed)

    @pytest.mark.asyncio
    async def test_get_command_history_ordered_by_timestamp(
        self, context_repo, sample_project_id
    ):
        """Test that command history is returned ordered by timestamp (newest first)."""
        # Create commands with different timestamps
        import time

        commands = []
        for i in range(3):
            command = Command(
                id=uuid4(),
                project_id=sample_project_id,
                command_text=f"command_{i}",
                ai_reasoning=f"reason_{i}",
                status=CommandStatus.COMPLETED,
                timestamp=datetime.now(),
            )
            commands.append(command)
            time.sleep(0.001)  # Small delay to ensure different timestamps

        # Save context
        context = ProjectContext(history=commands)
        await context_repo.save_context(sample_project_id, context)

        # Get history
        history = await context_repo.get_command_history(sample_project_id)

        # Verify ordering (newest first)
        assert history[0].command_text == "command_2"
        assert history[1].command_text == "command_1"
        assert history[2].command_text == "command_0"

    @pytest.mark.asyncio
    async def test_update_command_status(
        self, context_repo, sample_project_id, sample_command
    ):
        """Test updating command status in history."""
        # Save context with command
        context = ProjectContext(history=[sample_command])
        await context_repo.save_context(sample_project_id, context)

        # Update command status
        await context_repo.update_command_status(
            sample_project_id, sample_command.id, CommandStatus.APPROVED
        )

        # Load and verify
        loaded_context = await context_repo.load_context(sample_project_id)
        assert loaded_context.history[0].status == CommandStatus.APPROVED

    @pytest.mark.asyncio
    async def test_update_command_status_not_found(
        self, context_repo, sample_project_id
    ):
        """Test updating non-existent command raises error."""
        non_existent_id = uuid4()

        with pytest.raises(ValueError, match="Command not found"):
            await context_repo.update_command_status(
                sample_project_id, non_existent_id, CommandStatus.APPROVED
            )

    @pytest.mark.asyncio
    async def test_atomic_file_operations(
        self, context_repo, sample_project_id, sample_context
    ):
        """Test that file operations are atomic using temporary files."""
        # Save context
        await context_repo.save_context(sample_project_id, sample_context)

        # Verify main file exists and no temp file remains
        context_file = context_repo._get_context_file_path(sample_project_id)
        temp_file = context_file.with_suffix(".tmp")

        assert context_file.exists()
        assert not temp_file.exists()

        # Verify content is valid JSON
        import json

        with open(context_file) as f:
            data = json.load(f)

        assert "history" in data
        assert "current_state" in data
        assert "ai_memory" in data
        assert "metadata" in data
        assert "last_updated" in data
