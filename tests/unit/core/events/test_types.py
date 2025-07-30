"""Unit tests for event type definitions."""

import pytest

from imthedev.core.events import EventPriority, EventTypes


class TestEventTypes:
    """Test the EventTypes class."""
    
    def test_event_type_values(self):
        """Test that event types have correct string values."""
        assert EventTypes.PROJECT_CREATED == "project.created"
        assert EventTypes.COMMAND_APPROVED == "command.approved"
        assert EventTypes.STATE_AUTOPILOT_ENABLED == "state.autopilot.enabled"
        assert EventTypes.SYSTEM_STARTUP == "system.startup"
    
    def test_event_naming_convention(self):
        """Test that all events follow the naming convention."""
        all_events = EventTypes.all_events()
        
        for event in all_events:
            # Should contain at least one dot
            assert '.' in event, f"Event {event} doesn't follow naming convention"
            
            # Should be lowercase
            assert event.islower(), f"Event {event} should be lowercase"
            
            # Should not have spaces
            assert ' ' not in event, f"Event {event} contains spaces"
    
    def test_all_events(self):
        """Test getting all event types."""
        all_events = EventTypes.all_events()
        
        # Should have a reasonable number of events
        assert len(all_events) > 20
        
        # Should include known events
        assert EventTypes.PROJECT_CREATED in all_events
        assert EventTypes.COMMAND_APPROVED in all_events
        assert EventTypes.SYSTEM_SHUTDOWN in all_events
        
        # Should not include class methods or private attributes
        assert "all_events" not in all_events
        assert "__dict__" not in all_events
    
    def test_is_valid_event(self):
        """Test event validation."""
        # Valid events
        assert EventTypes.is_valid_event(EventTypes.PROJECT_CREATED)
        assert EventTypes.is_valid_event(EventTypes.COMMAND_FAILED)
        
        # Invalid events
        assert not EventTypes.is_valid_event("invalid.event")
        assert not EventTypes.is_valid_event("")
        assert not EventTypes.is_valid_event("PROJECT_CREATED")  # Wrong case
    
    def test_get_domain(self):
        """Test extracting domain from event type."""
        assert EventTypes.get_domain("project.created") == "project"
        assert EventTypes.get_domain("command.approved") == "command"
        assert EventTypes.get_domain("state.autopilot.enabled") == "state"
        assert EventTypes.get_domain("ui.ready") == "ui"
        
        # Edge case - no dots
        assert EventTypes.get_domain("nodomain") == "nodomain"
    
    def test_get_events_by_domain(self):
        """Test filtering events by domain."""
        # Project events
        project_events = EventTypes.get_events_by_domain("project")
        assert len(project_events) >= 5
        assert all(e.startswith("project.") for e in project_events)
        assert EventTypes.PROJECT_CREATED in project_events
        assert EventTypes.PROJECT_DELETED in project_events
        
        # Command events
        command_events = EventTypes.get_events_by_domain("command")
        assert len(command_events) >= 7
        assert all(e.startswith("command.") for e in command_events)
        assert EventTypes.COMMAND_PROPOSED in command_events
        assert EventTypes.COMMAND_COMPLETED in command_events
        
        # Non-existent domain
        empty = EventTypes.get_events_by_domain("nonexistent")
        assert len(empty) == 0
    
    def test_event_categories(self):
        """Test that all major categories have events."""
        domains = ["project", "context", "command", "ai", "state", "ui", "system", "storage"]
        
        for domain in domains:
            events = EventTypes.get_events_by_domain(domain)
            assert len(events) > 0, f"Domain '{domain}' has no events"


class TestEventPriority:
    """Test the EventPriority class."""
    
    def test_priority_values(self):
        """Test priority level values."""
        assert EventPriority.CRITICAL < EventPriority.HIGH
        assert EventPriority.HIGH < EventPriority.NORMAL
        assert EventPriority.NORMAL < EventPriority.LOW
    
    def test_get_priority(self):
        """Test getting priority for event types."""
        # Critical events
        assert EventPriority.get_priority(EventTypes.SYSTEM_ERROR) == EventPriority.CRITICAL
        assert EventPriority.get_priority(EventTypes.SYSTEM_SHUTDOWN_REQUESTED) == EventPriority.CRITICAL
        assert EventPriority.get_priority(EventTypes.COMMAND_FAILED) == EventPriority.CRITICAL
        
        # High priority events
        assert EventPriority.get_priority(EventTypes.UI_COMMAND_APPROVE_REQUESTED) == EventPriority.HIGH
        assert EventPriority.get_priority(EventTypes.UI_COMMAND_REJECT_REQUESTED) == EventPriority.HIGH
        assert EventPriority.get_priority(EventTypes.COMMAND_EXECUTING) == EventPriority.HIGH
        
        # Low priority events
        assert EventPriority.get_priority(EventTypes.STORAGE_SAVE_STARTED) == EventPriority.LOW
        assert EventPriority.get_priority(EventTypes.STATE_PERSISTED) == EventPriority.LOW
        assert EventPriority.get_priority(EventTypes.CONTEXT_SAVED) == EventPriority.LOW
        
        # Normal priority (default)
        assert EventPriority.get_priority(EventTypes.PROJECT_CREATED) == EventPriority.NORMAL
        assert EventPriority.get_priority(EventTypes.AI_GENERATION_STARTED) == EventPriority.NORMAL
        assert EventPriority.get_priority("unknown.event") == EventPriority.NORMAL
    
    def test_priority_ordering(self):
        """Test that priorities can be used for sorting."""
        events = [
            (EventTypes.PROJECT_CREATED, EventPriority.get_priority(EventTypes.PROJECT_CREATED)),
            (EventTypes.SYSTEM_ERROR, EventPriority.get_priority(EventTypes.SYSTEM_ERROR)),
            (EventTypes.STORAGE_SAVE_STARTED, EventPriority.get_priority(EventTypes.STORAGE_SAVE_STARTED)),
            (EventTypes.UI_COMMAND_APPROVE_REQUESTED, EventPriority.get_priority(EventTypes.UI_COMMAND_APPROVE_REQUESTED)),
        ]
        
        # Sort by priority (lower number = higher priority)
        sorted_events = sorted(events, key=lambda x: x[1])
        
        # Check order
        assert sorted_events[0][0] == EventTypes.SYSTEM_ERROR  # Critical
        assert sorted_events[1][0] == EventTypes.UI_COMMAND_APPROVE_REQUESTED  # High
        assert sorted_events[2][0] == EventTypes.PROJECT_CREATED  # Normal
        assert sorted_events[3][0] == EventTypes.STORAGE_SAVE_STARTED  # Low