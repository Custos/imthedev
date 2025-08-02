"""Test isolation utilities for TUI test suite.

This module provides shared utilities for properly isolating TUI tests
to prevent test pollution and ensure tests work both individually and together.
"""

import sys
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional
from unittest.mock import MagicMock

import pytest


class MockMessage:
    """Base mock message class for component communication."""
    pass


class ComponentMocker:
    """Centralized component mocking utility to ensure test isolation."""
    
    def __init__(self):
        """Initialize the component mocker with mock definitions."""
        self._original_modules: Dict[str, Any] = {}
        self._mock_components = self._create_mock_components()
    
    def _create_mock_components(self) -> Dict[str, Any]:
        """Create all mock components with their message classes."""
        mocks = {}
        
        # ProjectSelector mock
        project_selector = MagicMock()
        project_selector.__name__ = "ProjectSelector"
        
        # Create ProjectSelected message class
        def project_selected_init(self, project=None, project_id=None, 
                                   project_name=None, project_path=None):
            setattr(self, "project", project)
            setattr(self, "project_id", project_id)
            setattr(self, "project_name", project_name)
            setattr(self, "project_path", project_path)
        
        project_selected = type(
            "ProjectSelected",
            (MockMessage,),
            {"__init__": project_selected_init},
        )
        project_selector.ProjectSelected = project_selected
        mocks["project_selector"] = project_selector
        
        # CommandDashboard mock
        command_dashboard = MagicMock()
        command_dashboard.__name__ = "CommandDashboard"
        
        # Create CommandDashboard message classes
        def command_submitted_init(self, command=None, command_id=None):
            setattr(self, "command", command)
            setattr(self, "command_id", command_id)
        
        command_submitted = type(
            "CommandSubmitted",
            (MockMessage,),
            {"__init__": command_submitted_init},
        )
        command_cleared = type("CommandCleared", (MockMessage,), {})
        command_changed = type("CommandChanged", (MockMessage,), {})
        navigation_requested = type("NavigationRequested", (MockMessage,), {})
        
        command_dashboard.CommandSubmitted = command_submitted
        command_dashboard.CommandCleared = command_cleared
        command_dashboard.CommandChanged = command_changed
        command_dashboard.NavigationRequested = navigation_requested
        mocks["command_dashboard"] = command_dashboard
        
        # ApprovalControls mock
        approval_controls = MagicMock()
        approval_controls.__name__ = "ApprovalControls"
        
        # Create ApprovalControls message classes
        def command_approved_init(self, command_id=None):
            setattr(self, "command_id", command_id)
        
        command_approved = type(
            "CommandApproved",
            (MockMessage,),
            {"__init__": command_approved_init},
        )
        def command_denied_init(self, command_id=None):
            setattr(self, "command_id", command_id)
        
        command_denied = type(
            "CommandDenied",
            (MockMessage,),
            {"__init__": command_denied_init},
        )
        def autopilot_toggled_init(self, enabled=None):
            setattr(self, "enabled", enabled)
        
        autopilot_toggled = type(
            "AutopilotToggled",
            (MockMessage,),
            {"__init__": autopilot_toggled_init},
        )
        
        approval_controls.CommandApproved = command_approved
        approval_controls.CommandDenied = command_denied
        approval_controls.AutopilotToggled = autopilot_toggled
        mocks["approval_controls"] = approval_controls
        
        # StatusBar mock
        status_bar = MagicMock()
        status_bar.__name__ = "StatusBar"
        
        # Create StatusBar message classes
        autopilot_toggled_sb = type("AutopilotToggled", (MockMessage,), {})
        model_changed = type("ModelChanged", (MockMessage,), {})
        status_message_changed = type("StatusMessageChanged", (MockMessage,), {})
        
        status_bar.AutopilotToggled = autopilot_toggled_sb
        status_bar.ModelChanged = model_changed
        status_bar.StatusMessageChanged = status_message_changed
        mocks["status_bar"] = status_bar
        
        return mocks
    
    def setup_mocks(self) -> None:
        """Install mocked component modules in sys.modules."""
        # Save original modules if they exist
        module_names = [
            "imthedev.ui.tui.components.project_selector",
            "imthedev.ui.tui.components.command_dashboard",
            "imthedev.ui.tui.components.approval_controls",
            "imthedev.ui.tui.components.status_bar",
        ]
        
        for module_name in module_names:
            if module_name in sys.modules:
                self._original_modules[module_name] = sys.modules[module_name]
        
        # Install mocks
        sys.modules["imthedev.ui.tui.components.project_selector"] = MagicMock(
            ProjectSelector=self._mock_components["project_selector"]
        )
        sys.modules["imthedev.ui.tui.components.command_dashboard"] = MagicMock(
            CommandDashboard=self._mock_components["command_dashboard"]
        )
        sys.modules["imthedev.ui.tui.components.approval_controls"] = MagicMock(
            ApprovalControls=self._mock_components["approval_controls"]
        )
        sys.modules["imthedev.ui.tui.components.status_bar"] = MagicMock(
            StatusBar=self._mock_components["status_bar"]
        )
    
    def cleanup_mocks(self) -> None:
        """Remove mocked component modules and restore originals."""
        module_names = [
            "imthedev.ui.tui.components.project_selector",
            "imthedev.ui.tui.components.command_dashboard",
            "imthedev.ui.tui.components.approval_controls",
            "imthedev.ui.tui.components.status_bar",
        ]
        
        # Remove mocked modules
        for module_name in module_names:
            if module_name in sys.modules:
                del sys.modules[module_name]
        
        # Restore original modules
        for module_name, module in self._original_modules.items():
            sys.modules[module_name] = module
        
        self._original_modules.clear()
    
    def get_mock(self, component_name: str) -> Optional[Any]:
        """Get a specific mock component."""
        return self._mock_components.get(component_name)


# Global instance for reuse
_component_mocker = ComponentMocker()


@contextmanager
def isolated_tui_test() -> Generator[ComponentMocker, None, None]:
    """Context manager for isolated TUI testing.
    
    This ensures proper setup and cleanup of mocked modules.
    
    Usage:
        with isolated_tui_test() as mocker:
            # Import and test TUI components
            from imthedev.ui.tui.app import ImTheDevApp
            app = ImTheDevApp()
            # ... test code ...
    """
    _component_mocker.setup_mocks()
    try:
        yield _component_mocker
    finally:
        _component_mocker.cleanup_mocks()


@pytest.fixture
def mock_tui_components():
    """Pytest fixture for isolated TUI component mocking.
    
    This fixture ensures proper setup and cleanup of mocked modules
    for each test function.
    """
    mocker = ComponentMocker()
    mocker.setup_mocks()
    yield mocker
    mocker.cleanup_mocks()


@pytest.fixture
def clean_imports():
    """Fixture to ensure clean import state for tests.
    
    This removes any previously imported TUI modules to ensure
    fresh imports with proper mocking.
    """
    # List of modules to clean
    modules_to_clean = [
        "imthedev.ui.tui.app",
        "imthedev.ui.tui.components",
        "imthedev.ui.tui.components.project_selector",
        "imthedev.ui.tui.components.command_dashboard",
        "imthedev.ui.tui.components.approval_controls",
        "imthedev.ui.tui.components.status_bar",
    ]
    
    # Store original modules
    original_modules = {}
    for module_name in modules_to_clean:
        if module_name in sys.modules:
            original_modules[module_name] = sys.modules[module_name]
            del sys.modules[module_name]
    
    yield
    
    # Note: We don't restore the modules here as they should be
    # re-imported fresh in each test with proper mocking