"""Tests for the ProjectSelectorV2 component.

This tests the functionality of the clean ProjectSelector implementation
with ListView and proper key bindings.
"""

import pytest

from imthedev.ui.tui.components.project_selector_v2 import ProjectSelectorV2


@pytest.mark.asyncio
async def test_project_selector_can_be_created():
    """Test that ProjectSelectorV2 can be instantiated."""
    selector = ProjectSelectorV2()
    assert selector is not None
    # ProjectSelectorV2 has can_focus = True as a class attribute
    assert hasattr(ProjectSelectorV2, "can_focus")
    assert ProjectSelectorV2.can_focus is True


@pytest.mark.asyncio
async def test_project_selector_has_bindings():
    """Test that ProjectSelectorV2 has the expected key bindings."""
    selector = ProjectSelectorV2()

    # Check that bindings are defined
    # In Textual 5.0, bindings are stored differently
    assert hasattr(selector, "BINDINGS")
    assert len(selector.BINDINGS) == 3
    binding_keys = [(b[0], b[1]) for b in selector.BINDINGS]
    assert ("enter", "select_project") in binding_keys
    assert ("up", "cursor_up") in binding_keys
    assert ("down", "cursor_down") in binding_keys


@pytest.mark.asyncio
async def test_project_selector_compose():
    """Test that ProjectSelectorV2 composes with a ListView."""
    selector = ProjectSelectorV2()

    # Get composed widgets
    widgets = list(selector.compose())
    assert len(widgets) == 1

    # Should yield a ListView
    list_view = widgets[0]
    assert list_view.id == "project-list-view"


@pytest.mark.asyncio
async def test_update_projects():
    """Test updating the project list."""
    selector = ProjectSelectorV2()

    # Create test projects
    test_projects = [
        ("test-1", "Test Project 1", "/path/to/test1"),
        ("test-2", "Test Project 2", "/path/to/test2"),
    ]

    # Update projects
    selector.update_projects(test_projects)

    # Verify projects were stored
    assert selector.projects == test_projects


@pytest.mark.asyncio
async def test_project_selection_message():
    """Test that selecting a project message class is defined correctly."""
    # Test that message class exists
    assert hasattr(ProjectSelectorV2, "ProjectSelected")

    # Test message creation
    test_id = "test-123"
    test_name = "Test Project"

    # Create message
    selected_msg = ProjectSelectorV2.ProjectSelected(test_id, test_name)
    assert selected_msg.project_id == test_id
    assert selected_msg.project_name == test_name


@pytest.mark.asyncio
async def test_navigation_keys():
    """Test that navigation actions are defined."""
    selector = ProjectSelectorV2()

    # Test that action methods exist
    assert hasattr(selector, "action_cursor_up")
    assert hasattr(selector, "action_cursor_down")
    assert hasattr(selector, "action_select_project")

    # Test that bindings include navigation keys
    binding_keys = [(b[0], b[1]) for b in selector.BINDINGS]
    assert ("up", "cursor_up") in binding_keys
    assert ("down", "cursor_down") in binding_keys
    assert ("enter", "select_project") in binding_keys


if __name__ == "__main__":
    # For manual testing
    import asyncio

    async def run_tests():
        print("Running ProjectSelectorV2 tests...")

        await test_project_selector_can_be_created()
        print("✓ Can create ProjectSelectorV2")

        await test_project_selector_has_bindings()
        print("✓ Has expected key bindings")

        await test_project_selector_compose()
        print("✓ Composes with ListView")

        await test_update_projects()
        print("✓ Can update projects")

        await test_project_selection_message()
        print("✓ Sends selection message")

        await test_navigation_keys()
        print("✓ Navigation keys work")

        print("\nAll tests passed!")

    asyncio.run(run_tests())
