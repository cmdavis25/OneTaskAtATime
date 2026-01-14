"""
Base E2E Test Class

Provides common fixtures and utilities for end-to-end testing of OneTaskAtATime.
Handles application lifecycle, database setup, and UI interaction helpers.
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional, List
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtTest import QTest

from src.ui.main_window import MainWindow
from src.database.schema import DatabaseSchema
from src.database.connection import DatabaseConnection
from src.models.task import Task
from src.models.enums import TaskState, Priority
from src.database.task_dao import TaskDAO
from src.database.context_dao import ContextDAO
from src.database.dependency_dao import DependencyDAO


class BaseE2ETest:
    """
    Base class for E2E tests with application lifecycle management.

    Provides fixtures for:
    - Full application instance with temporary database
    - Pre-seeded test data
    - UI interaction helpers
    - Time mocking for resurfacing tests
    """

    @pytest.fixture
    def qapp(self):
        """
        Create QApplication instance for tests.

        Note: pytest-qt provides this automatically, but we define it explicitly
        for clarity and to ensure it's properly initialized.
        """
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app
        # Don't quit the app - pytest-qt handles cleanup

    @pytest.fixture
    def temp_db_path(self, tmp_path):
        """
        Create a temporary database file path.

        Args:
            tmp_path: pytest's temporary directory fixture

        Returns:
            Path to temporary database file
        """
        db_path = tmp_path / "test_e2e.db"
        return str(db_path)

    @pytest.fixture
    def test_db_connection(self, temp_db_path):
        """
        Create and initialize a test database connection.

        This fixture bypasses the DatabaseConnection singleton to create
        an isolated test database for each test.

        Args:
            temp_db_path: Path to temporary database file

        Returns:
            sqlite3.Connection: Initialized test database connection
        """
        # Create connection
        connection = sqlite3.connect(temp_db_path, check_same_thread=False)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row

        # Initialize schema
        DatabaseSchema.initialize_database(connection)
        DatabaseSchema.migrate_to_elo_system(connection)
        DatabaseSchema.migrate_to_recurring_tasks(connection)
        DatabaseSchema.migrate_to_notification_system(connection)
        connection.commit()

        yield connection

        # Cleanup
        connection.close()

    @pytest.fixture
    def app_instance(self, qtbot, qapp, test_db_connection, temp_db_path, monkeypatch):
        """
        Launch full application with temporary database.

        This fixture:
        1. Patches DatabaseConnection to use test database
        2. Creates MainWindow instance
        3. Shows and renders the window
        4. Cleans up after test

        Args:
            qtbot: pytest-qt fixture for widget testing
            qapp: QApplication instance
            test_db_connection: Initialized test database
            temp_db_path: Path to test database
            monkeypatch: pytest fixture for patching

        Returns:
            MainWindow: Fully initialized application window
        """
        # Reset DatabaseConnection singleton
        DatabaseConnection._instance = None
        DatabaseConnection._connection = None

        # Patch DatabaseConnection to use test database
        original_connect = DatabaseConnection._connect

        def mock_connect(self):
            """Use test database instead of production database."""
            self._connection = test_db_connection

        monkeypatch.setattr(DatabaseConnection, '_connect', mock_connect)

        # Create main window in test mode (skips Welcome Wizard and ranking dialogs)
        app = MainWindow(qapp, test_mode=True)
        qtbot.addWidget(app)
        app.show()

        # Wait for window to be visible and rendered
        qtbot.waitExposed(app)
        QTest.qWait(100)  # Additional time for initialization

        yield app

        # Cleanup
        app.close()

        # Reset DatabaseConnection singleton for next test
        DatabaseConnection._instance = None
        DatabaseConnection._connection = None

    @pytest.fixture
    def seeded_app(self, app_instance, test_db_connection):
        """
        Application with pre-seeded test data.

        Seeds the database with:
        - 10 active tasks (varied priorities)
        - 5 deferred tasks
        - 3 delegated tasks
        - 2 someday tasks
        - 5 completed tasks
        - 2 contexts
        - 3 project tags
        - 3 task dependencies

        Args:
            app_instance: MainWindow instance
            test_db_connection: Test database connection

        Returns:
            MainWindow: Application with seeded data
        """
        task_dao = TaskDAO(test_db_connection)
        context_dao = ContextDAO(test_db_connection)
        dependency_dao = DependencyDAO(test_db_connection)

        # Create contexts
        from src.models import Context
        work_ctx = context_dao.create(Context(name="Work", description="Office and computer work"))
        work_ctx_id = work_ctx.id
        home_ctx = context_dao.create(Context(name="Home", description="Personal and home tasks"))
        home_ctx_id = home_ctx.id

        # Create active tasks
        active_tasks = []
        for i in range(10):
            task = Task(
                title=f"Active Task {i+1}",
                description=f"Description for active task {i+1}",
                base_priority=2 if i % 3 != 0 else 3,
                due_date=date.today() + timedelta(days=i+1),
                state=TaskState.ACTIVE,
                context_id=work_ctx_id if i % 2 == 0 else home_ctx_id,
                elo_rating=1500.0 + (i * 10),
                comparison_count=i
            )
            created_task = task_dao.create(task)
            active_tasks.append(created_task)

        # Create deferred tasks
        for i in range(5):
            task = Task(
                title=f"Deferred Task {i+1}",
                description=f"Will start later",
                base_priority=2,
                due_date=date.today() + timedelta(days=10+i),
                start_date=date.today() + timedelta(days=5+i),
                state=TaskState.DEFERRED,
                context_id=work_ctx_id
            )
            task_dao.create(task)

        # Create delegated tasks
        for i in range(3):
            task = Task(
                title=f"Delegated Task {i+1}",
                description=f"Waiting on someone else",
                base_priority=1,
                due_date=date.today() + timedelta(days=15+i),
                delegated_to=f"Person {i+1}",
                follow_up_date=date.today() + timedelta(days=7+i),
                state=TaskState.DELEGATED,
                context_id=home_ctx_id
            )
            task_dao.create(task)

        # Create someday tasks
        for i in range(2):
            task = Task(
                title=f"Someday Task {i+1}",
                description=f"Not urgent, someday",
                base_priority=1,
                state=TaskState.SOMEDAY,
                context_id=work_ctx_id
            )
            task_dao.create(task)

        # Create completed tasks
        for i in range(5):
            task = Task(
                title=f"Completed Task {i+1}",
                description=f"Already done",
                base_priority=2,
                state=TaskState.COMPLETED,
                completed_at=datetime.now() - timedelta(days=i+1),
                context_id=home_ctx_id
            )
            task_dao.create(task)

        # Create dependencies (task 2 depends on task 1, task 3 depends on task 2)
        if len(active_tasks) >= 3:
            dependency_dao.add_dependency(active_tasks[1].id, active_tasks[0].id)
            dependency_dao.add_dependency(active_tasks[2].id, active_tasks[1].id)

        test_db_connection.commit()

        # Refresh UI to show seeded data
        if hasattr(app_instance, 'focus_mode'):
            app_instance._refresh_focus_task()

        return app_instance

    # UI Interaction Helpers

    def click_button(self, qtbot, button, wait_ms=100):
        """
        Click a button and wait for UI to update.

        Args:
            qtbot: pytest-qt fixture
            button: QPushButton to click
            wait_ms: Milliseconds to wait after click
        """
        qtbot.mouseClick(button, Qt.LeftButton)
        QTest.qWait(wait_ms)

    def close_all_dialogs(self):
        """
        Close all open dialogs (for cleanup after failed tests).
        """
        from PyQt5.QtWidgets import QDialog
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QDialog) and widget.isVisible():
                widget.reject()
                QTest.qWait(50)

    def find_dialog(self, app, dialog_class, timeout=1000):
        """
        Find an open dialog of specified type.

        Args:
            app: Application instance
            dialog_class: Class of dialog to find
            timeout: Max time to wait in milliseconds

        Returns:
            Dialog instance or None if not found

        Note: If dialog is not found but other dialogs are open,
        they will be automatically closed to prevent test blocking.
        """
        import time
        start_time = time.time()
        found_dialog = None

        while (time.time() - start_time) * 1000 < timeout:
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, dialog_class) and widget.isVisible():
                    return widget
            QTest.qWait(50)

        # Dialog not found - close any open dialogs to prevent blocking
        from PyQt5.QtWidgets import QDialog
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QDialog) and widget.isVisible():
                print(f"\n  Warning: Closing unexpected dialog: {widget.__class__.__name__}")
                widget.reject()
                QTest.qWait(50)

        return None

    def wait_for_condition(self, condition_func, timeout_ms=5000):
        """
        Wait for a condition to become true.

        Args:
            condition_func: Function that returns True when condition is met
            timeout_ms: Maximum time to wait in milliseconds

        Returns:
            True if condition met, False if timeout
        """
        import time
        start_time = time.time()
        while (time.time() - start_time) * 1000 < timeout_ms:
            if condition_func():
                return True
            QTest.qWait(50)
        return False

    def get_focus_task(self, app):
        """
        Get the currently displayed focus task.

        Args:
            app: Application instance

        Returns:
            Task or None if no focus task
        """
        if hasattr(app, 'focus_mode'):
            return app.focus_mode.get_current_task()
        return None

    def assert_task_exists(self, app, title):
        """
        Assert that a task with given title exists.

        Args:
            app: Application instance
            title: Task title to search for
        """
        tasks = app.task_service.get_all_tasks()
        titles = [t.title for t in tasks]
        assert title in titles, f"Task '{title}' not found. Available: {titles}"

    def assert_task_state(self, app, task_id, expected_state):
        """
        Assert that a task has expected state.

        Args:
            app: Application instance
            task_id: Task ID
            expected_state: Expected TaskState
        """
        task = app.task_service.get_task_by_id(task_id)
        assert task is not None, f"Task {task_id} not found"
        assert task.state == expected_state, \
            f"Task {task_id} state is {task.state}, expected {expected_state}"
