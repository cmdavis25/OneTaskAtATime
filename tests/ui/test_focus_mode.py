"""
Unit tests for FocusModeWidget.

Tests the core Focus Mode UI component including:
- Task display
- Signal emissions
- Button state management
- Filter functionality
- Empty state handling
"""

import pytest
import sqlite3
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from PyQt5.QtCore import Qt

from src.models.task import Task
from src.models.enums import TaskState
from src.database.schema import DatabaseSchema


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
def focus_mode_widget(qapp, db_connection):
    """Create FocusModeWidget instance."""
    from src.ui.focus_mode import FocusModeWidget
    widget = FocusModeWidget(db_connection, test_mode=True)
    yield widget
    widget.close()


@pytest.fixture
def sample_task():
    """Create a sample task."""
    return Task(
        id=1,
        title="Test Task",
        description="Test description",
        base_priority=2,
        due_date=date.today() + timedelta(days=7),
        state=TaskState.ACTIVE
    )


class TestTaskDisplay:
    """Test task display functionality."""

    def test_set_task_displays_title(self, focus_mode_widget, sample_task):
        """Test that setting a task displays its title."""
        focus_mode_widget.set_task(sample_task)

        assert sample_task.title in focus_mode_widget.task_title_label.text()

    def test_set_task_displays_metadata(self, focus_mode_widget, sample_task):
        """Test that setting a task displays metadata."""
        focus_mode_widget.set_task(sample_task)

        metadata = focus_mode_widget.task_metadata_label.text()
        assert "Priority" in metadata

    def test_set_task_displays_due_date(self, focus_mode_widget, sample_task):
        """Test that task with due date shows it in metadata."""
        focus_mode_widget.set_task(sample_task)

        metadata = focus_mode_widget.task_metadata_label.text()
        assert "Due" in metadata

    def test_set_task_displays_description(self, focus_mode_widget, sample_task):
        """Test that task description is displayed."""
        focus_mode_widget.set_task(sample_task)

        assert focus_mode_widget.task_description.toPlainText() == sample_task.description
        # Check that widget is not hidden (isHidden checks explicitly hidden flag)
        assert not focus_mode_widget.task_description.isHidden()

    def test_set_task_hides_empty_description(self, focus_mode_widget):
        """Test that empty description hides the description widget."""
        task = Task(
            id=1,
            title="No Description Task",
            base_priority=2,
            description=None
        )

        focus_mode_widget.set_task(task)

        assert not focus_mode_widget.task_description.isVisible()

    def test_set_task_none_shows_empty_state(self, focus_mode_widget):
        """Test that setting None shows empty state."""
        focus_mode_widget.set_task(None)

        assert "No tasks" in focus_mode_widget.task_title_label.text()

    def test_get_current_task_returns_set_task(self, focus_mode_widget, sample_task):
        """Test that get_current_task returns the set task."""
        focus_mode_widget.set_task(sample_task)

        current = focus_mode_widget.get_current_task()

        assert current == sample_task

    def test_get_current_task_none_when_empty(self, focus_mode_widget):
        """Test that get_current_task returns None when empty."""
        focus_mode_widget.set_task(None)

        current = focus_mode_widget.get_current_task()

        assert current is None


class TestButtonStates:
    """Test button enable/disable states."""

    def test_buttons_enabled_with_task(self, focus_mode_widget, sample_task):
        """Test that action buttons are enabled when task is displayed."""
        focus_mode_widget.set_task(sample_task)

        assert focus_mode_widget.complete_button.isEnabled()
        assert focus_mode_widget.defer_button.isEnabled()
        assert focus_mode_widget.delegate_button.isEnabled()
        assert focus_mode_widget.someday_button.isEnabled()
        assert focus_mode_widget.trash_button.isEnabled()

    def test_buttons_disabled_without_task(self, focus_mode_widget):
        """Test that action buttons are disabled in empty state."""
        focus_mode_widget.set_task(None)

        assert not focus_mode_widget.complete_button.isEnabled()
        assert not focus_mode_widget.defer_button.isEnabled()
        assert not focus_mode_widget.delegate_button.isEnabled()
        assert not focus_mode_widget.someday_button.isEnabled()
        assert not focus_mode_widget.trash_button.isEnabled()


class TestSignalEmission:
    """Test signal emission on button clicks."""

    def test_complete_button_emits_signal(self, focus_mode_widget, sample_task):
        """Test that Complete button emits task_completed signal."""
        focus_mode_widget.set_task(sample_task)

        # Connect to signal
        signal_received = []
        focus_mode_widget.task_completed.connect(lambda id: signal_received.append(id))

        # Click button
        focus_mode_widget.complete_button.click()

        assert len(signal_received) == 1
        assert signal_received[0] == sample_task.id

    def test_defer_button_emits_signal(self, focus_mode_widget, sample_task):
        """Test that Defer button emits task_deferred signal."""
        focus_mode_widget.set_task(sample_task)

        signal_received = []
        focus_mode_widget.task_deferred.connect(lambda id: signal_received.append(id))

        focus_mode_widget.defer_button.click()

        assert len(signal_received) == 1
        assert signal_received[0] == sample_task.id

    def test_delegate_button_emits_signal(self, focus_mode_widget, sample_task):
        """Test that Delegate button emits task_delegated signal."""
        focus_mode_widget.set_task(sample_task)

        signal_received = []
        focus_mode_widget.task_delegated.connect(lambda id: signal_received.append(id))

        focus_mode_widget.delegate_button.click()

        assert len(signal_received) == 1
        assert signal_received[0] == sample_task.id

    def test_someday_button_emits_signal(self, focus_mode_widget, sample_task):
        """Test that Someday button emits task_someday signal (in test mode)."""
        focus_mode_widget.set_task(sample_task)

        signal_received = []
        focus_mode_widget.task_someday.connect(lambda id: signal_received.append(id))

        focus_mode_widget.someday_button.click()

        assert len(signal_received) == 1
        assert signal_received[0] == sample_task.id

    def test_trash_button_emits_signal(self, focus_mode_widget, sample_task):
        """Test that Trash button emits task_trashed signal (in test mode)."""
        focus_mode_widget.set_task(sample_task)

        signal_received = []
        focus_mode_widget.task_trashed.connect(lambda id: signal_received.append(id))

        focus_mode_widget.trash_button.click()

        assert len(signal_received) == 1
        assert signal_received[0] == sample_task.id

    def test_refresh_button_emits_signal(self, focus_mode_widget):
        """Test that Refresh button emits task_refreshed signal."""
        signal_received = []
        focus_mode_widget.task_refreshed.connect(lambda: signal_received.append(True))

        focus_mode_widget.refresh_button.click()

        assert len(signal_received) == 1

    def test_no_signal_when_no_task(self, focus_mode_widget):
        """Test that buttons don't emit signals when no task."""
        focus_mode_widget.set_task(None)

        signal_received = []
        focus_mode_widget.task_completed.connect(lambda id: signal_received.append(id))

        # Button is disabled but try clicking anyway
        focus_mode_widget.complete_button.click()

        assert len(signal_received) == 0


class TestFilterFunctionality:
    """Test filter functionality."""

    def test_initial_context_filter_is_none(self, focus_mode_widget):
        """Test that initial context filter is None."""
        assert focus_mode_widget.get_active_context_filter() is None

    def test_initial_tag_filters_is_empty(self, focus_mode_widget):
        """Test that initial tag filters is empty set."""
        assert focus_mode_widget.get_active_tag_filters() == set()

    def test_clear_context_filter(self, focus_mode_widget):
        """Test clearing context filter."""
        # Set a filter first
        focus_mode_widget.active_context_filter = 1

        # Clear it
        focus_mode_widget._on_clear_context_filter()

        assert focus_mode_widget.active_context_filter is None

    def test_clear_context_filter_emits_signal(self, focus_mode_widget):
        """Test that clearing context filter emits filters_changed."""
        focus_mode_widget.active_context_filter = 1

        signal_received = []
        focus_mode_widget.filters_changed.connect(lambda: signal_received.append(True))

        focus_mode_widget._on_clear_context_filter()

        assert len(signal_received) == 1

    def test_clear_tag_filters(self, focus_mode_widget):
        """Test clearing tag filters."""
        # Set filters first
        focus_mode_widget.active_tag_filters = {1, 2, 3}

        # Clear them
        focus_mode_widget._on_clear_tag_filters()

        assert len(focus_mode_widget.active_tag_filters) == 0

    def test_clear_tag_filters_emits_signal(self, focus_mode_widget):
        """Test that clearing tag filters emits filters_changed."""
        focus_mode_widget.active_tag_filters = {1, 2, 3}

        signal_received = []
        focus_mode_widget.filters_changed.connect(lambda: signal_received.append(True))

        focus_mode_widget._on_clear_tag_filters()

        assert len(signal_received) == 1

    def test_context_filter_label_updates(self, focus_mode_widget):
        """Test that context filter label updates when filter cleared."""
        focus_mode_widget._on_clear_context_filter()

        assert "All Contexts" in focus_mode_widget.context_filter_label.text()

    def test_tag_filter_label_updates(self, focus_mode_widget):
        """Test that tag filter label updates when filters cleared."""
        focus_mode_widget._on_clear_tag_filters()

        assert "All Project Tags" in focus_mode_widget.tags_filter_label.text()


class TestEmptyState:
    """Test empty state display."""

    def test_empty_state_message(self, focus_mode_widget):
        """Test that empty state shows appropriate message."""
        focus_mode_widget.set_task(None)

        assert "No tasks" in focus_mode_widget.task_title_label.text()

    def test_empty_state_encourages_adding_task(self, focus_mode_widget):
        """Test that empty state encourages adding a task."""
        focus_mode_widget.set_task(None)

        description = focus_mode_widget.task_description.toPlainText()
        assert "task" in description.lower()


class TestPriorityDisplay:
    """Test priority-related display."""

    def test_high_priority_displayed(self, focus_mode_widget):
        """Test that high priority is displayed correctly."""
        task = Task(
            id=1,
            title="High Priority Task",
            base_priority=3,
            state=TaskState.ACTIVE
        )

        focus_mode_widget.set_task(task)

        metadata = focus_mode_widget.task_metadata_label.text()
        assert "High" in metadata

    def test_medium_priority_displayed(self, focus_mode_widget):
        """Test that medium priority is displayed correctly."""
        task = Task(
            id=1,
            title="Medium Priority Task",
            base_priority=2,
            state=TaskState.ACTIVE
        )

        focus_mode_widget.set_task(task)

        metadata = focus_mode_widget.task_metadata_label.text()
        assert "Medium" in metadata

    def test_low_priority_displayed(self, focus_mode_widget):
        """Test that low priority is displayed correctly."""
        task = Task(
            id=1,
            title="Low Priority Task",
            base_priority=1,
            state=TaskState.ACTIVE
        )

        focus_mode_widget.set_task(task)

        metadata = focus_mode_widget.task_metadata_label.text()
        assert "Low" in metadata


class TestEffectivePriorityDisplay:
    """Test effective priority display."""

    def test_adjusted_priority_shows_effective(self, focus_mode_widget):
        """Test that adjusted priority shows effective value."""
        task = Task(
            id=1,
            title="Adjusted Task",
            base_priority=2,
            priority_adjustment=0.5,
            state=TaskState.ACTIVE
        )

        focus_mode_widget.set_task(task)

        metadata = focus_mode_widget.task_metadata_label.text()
        assert "Effective" in metadata


class TestWidgetProperties:
    """Test widget properties and configuration."""

    def test_widget_has_whats_this(self, focus_mode_widget):
        """Test that widget has WhatsThis help text."""
        assert len(focus_mode_widget.whatsThis()) > 0

    def test_buttons_have_tooltips(self, focus_mode_widget):
        """Test that buttons have tooltips."""
        assert len(focus_mode_widget.complete_button.toolTip()) > 0
        assert len(focus_mode_widget.defer_button.toolTip()) > 0
        assert len(focus_mode_widget.delegate_button.toolTip()) > 0

    def test_button_text_includes_shortcuts(self, focus_mode_widget):
        """Test that button text includes keyboard shortcuts."""
        assert "Alt+" in focus_mode_widget.complete_button.text()
        assert "Alt+" in focus_mode_widget.defer_button.text()
        assert "Alt+" in focus_mode_widget.delegate_button.text()
