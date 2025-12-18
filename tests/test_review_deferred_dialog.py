"""
Tests for Review Deferred Tasks Dialog.

Verifies that the dialog correctly displays deferred tasks and allows activation.
"""

import pytest
from datetime import date, timedelta
from src.ui.review_deferred_dialog import ReviewDeferredDialog
from src.models.task import Task
from src.models.enums import TaskState, Priority
from src.services.task_service import TaskService
from src.algorithms.priority import calculate_importance_for_tasks


class MockDatabaseConnection:
    """Mock DatabaseConnection for testing."""
    def __init__(self, connection):
        self._connection = connection

    def get_connection(self):
        return self._connection

    def close(self):
        pass


@pytest.fixture
def db_connection(test_db):
    """Create mock database connection for testing."""
    return MockDatabaseConnection(test_db)


@pytest.fixture
def task_service(db_connection):
    """Create task service for testing."""
    return TaskService(db_connection)


def test_review_dialog_shows_deferred_tasks(qtbot, db_connection, task_service):
    """Test that dialog displays deferred tasks."""
    # Create some deferred tasks with same due date to ensure HIGH comes first
    task1 = Task(
        title="Deferred Task 1",
        base_priority=Priority.HIGH.value,
        state=TaskState.DEFERRED,
        start_date=date.today() + timedelta(days=7),
        due_date=date.today() + timedelta(days=14)
    )
    task2 = Task(
        title="Deferred Task 2",
        base_priority=Priority.MEDIUM.value,
        state=TaskState.DEFERRED,
        start_date=date.today() + timedelta(days=3),
        due_date=date.today() + timedelta(days=14)  # Same due date as task1
    )

    task_service.create_task(task1)
    task_service.create_task(task2)

    # Create dialog
    dialog = ReviewDeferredDialog(db_connection)

    # Verify tasks are loaded
    assert len(dialog.reviewable_tasks) == 2
    assert dialog.task_table.rowCount() == 2

    # Verify tasks are sorted by importance (HIGH priority should come first when due dates are equal)
    assert dialog.reviewable_tasks[0].base_priority == Priority.HIGH.value


def test_review_dialog_empty_state(qtbot, db_connection):
    """Test dialog when no deferred tasks exist."""
    dialog = ReviewDeferredDialog(db_connection)

    # Verify no tasks loaded
    assert len(dialog.reviewable_tasks) == 0
    assert dialog.task_table.rowCount() == 0
    assert "No deferred or postponed tasks found" in dialog.info_label.text()


def test_review_dialog_sorts_by_importance(qtbot, db_connection, task_service):
    """Test that tasks are sorted by importance (Priority × Urgency)."""
    # Create tasks with different importance levels
    # High priority, far due date (lower urgency)
    task1 = Task(
        title="High Priority Far",
        base_priority=Priority.HIGH.value,
        state=TaskState.DEFERRED,
        due_date=date.today() + timedelta(days=30)
    )

    # Medium priority, near due date (higher urgency)
    task2 = Task(
        title="Medium Priority Near",
        base_priority=Priority.MEDIUM.value,
        state=TaskState.DEFERRED,
        due_date=date.today() + timedelta(days=1)
    )

    # Low priority
    task3 = Task(
        title="Low Priority",
        base_priority=Priority.LOW.value,
        state=TaskState.DEFERRED,
        due_date=date.today() + timedelta(days=15)
    )

    task_service.create_task(task1)
    task_service.create_task(task2)
    task_service.create_task(task3)

    dialog = ReviewDeferredDialog(db_connection)

    # Verify sorting by importance
    assert len(dialog.reviewable_tasks) == 3

    # Calculate importance for comparison
    importance_scores = calculate_importance_for_tasks(dialog.reviewable_tasks)
    importances = [importance_scores.get(task.id, 0.0) for task in dialog.reviewable_tasks]

    # Verify descending order
    assert importances == sorted(importances, reverse=True)


def test_activate_task_changes_state(qtbot, db_connection, task_service):
    """Test that activating a task changes its state to ACTIVE."""
    # Create a deferred task
    task = Task(
        title="Test Deferred Task",
        base_priority=Priority.MEDIUM.value,
        state=TaskState.DEFERRED,
        start_date=date.today() + timedelta(days=5)
    )
    created_task = task_service.create_task(task)

    # Verify initial state
    assert created_task.state == TaskState.DEFERRED

    # Activate the task using task service (simulating dialog behavior)
    activated_task = task_service.activate_task(created_task.id)

    # Verify state changed
    assert activated_task.state == TaskState.ACTIVE
    assert activated_task.start_date is None  # Start date should be cleared


def test_review_dialog_highlights_future_start_dates(qtbot, db_connection, task_service):
    """Test that tasks with future start dates are highlighted."""
    # Create task with future start date
    future_task = Task(
        title="Future Task",
        base_priority=Priority.MEDIUM.value,
        state=TaskState.DEFERRED,
        start_date=date.today() + timedelta(days=10)
    )

    # Create task with past start date
    past_task = Task(
        title="Past Task",
        base_priority=Priority.MEDIUM.value,
        state=TaskState.DEFERRED,
        start_date=date.today() - timedelta(days=5)
    )

    task_service.create_task(future_task)
    task_service.create_task(past_task)

    dialog = ReviewDeferredDialog(db_connection)

    # Check that future dates are highlighted (background color set)
    # Find the row with future task
    for row in range(dialog.task_table.rowCount()):
        task = dialog.reviewable_tasks[row]
        start_date_item = dialog.task_table.item(row, 5)  # Start date column

        if task.start_date and task.start_date > date.today():
            # Should have yellow background
            assert start_date_item.background().color().name() == '#ffff00'  # Yellow
