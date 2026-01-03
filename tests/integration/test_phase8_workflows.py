"""
Integration tests for Phase 8 workflows.

Tests complete workflows combining multiple Phase 8 features.
"""

import pytest
import sqlite3
from datetime import datetime, date

from src.models.task import Task
from src.models.enums import TaskState, TaskEventType
from src.database.task_dao import TaskDAO
from src.database.task_history_dao import TaskHistoryDAO
from src.database.schema import DatabaseSchema
from src.services.task_history_service import TaskHistoryService
from src.services.undo_manager import UndoManager
from src.commands.complete_task_command import CompleteTaskCommand
from src.commands.change_priority_command import ChangePriorityCommand


@pytest.fixture
def db_connection():
    """Create in-memory database for testing."""
    conn = sqlite3.connect(":memory:")
    DatabaseSchema.initialize_database(conn)
    yield conn
    conn.close()


@pytest.fixture
def task_dao(db_connection):
    """Create TaskDAO instance."""
    return TaskDAO(db_connection)


@pytest.fixture
def history_dao(db_connection):
    """Create TaskHistoryDAO instance."""
    return TaskHistoryDAO(db_connection)


@pytest.fixture
def history_service(history_dao):
    """Create TaskHistoryService instance."""
    return TaskHistoryService(history_dao)


@pytest.fixture
def undo_manager():
    """Create UndoManager instance."""
    return UndoManager(max_stack_size=10)


def test_task_completion_with_undo(task_dao, undo_manager):
    """Test completing a task and undoing it."""
    # Create a task
    task = task_dao.create(Task(
        title="Test Task",
        description="Test",
        base_priority=2,
        state=TaskState.ACTIVE
    ))

    # Complete the task using command
    complete_cmd = CompleteTaskCommand(task_dao, task.id)
    assert undo_manager.execute_command(complete_cmd)

    # Verify completion
    completed_task = task_dao.get_by_id(task.id)
    assert completed_task.state == TaskState.COMPLETED
    assert completed_task.completed_at is not None

    # Undo
    assert undo_manager.undo()

    # Verify restoration
    restored_task = task_dao.get_by_id(task.id)
    assert restored_task.state == TaskState.ACTIVE
    assert restored_task.completed_at is None


def test_task_history_records_all_changes(task_dao, history_service):
    """Test that all task changes are recorded in history."""
    # Create task
    task = task_dao.create(Task(
        title="Test Task",
        description="Test",
        base_priority=2,
        state=TaskState.ACTIVE
    ))

    # Record creation
    history_service.record_task_created(task)

    # Change priority
    old_task = task_dao.get_by_id(task.id)
    task.base_priority = 3
    task_dao.update(task)
    history_service.record_priority_change(task, old_priority=2, new_priority=3)

    # Defer task
    task.state = TaskState.DEFERRED
    task.start_date = date.today()
    task_dao.update(task)
    history_service.record_state_change(task, TaskState.ACTIVE, TaskState.DEFERRED)

    # Complete task
    task.state = TaskState.COMPLETED
    task.completed_at = datetime.now()
    task_dao.update(task)
    history_service.record_state_change(task, TaskState.DEFERRED, TaskState.COMPLETED)

    # Verify all events recorded
    timeline = history_service.get_timeline(task.id)
    assert len(timeline) >= 4

    event_types = [event.event_type for event in timeline]
    assert TaskEventType.CREATED in event_types
    assert TaskEventType.PRIORITY_CHANGED in event_types
    assert TaskEventType.DEFERRED in event_types
    assert TaskEventType.COMPLETED in event_types


def test_multiple_undo_redo_sequence(task_dao, undo_manager):
    """Test multiple undo/redo operations in sequence."""
    # Create task
    task = task_dao.create(Task(
        title="Test Task",
        base_priority=1,
        state=TaskState.ACTIVE
    ))

    # Perform multiple operations
    # 1. Change priority to Medium
    cmd1 = ChangePriorityCommand(task_dao, task.id, new_priority=2)
    undo_manager.execute_command(cmd1)

    # 2. Change priority to High
    cmd2 = ChangePriorityCommand(task_dao, task.id, new_priority=3)
    undo_manager.execute_command(cmd2)

    # Verify current state is High
    current_task = task_dao.get_by_id(task.id)
    assert current_task.base_priority == 3

    # Undo twice
    undo_manager.undo()  # Back to Medium
    undo_manager.undo()  # Back to Low

    # Verify back to Low
    restored_task = task_dao.get_by_id(task.id)
    assert restored_task.base_priority == 1

    # Redo twice
    undo_manager.redo()  # Forward to Medium
    undo_manager.redo()  # Forward to High

    # Verify back to High
    final_task = task_dao.get_by_id(task.id)
    assert final_task.base_priority == 3


def test_history_and_undo_integration(task_dao, history_service, undo_manager):
    """Test that history and undo work together."""
    # Create task
    task = task_dao.create(Task(
        title="Integration Test Task",
        base_priority=2,
        state=TaskState.ACTIVE
    ))

    # Record creation
    history_service.record_task_created(task)

    # Complete task with command
    complete_cmd = CompleteTaskCommand(task_dao, task.id)
    undo_manager.execute_command(complete_cmd)

    # Record completion in history
    completed_task = task_dao.get_by_id(task.id)
    history_service.record_state_change(
        completed_task,
        TaskState.ACTIVE,
        TaskState.COMPLETED
    )

    # Verify history shows completion
    timeline = history_service.get_timeline(task.id)
    assert any(e.event_type == TaskEventType.COMPLETED for e in timeline)

    # Undo completion
    undo_manager.undo()

    # Could record restoration in history if desired
    restored_task = task_dao.get_by_id(task.id)
    history_service.record_state_change(
        restored_task,
        TaskState.COMPLETED,
        TaskState.ACTIVE
    )

    # Verify history shows both completion and restoration
    final_timeline = history_service.get_timeline(task.id)
    assert len([e for e in final_timeline if e.event_type == TaskEventType.COMPLETED]) >= 1
    assert any(e.event_type == TaskEventType.ACTIVATED for e in final_timeline)


def test_undo_stack_size_limit(task_dao, undo_manager):
    """Test that undo stack respects size limit."""
    # Create task
    task = task_dao.create(Task(
        title="Test Task",
        base_priority=1,
        state=TaskState.ACTIVE
    ))

    # Perform more operations than stack size (10)
    for i in range(15):
        priority = (i % 3) + 1  # Cycle through 1, 2, 3
        cmd = ChangePriorityCommand(task_dao, task.id, new_priority=priority)
        undo_manager.execute_command(cmd)

    # Verify stack size is limited to 10
    assert undo_manager.get_undo_count() == 10
    assert undo_manager.get_redo_count() == 0


def test_formatted_history_messages(history_service, task_dao):
    """Test that history events have human-readable messages."""
    # Create task
    task = task_dao.create(Task(
        title="Readable Test",
        base_priority=2,
        state=TaskState.ACTIVE
    ))

    # Record various events
    create_event = history_service.record_task_created(task)
    priority_event = history_service.record_priority_change(task, 2, 3)
    completion_event = history_service.record_state_change(
        task,
        TaskState.ACTIVE,
        TaskState.COMPLETED
    )

    # Verify messages are readable
    create_msg = history_service.get_formatted_summary(create_event)
    assert "created" in create_msg.lower()

    priority_msg = history_service.get_formatted_summary(priority_event)
    assert "priority" in priority_msg.lower()
    assert "medium" in priority_msg.lower() or "high" in priority_msg.lower()

    complete_msg = history_service.get_formatted_summary(completion_event)
    assert "completed" in complete_msg.lower()
