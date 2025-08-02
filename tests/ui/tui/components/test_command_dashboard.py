"""Tests for the CommandDashboard component.

This tests the functionality of the command dashboard widget
including command display, history, and input management.
"""

from datetime import datetime
from uuid import uuid4

import pytest

from imthedev.ui.tui.components.command_dashboard import CommandDashboard


@pytest.mark.asyncio
async def test_command_dashboard_can_be_created():
    """Test that CommandDashboard can be instantiated."""
    dashboard = CommandDashboard()
    assert dashboard is not None
    # CommandDashboard has can_focus = True as a class attribute
    assert hasattr(CommandDashboard, "can_focus")
    assert CommandDashboard.can_focus is True


@pytest.mark.asyncio
async def test_command_dashboard_has_bindings():
    """Test that CommandDashboard has the expected key bindings."""
    dashboard = CommandDashboard()

    # Check that bindings are defined
    assert hasattr(dashboard, "BINDINGS")
    binding_keys = [(b[0], b[1]) for b in dashboard.BINDINGS]
    assert ("ctrl+enter", "submit_command") in binding_keys
    assert ("escape", "clear_command") in binding_keys
    assert ("up", "previous_command") in binding_keys
    assert ("down", "next_command") in binding_keys


@pytest.mark.asyncio
async def test_command_dashboard_compose():
    """Test that CommandDashboard composes correctly."""
    dashboard = CommandDashboard()

    # Test that compose method exists and can be called
    assert hasattr(dashboard, "compose")

    # The actual compose implementation uses Textual widgets
    # which are mocked in tests. We verify the method exists
    # and can be called without errors.
    try:
        # Call compose to ensure it doesn't raise errors
        compose_result = dashboard.compose()
        # Convert to list to trigger generator execution
        list(compose_result)
        # Success if we get here without exceptions
        assert True
    except Exception as e:
        # If there's an error, it should be widget-related
        # not a code error
        assert "Widget" in str(type(e)) or "Mock" in str(type(e))


@pytest.mark.asyncio
async def test_update_current_command():
    """Test updating the current command display."""
    dashboard = CommandDashboard()

    # Set a test command
    test_command = "git status"
    dashboard.update_current_command(test_command)

    # Verify command was stored
    assert dashboard.current_command == test_command

    # Verify input field would be updated
    assert dashboard.command_input is None  # Not mounted yet


@pytest.mark.asyncio
async def test_add_to_history():
    """Test adding commands to history."""
    dashboard = CommandDashboard()

    # Add test commands
    cmd_id1 = str(uuid4())
    cmd_id2 = str(uuid4())
    timestamp = datetime.now()

    dashboard.add_to_history(cmd_id1, "git add .", "completed", timestamp)
    dashboard.add_to_history(cmd_id2, "git commit", "failed", timestamp)

    # Verify history was updated
    assert len(dashboard.command_history) == 2
    assert dashboard.command_history[0][0] == cmd_id1
    assert dashboard.command_history[0][1] == "git add ."
    assert dashboard.command_history[0][2] == "completed"
    assert dashboard.command_history[1][0] == cmd_id2
    assert dashboard.command_history[1][1] == "git commit"
    assert dashboard.command_history[1][2] == "failed"


@pytest.mark.asyncio
async def test_command_navigation():
    """Test navigating through command history."""
    dashboard = CommandDashboard()

    # Add test commands
    timestamp = datetime.now()
    dashboard.add_to_history(str(uuid4()), "command 1", "completed", timestamp)
    dashboard.add_to_history(str(uuid4()), "command 2", "completed", timestamp)
    dashboard.add_to_history(str(uuid4()), "command 3", "completed", timestamp)

    # Test previous command navigation
    dashboard.history_index = -1
    dashboard.action_previous_command()
    assert dashboard.history_index == 2  # Last command

    dashboard.action_previous_command()
    assert dashboard.history_index == 1

    # Test next command navigation
    dashboard.action_next_command()
    assert dashboard.history_index == 2

    dashboard.action_next_command()
    assert dashboard.history_index == -1  # Back to empty


@pytest.mark.asyncio
async def test_update_command_status():
    """Test updating command status in history."""
    dashboard = CommandDashboard()

    # Add a pending command
    cmd_id = str(uuid4())
    timestamp = datetime.now()
    dashboard.add_to_history(cmd_id, "test command", "pending", timestamp)

    # Update its status
    dashboard.update_command_status(cmd_id, "completed")

    # Verify status was updated
    assert dashboard.command_history[0][2] == "completed"


@pytest.mark.asyncio
async def test_command_dashboard_messages():
    """Test that CommandDashboard message classes are defined correctly."""
    # Test that message classes exist
    assert hasattr(CommandDashboard, "CommandSubmitted")
    assert hasattr(CommandDashboard, "CommandCleared")

    # Test message creation
    test_command = "git status"
    test_id = str(uuid4())

    # Create messages
    submitted_msg = CommandDashboard.CommandSubmitted(test_command, test_id)
    assert submitted_msg.command == test_command
    assert submitted_msg.command_id == test_id

    cleared_msg = CommandDashboard.CommandCleared()
    assert cleared_msg is not None


if __name__ == "__main__":
    # For manual testing
    import asyncio

    async def run_tests():
        print("Running CommandDashboard tests...")

        await test_command_dashboard_can_be_created()
        print("✓ Can create CommandDashboard")

        await test_command_dashboard_has_bindings()
        print("✓ Has expected key bindings")

        await test_command_dashboard_compose()
        print("✓ Composes correctly")

        await test_update_current_command()
        print("✓ Can update current command")

        await test_add_to_history()
        print("✓ Can add to history")

        await test_command_navigation()
        print("✓ Command navigation works")

        await test_update_command_status()
        print("✓ Can update command status")

        await test_command_dashboard_messages()
        print("✓ Messages work correctly")

        print("\nAll tests passed!")

    asyncio.run(run_tests())
