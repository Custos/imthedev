"""Unit tests for the event bus implementation."""

import asyncio
from datetime import datetime
from uuid import uuid4

import pytest

from imthedev.core.events import Event, EventBus, EventTypes, ScopedEventBus


class TestEvent:
    """Test the Event dataclass."""
    
    def test_event_creation(self):
        """Test creating an event with required fields."""
        event = Event(
            type=EventTypes.PROJECT_CREATED,
            payload={"project_id": str(uuid4()), "name": "Test Project"}
        )
        
        assert event.type == EventTypes.PROJECT_CREATED
        assert "project_id" in event.payload
        assert isinstance(event.id, type(uuid4()))
        assert isinstance(event.timestamp, datetime)
        assert event.source is None
        assert event.correlation_id is None
    
    def test_event_with_optional_fields(self):
        """Test creating an event with all fields."""
        correlation_id = uuid4()
        event = Event(
            type=EventTypes.COMMAND_APPROVED,
            payload={"command_id": str(uuid4())},
            source="test_source",
            correlation_id=correlation_id
        )
        
        assert event.source == "test_source"
        assert event.correlation_id == correlation_id
    
    def test_event_validation(self):
        """Test event validation in post_init."""
        # Empty type should raise
        with pytest.raises(ValueError, match="Event type cannot be empty"):
            Event(type="", payload={})
        
        # Non-dict payload should raise
        with pytest.raises(ValueError, match="Event payload must be a dictionary"):
            Event(type="test", payload="not a dict")  # type: ignore


class TestEventBus:
    """Test the EventBus implementation."""
    
    @pytest.fixture
    def event_bus(self):
        """Create a fresh event bus for each test."""
        return EventBus(name="test")
    
    def test_bus_initialization(self, event_bus):
        """Test event bus is properly initialized."""
        assert event_bus.name == "test"
        assert event_bus.get_handler_count() == 0
        assert len(event_bus.get_history()) == 0
    
    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self, event_bus):
        """Test basic subscribe and publish functionality."""
        received_events = []
        
        def handler(event: Event):
            received_events.append(event)
        
        # Subscribe to project events
        event_bus.subscribe(EventTypes.PROJECT_CREATED, handler)
        
        # Publish a project created event
        event = Event(
            type=EventTypes.PROJECT_CREATED,
            payload={"name": "Test"}
        )
        await event_bus.publish(event)
        
        assert len(received_events) == 1
        assert received_events[0] == event
    
    @pytest.mark.asyncio
    async def test_async_handler(self, event_bus):
        """Test async event handlers."""
        received_events = []
        
        async def async_handler(event: Event):
            await asyncio.sleep(0.01)  # Simulate async work
            received_events.append(event)
        
        event_bus.subscribe_async(EventTypes.COMMAND_EXECUTING, async_handler)
        
        event = Event(
            type=EventTypes.COMMAND_EXECUTING,
            payload={"command": "test"}
        )
        await event_bus.publish(event)
        
        assert len(received_events) == 1
        assert received_events[0] == event
    
    @pytest.mark.asyncio
    async def test_multiple_handlers(self, event_bus):
        """Test multiple handlers for same event type."""
        handler1_events = []
        handler2_events = []
        
        def handler1(event: Event):
            handler1_events.append(event)
        
        def handler2(event: Event):
            handler2_events.append(event)
        
        event_bus.subscribe(EventTypes.STATE_UPDATED, handler1)
        event_bus.subscribe(EventTypes.STATE_UPDATED, handler2)
        
        event = Event(
            type=EventTypes.STATE_UPDATED,
            payload={"key": "value"}
        )
        await event_bus.publish(event)
        
        assert len(handler1_events) == 1
        assert len(handler2_events) == 1
        assert handler1_events[0] == handler2_events[0] == event
    
    @pytest.mark.asyncio
    async def test_global_handler(self, event_bus):
        """Test global handler receives all events."""
        all_events = []
        
        def global_handler(event: Event):
            all_events.append(event)
        
        event_bus.subscribe_all(global_handler)
        
        # Publish different event types
        event1 = Event(type=EventTypes.PROJECT_CREATED, payload={})
        event2 = Event(type=EventTypes.COMMAND_APPROVED, payload={})
        event3 = Event(type=EventTypes.STATE_UPDATED, payload={})
        
        await event_bus.publish(event1)
        await event_bus.publish(event2)
        await event_bus.publish(event3)
        
        assert len(all_events) == 3
        assert all_events == [event1, event2, event3]
    
    @pytest.mark.asyncio
    async def test_unsubscribe(self, event_bus):
        """Test unsubscribing handlers."""
        received_events = []
        
        def handler(event: Event):
            received_events.append(event)
        
        # Subscribe and publish
        event_bus.subscribe(EventTypes.PROJECT_CREATED, handler)
        event1 = Event(type=EventTypes.PROJECT_CREATED, payload={})
        await event_bus.publish(event1)
        
        assert len(received_events) == 1
        
        # Unsubscribe and publish again
        event_bus.unsubscribe(EventTypes.PROJECT_CREATED, handler)
        event2 = Event(type=EventTypes.PROJECT_CREATED, payload={})
        await event_bus.publish(event2)
        
        assert len(received_events) == 1  # No new event received
    
    @pytest.mark.asyncio
    async def test_error_handling(self, event_bus):
        """Test that errors in handlers don't break event bus."""
        successful_events = []
        
        def failing_handler(event: Event):
            raise RuntimeError("Handler error")
        
        def working_handler(event: Event):
            successful_events.append(event)
        
        # Subscribe both handlers
        event_bus.subscribe(EventTypes.SYSTEM_ERROR, failing_handler)
        event_bus.subscribe(EventTypes.SYSTEM_ERROR, working_handler)
        
        # Publish event - should not raise
        event = Event(type=EventTypes.SYSTEM_ERROR, payload={"error": "test"})
        await event_bus.publish(event)
        
        # Working handler should still receive event
        assert len(successful_events) == 1
        assert successful_events[0] == event
    
    @pytest.mark.asyncio
    async def test_event_history(self, event_bus):
        """Test event history functionality."""
        # Publish some events
        events = []
        for i in range(5):
            event = Event(
                type=EventTypes.STATE_UPDATED,
                payload={"index": i}
            )
            events.append(event)
            await event_bus.publish(event)
        
        # Check full history
        history = event_bus.get_history()
        assert len(history) == 5
        assert history == events
        
        # Check limited history
        limited = event_bus.get_history(limit=3)
        assert len(limited) == 3
        assert limited == events[-3:]
        
        # Check filtered history
        # Add a different event type
        other_event = Event(type=EventTypes.PROJECT_CREATED, payload={})
        await event_bus.publish(other_event)
        
        filtered = event_bus.get_history(event_type=EventTypes.STATE_UPDATED)
        assert len(filtered) == 5
        assert all(e.type == EventTypes.STATE_UPDATED for e in filtered)
    
    @pytest.mark.asyncio
    async def test_pause_and_resume(self, event_bus):
        """Test pausing and resuming event processing."""
        received_events = []
        
        def handler(event: Event):
            received_events.append(event)
        
        event_bus.subscribe(EventTypes.COMMAND_PROPOSED, handler)
        
        # Pause the bus
        event_bus.pause()
        
        # Publish events while paused
        event1 = Event(type=EventTypes.COMMAND_PROPOSED, payload={"cmd": "1"})
        event2 = Event(type=EventTypes.COMMAND_PROPOSED, payload={"cmd": "2"})
        
        await event_bus.publish(event1)
        await event_bus.publish(event2)
        
        # No events should be received yet
        assert len(received_events) == 0
        
        # Resume processing
        await event_bus.resume()
        
        # Events should now be processed
        assert len(received_events) == 2
        assert received_events == [event1, event2]
    
    def test_handler_count(self, event_bus):
        """Test getting handler counts."""
        def handler1(event: Event): pass
        def handler2(event: Event): pass
        def global_handler(event: Event): pass
        
        # Subscribe handlers
        event_bus.subscribe(EventTypes.PROJECT_CREATED, handler1)
        event_bus.subscribe(EventTypes.PROJECT_CREATED, handler2)
        event_bus.subscribe(EventTypes.COMMAND_APPROVED, handler1)
        event_bus.subscribe_all(global_handler)
        
        # Check counts
        assert event_bus.get_handler_count(EventTypes.PROJECT_CREATED) == 2
        assert event_bus.get_handler_count(EventTypes.COMMAND_APPROVED) == 1
        assert event_bus.get_handler_count(EventTypes.STATE_UPDATED) == 0
        assert event_bus.get_handler_count() == 4  # Total including global


class TestScopedEventBus:
    """Test the ScopedEventBus implementation."""
    
    @pytest.mark.asyncio
    async def test_scoped_bus_namespace(self):
        """Test that scoped bus adds namespace to events."""
        parent_bus = EventBus("parent")
        scoped_bus = ScopedEventBus("ui", parent_bus)
        
        parent_events = []
        
        def parent_handler(event: Event):
            parent_events.append(event)
        
        parent_bus.subscribe_all(parent_handler)
        
        # Publish from scoped bus
        event = Event(
            type=EventTypes.UI_READY,
            payload={}
        )
        await scoped_bus.publish(event)
        
        # Parent should receive event with source set
        assert len(parent_events) == 1
        assert parent_events[0].source == "ui"
    
    @pytest.mark.asyncio
    async def test_scoped_bus_local_events(self):
        """Test that local events don't propagate to parent."""
        parent_bus = EventBus("parent")
        scoped_bus = ScopedEventBus("worker", parent_bus)
        
        parent_events = []
        scoped_events = []
        
        def parent_handler(event: Event):
            parent_events.append(event)
        
        def scoped_handler(event: Event):
            scoped_events.append(event)
        
        parent_bus.subscribe_all(parent_handler)
        scoped_bus.subscribe_all(scoped_handler)
        
        # Publish local event (starts with _local_)
        local_event = Event(
            type="_local_worker_status",
            payload={"status": "busy"}
        )
        await scoped_bus.publish(local_event)
        
        # Only scoped bus should receive it
        assert len(scoped_events) == 1
        assert len(parent_events) == 0
        
        # Publish normal event
        normal_event = Event(
            type=EventTypes.COMMAND_COMPLETED,
            payload={}
        )
        await scoped_bus.publish(normal_event)
        
        # Both should receive it
        assert len(scoped_events) == 2
        assert len(parent_events) == 1