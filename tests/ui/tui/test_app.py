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
    
    def test_app_bindings(self) -> None:
        """Test that app has the expected key bindings."""
        app = ImTheDevApp()
        
        # Check that bindings are defined
        assert len(app.BINDINGS) >= 4
        
        # Check specific bindings exist
        binding_keys = [binding.key for binding in app.BINDINGS]
        assert "q" in binding_keys  # Quit
        assert "p" in binding_keys  # Toggle Autopilot
        assert "a" in binding_keys  # Approve
        assert "d" in binding_keys  # Deny
    
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
        
        # Verify they're callable
        assert callable(app.action_toggle_autopilot)
        assert callable(app.action_approve_command)
        assert callable(app.action_deny_command)
    
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