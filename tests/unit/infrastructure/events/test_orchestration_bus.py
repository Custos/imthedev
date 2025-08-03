"""Unit tests for the orchestration event bus."""

import asyncio
import pytest
from uuid import uuid4

from imthedev.infrastructure.events import (
    OrchestrationEvent,
    OrchestrationEventBus,
    CommandProposed,
    ExecutionStarted,
)


@pytest.fixture
def event_bus():
    """Create a fresh event bus for testing."""
    return OrchestrationEventBus()


@pytest.mark.asyncio
async def test_event_subscription_and_emission(event_bus):
    """Test basic event subscription and emission."""
    received_events = []
    
    async def handler(event: OrchestrationEvent):
        received_events.append(event)
    
    # Subscribe to events
    event_bus.subscribe(CommandProposed, handler)
    
    # Emit an event
    test_event = CommandProposed(
        command_text="/sc:test",
        reasoning="Testing",
        confidence=0.9
    )
    await event_bus.emit(test_event)
    
    # Allow event processing
    await asyncio.sleep(0.01)
    
    # Check event was received
    assert len(received_events) == 1
    assert received_events[0].command_text == "/sc:test"
    assert received_events[0].confidence == 0.9


@pytest.mark.asyncio
async def test_multiple_handlers_same_event(event_bus):
    """Test multiple handlers for the same event type."""
    handler1_called = False
    handler2_called = False
    
    async def handler1(event: OrchestrationEvent):
        nonlocal handler1_called
        handler1_called = True
    
    async def handler2(event: OrchestrationEvent):
        nonlocal handler2_called
        handler2_called = True
    
    # Subscribe both handlers
    event_bus.subscribe(ExecutionStarted, handler1)
    event_bus.subscribe(ExecutionStarted, handler2)
    
    # Emit event
    await event_bus.emit(ExecutionStarted(command="/sc:test"))
    await asyncio.sleep(0.01)
    
    # Both handlers should be called
    assert handler1_called
    assert handler2_called


@pytest.mark.asyncio
async def test_event_inheritance_handling(event_bus):
    """Test that parent class handlers receive child events."""
    base_events = []
    specific_events = []
    
    async def base_handler(event: OrchestrationEvent):
        base_events.append(event)
    
    async def specific_handler(event: CommandProposed):
        specific_events.append(event)
    
    # Subscribe to base and specific
    event_bus.subscribe(OrchestrationEvent, base_handler)
    event_bus.subscribe(CommandProposed, specific_handler)
    
    # Emit specific event
    test_event = CommandProposed(command_text="/sc:test")
    await event_bus.emit(test_event)
    await asyncio.sleep(0.01)
    
    # Both handlers should receive it
    assert len(base_events) == 1
    assert len(specific_events) == 1


@pytest.mark.asyncio
async def test_unsubscribe_handler(event_bus):
    """Test unsubscribing a handler."""
    call_count = 0
    
    async def handler(event: OrchestrationEvent):
        nonlocal call_count
        call_count += 1
    
    # Subscribe and emit
    event_bus.subscribe(CommandProposed, handler)
    await event_bus.emit(CommandProposed(command_text="/sc:test1"))
    await asyncio.sleep(0.01)
    assert call_count == 1
    
    # Unsubscribe and emit again
    event_bus.unsubscribe(CommandProposed, handler)
    await event_bus.emit(CommandProposed(command_text="/sc:test2"))
    await asyncio.sleep(0.01)
    assert call_count == 1  # Should not increase


@pytest.mark.asyncio
async def test_event_history_and_replay(event_bus):
    """Test event history and replay functionality."""
    replayed_events = []
    
    async def handler(event: CommandProposed):
        replayed_events.append(event)
    
    # Emit some events
    event1 = CommandProposed(command_text="/sc:test1", confidence=0.8)
    event2 = CommandProposed(command_text="/sc:test2", confidence=0.9)
    await event_bus.emit(event1)
    await event_bus.emit(event2)
    await asyncio.sleep(0.01)
    
    # Subscribe handler after events were emitted
    event_bus.subscribe(CommandProposed, handler)
    
    # Replay events
    await event_bus.replay_events()
    await asyncio.sleep(0.01)
    
    # Should receive both historical events
    assert len(replayed_events) == 2
    assert replayed_events[0].command_text == "/sc:test1"
    assert replayed_events[1].command_text == "/sc:test2"


@pytest.mark.asyncio
async def test_event_replay_with_filter(event_bus):
    """Test replaying events with a filter function."""
    replayed_events = []
    
    async def handler(event: CommandProposed):
        replayed_events.append(event)
    
    # Emit events with different confidence levels
    await event_bus.emit(CommandProposed(command_text="/sc:low", confidence=0.3))
    await event_bus.emit(CommandProposed(command_text="/sc:high", confidence=0.9))
    await asyncio.sleep(0.01)
    
    event_bus.subscribe(CommandProposed, handler)
    
    # Replay only high confidence events
    def high_confidence_filter(event):
        return hasattr(event, 'confidence') and event.confidence > 0.5
    
    await event_bus.replay_events(high_confidence_filter)
    await asyncio.sleep(0.01)
    
    # Should only receive high confidence event
    assert len(replayed_events) == 1
    assert replayed_events[0].command_text == "/sc:high"


@pytest.mark.asyncio
async def test_concurrent_event_processing(event_bus):
    """Test that events are processed concurrently."""
    processing_order = []
    
    async def slow_handler(event: OrchestrationEvent):
        await asyncio.sleep(0.01)
        processing_order.append(f"slow-{event.metadata.get('id')}")
    
    async def fast_handler(event: OrchestrationEvent):
        processing_order.append(f"fast-{event.metadata.get('id')}")
    
    # Subscribe both handlers
    event_bus.subscribe(OrchestrationEvent, slow_handler)
    event_bus.subscribe(OrchestrationEvent, fast_handler)
    
    # Emit event
    await event_bus.emit(OrchestrationEvent(metadata={"id": "1"}))
    await asyncio.sleep(0.02)
    
    # Fast handler should complete first due to concurrent processing
    assert processing_order[0] == "fast-1"
    assert processing_order[1] == "slow-1"


@pytest.mark.asyncio
async def test_event_metrics(event_bus):
    """Test event bus metrics collection."""
    # Subscribe a handler
    async def handler(event: OrchestrationEvent):
        await asyncio.sleep(0.001)
    
    event_bus.subscribe(OrchestrationEvent, handler)
    
    # Emit some events
    for i in range(5):
        await event_bus.emit(OrchestrationEvent(metadata={"id": i}))
    
    await asyncio.sleep(0.02)
    
    # Check metrics
    metrics = event_bus.get_metrics()
    assert metrics["events_processed"] == 5
    assert metrics["events_failed"] == 0
    assert metrics["events_in_history"] == 5
    assert metrics["handlers_registered"] == 1
    assert metrics["average_processing_time"] > 0


@pytest.mark.asyncio
async def test_error_handling_in_handler(event_bus):
    """Test that errors in one handler don't affect others."""
    successful_calls = 0
    
    async def failing_handler(event: OrchestrationEvent):
        raise ValueError("Handler error")
    
    async def working_handler(event: OrchestrationEvent):
        nonlocal successful_calls
        successful_calls += 1
    
    # Subscribe both
    event_bus.subscribe(OrchestrationEvent, failing_handler)
    event_bus.subscribe(OrchestrationEvent, working_handler)
    
    # Emit event
    await event_bus.emit(OrchestrationEvent())
    await asyncio.sleep(0.01)
    
    # Working handler should still be called
    assert successful_calls == 1


@pytest.mark.asyncio
async def test_clear_history(event_bus):
    """Test clearing event history."""
    # Emit some events
    for i in range(3):
        await event_bus.emit(OrchestrationEvent(metadata={"id": i}))
    
    await asyncio.sleep(0.01)
    
    metrics = event_bus.get_metrics()
    assert metrics["events_in_history"] == 3
    
    # Clear history
    event_bus.clear_history()
    
    metrics = event_bus.get_metrics()
    assert metrics["events_in_history"] == 0