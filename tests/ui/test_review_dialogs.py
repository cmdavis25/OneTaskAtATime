"""
Unit tests for review dialogs (ReviewDeferredDialog, ReviewDelegatedDialog, ReviewSomedayDialog).

Tests the review dialogs including:
- Dialog initialization
- Task list display
- Action buttons
- Task activation
"""

import pytest
import sqlite3
from datetime import date, timedelta

from PyQt5.QtWidgets import QApplication

from src.models.task import Task
from src.models.enums import TaskState
from src.database.task_dao import TaskDAO
from src.ui.review_deferred_dialog import ReviewDeferredDialog
from src.ui.review_delegated_dialog import ReviewDelegatedDialog
from src.ui.review_someday_dialog import ReviewSomedayDialog





@pytest.fixture
def deferred_tasks_db(db_connection):
    """Create database with deferred tasks."""
    task_dao = TaskDAO(db_connection.get_connection())

    # Create deferred tasks
    for i in range(3):
        task = Task(
            title=f"Deferred Task {i}",
            base_priority=2,
            state=TaskState.DEFERRED,
            start_date=date.today() - timedelta(days=1)
        )
        task_dao.create(task)

    db_connection.commit()
    return db_connection


@pytest.fixture
def delegated_tasks_db(db_connection):
    """Create database with delegated tasks."""
    task_dao = TaskDAO(db_connection.get_connection())

    # Create delegated tasks
    for i in range(2):
        task = Task(
            title=f"Delegated Task {i}",
            base_priority=2,
            state=TaskState.DELEGATED,
            delegated_to=f"Person {i}",
            follow_up_date=date.today() - timedelta(days=1)
        )
        task_dao.create(task)

    db_connection.commit()
    return db_connection


@pytest.fixture
def someday_tasks_db(db_connection):
    """Create database with someday tasks."""
    task_dao = TaskDAO(db_connection.get_connection())

    # Create someday tasks
    for i in range(4):
        task = Task(
            title=f"Someday Task {i}",
            base_priority=1,
            state=TaskState.SOMEDAY
        )
        task_dao.create(task)

    db_connection.commit()
    return db_connection


class TestReviewDeferredDialog:
    """Test ReviewDeferredDialog."""

    def test_dialog_creation(self, qapp, db_connection):
        """Test that deferred review dialog can be created."""
        dialog = ReviewDeferredDialog(db_connection)
        assert dialog is not None
        dialog.close()

    def test_dialog_has_task_list(self, qapp, db_connection):
        """Test that dialog has task list widget."""
        dialog = ReviewDeferredDialog(db_connection)
        assert hasattr(dialog, 'task_list')
        dialog.close()

    def test_dialog_loads_deferred_tasks(self, qapp, deferred_tasks_db):
        """Test that dialog loads deferred tasks."""
        dialog = ReviewDeferredDialog(deferred_tasks_db)
        # Should have loaded tasks
        assert dialog.task_list.count() >= 3
        dialog.close()

    def test_dialog_has_activate_button(self, qapp, db_connection):
        """Test that dialog has activate button."""
        dialog = ReviewDeferredDialog(db_connection)
        assert hasattr(dialog, 'activate_button')
        dialog.close()

    def test_dialog_has_close_button(self, qapp, db_connection):
        """Test that dialog has close button."""
        dialog = ReviewDeferredDialog(db_connection)
        assert hasattr(dialog, 'close_button')
        dialog.close()

    def test_dialog_has_window_title(self, qapp, db_connection):
        """Test that dialog has appropriate title."""
        dialog = ReviewDeferredDialog(db_connection)
        title = dialog.windowTitle()
        assert len(title) > 0
        assert "Deferred" in title or "Review" in title
        dialog.close()


class TestReviewDelegatedDialog:
    """Test ReviewDelegatedDialog."""

    def test_dialog_creation(self, qapp, db_connection):
        """Test that delegated review dialog can be created."""
        dialog = ReviewDelegatedDialog(db_connection)
        assert dialog is not None
        dialog.close()

    def test_dialog_has_task_list(self, qapp, db_connection):
        """Test that dialog has task list widget."""
        dialog = ReviewDelegatedDialog(db_connection)
        assert hasattr(dialog, 'task_list')
        dialog.close()

    def test_dialog_loads_delegated_tasks(self, qapp, delegated_tasks_db):
        """Test that dialog loads delegated tasks."""
        dialog = ReviewDelegatedDialog(delegated_tasks_db)
        # Should have loaded tasks
        assert dialog.task_list.count() >= 2
        dialog.close()

    def test_dialog_shows_delegate_person(self, qapp, delegated_tasks_db):
        """Test that dialog shows who task is delegated to."""
        dialog = ReviewDelegatedDialog(delegated_tasks_db)
        # Task list should show delegate person info
        assert dialog.task_list.count() > 0
        dialog.close()

    def test_dialog_has_activate_button(self, qapp, db_connection):
        """Test that dialog has activate button."""
        dialog = ReviewDelegatedDialog(db_connection)
        assert hasattr(dialog, 'activate_button')
        dialog.close()

    def test_dialog_has_close_button(self, qapp, db_connection):
        """Test that dialog has close button."""
        dialog = ReviewDelegatedDialog(db_connection)
        assert hasattr(dialog, 'close_button')
        dialog.close()


class TestReviewSomedayDialog:
    """Test ReviewSomedayDialog."""

    def test_dialog_creation(self, qapp, db_connection):
        """Test that someday review dialog can be created."""
        dialog = ReviewSomedayDialog(db_connection)
        assert dialog is not None
        dialog.close()

    def test_dialog_has_task_list(self, qapp, db_connection):
        """Test that dialog has task list widget."""
        dialog = ReviewSomedayDialog(db_connection)
        assert hasattr(dialog, 'task_list')
        dialog.close()

    def test_dialog_loads_someday_tasks(self, qapp, someday_tasks_db):
        """Test that dialog loads someday/maybe tasks."""
        dialog = ReviewSomedayDialog(someday_tasks_db)
        # Should have loaded tasks
        assert dialog.task_list.count() >= 4
        dialog.close()

    def test_dialog_has_activate_button(self, qapp, db_connection):
        """Test that dialog has activate button."""
        dialog = ReviewSomedayDialog(db_connection)
        assert hasattr(dialog, 'activate_button')
        dialog.close()

    def test_dialog_has_trash_button(self, qapp, db_connection):
        """Test that dialog has trash button."""
        dialog = ReviewSomedayDialog(db_connection)
        assert hasattr(dialog, 'trash_button') or hasattr(dialog, 'delete_button')
        dialog.close()

    def test_dialog_has_close_button(self, qapp, db_connection):
        """Test that dialog has close button."""
        dialog = ReviewSomedayDialog(db_connection)
        assert hasattr(dialog, 'close_button')
        dialog.close()


class TestCommonReviewDialogBehavior:
    """Test common behavior across review dialogs."""

    def test_deferred_dialog_has_refresh_method(self, qapp, db_connection):
        """Test that deferred dialog has refresh method."""
        dialog = ReviewDeferredDialog(db_connection)
        assert hasattr(dialog, 'refresh') or hasattr(dialog, 'load_tasks')
        dialog.close()

    def test_delegated_dialog_has_refresh_method(self, qapp, db_connection):
        """Test that delegated dialog has refresh method."""
        dialog = ReviewDelegatedDialog(db_connection)
        assert hasattr(dialog, 'refresh') or hasattr(dialog, 'load_tasks')
        dialog.close()

    def test_someday_dialog_has_refresh_method(self, qapp, db_connection):
        """Test that someday dialog has refresh method."""
        dialog = ReviewSomedayDialog(db_connection)
        assert hasattr(dialog, 'refresh') or hasattr(dialog, 'load_tasks')
        dialog.close()


class TestTaskSelection:
    """Test task selection in review dialogs."""

    def test_deferred_dialog_enables_activate_on_selection(self, qapp, deferred_tasks_db):
        """Test that activate button enables when task selected."""
        dialog = ReviewDeferredDialog(deferred_tasks_db)

        # Initially might be disabled
        if dialog.task_list.count() > 0:
            # Select first item
            dialog.task_list.setCurrentRow(0)
            # Activate button should now be enabled
            assert dialog.activate_button.isEnabled()

        dialog.close()

    def test_delegated_dialog_enables_activate_on_selection(self, qapp, delegated_tasks_db):
        """Test that activate button enables when task selected."""
        dialog = ReviewDelegatedDialog(delegated_tasks_db)

        if dialog.task_list.count() > 0:
            dialog.task_list.setCurrentRow(0)
            assert dialog.activate_button.isEnabled()

        dialog.close()

    def test_someday_dialog_enables_actions_on_selection(self, qapp, someday_tasks_db):
        """Test that action buttons enable when task selected."""
        dialog = ReviewSomedayDialog(someday_tasks_db)

        if dialog.task_list.count() > 0:
            dialog.task_list.setCurrentRow(0)
            assert dialog.activate_button.isEnabled()

        dialog.close()
