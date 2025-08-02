"""Global test configuration and fixtures for the imthedev test suite.

This module provides common fixtures and configuration that can be shared
across all test modules.
"""

import sys
from typing import Any
from unittest.mock import MagicMock

# Import the test helpers if we're running UI tests
if any("ui/tui" in arg for arg in sys.argv):
    try:
        from tests.ui.tui.test_helpers import (
            MockButton,
            MockContainer,
            MockLabel,
            MockListItem,
            MockListView,
            MockMessage,
            MockRichLog,
            MockWidget,
        )

        USE_MOCK_WIDGETS = True
    except ImportError:
        USE_MOCK_WIDGETS = False
else:
    USE_MOCK_WIDGETS = False


def create_textual_mocks() -> None:
    """Create properly configured textual mocks."""
    # Create base mocks for textual components
    textual_mock = MagicMock()

    if USE_MOCK_WIDGETS:
        # Use our custom mock classes for better testing
        app_mock = type("App", (MockWidget,), {})
        widget_mock = MockWidget
        container_mock = MockContainer
        button_mock = MockButton
        listview_mock = MockListView
        listitem_mock = MockListItem
        label_mock = MockLabel
        richlog_mock = MockRichLog
        message_mock = MockMessage
    else:
        # Create App base class mock
        app_mock = MagicMock()
        app_mock.__name__ = "App"
        app_mock.return_value = MagicMock()

        # Create Widget base class mock
        widget_mock = MagicMock()
        widget_mock.__name__ = "Widget"
        widget_mock.return_value = MagicMock()

        # Create Container base class mock
        container_mock = MagicMock()
        container_mock.__name__ = "Container"
        container_mock.return_value = MagicMock()

        # Create mocks for widgets
        button_mock = MagicMock()
        button_mock.__name__ = "Button"
        button_mock.return_value = MagicMock()

        listview_mock = MagicMock()
        listview_mock.__name__ = "ListView"
        listview_mock.return_value = MagicMock()

        listitem_mock = MagicMock()
        listitem_mock.__name__ = "ListItem"
        listitem_mock.return_value = MagicMock()

        label_mock = MagicMock()
        label_mock.__name__ = "Label"
        label_mock.return_value = MagicMock()

        richlog_mock = MagicMock()
        richlog_mock.__name__ = "RichLog"
        richlog_mock.return_value = MagicMock()

        # Create Message base class mock
        message_mock = MagicMock()
        message_mock.__name__ = "Message"

    # Create Reactive mock that supports both function call and type annotation
    class ReactiveMock:
        def __call__(self, *args: Any, **kwargs: Any) -> property:
            return property(
                lambda self: args[0] if args else None, lambda self, value: None
            )

        def __getitem__(self, key: Any) -> "ReactiveMock":
            # Support reactive[type] syntax
            return self

    reactive_mock = ReactiveMock()

    # Create ComposeResult type
    compose_result_mock = MagicMock()
    compose_result_mock.__name__ = "ComposeResult"

    # Set up module structure
    textual_app_module = MagicMock()
    textual_app_module.App = app_mock
    textual_app_module.ComposeResult = compose_result_mock

    textual_widget_module = MagicMock()
    textual_widget_module.Widget = widget_mock

    textual_widgets_module = MagicMock()
    textual_widgets_module.Button = button_mock
    textual_widgets_module.ListView = listview_mock
    textual_widgets_module.ListItem = listitem_mock
    textual_widgets_module.Label = label_mock
    textual_widgets_module.RichLog = richlog_mock

    textual_containers_module = MagicMock()
    textual_containers_module.Container = container_mock
    textual_containers_module.Horizontal = container_mock
    textual_containers_module.Vertical = container_mock

    textual_reactive_module = MagicMock()
    textual_reactive_module.reactive = reactive_mock

    textual_message_module = MagicMock()
    textual_message_module.Message = message_mock

    # Set up the modules
    sys.modules["textual"] = textual_mock
    sys.modules["textual.app"] = textual_app_module
    sys.modules["textual.widget"] = textual_widget_module
    sys.modules["textual.widgets"] = textual_widgets_module
    sys.modules["textual.containers"] = textual_containers_module
    sys.modules["textual.events"] = MagicMock()
    sys.modules["textual.screen"] = MagicMock()
    sys.modules["textual.reactive"] = textual_reactive_module
    sys.modules["textual.message"] = textual_message_module
    sys.modules["textual.geometry"] = MagicMock()
    sys.modules["textual.strip"] = MagicMock()


# Initialize textual mocks before any imports
create_textual_mocks()

# Mock anthropic and openai to avoid requiring API keys during testing
sys.modules["anthropic"] = MagicMock()
sys.modules["openai"] = MagicMock()
