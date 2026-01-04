"""
UI tests for ShortcutsDialog.

Tests keyboard shortcuts reference dialog.
"""

import pytest
from PyQt5.QtWidgets import QApplication

from src.ui.shortcuts_dialog import ShortcutsDialog


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for UI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def shortcuts_dialog(qapp):
    """Create ShortcutsDialog instance."""
    dialog = ShortcutsDialog()
    yield dialog
    dialog.close()


def test_dialog_creation(shortcuts_dialog):
    """Test that dialog is created successfully."""
    assert shortcuts_dialog is not None
    assert shortcuts_dialog.windowTitle() == "Keyboard Shortcuts"


def test_has_tab_widget(shortcuts_dialog):
    """Test that dialog has tab widget."""
    assert shortcuts_dialog.tab_widget is not None
    assert shortcuts_dialog.tab_widget.count() == 5  # 5 categories


def test_tab_names(shortcuts_dialog):
    """Test that all expected tabs are present."""
    tab_names = [
        shortcuts_dialog.tab_widget.tabText(i)
        for i in range(shortcuts_dialog.tab_widget.count())
    ]

    assert "General" in tab_names
    assert "Navigation" in tab_names
    assert "Focus Mode" in tab_names
    assert "Task List" in tab_names
    assert "Dialogs" in tab_names


def test_shortcuts_data_structure():
    """Test that SHORTCUTS dictionary is properly structured."""
    assert "General" in ShortcutsDialog.SHORTCUTS
    assert "Focus Mode" in ShortcutsDialog.SHORTCUTS

    # Check that shortcuts are tuples of (action, shortcut)
    general_shortcuts = ShortcutsDialog.SHORTCUTS["General"]
    assert len(general_shortcuts) > 0
    assert len(general_shortcuts[0]) == 2  # (action, shortcut)


def test_all_shortcuts_have_descriptions():
    """Test that all shortcuts have both action and key combo."""
    for category, shortcuts in ShortcutsDialog.SHORTCUTS.items():
        for action, shortcut in shortcuts:
            assert action  # Not empty
            assert shortcut  # Not empty
            assert isinstance(action, str)
            assert isinstance(shortcut, str)


def test_focus_mode_shortcuts_present():
    """Test that Focus Mode shortcuts are documented."""
    focus_shortcuts = ShortcutsDialog.SHORTCUTS["Focus Mode"]

    actions = [action for action, _ in focus_shortcuts]

    assert any("Complete" in action for action in actions)
    assert any("Defer" in action for action in actions)
    assert any("Delegate" in action for action in actions)


def test_dialog_minimum_size(shortcuts_dialog):
    """Test that dialog has minimum size set."""
    assert shortcuts_dialog.minimumWidth() == 650
    assert shortcuts_dialog.minimumHeight() == 500


def test_print_button_enabled(shortcuts_dialog):
    """Test that print button is enabled."""
    from PyQt5.QtWidgets import QPushButton

    # Find the print button
    buttons = shortcuts_dialog.findChildren(QPushButton)
    print_button = None
    for button in buttons:
        if button.text() == "Print":
            print_button = button
            break

    assert print_button is not None, "Print button should exist"
    assert print_button.isEnabled(), "Print button should be enabled"


def test_generate_shortcuts_html(shortcuts_dialog):
    """Test that HTML generation works correctly."""
    html = shortcuts_dialog._generate_shortcuts_html()

    assert html is not None
    assert "OneTaskAtATime - Keyboard Shortcuts" in html
    assert "<table>" in html
    assert "General" in html
    assert "Focus Mode" in html

    # Check that some shortcuts are included
    assert "Ctrl+N" in html  # New Task
    assert "Alt+C" in html  # Complete Task
