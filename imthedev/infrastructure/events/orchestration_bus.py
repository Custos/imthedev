"""Central event bus for dual-AI orchestration.

This module provides the core event dispatcher for communication between
Gemini orchestrator and Claude Code executor components.
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine, Optional
from uuid import UUID, uuid4
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OrchestrationEvent:
    """Base class for all orchestration events."""
    
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class OrchestrationEventBus:
    """Central event dispatcher for orchestration system.
    
    Handles async event distribution between components with support for
    event replay, filtering, and performance monitoring.
    """
    
    def __init__(self) -> None:
        """Initialize the event bus."""
        self._handlers: dict[type[OrchestrationEvent], list[Callable]] = defaultdict(list)
        self._event_history: list[OrchestrationEvent] = []
        self._replay_mode: bool = False
        self._event_queue: asyncio.Queue[OrchestrationEvent] = asyncio.Queue()
        self._processing: bool = False
        self._metrics = {
            "events_processed": 0,
            "events_failed": 0,
            "total_processing_time": 0.0,
        }
    
    def subscribe(
        self,
        event_type: type[OrchestrationEvent],
        handler: Callable[[OrchestrationEvent], Coroutine[Any, Any, None]]
    ) -> None:
        """Subscribe a handler to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            handler: Async function to handle the event
        """
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed {handler.__name__} to {event_type.__name__}")
    
    def unsubscribe(
        self,
        event_type: type[OrchestrationEvent],
        handler: Callable[[OrchestrationEvent], Coroutine[Any, Any, None]]
    ) -> None:
        """Unsubscribe a handler from an event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler to remove
        """
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            logger.debug(f"Unsubscribed {handler.__name__} from {event_type.__name__}")
    
    async def emit(self, event: OrchestrationEvent) -> None:
        """Emit an event to all subscribed handlers.
        
        Args:
            event: Event to emit
        """
        await self._event_queue.put(event)
        
        # Start processing if not already running
        if not self._processing:
            asyncio.create_task(self._process_events())
    
    async def _process_events(self) -> None:
        """Process events from the queue."""
        self._processing = True
        
        while not self._event_queue.empty():
            event = await self._event_queue.get()
            
            # Store in history for replay capability
            self._event_history.append(event)
            
            # Track metrics
            start_time = asyncio.get_event_loop().time()
            
            # Get all handlers for this event type and its parent classes
            handlers = self._get_handlers_for_event(event)
            
            # Execute handlers concurrently
            if handlers:
                try:
                    await asyncio.gather(
                        *[handler(event) for handler in handlers],
                        return_exceptions=True
                    )
                    self._metrics["events_processed"] += 1
                except Exception as e:
                    logger.error(f"Error processing event {event.id}: {e}")
                    self._metrics["events_failed"] += 1
            
            # Update processing time metric
            processing_time = asyncio.get_event_loop().time() - start_time
            self._metrics["total_processing_time"] += processing_time
            
            # Log if processing is slow
            if processing_time > 0.01:  # 10ms threshold
                logger.warning(
                    f"Event {event.__class__.__name__} took {processing_time:.3f}s to process"
                )
        
        self._processing = False
    
    def _get_handlers_for_event(
        self, event: OrchestrationEvent
    ) -> list[Callable]:
        """Get all handlers that should process this event.
        
        Args:
            event: Event to find handlers for
            
        Returns:
            List of handler functions
        """
        handlers = []
        
        # Check event type and all parent classes
        for event_class in event.__class__.__mro__:
            if event_class in self._handlers:
                handlers.extend(self._handlers[event_class])
        
        return handlers
    
    async def replay_events(
        self,
        filter_fn: Optional[Callable[[OrchestrationEvent], bool]] = None
    ) -> None:
        """Replay historical events for debugging.
        
        Args:
            filter_fn: Optional function to filter which events to replay
        """
        self._replay_mode = True
        
        events_to_replay = self._event_history
        if filter_fn:
            events_to_replay = [e for e in events_to_replay if filter_fn(e)]
        
        logger.info(f"Replaying {len(events_to_replay)} events")
        
        for event in events_to_replay:
            await self.emit(event)
        
        self._replay_mode = False
    
    def get_metrics(self) -> dict[str, Any]:
        """Get event bus performance metrics.
        
        Returns:
            Dictionary of metrics
        """
        avg_time = 0.0
        if self._metrics["events_processed"] > 0:
            avg_time = (
                self._metrics["total_processing_time"] / 
                self._metrics["events_processed"]
            )
        
        return {
            **self._metrics,
            "average_processing_time": avg_time,
            "events_in_history": len(self._event_history),
            "handlers_registered": sum(len(h) for h in self._handlers.values()),
        }
    
    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()
        logger.info("Event history cleared")


# Global event bus instance
orchestration_bus = OrchestrationEventBus()