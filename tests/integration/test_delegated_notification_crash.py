"""
Integration test for delegated task notification crash bug.

This test reproduces the exact scenario that caused the crash:
1. Create a delegated task with today's follow-up date
2. Launch the application
3. Trigger the scheduler startup checks
4. Verify no crash occurs when processing the notification

This prevents regression of the bug where ReviewDelegatedDialog was being
passed the wrong type (sqlite3.Connection instead of DatabaseConnection).
"""

import pytest
from datetime import date
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from src.models.task import Task, TaskState
from src.database.connection import DatabaseConnection
from src.database.task_dao import TaskDAO
from src.ui.main_window import MainWindow


class TestDelegatedNotificationCrash:
    """Test suite for delegated task notification crash bug."""

    @pytest.fixture
    def db_with_delegated_task(self):
        """Create a database with a delegated task ready for follow-up today."""
        db_connection = DatabaseConnection()
        task_dao = TaskDAO(db_connection.get_connection())

        # Create a delegated task with today's follow-up date
        task = Task(
            title="Test Delegated Task - Follow-up Today",
            description="This task should trigger a notification on startup",
            state=TaskState.DELEGATED,
            delegated_to="Test Person",
            follow_up_date=date.today(),  # Today - should trigger notification
            base_priority=2
        )
        created_task = task_dao.create(task)

        yield db_connection

        # Cleanup
        db_connection.close()

    def test_app_startup_with_delegated_notification(self, qapp, db_with_delegated_task):
        """
        Test that app starts successfully when delegated task notification is triggered.

        This test:
        1. Creates a delegated task with today as follow-up date
        2. Launches MainWindow (which triggers scheduler startup checks)
        3. Waits for startup checks to complete
        4. Verifies no crash occurred
        """
        # Create MainWindow with test mode OFF to trigger scheduler
        # (test_mode=False means scheduler will run startup checks)
        window = MainWindow(app=qapp, test_mode=False, db_connection=db_with_delegated_task)

        # Show the window
        window.show()

        # Process events to ensure UI is fully initialized
        qapp.processEvents()

        # Wait for the delayed startup checks to run (1 second delay in code)
        # We need to process events during this time
        import time
        start_time = time.time()
        while time.time() - start_time < 2.0:  # Wait up to 2 seconds
            qapp.processEvents()
            time.sleep(0.1)

        # If we got here without crashing, the test passed
        assert window is not None
        assert window.isVisible()

        # Verify the notification was created
        unread_count = window.notification_manager.get_unread_count()
        assert unread_count > 0, "Should have created a notification for delegated task"

        # Cleanup
        window.close()

    def test_review_delegated_dialog_with_database_connection(self, qapp, db_with_delegated_task):
        """
        Test that ReviewDelegatedDialog accepts DatabaseConnection object.

        This specifically tests the fix for the AttributeError where
        ReviewDelegatedDialog was receiving sqlite3.Connection instead of
        DatabaseConnection, causing .get_connection() to fail.
        """
        from src.ui.review_delegated_dialog import ReviewDelegatedDialog
        from src.database.task_dao import TaskDAO

        # Get the delegated task
        task_dao = TaskDAO(db_with_delegated_task.get_connection())
        tasks = task_dao.get_delegated_tasks_for_followup(date.today(), days_before=0)

        assert len(tasks) > 0, "Should have at least one delegated task"

        # Create dialog with DatabaseConnection (not .get_connection())
        # This is the correct usage that was fixed
        dialog = ReviewDelegatedDialog(db_with_delegated_task, tasks)

        # Verify dialog was created successfully
        assert dialog is not None
        assert hasattr(dialog, 'task_service')
        assert hasattr(dialog, 'reviewable_tasks')
        assert len(dialog.reviewable_tasks) > 0

        # Cleanup
        dialog.close()

    def test_notification_action_handler_calls_dialog_correctly(self, qapp, db_with_delegated_task):
        """
        Test that notification action handler calls ReviewDelegatedDialog correctly.

        This tests the _on_notification_action method in MainWindow to ensure
        it passes the DatabaseConnection object (not sqlite3.Connection) to
        ReviewDelegatedDialog.
        """
        from src.models.notification import Notification, NotificationType

        # Create MainWindow
        window = MainWindow(app=qapp, test_mode=True, db_connection=db_with_delegated_task)
        window.show()
        qapp.processEvents()

        # Create a test notification with delegated task action
        from src.database.task_dao import TaskDAO
        task_dao = TaskDAO(db_with_delegated_task.get_connection())
        tasks = task_dao.get_delegated_tasks_for_followup(date.today(), days_before=0)

        notification = Notification(
            type=NotificationType.INFO,
            title="Follow-up Required",
            message="1 delegated task(s) have reached their follow-up date.",
            action_type='open_review_delegated',
            action_data={'task_ids': [task.id for task in tasks]}
        )

        # This should NOT crash - it should open the dialog correctly
        try:
            window._on_notification_action(notification)
            # If we get here without AttributeError, the fix is working
            success = True
        except AttributeError as e:
            if "'sqlite3.Connection' object has no attribute 'get_connection'" in str(e):
                success = False
                pytest.fail(f"ReviewDelegatedDialog received wrong type: {e}")
            else:
                raise

        assert success, "Notification action handler should call ReviewDelegatedDialog without errors"

        # Cleanup
        window.close()

    def test_scheduler_startup_checks_dont_crash(self, qapp, db_with_delegated_task):
        """
        Test that scheduler startup checks run without crashing.

        This specifically tests that running check_delegated_tasks() after
        MainWindow initialization doesn't cause crashes.
        """
        # Create MainWindow in test mode (scheduler won't auto-run)
        window = MainWindow(app=qapp, test_mode=True, db_connection=db_with_delegated_task)
        window.show()
        qapp.processEvents()

        # Manually trigger the startup checks method
        # This is what gets called 1 second after startup
        try:
            window._run_startup_checks()
            qapp.processEvents()
            success = True
        except Exception as e:
            success = False
            pytest.fail(f"Startup checks crashed: {e}")

        assert success, "Startup checks should complete without errors"

        # Cleanup
        window.close()
