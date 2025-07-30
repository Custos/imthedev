"""Event bus implementation for decoupled communication between components.

This module provides the core event-driven architecture that enables
loose coupling between different layers and components of the application.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID, uuid4
from weakref import WeakSet

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Base event class for all system events.
    
    Attributes:
        id: Unique identifier for the event instance
        type: Event type identifier (from EventTypes)
        timestamp: When the event was created
        payload: Event-specific data
        source: Optional identifier of the event source
        correlation_id: Optional ID to correlate related events
    """
    
    type: str
    payload: Dict[str, Any]
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None
    correlation_id: Optional[UUID] = None
    
    def __post_init__(self) -> None:
        """Validate event data after initialization."""
        if not self.type:
            raise ValueError("Event type cannot be empty")
        if not isinstance(self.payload, dict):
            raise ValueError("Event payload must be a dictionary")


EventHandler = Callable[[Event], None]
AsyncEventHandler = Callable[[Event], asyncio.Future]


class EventBus:
    """Central event bus for publish-subscribe communication.
    
    This implementation supports both synchronous and asynchronous handlers,
    with proper error handling and optional event filtering.
    """
    
    def __init__(self, name: str = "main"):
        """Initialize the event bus.
        
        Args:
            name: Bus identifier for logging and debugging
        """
        self.name = name
        self._handlers: Dict[str, Set[EventHandler]] = {}
        self._async_handlers: Dict[str, Set[AsyncEventHandler]] = {}
        self._global_handlers: Set[EventHandler] = WeakSet()
        self._event_history: List[Event] = []
        self._history_limit = 1000
        self._paused = False
        self._event_queue: asyncio.Queue[Event] = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None
        
    def subscribe(
        self,
        event_type: str,
        handler: EventHandler,
        weak: bool = True
    ) -> None:
        """Subscribe a handler to a specific event type.
        
        Args:
            event_type: Type of events to handle
            handler: Callback function to handle events
            weak: If True, use weak reference (handler can be garbage collected)
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = set() if not weak else WeakSet()
        
        self._handlers[event_type].add(handler)
        logger.debug(f"Handler {handler} subscribed to {event_type}")
    
    def subscribe_async(
        self,
        event_type: str,
        handler: AsyncEventHandler
    ) -> None:
        """Subscribe an async handler to a specific event type.
        
        Args:
            event_type: Type of events to handle
            handler: Async callback function to handle events
        """
        if event_type not in self._async_handlers:
            self._async_handlers[event_type] = set()
        
        self._async_handlers[event_type].add(handler)
        logger.debug(f"Async handler {handler} subscribed to {event_type}")
    
    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe a handler to all events.
        
        Args:
            handler: Callback to receive all events
        """
        self._global_handlers.add(handler)
        logger.debug(f"Handler {handler} subscribed to all events")
    
    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe a handler from an event type.
        
        Args:
            event_type: Event type to unsubscribe from
            handler: Handler to remove
        """
        if event_type in self._handlers:
            self._handlers[event_type].discard(handler)
            if not self._handlers[event_type]:
                del self._handlers[event_type]
        
        if event_type in self._async_handlers:
            self._async_handlers[event_type].discard(handler)
            if not self._async_handlers[event_type]:
                del self._async_handlers[event_type]
    
    def unsubscribe_all(self, handler: EventHandler) -> None:
        """Remove a handler from all subscriptions.
        
        Args:
            handler: Handler to remove completely
        """
        for event_type in list(self._handlers.keys()):
            self.unsubscribe(event_type, handler)
        
        self._global_handlers.discard(handler)
    
    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribed handlers.
        
        Args:
            event: Event to publish
        """
        if self._paused:
            await self._event_queue.put(event)
            return
        
        # Add to history
        self._add_to_history(event)
        
        # Log event
        logger.debug(
            f"Publishing event: type={event.type}, "
            f"id={event.id}, source={event.source}"
        )
        
        # Notify type-specific handlers
        await self._notify_handlers(event)
        
        # Notify global handlers
        await self._notify_global_handlers(event)
    
    async def _notify_handlers(self, event: Event) -> None:
        """Notify all handlers for a specific event type."""
        # Synchronous handlers
        if event.type in self._handlers:
            for handler in list(self._handlers[event.type]):
                try:
                    handler(event)
                except Exception as e:
                    logger.error(
                        f"Error in event handler {handler} for {event.type}: {e}",
                        exc_info=True
                    )
        
        # Asynchronous handlers
        if event.type in self._async_handlers:
            tasks = []
            for handler in list(self._async_handlers[event.type]):
                tasks.append(self._call_async_handler(handler, event))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _notify_global_handlers(self, event: Event) -> None:
        """Notify all global handlers."""
        for handler in list(self._global_handlers):
            try:
                handler(event)
            except Exception as e:
                logger.error(
                    f"Error in global handler {handler}: {e}",
                    exc_info=True
                )
    
    async def _call_async_handler(
        self,
        handler: AsyncEventHandler,
        event: Event
    ) -> None:
        """Call an async handler with error handling."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(
                f"Error in async handler {handler} for {event.type}: {e}",
                exc_info=True
            )
    
    def _add_to_history(self, event: Event) -> None:
        """Add event to history with size limit."""
        self._event_history.append(event)
        if len(self._event_history) > self._history_limit:
            self._event_history.pop(0)
    
    def get_history(
        self,
        event_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Event]:
        """Get event history with optional filtering.
        
        Args:
            event_type: Filter by event type
            limit: Maximum number of events to return
            
        Returns:
            List of events matching criteria
        """
        history = self._event_history
        
        if event_type:
            history = [e for e in history if e.type == event_type]
        
        if limit:
            history = history[-limit:]
        
        return history.copy()
    
    def pause(self) -> None:
        """Pause event processing (events are queued)."""
        self._paused = True
        logger.info(f"Event bus '{self.name}' paused")
    
    async def resume(self) -> None:
        """Resume event processing and process queued events."""
        self._paused = False
        logger.info(f"Event bus '{self.name}' resumed")
        
        # Process queued events
        while not self._event_queue.empty():
            try:
                event = self._event_queue.get_nowait()
                await self.publish(event)
            except asyncio.QueueEmpty:
                break
    
    def clear_history(self) -> None:
        """Clear the event history."""
        self._event_history.clear()
    
    def get_handler_count(self, event_type: Optional[str] = None) -> int:
        """Get count of registered handlers.
        
        Args:
            event_type: Count handlers for specific type, or all if None
            
        Returns:
            Number of registered handlers
        """
        if event_type:
            sync_count = len(self._handlers.get(event_type, set()))
            async_count = len(self._async_handlers.get(event_type, set()))
            return sync_count + async_count
        else:
            total = len(self._global_handlers)
            for handlers in self._handlers.values():
                total += len(handlers)
            for handlers in self._async_handlers.values():
                total += len(handlers)
            return total


class ScopedEventBus(EventBus):
    """Event bus with namespace scoping for modularity.
    
    This allows different parts of the application to have isolated
    event spaces while still enabling cross-namespace communication.
    """
    
    def __init__(self, namespace: str, parent: Optional[EventBus] = None):
        """Initialize scoped event bus.
        
        Args:
            namespace: Namespace for this bus
            parent: Optional parent bus for event propagation
        """
        super().__init__(name=f"{namespace}_bus")
        self.namespace = namespace
        self.parent = parent
        
    async def publish(self, event: Event) -> None:
        """Publish event with namespace scoping."""
        # Add namespace to event if not present
        if not event.source:
            event.source = self.namespace
        
        # Publish locally
        await super().publish(event)
        
        # Propagate to parent if configured
        if self.parent and not event.type.startswith("_local_"):
            await self.parent.publish(event)