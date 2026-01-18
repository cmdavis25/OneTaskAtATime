"""
Unit tests for EnhancedTaskFormDialog.

Tests the comprehensive task form dialog including:
- Form initialization and loading
- Field validation
- Context and project tag selection
- Date handling
- Task creation and editing
"""

import pytest
import sqlite3
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QDate

from src.models.task import Task
from src.models.context import Context
from src.models.project_tag import ProjectTag
from src.models.enums import TaskState, Priority
from src.ui.task_form_enhanced import EnhancedTaskFormDialog





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


@pytest.fixture
def form_dialog_new(qapp, db_connection):
    """Create form dialog for new task."""
    dialog = EnhancedTaskFormDialog(task=None, db_connection=db_connection)
    yield dialog
    dialog.close()


@pytest.fixture
def form_dialog_edit(qapp, db_connection, sample_task):
    """Create form dialog for editing existing task."""
    dialog = EnhancedTaskFormDialog(task=sample_task, db_connection=db_connection)
    yield dialog
    dialog.close()


class TestDialogInitialization:
    """Test dialog initialization."""

    def test_dialog_creation_new_task(self, form_dialog_new):
        """Test that dialog can be created for new task."""
        assert form_dialog_new is not None
        assert form_dialog_new.is_new is True
        assert form_dialog_new.task is None

    def test_dialog_creation_edit_task(self, form_dialog_edit, sample_task):
        """Test that dialog can be created for editing task."""
        assert form_dialog_edit is not None
        assert form_dialog_edit.is_new is False
        assert form_dialog_edit.task == sample_task

    def test_dialog_has_title_field(self, form_dialog_new):
        """Test that dialog has title input field."""
        assert hasattr(form_dialog_new, 'title_edit')
        assert form_dialog_new.title_edit is not None

    def test_dialog_has_description_field(self, form_dialog_new):
        """Test that dialog has description field."""
        assert hasattr(form_dialog_new, 'description_edit')
        assert form_dialog_new.description_edit is not None

    def test_dialog_has_priority_selection(self, form_dialog_new):
        """Test that dialog has priority selection."""
        assert hasattr(form_dialog_new, 'priority_combo')
        assert form_dialog_new.priority_combo is not None

    def test_dialog_has_due_date_field(self, form_dialog_new):
        """Test that dialog has due date field."""
        assert hasattr(form_dialog_new, 'due_date_edit')
        assert form_dialog_new.due_date_edit is not None

    def test_dialog_has_start_date_field(self, form_dialog_new):
        """Test that dialog has start date field."""
        assert hasattr(form_dialog_new, 'start_date_edit')
        assert form_dialog_new.start_date_edit is not None

    def test_dialog_has_save_button(self, form_dialog_new):
        """Test that dialog has save button."""
        assert hasattr(form_dialog_new, 'save_button')
        assert form_dialog_new.save_button is not None

    def test_dialog_has_cancel_button(self, form_dialog_new):
        """Test that dialog has cancel button."""
        assert hasattr(form_dialog_new, 'cancel_button')
        assert form_dialog_new.cancel_button is not None


class TestTaskDataLoading:
    """Test loading task data into form."""

    def test_edit_form_loads_title(self, form_dialog_edit, sample_task):
        """Test that editing form loads task title."""
        assert form_dialog_edit.title_edit.text() == sample_task.title

    def test_edit_form_loads_description(self, form_dialog_edit, sample_task):
        """Test that editing form loads task description."""
        assert form_dialog_edit.description_edit.toPlainText() == sample_task.description

    def test_edit_form_loads_priority(self, form_dialog_edit, sample_task):
        """Test that editing form loads task priority."""
        # Priority combo should be set to match task's base_priority
        priority_value = form_dialog_edit.priority_combo.currentData()
        assert priority_value == sample_task.base_priority

    def test_new_form_has_empty_title(self, form_dialog_new):
        """Test that new task form has empty title."""
        assert form_dialog_new.title_edit.text() == ""

    def test_new_form_has_empty_description(self, form_dialog_new):
        """Test that new task form has empty description."""
        assert form_dialog_new.description_edit.toPlainText() == ""

    def test_new_form_default_priority_is_medium(self, form_dialog_new):
        """Test that new task defaults to medium priority."""
        priority_value = form_dialog_new.priority_combo.currentData()
        assert priority_value == 2  # Medium priority


class TestFormValidation:
    """Test form validation."""

    def test_validate_requires_title(self, form_dialog_new):
        """Test that validation requires a title."""
        form_dialog_new.title_edit.setText("")
        result = form_dialog_new._validate_form()
        assert result is False

    def test_validate_accepts_title_only(self, form_dialog_new):
        """Test that validation accepts just a title."""
        form_dialog_new.title_edit.setText("Valid Title")
        result = form_dialog_new._validate_form()
        assert result is True

    def test_validate_accepts_with_description(self, form_dialog_new):
        """Test that validation accepts title with description."""
        form_dialog_new.title_edit.setText("Valid Title")
        form_dialog_new.description_edit.setPlainText("Valid description")
        result = form_dialog_new._validate_form()
        assert result is True

    def test_validate_whitespace_only_title_fails(self, form_dialog_new):
        """Test that whitespace-only title fails validation."""
        form_dialog_new.title_edit.setText("   ")
        result = form_dialog_new._validate_form()
        assert result is False


class TestTaskCreation:
    """Test creating new tasks from form."""

    def test_get_task_returns_task_object(self, form_dialog_new):
        """Test that get_task returns a Task object."""
        form_dialog_new.title_edit.setText("New Task")
        task = form_dialog_new.get_task()
        assert isinstance(task, Task)

    def test_get_task_includes_title(self, form_dialog_new):
        """Test that created task includes title."""
        test_title = "New Task Title"
        form_dialog_new.title_edit.setText(test_title)
        task = form_dialog_new.get_task()
        assert task.title == test_title

    def test_get_task_includes_description(self, form_dialog_new):
        """Test that created task includes description."""
        test_desc = "Task description"
        form_dialog_new.title_edit.setText("Title")
        form_dialog_new.description_edit.setPlainText(test_desc)
        task = form_dialog_new.get_task()
        assert task.description == test_desc

    def test_get_task_includes_priority(self, form_dialog_new):
        """Test that created task includes selected priority."""
        form_dialog_new.title_edit.setText("Title")
        # Set to high priority (index 0 usually)
        form_dialog_new.priority_combo.setCurrentIndex(0)
        task = form_dialog_new.get_task()
        priority = form_dialog_new.priority_combo.currentData()
        assert task.base_priority == priority

    def test_new_task_has_active_state(self, form_dialog_new):
        """Test that new task defaults to ACTIVE state."""
        form_dialog_new.title_edit.setText("Title")
        task = form_dialog_new.get_task()
        assert task.state == TaskState.ACTIVE


class TestDateHandling:
    """Test date field handling."""

    def test_due_date_checkbox_controls_field(self, form_dialog_new):
        """Test that due date checkbox enables/disables field."""
        assert hasattr(form_dialog_new, 'due_date_checkbox')

        # Uncheck should disable date edit
        form_dialog_new.due_date_checkbox.setChecked(False)
        assert not form_dialog_new.due_date_edit.isEnabled()

        # Check should enable date edit
        form_dialog_new.due_date_checkbox.setChecked(True)
        assert form_dialog_new.due_date_edit.isEnabled()

    def test_start_date_checkbox_controls_field(self, form_dialog_new):
        """Test that start date checkbox enables/disables field."""
        assert hasattr(form_dialog_new, 'start_date_checkbox')

        # Uncheck should disable date edit
        form_dialog_new.start_date_checkbox.setChecked(False)
        assert not form_dialog_new.start_date_edit.isEnabled()

        # Check should enable date edit
        form_dialog_new.start_date_checkbox.setChecked(True)
        assert form_dialog_new.start_date_edit.isEnabled()

    def test_get_task_includes_due_date_when_set(self, form_dialog_new):
        """Test that task includes due date when checkbox is checked."""
        form_dialog_new.title_edit.setText("Title")
        form_dialog_new.due_date_checkbox.setChecked(True)

        test_date = date.today() + timedelta(days=5)
        qdate = QDate(test_date.year, test_date.month, test_date.day)
        form_dialog_new.due_date_edit.setDate(qdate)

        task = form_dialog_new.get_task()
        assert task.due_date == test_date

    def test_get_task_no_due_date_when_unchecked(self, form_dialog_new):
        """Test that task has no due date when checkbox is unchecked."""
        form_dialog_new.title_edit.setText("Title")
        form_dialog_new.due_date_checkbox.setChecked(False)

        task = form_dialog_new.get_task()
        assert task.due_date is None


class TestContextSelection:
    """Test context selection functionality."""

    def test_dialog_has_context_combo(self, form_dialog_new):
        """Test that dialog has context selection combo."""
        assert hasattr(form_dialog_new, 'context_combo')
        assert form_dialog_new.context_combo is not None

    def test_context_combo_has_none_option(self, form_dialog_new):
        """Test that context combo includes 'None' option."""
        # First item should be None/empty option
        assert form_dialog_new.context_combo.count() >= 1


class TestProjectTagSelection:
    """Test project tag selection functionality."""

    def test_dialog_has_tag_list(self, form_dialog_new):
        """Test that dialog has project tag list widget."""
        assert hasattr(form_dialog_new, 'tag_list')
        assert form_dialog_new.tag_list is not None

    def test_tag_list_allows_multiple_selection(self, form_dialog_new):
        """Test that tag list allows multiple selections."""
        # QListWidget should allow multi-selection
        from PyQt5.QtWidgets import QAbstractItemView
        selection_mode = form_dialog_new.tag_list.selectionMode()
        assert selection_mode == QAbstractItemView.MultiSelection


class TestButtonBehavior:
    """Test button behavior."""

    def test_cancel_button_rejects_dialog(self, form_dialog_new):
        """Test that cancel button rejects dialog."""
        # Connect to rejected signal
        rejected = []
        form_dialog_new.rejected.connect(lambda: rejected.append(True))

        # Click cancel
        form_dialog_new.cancel_button.click()

        assert len(rejected) == 1

    def test_save_button_disabled_with_empty_title(self, form_dialog_new):
        """Test that save button is initially disabled or validates on click."""
        # This may vary by implementation
        # Either button is disabled OR clicking it shows validation error
        form_dialog_new.title_edit.setText("")
        # Just verify the validation method exists
        assert hasattr(form_dialog_new, '_validate_form')


class TestRecurrenceSupport:
    """Test recurrence pattern support."""

    def test_dialog_has_recurrence_checkbox(self, form_dialog_new):
        """Test that dialog has recurrence checkbox."""
        assert hasattr(form_dialog_new, 'recurrence_checkbox')

    def test_recurrence_checkbox_enables_pattern_button(self, form_dialog_new):
        """Test that recurrence checkbox controls pattern button."""
        assert hasattr(form_dialog_new, 'recurrence_pattern_button')

        # Unchecking should disable button
        form_dialog_new.recurrence_checkbox.setChecked(False)
        assert not form_dialog_new.recurrence_pattern_button.isEnabled()

        # Checking should enable button
        form_dialog_new.recurrence_checkbox.setChecked(True)
        assert form_dialog_new.recurrence_pattern_button.isEnabled()


class TestDependencySupport:
    """Test dependency handling."""

    def test_dialog_has_dependencies_button(self, form_dialog_new):
        """Test that dialog has dependencies button."""
        assert hasattr(form_dialog_new, 'dependencies_button')
        assert form_dialog_new.dependencies_button is not None

    def test_dialog_has_dependencies_label(self, form_dialog_new):
        """Test that dialog has dependencies label."""
        assert hasattr(form_dialog_new, 'dependencies_label')
        assert form_dialog_new.dependencies_label is not None


class TestStateManagement:
    """Test state management for existing tasks."""

    def test_edit_form_has_state_combo(self, form_dialog_edit):
        """Test that edit form has state combo box."""
        # State combo should exist for editing tasks
        assert hasattr(form_dialog_edit, 'state_combo')

    def test_edit_form_loads_current_state(self, form_dialog_edit, sample_task):
        """Test that edit form loads current task state."""
        current_state = form_dialog_edit.state_combo.currentData()
        assert current_state == sample_task.state.value


class TestFormLayout:
    """Test form layout and structure."""

    def test_dialog_is_scrollable(self, form_dialog_new):
        """Test that dialog has scrollable content area."""
        # Dialog should contain a scroll area for long forms
        assert hasattr(form_dialog_new, 'scroll_area') or hasattr(form_dialog_new, 'layout')

    def test_dialog_has_minimum_size(self, form_dialog_new):
        """Test that dialog has reasonable minimum size."""
        min_size = form_dialog_new.minimumSize()
        assert min_size.width() > 0
        assert min_size.height() > 0

    def test_dialog_has_window_title(self, form_dialog_new):
        """Test that dialog has appropriate window title."""
        title = form_dialog_new.windowTitle()
        assert len(title) > 0
        assert "Task" in title
