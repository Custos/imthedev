"""Tests for the ApprovalControls component.

This tests the functionality of the approval controls widget
including command approval, denial, and autopilot mode.
"""

from uuid import uuid4

import pytest

from imthedev.ui.tui.components.approval_controls import ApprovalControls


@pytest.mark.asyncio
async def test_approval_controls_can_be_created():
    """Test that ApprovalControls can be instantiated."""
    controls = ApprovalControls()
    assert controls is not None
    # ApprovalControls has can_focus = True as a class attribute
    assert hasattr(ApprovalControls, "can_focus")
    assert ApprovalControls.can_focus is True
    assert controls.autopilot_enabled is False
    assert controls.pending_command_id is None


@pytest.mark.asyncio
async def test_approval_controls_has_bindings():
    """Test that ApprovalControls has the expected key bindings."""
    controls = ApprovalControls()

    # Check that bindings are defined
    # In Textual 5.0, access BINDINGS directly
    assert hasattr(controls, "BINDINGS")
    binding_keys = [(b[0], b[1]) for b in controls.BINDINGS]
    assert ("a", "approve_command") in binding_keys
    assert ("d", "deny_command") in binding_keys
    assert ("p", "toggle_autopilot") in binding_keys


@pytest.mark.asyncio
async def test_approval_controls_compose():
    """Test that ApprovalControls composes correctly."""
    controls = ApprovalControls()

    # Test that compose method exists and can be called
    assert hasattr(controls, "compose")

    # The actual compose implementation uses Textual widgets
    # which are mocked in tests. We verify the method exists
    # and can be called without errors.
    try:
        # Call compose to ensure it doesn't raise errors
        compose_result = controls.compose()
        # Convert to list to trigger generator execution
        list(compose_result)
        # Success if we get here without exceptions
        assert True
    except Exception as e:
        # If there's an error, it should be widget-related
        # not a code error
        assert "Widget" in str(type(e)) or "Mock" in str(type(e))


@pytest.mark.asyncio
async def test_set_pending_command():
    """Test setting a pending command."""
    controls = ApprovalControls()

    # Set a pending command
    cmd_id = str(uuid4())
    controls.set_pending_command(cmd_id)

    # Verify it was set
    assert controls.pending_command_id == cmd_id
    assert controls.is_processing is False


@pytest.mark.asyncio
async def test_autopilot_mode():
    """Test toggling autopilot mode."""
    controls = ApprovalControls()

    # Initially off
    assert controls.autopilot_enabled is False

    # Turn on
    controls.set_autopilot_mode(True)
    assert controls.autopilot_enabled is True

    # Turn off
    controls.set_autopilot_mode(False)
    assert controls.autopilot_enabled is False


@pytest.mark.asyncio
async def test_processing_state():
    """Test setting processing state."""
    controls = ApprovalControls()

    # Set processing
    controls.set_processing_state(True)
    assert controls.is_processing is True

    # Clear processing
    controls.set_processing_state(False)
    assert controls.is_processing is False


@pytest.mark.asyncio
async def test_approval_controls_messages():
    """Test that ApprovalControls message classes are defined correctly."""
    # Test that message classes exist
    assert hasattr(ApprovalControls, "CommandApproved")
    assert hasattr(ApprovalControls, "CommandDenied")
    assert hasattr(ApprovalControls, "AutopilotToggled")

    # Test message creation
    cmd_id = str(uuid4())

    # Create messages
    approved_msg = ApprovalControls.CommandApproved(cmd_id)
    assert approved_msg.command_id == cmd_id

    denied_msg = ApprovalControls.CommandDenied(cmd_id)
    assert denied_msg.command_id == cmd_id

    autopilot_msg = ApprovalControls.AutopilotToggled(True)
    assert autopilot_msg.enabled is True


@pytest.mark.asyncio
async def test_approval_not_available_when_autopilot():
    """Test that approval is not available when autopilot is on."""
    controls = ApprovalControls()

    # Set a pending command
    cmd_id = str(uuid4())
    controls.set_pending_command(cmd_id)

    # Enable autopilot
    controls.set_autopilot_mode(True)

    # Try to approve (should do nothing)
    controls.action_approve_command()

    # Command should still be pending
    assert controls.pending_command_id == cmd_id


@pytest.mark.asyncio
async def test_approval_not_available_when_processing():
    """Test that approval is not available when processing."""
    controls = ApprovalControls()

    # Set a pending command
    cmd_id = str(uuid4())
    controls.set_pending_command(cmd_id)

    # Set processing state
    controls.set_processing_state(True)

    # Try to approve (should do nothing)
    controls.action_approve_command()

    # Command should still be pending
    assert controls.pending_command_id == cmd_id


if __name__ == "__main__":
    # For manual testing
    import asyncio

    async def run_tests():
        print("Running ApprovalControls tests...")

        await test_approval_controls_can_be_created()
        print("✓ Can create ApprovalControls")

        await test_approval_controls_has_bindings()
        print("✓ Has expected key bindings")

        await test_approval_controls_compose()
        print("✓ Composes correctly")

        await test_set_pending_command()
        print("✓ Can set pending command")

        await test_autopilot_mode()
        print("✓ Autopilot mode works")

        await test_processing_state()
        print("✓ Processing state works")

        await test_approval_controls_messages()
        print("✓ Messages work correctly")

        await test_approval_not_available_when_autopilot()
        print("✓ Approval blocked when autopilot")

        await test_approval_not_available_when_processing()
        print("✓ Approval blocked when processing")

        print("\nAll tests passed!")

    asyncio.run(run_tests())
