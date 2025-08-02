"""Tests for CommandEngine implementation.

This module tests the complete command lifecycle including proposal,
approval/rejection, execution, and cancellation.
"""

import asyncio
from uuid import uuid4

import pytest

from imthedev.core.domain import CommandStatus
from imthedev.core.events import Event, EventBus, EventTypes
from imthedev.core.services.command_engine import (
    CommandEngineImpl,
)


class EventCollector:
    """Test helper to collect events for verification."""

    def __init__(self) -> None:
        self.events: list[Event] = []

    def __call__(self, event: Event) -> None:
        """Collect events for testing."""
        self.events.append(event)

    def get_events_by_type(self, event_type: EventTypes) -> list[Event]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.type == event_type]

    def clear(self) -> None:
        """Clear collected events."""
        self.events.clear()


@pytest.fixture
async def event_bus() -> EventBus:
    """Create an event bus for testing."""
    return EventBus()


@pytest.fixture
async def event_collector(event_bus: EventBus) -> EventCollector:
    """Create and register an event collector."""
    collector = EventCollector()

    # Subscribe to all command-related events
    event_bus.subscribe(EventTypes.COMMAND_PROPOSED, collector)
    event_bus.subscribe(EventTypes.COMMAND_APPROVED, collector)
    event_bus.subscribe(EventTypes.COMMAND_REJECTED, collector)
    event_bus.subscribe(EventTypes.COMMAND_EXECUTING, collector)
    event_bus.subscribe(EventTypes.COMMAND_COMPLETED, collector)
    event_bus.subscribe(EventTypes.COMMAND_FAILED, collector)
    event_bus.subscribe(EventTypes.COMMAND_CANCELLED, collector)

    return collector


@pytest.fixture
async def command_engine(event_bus: EventBus) -> CommandEngineImpl:
    """Create a command engine for testing."""
    return CommandEngineImpl(event_bus)


class TestCommandEngineProposal:
    """Test command proposal functionality."""

    async def test_propose_command_creates_pending_command(
        self, command_engine: CommandEngineImpl, event_collector: EventCollector
    ) -> None:
        """Test that proposing a command creates it in pending status."""
        project_id = uuid4()
        command_text = "echo 'Hello, World!'"
        ai_reasoning = "Testing basic command execution"

        command = await command_engine.propose_command(
            project_id, command_text, ai_reasoning
        )

        assert command.project_id == project_id
        assert command.command_text == command_text
        assert command.ai_reasoning == ai_reasoning
        assert command.status == CommandStatus.PROPOSED
        assert command.result is None

        # Verify command is in pending queue
        pending = command_engine.get_pending_commands()
        assert command.id in pending
        assert pending[command.id] == command

    async def test_propose_command_publishes_event(
        self, command_engine: CommandEngineImpl, event_collector: EventCollector
    ) -> None:
        """Test that proposing a command publishes the correct event."""
        project_id = uuid4()
        command_text = "ls -la"
        ai_reasoning = "List directory contents"

        command = await command_engine.propose_command(
            project_id, command_text, ai_reasoning
        )

        # Verify event was published
        events = event_collector.get_events_by_type(EventTypes.COMMAND_PROPOSED)
        assert len(events) == 1

        event = events[0]
        assert event.payload["command_id"] == str(command.id)
        assert event.payload["project_id"] == str(project_id)
        assert event.payload["command_text"] == command_text
        assert event.payload["ai_reasoning"] == ai_reasoning


class TestCommandApproval:
    """Test command approval workflow."""

    async def test_approve_command_transitions_status(
        self, command_engine: CommandEngineImpl, event_collector: EventCollector
    ) -> None:
        """Test that approving a command transitions it correctly."""
        command = await command_engine.propose_command(
            uuid4(), "echo 'test'", "Testing"
        )

        await command_engine.approve_command(command.id)

        # Command should be removed from pending queue
        pending = command_engine.get_pending_commands()
        assert command.id not in pending

        # Verify approval event
        events = event_collector.get_events_by_type(EventTypes.COMMAND_APPROVED)
        assert len(events) == 1
        assert events[0].payload["command_id"] == str(command.id)

    async def test_approve_nonexistent_command_raises_error(
        self, command_engine: CommandEngineImpl
    ) -> None:
        """Test that approving a non-existent command raises ValueError."""
        with pytest.raises(ValueError, match="not found in pending queue"):
            await command_engine.approve_command(uuid4())

    async def test_approved_command_starts_execution(
        self, command_engine: CommandEngineImpl, event_collector: EventCollector
    ) -> None:
        """Test that approved commands start executing."""
        command = await command_engine.propose_command(
            uuid4(), "echo 'executing'", "Test execution"
        )

        await command_engine.approve_command(command.id)

        # Wait for execution to start
        await asyncio.sleep(0.1)

        # Verify execution started event
        events = event_collector.get_events_by_type(EventTypes.COMMAND_EXECUTING)
        assert len(events) == 1
        assert events[0].payload["command_id"] == str(command.id)


class TestCommandRejection:
    """Test command rejection workflow."""

    async def test_reject_command_transitions_status(
        self, command_engine: CommandEngineImpl, event_collector: EventCollector
    ) -> None:
        """Test that rejecting a command transitions it correctly."""
        command = await command_engine.propose_command(
            uuid4(), "rm -rf /", "Dangerous command"
        )

        await command_engine.reject_command(command.id)

        # Command should be removed from pending queue
        pending = command_engine.get_pending_commands()
        assert command.id not in pending

        # Verify rejection event
        events = event_collector.get_events_by_type(EventTypes.COMMAND_REJECTED)
        assert len(events) == 1
        assert events[0].payload["command_id"] == str(command.id)
        assert "reason" in events[0].payload

    async def test_reject_nonexistent_command_raises_error(
        self, command_engine: CommandEngineImpl
    ) -> None:
        """Test that rejecting a non-existent command raises ValueError."""
        with pytest.raises(ValueError, match="not found in pending queue"):
            await command_engine.reject_command(uuid4())


class TestCommandExecution:
    """Test command execution functionality."""

    async def test_execute_successful_command(
        self, command_engine: CommandEngineImpl, event_collector: EventCollector
    ) -> None:
        """Test successful command execution."""
        command = await command_engine.propose_command(
            uuid4(), "echo 'Success!'", "Test successful execution"
        )

        await command_engine.execute_command(command.id)

        # Wait for execution to complete
        await asyncio.sleep(0.2)

        # Verify execution completed event
        events = event_collector.get_events_by_type(EventTypes.COMMAND_COMPLETED)
        assert len(events) == 1

        event = events[0]
        assert event.payload["command_id"] == str(command.id)
        assert event.payload["exit_code"] == 0
        assert "Success!" in event.payload["stdout"]

    async def test_execute_failing_command(
        self, command_engine: CommandEngineImpl, event_collector: EventCollector
    ) -> None:
        """Test command execution that fails."""
        command = await command_engine.propose_command(
            uuid4(), "exit 1", "Test failing command"
        )

        await command_engine.execute_command(command.id)

        # Wait for execution to complete
        await asyncio.sleep(0.2)

        # Verify execution failed event
        events = event_collector.get_events_by_type(EventTypes.COMMAND_FAILED)
        assert len(events) == 1

        event = events[0]
        assert event.payload["command_id"] == str(command.id)
        assert event.payload["exit_code"] == 1

    async def test_execute_invalid_command(
        self, command_engine: CommandEngineImpl, event_collector: EventCollector
    ) -> None:
        """Test execution of invalid command."""
        command = await command_engine.propose_command(
            uuid4(), "this_command_does_not_exist", "Test invalid command"
        )

        await command_engine.execute_command(command.id)

        # Wait for execution to fail
        await asyncio.sleep(0.2)

        # Verify execution failed event
        events = event_collector.get_events_by_type(EventTypes.COMMAND_FAILED)
        assert len(events) == 1

        event = events[0]
        assert event.payload["command_id"] == str(command.id)
        assert event.payload["exit_code"] != 0

    async def test_direct_execution_bypasses_approval(
        self, command_engine: CommandEngineImpl, event_collector: EventCollector
    ) -> None:
        """Test that direct execution bypasses approval workflow."""
        command = await command_engine.propose_command(
            uuid4(), "echo 'Autopilot'", "Test autopilot mode"
        )

        # Execute directly without approval
        await command_engine.execute_command(command.id)

        # Command should be removed from pending
        pending = command_engine.get_pending_commands()
        assert command.id not in pending

        # No approval event should be published
        approval_events = event_collector.get_events_by_type(
            EventTypes.COMMAND_APPROVED
        )
        assert len(approval_events) == 0

        # But execution should start
        await asyncio.sleep(0.1)
        start_events = event_collector.get_events_by_type(EventTypes.COMMAND_EXECUTING)
        assert len(start_events) == 1


class TestCommandCancellation:
    """Test command cancellation functionality."""

    async def test_cancel_executing_command(
        self, command_engine: CommandEngineImpl, event_collector: EventCollector
    ) -> None:
        """Test cancelling an executing command."""
        # Create a long-running command
        command = await command_engine.propose_command(
            uuid4(), "sleep 5", "Test cancellation"
        )

        await command_engine.execute_command(command.id)

        # Wait for execution to start
        await asyncio.sleep(0.1)

        # Cancel the command
        await command_engine.cancel_execution(command.id)

        # Verify cancellation event
        events = event_collector.get_events_by_type(EventTypes.COMMAND_CANCELLED)
        assert len(events) == 1
        assert events[0].payload["command_id"] == str(command.id)

    async def test_cancel_nonexecuting_command_raises_error(
        self, command_engine: CommandEngineImpl
    ) -> None:
        """Test that cancelling a non-executing command raises error."""
        with pytest.raises(ValueError, match="not currently executing"):
            await command_engine.cancel_execution(uuid4())


class TestPendingCommands:
    """Test pending command management."""

    async def test_get_pending_commands_returns_copy(
        self, command_engine: CommandEngineImpl
    ) -> None:
        """Test that get_pending_commands returns a copy."""
        command1 = await command_engine.propose_command(uuid4(), "echo '1'", "First")
        command2 = await command_engine.propose_command(uuid4(), "echo '2'", "Second")

        pending = command_engine.get_pending_commands()
        assert len(pending) == 2
        assert command1.id in pending
        assert command2.id in pending

        # Modifying returned dict shouldn't affect internal state
        pending.clear()

        actual_pending = command_engine.get_pending_commands()
        assert len(actual_pending) == 2


class TestConcurrentExecution:
    """Test concurrent command execution."""

    async def test_multiple_commands_execute_concurrently(
        self, command_engine: CommandEngineImpl, event_collector: EventCollector
    ) -> None:
        """Test that multiple commands can execute concurrently."""
        # Create multiple commands
        commands = []
        for i in range(3):
            command = await command_engine.propose_command(
                uuid4(), f"echo 'Command {i}'", f"Test concurrent {i}"
            )
            commands.append(command)

        # Execute all commands
        for command in commands:
            await command_engine.execute_command(command.id)

        # Wait for all to complete
        await asyncio.sleep(0.3)

        # Verify all completed
        completed_events = event_collector.get_events_by_type(
            EventTypes.COMMAND_COMPLETED
        )
        assert len(completed_events) == 3

        # Verify each command's output
        for i, command in enumerate(commands):
            matching_events = [
                e
                for e in completed_events
                if e.payload["command_id"] == str(command.id)
            ]
            assert len(matching_events) == 1
            assert f"Command {i}" in matching_events[0].payload["stdout"]


class TestErrorHandling:
    """Test error handling scenarios."""

    async def test_execution_with_stderr_output(
        self, command_engine: CommandEngineImpl, event_collector: EventCollector
    ) -> None:
        """Test command that produces stderr output."""
        command = await command_engine.propose_command(
            uuid4(),
            "python -c \"import sys; sys.stderr.write('Error output')\"",
            "Test stderr",
        )

        await command_engine.execute_command(command.id)
        await asyncio.sleep(0.2)

        # Should complete successfully even with stderr
        events = event_collector.get_events_by_type(EventTypes.COMMAND_COMPLETED)
        assert len(events) == 1
        assert "Error output" in events[0].payload["stderr"]

    async def test_command_timeout_behavior(
        self, command_engine: CommandEngineImpl, event_collector: EventCollector
    ) -> None:
        """Test behavior with long-running commands."""
        command = await command_engine.propose_command(
            uuid4(), "sleep 0.1", "Test timeout behavior"
        )

        await command_engine.execute_command(command.id)

        # Command should eventually complete
        await asyncio.sleep(0.3)

        events = event_collector.get_events_by_type(EventTypes.COMMAND_COMPLETED)
        assert len(events) == 1
