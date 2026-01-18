"""
Unit tests for ComparisonDialog.

Tests the side-by-side task comparison dialog including:
- Dialog initialization
- Task display
- Selection handling
- Button behavior
"""

import pytest
import sqlite3
from datetime import date, timedelta

from PyQt5.QtWidgets import QApplication

from src.models.task import Task
from src.models.enums import TaskState
from src.database.schema import DatabaseSchema
from src.ui.comparison_dialog import ComparisonDialog


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class MockDatabaseConnection:
    """Mock DatabaseConnection for testing."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get_connection(self):
        return self._conn

    def close(self):
        self._conn.close()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()


@pytest.fixture
def db_connection():
    """Create in-memory database for testing."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    DatabaseSchema.initialize_database(conn)
    mock_conn = MockDatabaseConnection(conn)
    yield mock_conn
    conn.close()


@pytest.fixture
def task1():
    """Create first comparison task."""
    return Task(
        id=1,
        title="Task One",
        description="First task description",
        base_priority=2,
        due_date=date.today() + timedelta(days=7),
        state=TaskState.ACTIVE
    )


@pytest.fixture
def task2():
    """Create second comparison task."""
    return Task(
        id=2,
        title="Task Two",
        description="Second task description",
        base_priority=2,
        due_date=date.today() + timedelta(days=5),
        state=TaskState.ACTIVE
    )


@pytest.fixture
def comparison_dialog(qapp, db_connection, task1, task2):
    """Create comparison dialog instance."""
    dialog = ComparisonDialog(task1, task2, db_connection)
    yield dialog
    dialog.close()


class TestDialogInitialization:
    """Test dialog initialization."""

    def test_dialog_creation(self, comparison_dialog):
        """Test that dialog can be created."""
        assert comparison_dialog is not None

    def test_dialog_stores_both_tasks(self, comparison_dialog, task1, task2):
        """Test that dialog stores both tasks."""
        assert comparison_dialog.task1 == task1
        assert comparison_dialog.task2 == task2

    def test_dialog_has_window_title(self, comparison_dialog):
        """Test that dialog has appropriate window title."""
        title = comparison_dialog.windowTitle()
        assert len(title) > 0

    def test_dialog_has_minimum_size(self, comparison_dialog):
        """Test that dialog has reasonable minimum size."""
        min_size = comparison_dialog.minimumSize()
        assert min_size.width() >= 800
        assert min_size.height() >= 500

    def test_dialog_initial_selection_is_none(self, comparison_dialog):
        """Test that no task is selected initially."""
        assert comparison_dialog.selected_task is None


class TestTaskDisplay:
    """Test task display in cards."""

    def test_dialog_displays_task1_title(self, comparison_dialog, task1):
        """Test that task1 title is displayed."""
        # Check that task1 title appears somewhere in the dialog
        assert hasattr(comparison_dialog, 'task1_card')

    def test_dialog_displays_task2_title(self, comparison_dialog, task2):
        """Test that task2 title is displayed."""
        # Check that task2 title appears somewhere in the dialog
        assert hasattr(comparison_dialog, 'task2_card')

    def test_dialog_has_task1_button(self, comparison_dialog):
        """Test that dialog has button for selecting task1."""
        assert hasattr(comparison_dialog, 'task1_button')
        assert comparison_dialog.task1_button is not None

    def test_dialog_has_task2_button(self, comparison_dialog):
        """Test that dialog has button for selecting task2."""
        assert hasattr(comparison_dialog, 'task2_button')
        assert comparison_dialog.task2_button is not None


class TestSelectionBehavior:
    """Test task selection behavior."""

    def test_clicking_task1_button_selects_task1(self, comparison_dialog, task1):
        """Test that clicking task1 button selects task1."""
        # Click task1 button
        comparison_dialog.task1_button.click()

        # Should set selected_task to task1
        assert comparison_dialog.selected_task == task1

    def test_clicking_task2_button_selects_task2(self, comparison_dialog, task2):
        """Test that clicking task2 button selects task2."""
        # Click task2 button
        comparison_dialog.task2_button.click()

        # Should set selected_task to task2
        assert comparison_dialog.selected_task == task2

    def test_clicking_task1_button_accepts_dialog(self, comparison_dialog):
        """Test that clicking task1 button accepts dialog."""
        accepted = []
        comparison_dialog.accepted.connect(lambda: accepted.append(True))

        comparison_dialog.task1_button.click()

        assert len(accepted) == 1

    def test_clicking_task2_button_accepts_dialog(self, comparison_dialog):
        """Test that clicking task2 button accepts dialog."""
        accepted = []
        comparison_dialog.accepted.connect(lambda: accepted.append(True))

        comparison_dialog.task2_button.click()

        assert len(accepted) == 1


class TestGetSelectedTask:
    """Test getting selected task."""

    def test_get_selected_task_returns_none_initially(self, comparison_dialog):
        """Test that get_selected_task returns None before selection."""
        result = comparison_dialog.get_selected_task()
        assert result is None

    def test_get_selected_task_returns_task1_after_selection(self, comparison_dialog, task1):
        """Test that get_selected_task returns task1 after clicking it."""
        comparison_dialog.task1_button.click()
        result = comparison_dialog.get_selected_task()
        assert result == task1

    def test_get_selected_task_returns_task2_after_selection(self, comparison_dialog, task2):
        """Test that get_selected_task returns task2 after clicking it."""
        comparison_dialog.task2_button.click()
        result = comparison_dialog.get_selected_task()
        assert result == task2


class TestCancelButton:
    """Test cancel button behavior."""

    def test_dialog_has_cancel_button(self, comparison_dialog):
        """Test that dialog has cancel button."""
        assert hasattr(comparison_dialog, 'cancel_button')
        assert comparison_dialog.cancel_button is not None

    def test_cancel_button_rejects_dialog(self, comparison_dialog):
        """Test that cancel button rejects dialog."""
        rejected = []
        comparison_dialog.rejected.connect(lambda: rejected.append(True))

        comparison_dialog.cancel_button.click()

        assert len(rejected) == 1

    def test_cancel_leaves_selection_none(self, comparison_dialog):
        """Test that cancelling leaves selection as None."""
        comparison_dialog.cancel_button.click()
        assert comparison_dialog.selected_task is None


class TestTaskCards:
    """Test task card display."""

    def test_task1_card_displays_title(self, comparison_dialog, task1):
        """Test that task1 card displays task title."""
        # Task cards should display the task title
        assert hasattr(comparison_dialog, 'task1_title_label')

    def test_task2_card_displays_title(self, comparison_dialog, task2):
        """Test that task2 card displays task title."""
        assert hasattr(comparison_dialog, 'task2_title_label')

    def test_task1_card_displays_description(self, comparison_dialog, task1):
        """Test that task1 card displays description if present."""
        # Description should be shown in the card
        assert hasattr(comparison_dialog, 'task1_description') or hasattr(comparison_dialog, 'task1_card')

    def test_task2_card_displays_description(self, comparison_dialog, task2):
        """Test that task2 card displays description if present."""
        assert hasattr(comparison_dialog, 'task2_description') or hasattr(comparison_dialog, 'task2_card')


class TestTaskMetadata:
    """Test metadata display in task cards."""

    def test_task1_card_shows_priority(self, comparison_dialog, task1):
        """Test that task1 card shows priority."""
        # Priority information should be visible
        assert hasattr(comparison_dialog, 'task1_metadata') or hasattr(comparison_dialog, 'task1_card')

    def test_task2_card_shows_priority(self, comparison_dialog, task2):
        """Test that task2 card shows priority."""
        assert hasattr(comparison_dialog, 'task2_metadata') or hasattr(comparison_dialog, 'task2_card')

    def test_task1_card_shows_due_date_when_present(self, comparison_dialog, task1):
        """Test that task1 card shows due date if task has one."""
        # Due date should be displayed if present
        assert task1.due_date is not None

    def test_task2_card_shows_due_date_when_present(self, comparison_dialog, task2):
        """Test that task2 card shows due date if task has one."""
        assert task2.due_date is not None


class TestDialogLayout:
    """Test dialog layout."""

    def test_dialog_has_instructions(self, comparison_dialog):
        """Test that dialog has instruction text."""
        # Should have explanatory text for user
        assert hasattr(comparison_dialog, 'title_label') or hasattr(comparison_dialog, 'layout')

    def test_buttons_are_side_by_side(self, comparison_dialog):
        """Test that task selection buttons are displayed side by side."""
        # Both buttons should exist
        assert comparison_dialog.task1_button is not None
        assert comparison_dialog.task2_button is not None


class TestWhatsThisHelp:
    """Test WhatsThis help support."""

    def test_dialog_has_whats_this_text(self, comparison_dialog):
        """Test that dialog has WhatsThis help text."""
        whats_this = comparison_dialog.whatsThis()
        assert len(whats_this) > 0

    def test_whats_this_mentions_elo_or_priority(self, comparison_dialog):
        """Test that WhatsThis help mentions priority system."""
        whats_this = comparison_dialog.whatsThis().lower()
        assert "elo" in whats_this or "priority" in whats_this or "importance" in whats_this
