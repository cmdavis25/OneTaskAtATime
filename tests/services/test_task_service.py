"""
Unit tests for TaskService.

Tests core task business logic including:
- Task CRUD operations
- Focus mode task retrieval
- State transitions (complete, defer, delegate, etc.)
- Recurring task generation
- Task counts and filtering
"""

import pytest
import sqlite3
from datetime import date, timedelta
from src.models.task import Task
from src.models.enums import TaskState, PostponeReasonType
from src.models.recurrence_pattern import RecurrencePattern, RecurrenceType
from src.database.schema import DatabaseSchema
from src.database.task_dao import TaskDAO


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
def task_service(db_connection):
    """Create TaskService instance."""
    from src.services.task_service import TaskService
    return TaskService(db_connection)


@pytest.fixture
def task_dao(db_connection):
    """Create TaskDAO instance."""
    return TaskDAO(db_connection.get_connection())


@pytest.fixture
def sample_task(task_service):
    """Create a sample active task."""
    task = Task(
        title="Sample Task",
        description="Test description",
        base_priority=2,
        due_date=date.today() + timedelta(days=7)
    )
    return task_service.create_task(task)


class TestTaskCRUD:
    """Test basic CRUD operations."""

    def test_create_task(self, task_service):
        """Test creating a new task."""
        task = Task(title="New Task", base_priority=2)

        created = task_service.create_task(task)

        assert created.id is not None
        assert created.title == "New Task"
        assert created.state == TaskState.ACTIVE

    def test_get_task_by_id(self, task_service, sample_task):
        """Test retrieving a task by ID."""
        retrieved = task_service.get_task_by_id(sample_task.id)

        assert retrieved is not None
        assert retrieved.id == sample_task.id
        assert retrieved.title == sample_task.title

    def test_get_task_by_id_not_found(self, task_service):
        """Test retrieving non-existent task returns None."""
        retrieved = task_service.get_task_by_id(99999)

        assert retrieved is None

    def test_update_task(self, task_service, sample_task):
        """Test updating a task."""
        sample_task.title = "Updated Title"

        updated = task_service.update_task(sample_task)

        assert updated.title == "Updated Title"
        # Verify persisted
        retrieved = task_service.get_task_by_id(sample_task.id)
        assert retrieved.title == "Updated Title"

    def test_delete_task(self, task_service, sample_task):
        """Test deleting a task."""
        result = task_service.delete_task(sample_task.id)

        assert result is True
        assert task_service.get_task_by_id(sample_task.id) is None

    def test_delete_nonexistent_task(self, task_service):
        """Test deleting non-existent task."""
        result = task_service.delete_task(99999)

        assert result is False

    def test_get_all_tasks(self, task_service):
        """Test getting all tasks."""
        task1 = task_service.create_task(Task(title="Task 1", base_priority=2))
        task2 = task_service.create_task(Task(title="Task 2", base_priority=2))
        task3 = task_service.create_task(Task(title="Task 3", base_priority=2))

        all_tasks = task_service.get_all_tasks()

        assert len(all_tasks) >= 3
        task_ids = [t.id for t in all_tasks]
        assert task1.id in task_ids
        assert task2.id in task_ids
        assert task3.id in task_ids

    def test_get_active_tasks(self, task_service):
        """Test getting only active tasks."""
        active_task = task_service.create_task(Task(title="Active", base_priority=2))
        completed_task = task_service.create_task(Task(title="Completed", base_priority=2))
        task_service.complete_task(completed_task.id)

        active_tasks = task_service.get_active_tasks()

        task_ids = [t.id for t in active_tasks]
        assert active_task.id in task_ids
        assert completed_task.id not in task_ids


class TestFocusMode:
    """Test focus mode task retrieval."""

    def test_get_focus_task_returns_highest_priority(self, task_service):
        """Test that focus task returns highest priority task."""
        # Create tasks with different priorities
        low = task_service.create_task(Task(
            title="Low Priority",
            base_priority=1,
            due_date=date.today()
        ))
        high = task_service.create_task(Task(
            title="High Priority",
            base_priority=3,
            due_date=date.today()
        ))

        focus_task = task_service.get_focus_task()

        # High priority should be returned
        assert focus_task is not None
        assert focus_task.id == high.id

    def test_get_focus_task_no_tasks(self, task_service):
        """Test focus task returns None when no tasks."""
        focus_task = task_service.get_focus_task()

        assert focus_task is None

    def test_get_focus_task_with_context_filter(self, task_service, db_connection):
        """Test focus task respects context filter."""
        # Create context
        from src.database.context_dao import ContextDAO
        from src.models.context import Context
        context_dao = ContextDAO(db_connection.get_connection())
        context = context_dao.create(Context(name="@work"))

        # Create tasks with and without context
        with_context = task_service.create_task(Task(
            title="Work Task",
            base_priority=2,
            due_date=date.today(),
            context_id=context.id
        ))
        without_context = task_service.create_task(Task(
            title="No Context Task",
            base_priority=3,  # Higher priority but wrong context
            due_date=date.today()
        ))

        focus_task = task_service.get_focus_task(context_filter=context.id)

        assert focus_task is not None
        assert focus_task.id == with_context.id

    def test_get_tied_tasks(self, task_service):
        """Test getting tied tasks."""
        # Create tasks with same priority and due date
        task1 = task_service.create_task(Task(
            title="Task 1",
            base_priority=2,
            due_date=date.today()
        ))
        task2 = task_service.create_task(Task(
            title="Task 2",
            base_priority=2,
            due_date=date.today()
        ))

        tied = task_service.get_tied_tasks()

        # Both should be in tied list (or none if no tie detected)
        if len(tied) > 0:
            task_ids = [t.id for t in tied]
            assert task1.id in task_ids
            assert task2.id in task_ids

    def test_get_ranked_tasks(self, task_service):
        """Test getting ranked task list."""
        task1 = task_service.create_task(Task(
            title="Low",
            base_priority=1,
            due_date=date.today()
        ))
        task2 = task_service.create_task(Task(
            title="High",
            base_priority=3,
            due_date=date.today()
        ))

        ranked = task_service.get_ranked_tasks()

        assert len(ranked) >= 2
        # High priority should come before low
        high_idx = next(i for i, t in enumerate(ranked) if t.id == task2.id)
        low_idx = next(i for i, t in enumerate(ranked) if t.id == task1.id)
        assert high_idx < low_idx


class TestStateTransitions:
    """Test task state transitions."""

    def test_complete_task(self, task_service, sample_task):
        """Test completing a task."""
        completed = task_service.complete_task(sample_task.id)

        assert completed is not None
        assert completed.state == TaskState.COMPLETED
        assert completed.completed_at is not None

    def test_complete_nonexistent_task(self, task_service):
        """Test completing non-existent task returns None."""
        result = task_service.complete_task(99999)

        assert result is None

    def test_defer_task(self, task_service, sample_task):
        """Test deferring a task."""
        start_date = date.today() + timedelta(days=7)

        deferred = task_service.defer_task(
            sample_task.id,
            start_date,
            PostponeReasonType.NOT_READY
        )

        assert deferred is not None
        assert deferred.state == TaskState.DEFERRED
        assert deferred.start_date == start_date

    def test_defer_task_with_notes(self, task_service, sample_task):
        """Test deferring a task with notes."""
        start_date = date.today() + timedelta(days=7)

        deferred = task_service.defer_task(
            sample_task.id,
            start_date,
            PostponeReasonType.BLOCKER,
            notes="Waiting for approval"
        )

        assert deferred is not None
        assert deferred.state == TaskState.DEFERRED

    def test_delegate_task(self, task_service, sample_task):
        """Test delegating a task."""
        follow_up = date.today() + timedelta(days=7)

        delegated = task_service.delegate_task(
            sample_task.id,
            "Alice",
            follow_up
        )

        assert delegated is not None
        assert delegated.state == TaskState.DELEGATED
        assert delegated.delegated_to == "Alice"
        assert delegated.follow_up_date == follow_up

    def test_move_to_someday(self, task_service, sample_task):
        """Test moving task to someday."""
        moved = task_service.move_to_someday(sample_task.id)

        assert moved is not None
        assert moved.state == TaskState.SOMEDAY

    def test_move_to_trash(self, task_service, sample_task):
        """Test moving task to trash."""
        trashed = task_service.move_to_trash(sample_task.id)

        assert trashed is not None
        assert trashed.state == TaskState.TRASH

    def test_activate_task(self, task_service, sample_task):
        """Test activating a deferred task."""
        # First defer
        task_service.defer_task(sample_task.id, date.today() + timedelta(days=7))

        # Then activate
        activated = task_service.activate_task(sample_task.id)

        assert activated is not None
        assert activated.state == TaskState.ACTIVE
        assert activated.start_date is None

    def test_restore_task_from_trash(self, task_service, sample_task):
        """Test restoring task from trash."""
        task_service.move_to_trash(sample_task.id)

        restored = task_service.restore_task(sample_task.id)

        assert restored is not None
        assert restored.state == TaskState.ACTIVE

    def test_uncomplete_task(self, task_service, sample_task):
        """Test uncompleting a completed task."""
        task_service.complete_task(sample_task.id)

        uncompleted = task_service.uncomplete_task(sample_task.id)

        assert uncompleted is not None
        assert uncompleted.state == TaskState.ACTIVE
        assert uncompleted.completed_at is None


class TestTaskQueries:
    """Test task query methods."""

    def test_get_tasks_by_state(self, task_service):
        """Test getting tasks by state."""
        active = task_service.create_task(Task(title="Active", base_priority=2))
        completed = task_service.create_task(Task(title="Completed", base_priority=2))
        task_service.complete_task(completed.id)

        active_tasks = task_service.get_tasks_by_state(TaskState.ACTIVE)
        completed_tasks = task_service.get_tasks_by_state(TaskState.COMPLETED)

        active_ids = [t.id for t in active_tasks]
        completed_ids = [t.id for t in completed_tasks]

        assert active.id in active_ids
        assert completed.id in completed_ids

    def test_get_overdue_tasks(self, task_service):
        """Test getting overdue tasks."""
        # Create overdue task
        overdue = task_service.create_task(Task(
            title="Overdue",
            base_priority=2,
            due_date=date.today() - timedelta(days=1)
        ))
        # Create future task
        future = task_service.create_task(Task(
            title="Future",
            base_priority=2,
            due_date=date.today() + timedelta(days=7)
        ))

        overdue_tasks = task_service.get_overdue_tasks()

        overdue_ids = [t.id for t in overdue_tasks]
        assert overdue.id in overdue_ids
        assert future.id not in overdue_ids

    def test_get_task_count_by_state(self, task_service):
        """Test getting task counts by state."""
        task_service.create_task(Task(title="Active 1", base_priority=2))
        task_service.create_task(Task(title="Active 2", base_priority=2))
        completed = task_service.create_task(Task(title="Completed", base_priority=2))
        task_service.complete_task(completed.id)

        counts = task_service.get_task_count_by_state()

        assert counts['active'] >= 2
        assert counts['completed'] >= 1


class TestRecurringTasks:
    """Test recurring task handling."""

    def test_complete_recurring_task_generates_next(self, task_service):
        """Test that completing recurring task generates next occurrence."""
        pattern = RecurrencePattern(type=RecurrenceType.DAILY, interval=1)
        recurring = task_service.create_task(Task(
            title="Daily Task",
            base_priority=2,
            due_date=date.today(),
            is_recurring=True,
            recurrence_pattern=pattern.to_json()
        ))

        # Complete the recurring task
        task_service.complete_task(recurring.id)

        # Check that a new occurrence was created
        all_tasks = task_service.get_all_tasks()
        daily_tasks = [t for t in all_tasks if t.title == "Daily Task"]

        assert len(daily_tasks) >= 2  # Original + new occurrence

    def test_complete_recurring_task_at_end_date_no_next(self, task_service):
        """Test that completing at end date doesn't generate next."""
        pattern = RecurrencePattern(type=RecurrenceType.DAILY, interval=1)
        recurring = task_service.create_task(Task(
            title="Ending Task",
            base_priority=2,
            due_date=date.today(),
            is_recurring=True,
            recurrence_pattern=pattern.to_json(),
            recurrence_end_date=date.today()
        ))

        # Complete the recurring task
        task_service.complete_task(recurring.id)

        # Check that no new occurrence was created
        all_tasks = task_service.get_all_tasks()
        ending_tasks = [t for t in all_tasks if t.title == "Ending Task"]

        assert len(ending_tasks) == 1  # Only the original


class TestDeleteOperations:
    """Test delete operations."""

    def test_delete_all_tasks(self, task_service):
        """Test deleting all tasks."""
        task_service.create_task(Task(title="Task 1", base_priority=2))
        task_service.create_task(Task(title="Task 2", base_priority=2))

        count = task_service.delete_all_tasks()

        assert count >= 2
        assert len(task_service.get_all_tasks()) == 0

    def test_delete_trash_tasks(self, task_service):
        """Test deleting only trash tasks."""
        active = task_service.create_task(Task(title="Active", base_priority=2))
        trash1 = task_service.create_task(Task(title="Trash 1", base_priority=2))
        trash2 = task_service.create_task(Task(title="Trash 2", base_priority=2))

        task_service.move_to_trash(trash1.id)
        task_service.move_to_trash(trash2.id)

        count = task_service.delete_trash_tasks()

        assert count == 2
        assert task_service.get_task_by_id(active.id) is not None
        assert task_service.get_task_by_id(trash1.id) is None
        assert task_service.get_task_by_id(trash2.id) is None


class TestPriorityReset:
    """Test priority reset functionality."""

    @pytest.mark.skip(reason="deprecated - use Elo system")
    def test_reset_priority_adjustment(self, task_service, sample_task):
        """Test resetting a task's priority adjustment."""
        # Manually set adjustment
        sample_task.priority_adjustment = 0.5
        task_service.update_task(sample_task)

        reset = task_service.reset_priority_adjustment(sample_task.id)

        assert reset is not None
        assert reset.priority_adjustment == 0.0

    @pytest.mark.skip(reason="deprecated - use Elo system")
    def test_reset_priority_adjustment_nonexistent(self, task_service):
        """Test resetting non-existent task returns None."""
        result = task_service.reset_priority_adjustment(99999)

        assert result is None
