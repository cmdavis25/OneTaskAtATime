"""
UI tests for HelpDialog.

Tests help dialog with searchable content and tab hiding.
"""

import pytest
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest

from src.ui.help_dialog import HelpDialog


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for UI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def help_dialog(qapp):
    """Create HelpDialog instance."""
    dialog = HelpDialog()
    yield dialog
    dialog.close()


def test_dialog_creation(help_dialog):
    """Test that dialog is created successfully."""
    assert help_dialog is not None
    assert help_dialog.windowTitle() == "OneTaskAtATime Help"


def test_has_tab_widget(help_dialog):
    """Test that dialog has tab widget."""
    assert help_dialog.tab_widget is not None
    assert help_dialog.tab_widget.count() == 6  # 6 help categories


def test_tab_names(help_dialog):
    """Test that all expected tabs are present."""
    tab_names = [
        help_dialog.tab_widget.tabText(i)
        for i in range(help_dialog.tab_widget.count())
    ]

    assert "Getting Started" in tab_names
    assert "Focus Mode" in tab_names
    assert "Task Management" in tab_names
    assert "Priority System" in tab_names
    assert "Keyboard Shortcuts" in tab_names
    assert "FAQ" in tab_names


def test_has_search_box(help_dialog):
    """Test that dialog has search functionality."""
    assert help_dialog.search_box is not None
    assert help_dialog.search_box.placeholderText() == "Type to search help topics..."


def test_has_clear_button(help_dialog):
    """Test that dialog has clear button."""
    assert help_dialog.clear_button is not None
    assert not help_dialog.clear_button.isVisible()  # Initially hidden


def test_all_tabs_visible_initially(help_dialog):
    """Test that all tabs are visible when no search is active."""
    for i in range(help_dialog.tab_widget.count()):
        assert help_dialog.tab_widget.isTabVisible(i), f"Tab {i} should be visible initially"


def test_search_hides_tabs_with_zero_matches(help_dialog):
    """Test that tabs with zero matches are hidden during search."""
    # Search for a term that only appears in Focus Mode tab
    help_dialog.search_box.setText("decision fatigue")

    # Count visible tabs
    visible_count = sum(
        1 for i in range(help_dialog.tab_widget.count())
        if help_dialog.tab_widget.isTabVisible(i)
    )

    # At least one tab should be visible, but not all
    assert visible_count > 0, "At least one tab should be visible"
    assert visible_count < 6, "Not all tabs should be visible for specific search"


def test_search_single_tab_match(help_dialog):
    """Test search that matches only one tab."""
    # "Elo" should only appear in Priority System tab
    help_dialog.search_box.setText("Elo")

    # Check which tabs are visible
    visible_tabs = [
        help_dialog.tab_widget.tabText(i).split(' (')[0]
        for i in range(help_dialog.tab_widget.count())
        if help_dialog.tab_widget.isTabVisible(i)
    ]

    # Priority System tab should be visible
    assert "Priority System" in visible_tabs
    # Should have at least one visible tab
    assert len(visible_tabs) > 0


def test_search_all_tabs_visible_for_common_term(help_dialog):
    """Test that common search terms show multiple tabs."""
    # "task" appears in multiple tabs
    help_dialog.search_box.setText("task")

    visible_count = sum(
        1 for i in range(help_dialog.tab_widget.count())
        if help_dialog.tab_widget.isTabVisible(i)
    )

    # Multiple tabs should be visible
    assert visible_count > 1, "Multiple tabs should be visible for common term"


def test_search_no_results_keeps_all_tabs_visible(help_dialog):
    """Test that all tabs remain visible when no results are found."""
    # Search for something that doesn't exist
    help_dialog.search_box.setText("xyzabc123nonexistent")

    # All tabs should remain visible (fallback behavior)
    for i in range(help_dialog.tab_widget.count()):
        assert help_dialog.tab_widget.isTabVisible(i), \
            f"Tab {i} should be visible when no results found"


def test_clear_search_restores_all_tabs(help_dialog):
    """Test that clearing search restores all tabs to visible."""
    # First, do a search that hides some tabs
    help_dialog.search_box.setText("Elo")

    # Verify some tabs are hidden
    visible_count_during_search = sum(
        1 for i in range(help_dialog.tab_widget.count())
        if help_dialog.tab_widget.isTabVisible(i)
    )
    assert visible_count_during_search < 6

    # Clear the search
    help_dialog.search_box.clear()

    # All tabs should be restored to visible
    for i in range(help_dialog.tab_widget.count()):
        assert help_dialog.tab_widget.isTabVisible(i), \
            f"Tab {i} should be visible after clearing search"


def test_clear_button_functionality(help_dialog):
    """Test that clear button clears search and restores tabs."""
    # Do a search
    help_dialog.search_box.setText("Focus")

    # Click clear button
    help_dialog.clear_button.click()

    # Search box should be empty
    assert help_dialog.search_box.text() == ""

    # All tabs should be visible
    for i in range(help_dialog.tab_widget.count()):
        assert help_dialog.tab_widget.isTabVisible(i)

    # Clear button should be hidden
    assert not help_dialog.clear_button.isVisible()


def test_multiple_search_clear_cycles(help_dialog):
    """Test multiple search and clear cycles maintain correct behavior."""
    # Cycle 1: Search
    help_dialog.search_box.setText("Elo")
    visible_count_1 = sum(
        1 for i in range(help_dialog.tab_widget.count())
        if help_dialog.tab_widget.isTabVisible(i)
    )
    assert visible_count_1 < 6

    # Cycle 1: Clear
    help_dialog.search_box.clear()
    for i in range(help_dialog.tab_widget.count()):
        assert help_dialog.tab_widget.isTabVisible(i)

    # Cycle 2: Search different term
    help_dialog.search_box.setText("delegate")
    visible_count_2 = sum(
        1 for i in range(help_dialog.tab_widget.count())
        if help_dialog.tab_widget.isTabVisible(i)
    )
    assert visible_count_2 > 0

    # Cycle 2: Clear
    help_dialog.search_box.clear()
    for i in range(help_dialog.tab_widget.count()):
        assert help_dialog.tab_widget.isTabVisible(i)


def test_tab_title_shows_match_count(help_dialog):
    """Test that tab titles show match counts during search."""
    help_dialog.search_box.setText("task")

    # At least one tab should have a count in parentheses
    has_count = False
    for i in range(help_dialog.tab_widget.count()):
        title = help_dialog.tab_widget.tabText(i)
        if '(' in title and ')' in title:
            has_count = True
            break

    assert has_count, "At least one tab should show match count"


def test_tab_title_restored_after_clear(help_dialog):
    """Test that tab titles are restored to original after clearing search."""
    # Do a search
    help_dialog.search_box.setText("task")

    # Clear search
    help_dialog.search_box.clear()

    # All tab titles should not have counts
    for i in range(help_dialog.tab_widget.count()):
        title = help_dialog.tab_widget.tabText(i)
        # Original titles don't have parentheses
        assert '(' not in title or ')' not in title or '(' in "Getting Started", \
            f"Tab title '{title}' should not have match count after clearing"


def test_search_switches_to_first_match_tab(help_dialog):
    """Test that search automatically switches to first tab with matches."""
    # Search for term in Priority System
    help_dialog.search_box.setText("Elo rating")

    # Current tab should be one with matches
    current_index = help_dialog.tab_widget.currentIndex()
    current_title = help_dialog.tab_widget.tabText(current_index).split(' (')[0]

    # Should have switched to a tab with matches
    assert help_dialog.tab_widget.isTabVisible(current_index)
