"""
Unit tests for MainWindow dependency persistence bug fix.

This test module specifically verifies that newly-created tasks correctly
persist dependencies when created through the TaskFormDialog in MainWindow.

Bug: Newly-created tasks don't remember assigned dependencies
Root Cause: TaskFormDialog was created without db_connection parameter in _on_new_task()
Fix: Added db_connection=self.db_connection to TaskFormDialog constructor (line 614)

These tests verify:
1. TaskFormDialog receives db_connection when created via _on_new_task()
2. Dependencies selected in the form dialog are persisted to the database
3. The dependency_dao can retrieve the persisted dependencies
4. The workflow correctly creates both task and dependency records
"""

import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch, call

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog

from src.models.task import Task
from src.models.dependency import Dependency
from src.models.enums import TaskState
from src.ui.main_window import MainWindow
from src.ui.task_form_dialog import TaskFormDialog
from src.database.task_dao import TaskDAO
from src.database.dependency_dao import DependencyDAO


@pytest.fixture
def main_window(qapp, db_connection):
    """Create MainWindow instance in test mode with test database."""
    window = MainWindow(app=qapp, test_mode=True)

    # Replace the production database connection with the test database connection
    # This ensures all database operations use the test database
    window.db_connection = db_connection

    # Re-initialize DAOs to use the test database
    window.task_dao = TaskDAO(db_connection.get_connection())
    window.dependency_dao = DependencyDAO(db_connection.get_connection())

    # Re-initialize services that depend on the database
    from src.services.task_service import TaskService
    from src.services.comparison_service import ComparisonService
    from src.database.task_history_dao import TaskHistoryDAO
    from src.services.task_history_service import TaskHistoryService

    window.task_service = TaskService(db_connection)
    window.comparison_service = ComparisonService(db_connection)

    # Re-initialize task history service to use test database
    task_history_dao = TaskHistoryDAO(db_connection.get_connection())
    window.task_history_service = TaskHistoryService(task_history_dao)

    yield window
    window.close()


@pytest.fixture
def blocking_tasks(db_connection):
    """Create sample blocking tasks in test database."""
    task_dao = TaskDAO(db_connection.get_connection())

    tasks = [
        Task(
            title="Blocking Task 1",
            description="First blocker",
            base_priority=3,
            state=TaskState.ACTIVE,
            elo_rating=1500.0,
            comparison_count=1
        ),
        Task(
            title="Blocking Task 2",
            description="Second blocker",
            base_priority=2,
            state=TaskState.ACTIVE,
            elo_rating=1500.0,
            comparison_count=1
        ),
    ]

    created_tasks = []
    for task in tasks:
        created = task_dao.create(task)
        created_tasks.append(created)

    return created_tasks


class TestTaskFormDialogDbConnection:
    """Test that TaskFormDialog receives db_connection properly."""

    def test_task_form_dialog_receives_db_connection(self, main_window):
        """Test that TaskFormDialog is created with db_connection parameter."""
        with patch('src.ui.main_window.TaskFormDialog') as mock_dialog_class:
            mock_dialog_instance = MagicMock()
            mock_dialog_instance.exec_.return_value = False  # User cancels
            mock_dialog_class.return_value = mock_dialog_instance

            # Trigger new task action
            main_window._on_new_task()

            # Verify TaskFormDialog was called with db_connection
            mock_dialog_class.assert_called_once_with(
                db_connection=main_window.db_connection,
                parent=main_window
            )

    def test_task_form_dialog_has_db_connection_attribute(self, main_window):
        """Test that TaskFormDialog instance actually has db_connection set."""
        # Create dialog directly as MainWindow would
        dialog = TaskFormDialog(db_connection=main_window.db_connection, parent=main_window)

        # Verify db_connection is set
        assert dialog.db_connection is not None
        assert dialog.db_connection == main_window.db_connection

        dialog.close()


class TestDependencyPersistence:
    """Test that dependencies are persisted when creating new tasks."""

    def test_dependencies_persisted_for_new_task(self, main_window, blocking_tasks):
        """Test that dependencies selected in dialog are saved to database."""
        blocking_task_1, blocking_task_2 = blocking_tasks

        with patch('src.ui.main_window.TaskFormDialog') as mock_dialog_class:
            mock_dialog = MagicMock()
            mock_dialog.exec_.return_value = True  # User accepts

            # Create a new task object (without ID - will be assigned by task_service)
            new_task = Task(
                title="New Blocked Task",
                description="This task has dependencies",
                base_priority=2,
                state=TaskState.ACTIVE,
                elo_rating=1500.0,
                comparison_count=0
            )
            mock_dialog.get_updated_task.return_value = new_task

            # Simulate user selecting dependencies in the dialog
            mock_dialog.dependencies = [blocking_task_1.id, blocking_task_2.id]

            mock_dialog_class.return_value = mock_dialog

            # Trigger new task action (task_service.create_task will assign ID)
            main_window._on_new_task()

            # Verify the task was created by retrieving it from database
            all_tasks = main_window.task_service.get_all_tasks()
            created_task = next(
                (t for t in all_tasks if t.title == "New Blocked Task"),
                None
            )
            assert created_task is not None
            assert created_task.id is not None

            # Verify dependencies were persisted
            dependency_dao = DependencyDAO(main_window.db_connection.get_connection())
            dependencies = dependency_dao.get_dependencies_for_task(created_task.id)

            assert len(dependencies) == 2
            blocking_ids = {dep.blocking_task_id for dep in dependencies}
            assert blocking_ids == {blocking_task_1.id, blocking_task_2.id}

    def test_no_dependencies_when_none_selected(self, main_window):
        """Test that no dependencies are created when none are selected."""
        with patch('src.ui.main_window.TaskFormDialog') as mock_dialog_class:
            mock_dialog = MagicMock()
            mock_dialog.exec_.return_value = True

            new_task = Task(
                title="Task Without Dependencies",
                description="No blockers",
                base_priority=1,
                state=TaskState.ACTIVE,
                elo_rating=1500.0,
                comparison_count=0
            )
            mock_dialog.get_updated_task.return_value = new_task

            # No dependencies selected
            mock_dialog.dependencies = []

            mock_dialog_class.return_value = mock_dialog

            # Trigger new task action
            main_window._on_new_task()

            # Verify the task was created
            all_tasks = main_window.task_service.get_all_tasks()
            created_task = next(
                (t for t in all_tasks if t.title == "Task Without Dependencies"),
                None
            )
            assert created_task is not None

            # Verify no dependencies were created
            dependency_dao = DependencyDAO(main_window.db_connection.get_connection())
            dependencies = dependency_dao.get_dependencies_for_task(created_task.id)

            assert len(dependencies) == 0

    def test_partial_dependencies_persisted(self, main_window, blocking_tasks):
        """Test that a subset of dependencies can be persisted."""
        blocking_task_1, blocking_task_2 = blocking_tasks

        with patch('src.ui.main_window.TaskFormDialog') as mock_dialog_class:
            mock_dialog = MagicMock()
            mock_dialog.exec_.return_value = True

            # Create task without ID - will be assigned by task_service
            new_task = Task(
                title="Partially Blocked Task",
                description="One dependency",
                base_priority=2,
                state=TaskState.ACTIVE,
                elo_rating=1500.0,
                comparison_count=0
            )
            mock_dialog.get_updated_task.return_value = new_task

            # Only one dependency selected
            mock_dialog.dependencies = [blocking_task_1.id]

            mock_dialog_class.return_value = mock_dialog

            # Trigger new task action
            main_window._on_new_task()

            # Verify the task was created
            all_tasks = main_window.task_service.get_all_tasks()
            created_task = next(
                (t for t in all_tasks if t.title == "Partially Blocked Task"),
                None
            )
            assert created_task is not None
            assert created_task.id is not None

            # Verify only one dependency was persisted
            dependency_dao = DependencyDAO(main_window.db_connection.get_connection())
            dependencies = dependency_dao.get_dependencies_for_task(created_task.id)

            assert len(dependencies) == 1
            assert dependencies[0].blocking_task_id == blocking_task_1.id


class TestDependencyWorkflow:
    """Test the complete dependency workflow."""

    def test_dependency_workflow_integration(self, main_window, blocking_tasks):
        """Integration test for complete dependency creation workflow."""
        blocking_task_1, blocking_task_2 = blocking_tasks
        dependency_dao = DependencyDAO(main_window.db_connection.get_connection())

        # Verify no dependencies exist initially for our blocking tasks
        initial_blocking_count_1 = len(dependency_dao.get_blocking_tasks(blocking_task_1.id))
        initial_blocking_count_2 = len(dependency_dao.get_blocking_tasks(blocking_task_2.id))

        with patch('src.ui.main_window.TaskFormDialog') as mock_dialog_class:
            mock_dialog = MagicMock()
            mock_dialog.exec_.return_value = True

            # Create task without ID - will be assigned by task_service
            new_task = Task(
                title="Integration Test Task",
                description="Testing full workflow",
                base_priority=3,
                due_date=date.today() + timedelta(days=7),
                state=TaskState.ACTIVE,
                elo_rating=1500.0,
                comparison_count=0
            )
            mock_dialog.get_updated_task.return_value = new_task
            mock_dialog.dependencies = [blocking_task_1.id, blocking_task_2.id]

            mock_dialog_class.return_value = mock_dialog

            # Execute the workflow
            main_window._on_new_task()

            # Verify task creation
            all_tasks = main_window.task_service.get_all_tasks()
            created_task = next(
                (t for t in all_tasks if t.title == "Integration Test Task"),
                None
            )
            assert created_task is not None
            assert created_task.id is not None

            # Verify dependencies from blocked task perspective
            dependencies = dependency_dao.get_dependencies_for_task(created_task.id)
            assert len(dependencies) == 2

            # Verify dependencies from blocking task perspective
            blocking_1 = dependency_dao.get_blocking_tasks(blocking_task_1.id)
            assert len(blocking_1) == initial_blocking_count_1 + 1
            assert any(d.blocked_task_id == created_task.id for d in blocking_1)

            blocking_2 = dependency_dao.get_blocking_tasks(blocking_task_2.id)
            assert len(blocking_2) == initial_blocking_count_2 + 1
            assert any(d.blocked_task_id == created_task.id for d in blocking_2)

            # Verify dependency properties
            for dep in dependencies:
                assert dep.blocked_task_id == created_task.id
                assert dep.blocking_task_id in [blocking_task_1.id, blocking_task_2.id]
                assert dep.created_at is not None
