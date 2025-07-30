"""Tests for the main ImTheDevApp application.

This module contains tests for the main TUI application class.
"""

import pytest

from imthedev.ui.tui import ImTheDevApp


class TestImTheDevApp:
    """Test suite for ImTheDevApp."""
    
    def test_app_initialization(self) -> None:
        """Test that ImTheDevApp can be initialized."""
        app = ImTheDevApp()
        assert isinstance(app, ImTheDevApp)
        assert app.TITLE == "imthedev - SuperClaude Workflow Manager"
        assert app.autopilot_enabled is False
        assert app.current_focus_widget is None
    
    def test_app_bindings(self) -> None:
        """Test that app has the expected key bindings."""
        app = ImTheDevApp()
        
        # Check that bindings are defined
        assert len(app.BINDINGS) >= 8
        
        # Check specific bindings exist
        binding_keys = [binding.key for binding in app.BINDINGS]
        assert "q" in binding_keys  # Quit
        assert "p" in binding_keys  # Toggle Autopilot
        assert "a" in binding_keys  # Approve
        assert "d" in binding_keys  # Deny
        assert "tab" in binding_keys  # Focus next
        assert "shift+tab" in binding_keys  # Focus previous
        assert "ctrl+p" in binding_keys  # Focus projects
        assert "ctrl+c" in binding_keys  # Focus commands
    
    def test_app_is_textual_app(self) -> None:
        """Test that ImTheDevApp inherits from Textual App."""
        from textual.app import App
        
        app = ImTheDevApp()
        assert isinstance(app, App)
    
    def test_app_compose_method_exists(self) -> None:
        """Test that the compose method is implemented."""
        app = ImTheDevApp()
        assert hasattr(app, 'compose')
        assert callable(app.compose)
    
    def test_app_actions_exist(self) -> None:
        """Test that required action methods exist."""
        app = ImTheDevApp()
        
        # Check action methods
        assert hasattr(app, 'action_toggle_autopilot')
        assert hasattr(app, 'action_approve_command')
        assert hasattr(app, 'action_deny_command')
        assert hasattr(app, 'action_focus_projects')
        assert hasattr(app, 'action_focus_commands')
        
        # Verify they're callable
        assert callable(app.action_toggle_autopilot)
        assert callable(app.action_approve_command)
        assert callable(app.action_deny_command)
        assert callable(app.action_focus_projects)
        assert callable(app.action_focus_commands)
    
    @pytest.mark.asyncio
    async def test_app_compose_returns_widgets(self) -> None:
        """Test that compose method yields expected widgets."""
        app = ImTheDevApp()
        
        # Get the compose result
        compose_result = app.compose()
        
        # Collect all yielded widgets
        widgets = list(compose_result)
        
        # Should have at least Header, Container, StatusBar, Footer
        assert len(widgets) >= 4
        
        # Check widget types (when Textual is available)
        widget_types = [type(w).__name__ for w in widgets]
        assert "Header" in widget_types
        assert "Container" in widget_types
        assert "StatusBar" in widget_types
        assert "Footer" in widget_types
    
    def test_toggle_autopilot_action(self) -> None:
        """Test that autopilot toggle action works correctly."""
        app = ImTheDevApp()
        
        # Initial state should be False
        assert app.autopilot_enabled is False
        
        # Toggle on
        app.action_toggle_autopilot()
        assert app.autopilot_enabled is True
        
        # Toggle off
        app.action_toggle_autopilot()
        assert app.autopilot_enabled is False
    
    def test_focus_navigation_actions(self) -> None:
        """Test focus navigation action methods."""
        app = ImTheDevApp()
        
        # Test that focus actions update current_focus_widget
        # Note: Without a running Textual app, we can't test actual focus,
        # but we can test that the tracking variable is updated
        
        # Initially should be None
        assert app.current_focus_widget is None
        
        # After on_mount is called, should focus projects
        app.on_mount()
        assert app.current_focus_widget == "project-selector"
    
    def test_app_has_on_mount_method(self) -> None:
        """Test that the app has an on_mount method for initialization."""
        app = ImTheDevApp()
        assert hasattr(app, 'on_mount')
        assert callable(app.on_mount)