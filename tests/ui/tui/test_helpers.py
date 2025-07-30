"""Test helpers for UI component testing.

This module provides utilities and base classes for testing UI components
with proper mocking of Textual framework components.
"""

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock


class MockWidget:
    """Mock implementation of a Textual Widget for testing."""
    
    def __init__(self, *args, **kwargs):
        """Initialize the mock widget with default attributes."""
        self._attributes: Dict[str, Any] = {}
        self._children: List[Any] = []
        self.id = kwargs.get('id', None)
        self.classes = kwargs.get('classes', [])
        
        # Initialize any attributes passed as kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def __setattr__(self, name: str, value: Any) -> None:
        """Set an attribute on the mock widget."""
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self._attributes[name] = value
            super().__setattr__(name, value)
    
    def __getattr__(self, name: str) -> Any:
        """Get an attribute from the mock widget."""
        if name in self._attributes:
            return self._attributes[name]
        # Return a MagicMock for undefined attributes
        mock = MagicMock()
        self._attributes[name] = mock
        return mock
    
    def mount(self, *widgets) -> None:
        """Mock mount method."""
        self._children.extend(widgets)
    
    def compose(self):
        """Mock compose method that returns an empty generator."""
        return iter([])
    
    async def on_mount(self) -> None:
        """Mock on_mount lifecycle method."""
        pass
    
    def refresh(self) -> None:
        """Mock refresh method."""
        pass
    
    def focus(self) -> None:
        """Mock focus method."""
        pass
    
    def blur(self) -> None:
        """Mock blur method."""
        pass


class MockContainer(MockWidget):
    """Mock implementation of a Textual Container."""
    pass


class MockListView(MockWidget):
    """Mock implementation of a Textual ListView."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.index = 0
        self.children = []
        self.highlighted_child = None
    
    def clear(self) -> None:
        """Clear all children."""
        self.children = []
        self.index = 0
        self.highlighted_child = None
    
    def append(self, child) -> None:
        """Append a child to the list."""
        self.children.append(child)
        if not self.highlighted_child and self.children:
            self.highlighted_child = self.children[0]


class MockListItem(MockWidget):
    """Mock implementation of a Textual ListItem."""
    
    def __init__(self, *children, **kwargs):
        super().__init__(**kwargs)
        self._children = list(children)


class MockLabel(MockWidget):
    """Mock implementation of a Textual Label."""
    
    def __init__(self, text: str = "", **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.renderable = text


class MockButton(MockWidget):
    """Mock implementation of a Textual Button."""
    
    def __init__(self, label: str = "", **kwargs):
        super().__init__(**kwargs)
        self.label = label
        self.disabled = kwargs.get('disabled', False)


class MockRichLog(MockWidget):
    """Mock implementation of a Textual RichLog."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lines = []
    
    def write(self, text: str) -> None:
        """Write text to the log."""
        self.lines.append(text)
    
    def clear(self) -> None:
        """Clear the log."""
        self.lines = []


class MockMessage:
    """Mock implementation of a Textual Message."""
    
    def __init__(self, sender=None):
        self.sender = sender
        self.prevented = False
    
    def prevent_default(self) -> None:
        """Prevent default handling of the message."""
        self.prevented = True
    
    def stop(self) -> None:
        """Stop propagation of the message."""
        pass


def create_mock_component(component_class):
    """Create a mock component that properly inherits from MockWidget.
    
    This function creates a new class that inherits from MockWidget
    but has the name and basic interface of the target component.
    """
    class MockedComponent(MockWidget):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Initialize any specific attributes the component should have
            if hasattr(component_class, '__init__'):
                # Try to extract default values from the real class if available
                pass
    
    MockedComponent.__name__ = component_class.__name__
    MockedComponent.__qualname__ = component_class.__qualname__
    return MockedComponent