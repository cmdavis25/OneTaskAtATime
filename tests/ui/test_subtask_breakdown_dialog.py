"""
Unit tests for SubtaskBreakdownDialog.

Tests the subtask breakdown functionality including:
- Dialog initialization
- Adding subtasks
- Editing subtasks
- Deleting subtasks
- Delete original option
- Validation
- Result retrieval
"""

import pytest
import sqlite3
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QMessageBox, QWidget

from src.models.task import Task
from src.models.enums import TaskState
from src.ui.subtask_breakdown_dialog import SubtaskBreakdownDialog


@pytest.fixture
def parent_with_db(qapp, db_connection):
    """Create a real QWidget parent with db_connection attribute."""
    parent = QWidget()
    parent.db_connection = db_connection
    yield parent
    parent.deleteLater()


@pytest.fixture
def sample_task():
    """Create a sample task."""
    return Task(
        id=1,
        title="Complex Task",
        description="Task that needs to be broken down",
        base_priority=2,
        due_date=date.today() + timedelta(days=7),
        state=TaskState.ACTIVE,
        elo_rating=1500.0,
        comparison_count=1
    )


class TestDialogInitialization:
    """Test dialog initialization."""

    def test_dialog_title_set(self, qapp, sample_task, parent_with_db):
        """Test that dialog title includes task title."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)
        assert "Break Down Task" in dialog.windowTitle()
        dialog.close()

    def test_minimum_size_set(self, qapp, sample_task, parent_with_db):
        """Test that minimum size is set."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)
        assert dialog.minimumWidth() == 700
        assert dialog.minimumHeight() == 600
        dialog.close()

    def test_task_stored(self, qapp, sample_task, parent_with_db):
        """Test that task is stored in dialog."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)
        assert dialog.task == sample_task
        dialog.close()

    def test_created_tasks_empty_initially(self, qapp, sample_task, parent_with_db):
        """Test that created_tasks list is empty initially."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)
        assert len(dialog.created_tasks) == 0
        dialog.close()

    def test_db_connection_inherited_from_parent(self, qapp, sample_task, parent_with_db):
        """Test that db_connection is inherited from parent."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)
        assert dialog.db_connection == parent_with_db.db_connection
        dialog.close()

    def test_whatsthis_help_enabled(self, qapp, sample_task, parent_with_db):
        """Test that WhatsThis help button is enabled."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)
        flags = dialog.windowFlags()
        assert flags & Qt.WindowContextHelpButtonHint
        dialog.close()


class TestUIComponents:
    """Test UI component creation."""

    def test_task_list_exists(self, qapp, sample_task, parent_with_db):
        """Test that task list widget exists."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)
        assert dialog.task_list is not None
        dialog.close()

    def test_add_button_exists(self, qapp, sample_task, parent_with_db):
        """Test that Add Task button exists."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)
        assert dialog.add_button is not None
        assert "Add" in dialog.add_button.text()
        dialog.close()

    def test_edit_button_exists(self, qapp, sample_task, parent_with_db):
        """Test that Edit Task button exists."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)
        assert dialog.edit_button is not None
        assert "Edit" in dialog.edit_button.text()
        dialog.close()

    def test_delete_button_exists(self, qapp, sample_task, parent_with_db):
        """Test that Delete Task button exists."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)
        assert dialog.delete_button is not None
        assert "Delete" in dialog.delete_button.text()
        dialog.close()

    def test_delete_original_checkbox_exists(self, qapp, sample_task, parent_with_db):
        """Test that delete original checkbox exists."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)
        assert dialog.delete_original_checkbox is not None
        dialog.close()

    def test_edit_button_initially_disabled(self, qapp, sample_task, parent_with_db):
        """Test that edit button is initially disabled."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)
        assert not dialog.edit_button.isEnabled()
        dialog.close()

    def test_delete_button_initially_disabled(self, qapp, sample_task, parent_with_db):
        """Test that delete button is initially disabled."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)
        assert not dialog.delete_button.isEnabled()
        dialog.close()


class TestAddingTasks:
    """Test adding subtasks."""

    def test_add_task_opens_dialog(self, qapp, sample_task, parent_with_db):
        """Test that add task button opens task form dialog."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        with patch('src.ui.subtask_breakdown_dialog.EnhancedTaskFormDialog') as mock_form:
            mock_instance = MagicMock()
            mock_instance.exec_.return_value = QDialog.Rejected
            mock_form.return_value = mock_instance

            dialog._on_add_task()

            # Dialog should be created
            mock_form.assert_called_once()

        dialog.close()

    def test_add_task_inherits_priority(self, qapp, sample_task, parent_with_db):
        """Test that new task inherits priority from parent."""
        sample_task.base_priority = 3
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        with patch('src.ui.subtask_breakdown_dialog.EnhancedTaskFormDialog') as mock_form:
            mock_instance = MagicMock()
            mock_instance.exec_.return_value = QDialog.Rejected
            mock_form.return_value = mock_instance

            dialog._on_add_task()

            # Check that task passed to dialog has correct priority
            call_args = mock_form.call_args
            new_task = call_args[1]['task']
            assert new_task.base_priority == 3

        dialog.close()

    def test_add_task_inherits_due_date(self, qapp, sample_task, parent_with_db):
        """Test that new task inherits due date from parent."""
        due_date = date.today() + timedelta(days=14)
        sample_task.due_date = due_date
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        with patch('src.ui.subtask_breakdown_dialog.EnhancedTaskFormDialog') as mock_form:
            mock_instance = MagicMock()
            mock_instance.exec_.return_value = QDialog.Rejected
            mock_form.return_value = mock_instance

            dialog._on_add_task()

            # Check that task passed to dialog has correct due date
            call_args = mock_form.call_args
            new_task = call_args[1]['task']
            assert new_task.due_date == due_date

        dialog.close()

    def test_add_task_adds_to_list(self, qapp, sample_task, parent_with_db):
        """Test that accepting task form adds task to list."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        new_task = Task(
            title="Subtask 1",
            base_priority=2,
            state=TaskState.ACTIVE,
            elo_rating=1500.0,
            comparison_count=0
        )

        with patch('src.ui.subtask_breakdown_dialog.EnhancedTaskFormDialog') as mock_form:
            mock_instance = MagicMock()
            mock_instance.exec_.return_value = QDialog.Accepted
            mock_instance.get_updated_task.return_value = new_task
            mock_form.return_value = mock_instance

            dialog._on_add_task()

            # Task should be added to created_tasks
            assert len(dialog.created_tasks) == 1
            assert dialog.created_tasks[0].title == "Subtask 1"

        dialog.close()

    def test_add_task_updates_list_widget(self, qapp, sample_task, parent_with_db):
        """Test that adding task updates the list widget."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        new_task = Task(
            title="Subtask 1",
            base_priority=2,
            state=TaskState.ACTIVE,
            elo_rating=1500.0,
            comparison_count=0
        )

        with patch('src.ui.subtask_breakdown_dialog.EnhancedTaskFormDialog') as mock_form:
            mock_instance = MagicMock()
            mock_instance.exec_.return_value = QDialog.Accepted
            mock_instance.get_updated_task.return_value = new_task
            mock_form.return_value = mock_instance

            dialog._on_add_task()

            # List widget should have one item
            assert dialog.task_list.count() == 1
            assert "Subtask 1" in dialog.task_list.item(0).text()

        dialog.close()


class TestEditingTasks:
    """Test editing subtasks."""

    def test_edit_button_enabled_with_selection(self, qapp, sample_task, parent_with_db):
        """Test that edit button is enabled when task is selected."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        # Add a task
        task = Task(title="Test Task", base_priority=2, state=TaskState.ACTIVE)
        dialog.created_tasks.append(task)
        dialog._refresh_task_list()

        # Select the task
        dialog.task_list.setCurrentRow(0)

        # Edit button should be enabled
        assert dialog.edit_button.isEnabled()

        dialog.close()

    def test_edit_task_opens_dialog(self, qapp, sample_task, parent_with_db):
        """Test that edit task opens dialog with selected task."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        # Add a task
        task = Task(title="Test Task", base_priority=2, state=TaskState.ACTIVE)
        dialog.created_tasks.append(task)
        dialog._refresh_task_list()

        # Select the task
        dialog.task_list.setCurrentRow(0)

        with patch('src.ui.subtask_breakdown_dialog.EnhancedTaskFormDialog') as mock_form:
            mock_instance = MagicMock()
            mock_instance.exec_.return_value = QDialog.Rejected
            mock_form.return_value = mock_instance

            dialog._on_edit_task()

            # Dialog should be opened with the task
            mock_form.assert_called_once()
            call_args = mock_form.call_args
            edited_task = call_args[1]['task']
            assert edited_task.title == "Test Task"

        dialog.close()

    def test_edit_task_updates_task(self, qapp, sample_task, parent_with_db):
        """Test that editing task updates the task in list."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        # Add a task
        task = Task(title="Original Title", base_priority=2, state=TaskState.ACTIVE)
        dialog.created_tasks.append(task)
        dialog._refresh_task_list()

        # Select the task
        dialog.task_list.setCurrentRow(0)

        # Edit the task
        edited_task = Task(title="Updated Title", base_priority=3, state=TaskState.ACTIVE)

        with patch('src.ui.subtask_breakdown_dialog.EnhancedTaskFormDialog') as mock_form:
            mock_instance = MagicMock()
            mock_instance.exec_.return_value = QDialog.Accepted
            mock_instance.get_updated_task.return_value = edited_task
            mock_form.return_value = mock_instance

            dialog._on_edit_task()

            # Task should be updated
            assert dialog.created_tasks[0].title == "Updated Title"
            assert dialog.created_tasks[0].base_priority == 3

        dialog.close()

    def test_double_click_edits_task(self, qapp, sample_task, parent_with_db):
        """Test that double-clicking task opens edit dialog."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        # Add a task
        task = Task(title="Test Task", base_priority=2, state=TaskState.ACTIVE)
        dialog.created_tasks.append(task)
        dialog._refresh_task_list()

        with patch('src.ui.subtask_breakdown_dialog.EnhancedTaskFormDialog') as mock_form:
            mock_instance = MagicMock()
            mock_instance.exec_.return_value = QDialog.Rejected
            mock_form.return_value = mock_instance

            # Simulate double click by calling the connected method
            item = dialog.task_list.item(0)
            dialog._on_edit_task()

            # Dialog should be opened
            mock_form.assert_called_once()

        dialog.close()


class TestDeletingTasks:
    """Test deleting subtasks."""

    def test_delete_button_enabled_with_selection(self, qapp, sample_task, parent_with_db):
        """Test that delete button is enabled when task is selected."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        # Add a task
        task = Task(title="Test Task", base_priority=2, state=TaskState.ACTIVE)
        dialog.created_tasks.append(task)
        dialog._refresh_task_list()

        # Select the task
        dialog.task_list.setCurrentRow(0)

        # Delete button should be enabled
        assert dialog.delete_button.isEnabled()

        dialog.close()

    def test_delete_task_requires_confirmation(self, qapp, sample_task, parent_with_db):
        """Test that deleting task requires confirmation."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        # Add a task
        task = Task(title="Test Task", base_priority=2, state=TaskState.ACTIVE)
        dialog.created_tasks.append(task)
        dialog._refresh_task_list()

        # Select the task
        dialog.task_list.setCurrentRow(0)

        with patch('src.ui.subtask_breakdown_dialog.MessageBox.question', return_value=QMessageBox.No):
            dialog._on_delete_task()

            # Task should not be deleted
            assert len(dialog.created_tasks) == 1

        dialog.close()

    def test_delete_task_removes_from_list(self, qapp, sample_task, parent_with_db):
        """Test that confirming deletion removes task from list."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        # Add a task
        task = Task(title="Test Task", base_priority=2, state=TaskState.ACTIVE)
        dialog.created_tasks.append(task)
        dialog._refresh_task_list()

        # Select the task
        dialog.task_list.setCurrentRow(0)

        with patch('src.ui.subtask_breakdown_dialog.MessageBox.question', return_value=QMessageBox.Yes):
            dialog._on_delete_task()

            # Task should be deleted
            assert len(dialog.created_tasks) == 0
            assert dialog.task_list.count() == 0

        dialog.close()

    def test_delete_task_no_selection(self, qapp, sample_task, parent_with_db):
        """Test that delete with no selection does nothing."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        # Add a task but don't select it
        task = Task(title="Test Task", base_priority=2, state=TaskState.ACTIVE)
        dialog.created_tasks.append(task)
        dialog._refresh_task_list()

        # Try to delete without selection
        dialog._on_delete_task()

        # Task should still be there
        assert len(dialog.created_tasks) == 1

        dialog.close()


class TestTaskListDisplay:
    """Test task list display formatting."""

    def test_task_title_displayed(self, qapp, sample_task, parent_with_db):
        """Test that task title is displayed."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        task = Task(title="My Task", base_priority=2, state=TaskState.ACTIVE)
        dialog.created_tasks.append(task)
        dialog._refresh_task_list()

        assert "My Task" in dialog.task_list.item(0).text()

        dialog.close()

    def test_priority_displayed(self, qapp, sample_task, parent_with_db):
        """Test that priority is displayed."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        task = Task(title="High Priority Task", base_priority=3, state=TaskState.ACTIVE)
        dialog.created_tasks.append(task)
        dialog._refresh_task_list()

        item_text = dialog.task_list.item(0).text()
        assert "High" in item_text

        dialog.close()

    def test_due_date_displayed(self, qapp, sample_task, parent_with_db):
        """Test that due date is displayed when set."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        due_date = date.today() + timedelta(days=5)
        task = Task(
            title="Task with Due Date",
            base_priority=2,
            due_date=due_date,
            state=TaskState.ACTIVE
        )
        dialog.created_tasks.append(task)
        dialog._refresh_task_list()

        item_text = dialog.task_list.item(0).text()
        assert "Due:" in item_text

        dialog.close()

    def test_multiple_tasks_displayed(self, qapp, sample_task, parent_with_db):
        """Test that multiple tasks are displayed."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        task1 = Task(title="Task 1", base_priority=2, state=TaskState.ACTIVE)
        task2 = Task(title="Task 2", base_priority=3, state=TaskState.ACTIVE)
        dialog.created_tasks.extend([task1, task2])
        dialog._refresh_task_list()

        assert dialog.task_list.count() == 2
        assert "Task 1" in dialog.task_list.item(0).text()
        assert "Task 2" in dialog.task_list.item(1).text()

        dialog.close()


class TestValidation:
    """Test dialog validation."""

    def test_confirm_without_tasks_shows_warning(self, qapp, sample_task, parent_with_db):
        """Test that confirming without tasks shows warning."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        with patch('src.ui.subtask_breakdown_dialog.MessageBox.warning') as mock_warning:
            dialog._on_confirm_clicked()

            # Warning should be shown
            mock_warning.assert_called_once()

        dialog.close()

    def test_confirm_with_tasks_succeeds(self, qapp, sample_task, parent_with_db):
        """Test that confirming with tasks succeeds."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        # Add a task
        task = Task(title="Subtask", base_priority=2, state=TaskState.ACTIVE)
        dialog.created_tasks.append(task)

        # Confirm should accept dialog
        dialog._on_confirm_clicked()

        assert dialog.result() == QDialog.Accepted

        dialog.close()


class TestDeleteOriginalOption:
    """Test delete original checkbox."""

    def test_delete_original_unchecked_by_default(self, qapp, sample_task, parent_with_db):
        """Test that delete original checkbox is unchecked by default."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)
        assert not dialog.delete_original_checkbox.isChecked()
        dialog.close()

    def test_delete_original_can_be_checked(self, qapp, sample_task, parent_with_db):
        """Test that delete original checkbox can be checked."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        dialog.delete_original_checkbox.setChecked(True)
        assert dialog.delete_original_checkbox.isChecked()

        dialog.close()

    def test_delete_original_requires_confirmation(self, qapp, sample_task, parent_with_db):
        """Test that delete original requires confirmation."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        # Add a task
        task = Task(title="Subtask", base_priority=2, state=TaskState.ACTIVE)
        dialog.created_tasks.append(task)

        # Check delete original
        dialog.delete_original_checkbox.setChecked(True)

        # Mock confirmation dialog to return No
        with patch('src.ui.subtask_breakdown_dialog.MessageBox.question', return_value=QMessageBox.No):
            dialog._on_confirm_clicked()

            # Dialog should not be accepted
            assert dialog.result() != QDialog.Accepted

        dialog.close()

    def test_delete_original_with_confirmation_succeeds(self, qapp, sample_task, parent_with_db):
        """Test that delete original with confirmation succeeds."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        # Add a task
        task = Task(title="Subtask", base_priority=2, state=TaskState.ACTIVE)
        dialog.created_tasks.append(task)

        # Check delete original
        dialog.delete_original_checkbox.setChecked(True)

        # Mock confirmation dialog to return Yes
        with patch('src.ui.subtask_breakdown_dialog.MessageBox.question', return_value=QMessageBox.Yes):
            dialog._on_confirm_clicked()

            # Dialog should be accepted
            assert dialog.result() == QDialog.Accepted

        dialog.close()


class TestResultRetrieval:
    """Test getting dialog results."""

    def test_get_result_returns_dict(self, qapp, sample_task, parent_with_db):
        """Test that get_result returns a dictionary."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)
        result = dialog.get_result()

        assert isinstance(result, dict)
        assert 'created_tasks' in result
        assert 'delete_original' in result

        dialog.close()

    def test_get_result_contains_created_tasks(self, qapp, sample_task, parent_with_db):
        """Test that get_result contains created tasks."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        task1 = Task(title="Task 1", base_priority=2, state=TaskState.ACTIVE)
        task2 = Task(title="Task 2", base_priority=3, state=TaskState.ACTIVE)
        dialog.created_tasks.extend([task1, task2])

        result = dialog.get_result()

        assert len(result['created_tasks']) == 2
        assert result['created_tasks'][0].title == "Task 1"
        assert result['created_tasks'][1].title == "Task 2"

        dialog.close()

    def test_get_result_contains_delete_original_flag(self, qapp, sample_task, parent_with_db):
        """Test that get_result contains delete_original flag."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        # Unchecked
        dialog.delete_original_checkbox.setChecked(False)
        result = dialog.get_result()
        assert result['delete_original'] is False

        # Checked
        dialog.delete_original_checkbox.setChecked(True)
        result = dialog.get_result()
        assert result['delete_original'] is True

        dialog.close()


class TestButtonState:
    """Test button enable/disable state."""

    def test_buttons_disabled_initially(self, qapp, sample_task, parent_with_db):
        """Test that edit and delete buttons are disabled initially."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        assert not dialog.edit_button.isEnabled()
        assert not dialog.delete_button.isEnabled()

        dialog.close()

    def test_buttons_enabled_after_selection(self, qapp, sample_task, parent_with_db):
        """Test that buttons are enabled after selection."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        # Add a task
        task = Task(title="Test Task", base_priority=2, state=TaskState.ACTIVE)
        dialog.created_tasks.append(task)
        dialog._refresh_task_list()

        # Select the task
        dialog.task_list.setCurrentRow(0)

        # Buttons should be enabled
        assert dialog.edit_button.isEnabled()
        assert dialog.delete_button.isEnabled()

        dialog.close()

    def test_buttons_disabled_after_deselection(self, qapp, sample_task, parent_with_db):
        """Test that buttons are disabled after deselection."""
        dialog = SubtaskBreakdownDialog(sample_task, parent_with_db)

        # Add a task
        task = Task(title="Test Task", base_priority=2, state=TaskState.ACTIVE)
        dialog.created_tasks.append(task)
        dialog._refresh_task_list()

        # Select then deselect
        dialog.task_list.setCurrentRow(0)
        dialog.task_list.clearSelection()

        # Buttons should be disabled
        assert not dialog.edit_button.isEnabled()
        assert not dialog.delete_button.isEnabled()

        dialog.close()
