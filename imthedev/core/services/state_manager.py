"""State management implementation for application-wide state.

This module provides the core state management functionality that maintains
and synchronizes global application state across all components.
"""

import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Set
from uuid import UUID
from weakref import WeakSet

from imthedev.core.events import Event, EventBus, EventPriority, EventTypes
from imthedev.core.interfaces import AIModel, ApplicationState, StateManager


logger = logging.getLogger(__name__)


class InvalidStateError(Exception):
    """Raised when state update contains invalid fields or values."""
    pass


class InvalidModelError(Exception):
    """Raised when attempting to set an unsupported AI model."""
    pass


class StateManagerImpl(StateManager):
    """Implementation of application state management with event notifications.
    
    This manager maintains the global application state and notifies all
    interested components when state changes occur. State is persisted
    to disk for session continuity.
    
    Features:
    - Centralized state management
    - Event-driven state change notifications
    - Persistent state storage
    - Type-safe state updates
    - Callback subscription management
    """
    
    VALID_AI_MODELS = {
        AIModel.CLAUDE,
        AIModel.CLAUDE_INSTANT,
        AIModel.GPT4,
        AIModel.GPT35_TURBO
    }
    
    def __init__(
        self,
        event_bus: EventBus,
        state_file_path: Optional[Path] = None
    ) -> None:
        """Initialize the state manager.
        
        Args:
            event_bus: Event bus for publishing state change events
            state_file_path: Optional path for persistent state storage
        """
        self._event_bus = event_bus
        self._state_file = state_file_path
        self._subscribers: WeakSet[Callable[[ApplicationState], None]] = WeakSet()
        
        # Initialize with default state
        self._state = ApplicationState()
        
        # Load persisted state if available
        if self._state_file and self._state_file.exists():
            self._load_state()
            
    def get_state(self) -> ApplicationState:
        """Get the current application state.
        
        Returns:
            Current application state object
        """
        return self._state
        
    async def update_state(self, updates: Dict[str, Any]) -> None:
        """Update application state with partial updates.
        
        Validates updates before applying them and notifies all subscribers
        and event listeners of the changes.
        
        Args:
            updates: Dictionary of state fields to update
            
        Raises:
            InvalidStateError: If updates contain invalid fields or values
        """
        # Validate update fields
        valid_fields = {
            'current_project_id',
            'autopilot_enabled',
            'selected_ai_model',
            'ui_preferences'
        }
        
        invalid_fields = set(updates.keys()) - valid_fields
        if invalid_fields:
            raise InvalidStateError(
                f"Invalid state fields: {', '.join(invalid_fields)}"
            )
            
        # Validate specific field values
        if 'selected_ai_model' in updates:
            model = updates['selected_ai_model']
            if model not in self.VALID_AI_MODELS:
                raise InvalidStateError(
                    f"Invalid AI model: {model}. Valid models: {', '.join(self.VALID_AI_MODELS)}"
                )
                
        if 'current_project_id' in updates and updates['current_project_id'] is not None:
            # Ensure it's a valid UUID
            try:
                UUID(str(updates['current_project_id']))
            except ValueError:
                raise InvalidStateError(
                    f"Invalid project ID format: {updates['current_project_id']}"
                )
                
        # Apply updates
        old_state = self._create_state_snapshot()
        
        for field, value in updates.items():
            setattr(self._state, field, value)
            
        # Persist state
        self._persist_state()
        
        # Notify subscribers
        self._notify_subscribers()
        
        # Publish state change event
        await self._publish_state_change_event(old_state, self._state, updates)
        
    async def toggle_autopilot(self) -> bool:
        """Toggle autopilot mode on/off.
        
        Returns:
            New autopilot state (True if enabled)
        """
        new_state = not self._state.autopilot_enabled
        await self.update_state({'autopilot_enabled': new_state})
        
        # Publish specific autopilot toggle event
        event_type = EventTypes.STATE_AUTOPILOT_ENABLED if new_state else EventTypes.STATE_AUTOPILOT_DISABLED
        await self._event_bus.publish(Event(
            type=event_type,
            payload={
                'enabled': new_state,
                'project_id': str(self._state.current_project_id) if self._state.current_project_id else None
            }
        ))
        
        return new_state
        
    async def set_ai_model(self, model: str) -> None:
        """Set the active AI model.
        
        Args:
            model: Model identifier to use
            
        Raises:
            InvalidModelError: If model is not supported
        """
        if model not in self.VALID_AI_MODELS:
            raise InvalidModelError(
                f"Unsupported AI model: {model}. "
                f"Valid models: {', '.join(self.VALID_AI_MODELS)}"
            )
            
        old_model = self._state.selected_ai_model
        await self.update_state({'selected_ai_model': model})
        
        # Publish specific model change event
        await self._event_bus.publish(Event(
            type=EventTypes.STATE_MODEL_CHANGED,
            payload={
                'old_model': old_model,
                'new_model': model
            }
        ))
        
    def subscribe(self, callback: Callable[[ApplicationState], None]) -> None:
        """Subscribe to state changes.
        
        The callback will be invoked whenever the application state changes.
        Uses weak references to prevent memory leaks.
        
        Args:
            callback: Function to call when state changes
                     Signature: callback(state: ApplicationState) -> None
        """
        self._subscribers.add(callback)
        logger.debug(f"State subscriber added: {callback}")
        
    def unsubscribe(self, callback: Callable[[ApplicationState], None]) -> None:
        """Unsubscribe from state changes.
        
        Args:
            callback: Previously subscribed callback to remove
        """
        self._subscribers.discard(callback)
        logger.debug(f"State subscriber removed: {callback}")
        
    def _create_state_snapshot(self) -> ApplicationState:
        """Create a snapshot of the current state.
        
        Returns:
            Copy of the current state
        """
        return ApplicationState(
            current_project_id=self._state.current_project_id,
            autopilot_enabled=self._state.autopilot_enabled,
            selected_ai_model=self._state.selected_ai_model,
            ui_preferences=self._state.ui_preferences.copy()
        )
        
    def _notify_subscribers(self) -> None:
        """Notify all subscribers of state change."""
        # Create a list to avoid set modification during iteration
        subscribers = list(self._subscribers)
        
        for callback in subscribers:
            try:
                callback(self._state)
            except Exception as e:
                logger.error(
                    f"Error in state change callback {callback}: {e}",
                    exc_info=True
                )
                
    async def _publish_state_change_event(
        self,
        old_state: ApplicationState,
        new_state: ApplicationState,
        changes: Dict[str, Any]
    ) -> None:
        """Publish event for state changes.
        
        Args:
            old_state: State before changes
            new_state: State after changes
            changes: Dictionary of changed fields
        """
        await self._event_bus.publish(Event(
            type=EventTypes.STATE_UPDATED,
            payload={
                'changes': changes,
                'old_state': {
                    'current_project_id': str(old_state.current_project_id) if old_state.current_project_id else None,
                    'autopilot_enabled': old_state.autopilot_enabled,
                    'selected_ai_model': old_state.selected_ai_model,
                    'ui_preferences': old_state.ui_preferences
                },
                'new_state': {
                    'current_project_id': str(new_state.current_project_id) if new_state.current_project_id else None,
                    'autopilot_enabled': new_state.autopilot_enabled,
                    'selected_ai_model': new_state.selected_ai_model,
                    'ui_preferences': new_state.ui_preferences
                }
            }
        ))
        
    def _persist_state(self) -> None:
        """Persist current state to disk."""
        if not self._state_file:
            return
            
        try:
            # Ensure directory exists
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Serialize state
            state_data = {
                'current_project_id': str(self._state.current_project_id) if self._state.current_project_id else None,
                'autopilot_enabled': self._state.autopilot_enabled,
                'selected_ai_model': self._state.selected_ai_model,
                'ui_preferences': self._state.ui_preferences
            }
            
            # Write atomically
            temp_file = self._state_file.with_suffix('.tmp')
            temp_file.write_text(json.dumps(state_data, indent=2))
            temp_file.replace(self._state_file)
            
            logger.debug("State persisted to disk")
            
        except Exception as e:
            logger.error(f"Failed to persist state: {e}", exc_info=True)
            
    def _load_state(self) -> None:
        """Load state from disk."""
        if not self._state_file or not self._state_file.exists():
            return
            
        try:
            state_data = json.loads(self._state_file.read_text())
            
            # Restore state
            project_id = state_data.get('current_project_id')
            self._state.current_project_id = UUID(project_id) if project_id else None
            self._state.autopilot_enabled = state_data.get('autopilot_enabled', False)
            self._state.selected_ai_model = state_data.get('selected_ai_model', AIModel.CLAUDE)
            self._state.ui_preferences = state_data.get('ui_preferences', {})
            
            logger.info("State loaded from disk")
            
        except Exception as e:
            logger.error(f"Failed to load state: {e}", exc_info=True)
            # Continue with default state