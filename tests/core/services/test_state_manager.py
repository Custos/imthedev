"""Tests for StateManager implementation.

This module tests the state management functionality including updates,
persistence, event notifications, and subscription management.
"""

import json
import tempfile
from pathlib import Path
from uuid import uuid4
from weakref import ref

import pytest

from imthedev.core.events import Event, EventBus, EventTypes
from imthedev.core.interfaces import AIModel, ApplicationState
from imthedev.core.services.state_manager import (
    InvalidModelError,
    InvalidStateError,
    StateManagerImpl,
)


class StateChangeCollector:
    """Test helper to collect state change callbacks."""

    def __init__(self) -> None:
        self.states: list[ApplicationState] = []
        self.call_count = 0

    def __call__(self, state: ApplicationState) -> None:
        """Collect state change notifications."""
        self.states.append(state)
        self.call_count += 1


@pytest.fixture
async def event_bus() -> EventBus:
    """Create an event bus for testing."""
    return EventBus()


@pytest.fixture
async def temp_state_file() -> Path:
    """Create a temporary file for state persistence."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = Path(f.name)
    yield temp_path
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
async def state_manager(event_bus: EventBus) -> StateManagerImpl:
    """Create a state manager without persistence."""
    return StateManagerImpl(event_bus)


@pytest.fixture
async def persistent_state_manager(
    event_bus: EventBus, temp_state_file: Path
) -> StateManagerImpl:
    """Create a state manager with persistence."""
    return StateManagerImpl(event_bus, temp_state_file)


class TestStateManagerBasics:
    """Test basic state management functionality."""

    async def test_initial_state(self, state_manager: StateManagerImpl) -> None:
        """Test that initial state has correct defaults."""
        state = state_manager.get_state()

        assert state.current_project_id is None
        assert state.autopilot_enabled is False
        assert state.selected_ai_model == AIModel.CLAUDE
        assert state.ui_preferences == {}

    async def test_update_state_single_field(
        self, state_manager: StateManagerImpl
    ) -> None:
        """Test updating a single state field."""
        project_id = uuid4()

        await state_manager.update_state({"current_project_id": project_id})

        state = state_manager.get_state()
        assert state.current_project_id == project_id
        # Other fields should remain unchanged
        assert state.autopilot_enabled is False
        assert state.selected_ai_model == AIModel.CLAUDE

    async def test_update_state_multiple_fields(
        self, state_manager: StateManagerImpl
    ) -> None:
        """Test updating multiple state fields at once."""
        updates = {
            "autopilot_enabled": True,
            "selected_ai_model": AIModel.GPT4,
            "ui_preferences": {"theme": "dark", "font_size": 14},
        }

        await state_manager.update_state(updates)

        state = state_manager.get_state()
        assert state.autopilot_enabled is True
        assert state.selected_ai_model == AIModel.GPT4
        assert state.ui_preferences == {"theme": "dark", "font_size": 14}

    async def test_update_state_invalid_field(
        self, state_manager: StateManagerImpl
    ) -> None:
        """Test that updating with invalid field raises error."""
        with pytest.raises(
            InvalidStateError, match="Invalid state fields: invalid_field"
        ):
            await state_manager.update_state({"invalid_field": "value"})

    async def test_update_state_invalid_model(
        self, state_manager: StateManagerImpl
    ) -> None:
        """Test that setting invalid AI model raises error."""
        with pytest.raises(InvalidStateError, match="Invalid AI model: invalid-model"):
            await state_manager.update_state({"selected_ai_model": "invalid-model"})

    async def test_update_state_invalid_project_id(
        self, state_manager: StateManagerImpl
    ) -> None:
        """Test that setting invalid project ID format raises error."""
        with pytest.raises(InvalidStateError, match="Invalid project ID format"):
            await state_manager.update_state({"current_project_id": "not-a-uuid"})


class TestAutopilotToggle:
    """Test autopilot toggle functionality."""

    async def test_toggle_autopilot_from_off(
        self, state_manager: StateManagerImpl
    ) -> None:
        """Test toggling autopilot from off to on."""
        # Initial state should be off
        assert state_manager.get_state().autopilot_enabled is False

        # Toggle on
        new_state = await state_manager.toggle_autopilot()
        assert new_state is True
        assert state_manager.get_state().autopilot_enabled is True

    async def test_toggle_autopilot_from_on(
        self, state_manager: StateManagerImpl
    ) -> None:
        """Test toggling autopilot from on to off."""
        # Set autopilot on
        await state_manager.update_state({"autopilot_enabled": True})

        # Toggle off
        new_state = await state_manager.toggle_autopilot()
        assert new_state is False
        assert state_manager.get_state().autopilot_enabled is False

    async def test_toggle_autopilot_publishes_event(
        self, state_manager: StateManagerImpl, event_bus: EventBus
    ) -> None:
        """Test that toggling autopilot publishes specific event."""
        events: list[Event] = []

        def collect_event(event: Event) -> None:
            events.append(event)

        event_bus.subscribe(EventTypes.STATE_AUTOPILOT_ENABLED, collect_event)
        event_bus.subscribe(EventTypes.STATE_AUTOPILOT_DISABLED, collect_event)

        await state_manager.toggle_autopilot()

        assert len(events) == 1
        assert events[0].type == EventTypes.STATE_AUTOPILOT_ENABLED
        assert events[0].payload["enabled"] is True


class TestAIModelSelection:
    """Test AI model selection functionality."""

    async def test_set_valid_ai_models(self, state_manager: StateManagerImpl) -> None:
        """Test setting each valid AI model."""
        for model in [AIModel.CLAUDE_INSTANT, AIModel.GPT4, AIModel.GPT35_TURBO]:
            await state_manager.set_ai_model(model)
            assert state_manager.get_state().selected_ai_model == model

    async def test_set_invalid_ai_model(self, state_manager: StateManagerImpl) -> None:
        """Test that setting invalid model raises error."""
        with pytest.raises(InvalidModelError, match="Unsupported AI model"):
            await state_manager.set_ai_model("invalid-model")

    async def test_model_change_publishes_event(
        self, state_manager: StateManagerImpl, event_bus: EventBus
    ) -> None:
        """Test that changing model publishes specific event."""
        events: list[Event] = []

        def collect_event(event: Event) -> None:
            events.append(event)

        event_bus.subscribe(EventTypes.STATE_MODEL_CHANGED, collect_event)

        await state_manager.set_ai_model(AIModel.GPT4)

        assert len(events) == 1
        assert events[0].type == EventTypes.STATE_MODEL_CHANGED
        assert events[0].payload["old_model"] == AIModel.CLAUDE
        assert events[0].payload["new_model"] == AIModel.GPT4


class TestSubscriptions:
    """Test state change subscription functionality."""

    async def test_subscribe_receives_updates(
        self, state_manager: StateManagerImpl
    ) -> None:
        """Test that subscribers receive state updates."""
        collector = StateChangeCollector()

        state_manager.subscribe(collector)

        # Make some changes
        await state_manager.update_state({"autopilot_enabled": True})
        await state_manager.toggle_autopilot()
        await state_manager.set_ai_model(AIModel.GPT4)

        assert collector.call_count == 3
        assert len(collector.states) == 3

        # Verify final state
        final_state = collector.states[-1]
        assert final_state.autopilot_enabled is False
        assert final_state.selected_ai_model == AIModel.GPT4

    async def test_unsubscribe_stops_updates(
        self, state_manager: StateManagerImpl
    ) -> None:
        """Test that unsubscribed callbacks don't receive updates."""
        collector = StateChangeCollector()

        state_manager.subscribe(collector)
        await state_manager.update_state({"autopilot_enabled": True})

        # Should have received one update
        assert collector.call_count == 1

        # Unsubscribe
        state_manager.unsubscribe(collector)

        # Make more changes
        await state_manager.toggle_autopilot()
        await state_manager.set_ai_model(AIModel.GPT4)

        # Should still only have one update
        assert collector.call_count == 1

    async def test_weak_reference_cleanup(
        self, state_manager: StateManagerImpl
    ) -> None:
        """Test that weak references allow garbage collection."""
        collector = StateChangeCollector()
        weak_ref = ref(collector)

        state_manager.subscribe(collector)

        # Delete the strong reference
        del collector

        # Weak reference should be dead
        assert weak_ref() is None

        # Updates should not crash
        await state_manager.update_state({"autopilot_enabled": True})

    async def test_subscriber_error_handling(
        self, state_manager: StateManagerImpl
    ) -> None:
        """Test that errors in subscribers don't affect others."""
        good_collector = StateChangeCollector()

        def bad_callback(state: ApplicationState) -> None:
            raise RuntimeError("Callback error")

        state_manager.subscribe(bad_callback)
        state_manager.subscribe(good_collector)

        # Update should not crash despite bad callback
        await state_manager.update_state({"autopilot_enabled": True})

        # Good collector should still receive update
        assert good_collector.call_count == 1


class TestEventNotifications:
    """Test event bus integration."""

    async def test_state_change_event_published(
        self, state_manager: StateManagerImpl, event_bus: EventBus
    ) -> None:
        """Test that state changes publish events."""
        events: list[Event] = []

        def collect_event(event: Event) -> None:
            events.append(event)

        event_bus.subscribe(EventTypes.STATE_UPDATED, collect_event)

        project_id = uuid4()
        await state_manager.update_state(
            {"current_project_id": project_id, "autopilot_enabled": True}
        )

        assert len(events) == 1
        event = events[0]
        assert event.type == EventTypes.STATE_UPDATED
        assert event.payload["changes"] == {
            "current_project_id": project_id,
            "autopilot_enabled": True,
        }
        assert event.payload["old_state"]["autopilot_enabled"] is False
        assert event.payload["new_state"]["autopilot_enabled"] is True


class TestStatePersistence:
    """Test state persistence functionality."""

    async def test_state_persisted_to_file(
        self, persistent_state_manager: StateManagerImpl, temp_state_file: Path
    ) -> None:
        """Test that state is saved to disk."""
        project_id = uuid4()

        await persistent_state_manager.update_state(
            {
                "current_project_id": project_id,
                "autopilot_enabled": True,
                "selected_ai_model": AIModel.GPT4,
                "ui_preferences": {"theme": "dark"},
            }
        )

        # Read the file
        assert temp_state_file.exists()
        state_data = json.loads(temp_state_file.read_text())

        assert state_data["current_project_id"] == str(project_id)
        assert state_data["autopilot_enabled"] is True
        assert state_data["selected_ai_model"] == AIModel.GPT4
        assert state_data["ui_preferences"] == {"theme": "dark"}

    async def test_state_loaded_from_file(
        self, event_bus: EventBus, temp_state_file: Path
    ) -> None:
        """Test that state is restored from disk."""
        project_id = uuid4()

        # Write initial state
        state_data = {
            "current_project_id": str(project_id),
            "autopilot_enabled": True,
            "selected_ai_model": AIModel.GPT4,
            "ui_preferences": {"theme": "light", "font_size": 12},
        }
        temp_state_file.write_text(json.dumps(state_data))

        # Create new manager that should load the state
        manager = StateManagerImpl(event_bus, temp_state_file)

        state = manager.get_state()
        assert state.current_project_id == project_id
        assert state.autopilot_enabled is True
        assert state.selected_ai_model == AIModel.GPT4
        assert state.ui_preferences == {"theme": "light", "font_size": 12}

    async def test_corrupt_state_file_handled(
        self, event_bus: EventBus, temp_state_file: Path
    ) -> None:
        """Test that corrupt state file doesn't crash."""
        # Write invalid JSON
        temp_state_file.write_text("{ invalid json")

        # Should not crash, should use default state
        manager = StateManagerImpl(event_bus, temp_state_file)

        state = manager.get_state()
        assert state.current_project_id is None
        assert state.autopilot_enabled is False
        assert state.selected_ai_model == AIModel.CLAUDE


class TestConcurrentUpdates:
    """Test concurrent state updates."""

    async def test_multiple_concurrent_updates(
        self, state_manager: StateManagerImpl
    ) -> None:
        """Test that concurrent updates are handled properly."""
        import asyncio

        # Create multiple update tasks
        tasks = [
            state_manager.update_state({"autopilot_enabled": True}),
            state_manager.update_state({"selected_ai_model": AIModel.GPT4}),
            state_manager.update_state({"ui_preferences": {"theme": "dark"}}),
        ]

        # Execute concurrently
        await asyncio.gather(*tasks)

        # Verify final state
        state = state_manager.get_state()
        assert state.autopilot_enabled is True
        assert state.selected_ai_model == AIModel.GPT4
        assert state.ui_preferences == {"theme": "dark"}
