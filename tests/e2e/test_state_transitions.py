"""
State Transition E2E Tests

Tests all valid task state transitions in OneTaskAtATime.
Verifies that state changes work correctly with proper side effects
(history logging, notification generation, Elo updates, etc.).
"""

import pytest
from datetime import datetime, date, timedelta
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest

from src.models.task import Task
from src.models.enums import TaskState, Priority
from tests.e2e.base_e2e_test import BaseE2ETest


@pytest.mark.e2e
@pytest.mark.integration
class TestStateTransitions(BaseE2ETest):
    """
    Test all valid task state transitions.

    State transition matrix:
    - ACTIVE → COMPLETED
    - ACTIVE → DEFERRED
    - ACTIVE → DELEGATED
    - ACTIVE → SOMEDAY
    - ACTIVE → TRASH
    - DEFERRED → ACTIVE (resurfacing)
    - DELEGATED → ACTIVE (follow-up)
    - SOMEDAY → ACTIVE (review)
    - TRASH → ACTIVE (restore)
    - COMPLETED → ACTIVE (undo/restore)
    """

    def test_transition_active_to_completed(self, app_instance, qtbot):
        """
        Test ACTIVE → COMPLETED transition.

        Verifies:
        - State changes to COMPLETED
        - completed_at timestamp set
        - History event logged
        - Task removed from focus queue
        """
        # Create active task
        task = Task(
            title="Active to Completed",
            description="Test completion",
            base_priority=2,
            due_date=date.today() + timedelta(days=1),
            state=TaskState.ACTIVE
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id

        # Complete the task
        app_instance.task_service.complete_task(task_id)
        QTest.qWait(100)

        # Verify state transition
        completed_task = app_instance.task_service.get_task_by_id(task_id)
        assert completed_task.state == TaskState.COMPLETED
        assert completed_task.completed_at is not None

        # Verify history logged
        events = app_instance.task_history_service.get_timeline(task_id)
        assert len(events) > 0, "Should have history events"

        # Verify not in active task list
        active_tasks = app_instance.task_service.get_tasks_by_state(TaskState.ACTIVE)
        active_ids = [t.id for t in active_tasks]
        assert task_id not in active_ids

    def test_transition_active_to_deferred(self, app_instance, qtbot):
        """
        Test ACTIVE → DEFERRED transition.

        Verifies:
        - State changes to DEFERRED
        - start_date is set
        - History event logged
        - Task removed from focus queue
        """
        # Create active task
        task = Task(
            title="Active to Deferred",
            description="Will defer this",
            base_priority=3,
            due_date=date.today() + timedelta(days=5),
            state=TaskState.ACTIVE
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id

        # Defer the task
        start_date = date.today() + timedelta(days=2)
        app_instance.task_service.defer_task(task_id, start_date=start_date)
        QTest.qWait(100)

        # Verify state transition
        deferred_task = app_instance.task_service.get_task_by_id(task_id)
        assert deferred_task.state == TaskState.DEFERRED
        assert deferred_task.start_date is not None

        # Verify history logged
        events = app_instance.task_history_service.get_timeline(task_id)
        assert len(events) > 0

        # Verify not in active queue
        active_tasks = app_instance.task_service.get_tasks_by_state(TaskState.ACTIVE)
        active_ids = [t.id for t in active_tasks]
        assert task_id not in active_ids

    def test_transition_active_to_delegated(self, app_instance, qtbot):
        """
        Test ACTIVE → DELEGATED transition.

        Verifies:
        - State changes to DELEGATED
        - delegated_to field set
        - follow_up_date set
        - History event logged
        """
        # Create active task
        task = Task(
            title="Active to Delegated",
            description="Will delegate",
            base_priority=2,
            due_date=date.today() + timedelta(days=10),
            state=TaskState.ACTIVE
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id

        # Delegate the task
        follow_up = date.today() + timedelta(days=5)
        app_instance.task_service.delegate_task(
            task_id,
            delegated_to="Alice",
            follow_up_date=follow_up,
            notes="Please handle this"
        )
        QTest.qWait(100)

        # Verify state transition
        delegated_task = app_instance.task_service.get_task_by_id(task_id)
        assert delegated_task.state == TaskState.DELEGATED
        assert delegated_task.delegated_to == "Alice"
        assert delegated_task.follow_up_date is not None

        # Verify history logged
        events = app_instance.task_history_service.get_timeline(task_id)
        assert len(events) > 0

    def test_transition_active_to_someday(self, app_instance, qtbot):
        """
        Test ACTIVE → SOMEDAY transition.

        Verifies:
        - State changes to SOMEDAY
        - History event logged
        - Task removed from active queue
        """
        # Create active task
        task = Task(
            title="Active to Someday",
            description="Move to someday/maybe",
            base_priority=1,
            state=TaskState.ACTIVE
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id

        # Move to someday
        app_instance.task_service.move_to_someday(task_id)
        QTest.qWait(100)

        # Verify state transition
        someday_task = app_instance.task_service.get_task_by_id(task_id)
        assert someday_task.state == TaskState.SOMEDAY

        # Verify history logged
        events = app_instance.task_history_service.get_timeline(task_id)
        assert len(events) > 0

        # Verify not in active queue
        active_tasks = app_instance.task_service.get_tasks_by_state(TaskState.ACTIVE)
        active_ids = [t.id for t in active_tasks]
        assert task_id not in active_ids

    def test_transition_active_to_trash(self, app_instance, qtbot):
        """
        Test ACTIVE → TRASH transition.

        Verifies:
        - State changes to TRASH
        - History event logged
        - Task removed from all active views
        """
        # Create active task
        task = Task(
            title="Active to Trash",
            description="Will delete",
            base_priority=1,
            state=TaskState.ACTIVE
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id

        # Move to trash
        app_instance.task_service.move_to_trash(task_id)
        QTest.qWait(100)

        # Verify state transition
        trashed_task = app_instance.task_service.get_task_by_id(task_id)
        assert trashed_task is not None, "Task should exist in trash, not be deleted"
        assert trashed_task.state == TaskState.TRASH

        # Verify history logged
        events = app_instance.task_history_service.get_timeline(task_id)
        assert len(events) > 0

        # Verify not in active queue
        active_tasks = app_instance.task_service.get_tasks_by_state(TaskState.ACTIVE)
        active_ids = [t.id for t in active_tasks]
        assert task_id not in active_ids

    def test_transition_deferred_to_active(self, app_instance, qtbot):
        """
        Test DEFERRED → ACTIVE transition (resurfacing).

        Verifies:
        - State changes to ACTIVE
        - start_date cleared or left as-is
        - History event logged
        - Task appears in focus queue
        """
        # Create deferred task
        task = Task(
            title="Deferred to Active",
            description="Will reactivate",
            base_priority=2,
            due_date=date.today() + timedelta(days=5),
            start_date=date.today() + timedelta(days=2),
            state=TaskState.DEFERRED
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id

        # Activate the task (simulating resurfacing)
        app_instance.task_service.activate_task(task_id)
        QTest.qWait(100)

        # Verify state transition
        active_task = app_instance.task_service.get_task_by_id(task_id)
        assert active_task.state == TaskState.ACTIVE

        # Verify history logged
        events = app_instance.task_history_service.get_timeline(task_id)
        assert len(events) > 0

        # Verify in active queue
        active_tasks = app_instance.task_service.get_tasks_by_state(TaskState.ACTIVE)
        active_ids = [t.id for t in active_tasks]
        assert task_id in active_ids

    def test_transition_delegated_to_active(self, app_instance, qtbot):
        """
        Test DELEGATED → ACTIVE transition (follow-up).

        Verifies:
        - State changes to ACTIVE
        - History event logged
        - Task appears in focus queue
        """
        # Create delegated task
        task = Task(
            title="Delegated to Active",
            description="Follow up time",
            base_priority=3,
            due_date=date.today() + timedelta(days=10),
            delegated_to="Bob",
            follow_up_date=date.today(),
            state=TaskState.DELEGATED
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id

        # Activate the task (follow-up)
        app_instance.task_service.activate_task(task_id)
        QTest.qWait(100)

        # Verify state transition
        active_task = app_instance.task_service.get_task_by_id(task_id)
        assert active_task.state == TaskState.ACTIVE

        # Verify history logged
        events = app_instance.task_history_service.get_timeline(task_id)
        assert len(events) > 0

        # Verify in active queue
        active_tasks = app_instance.task_service.get_tasks_by_state(TaskState.ACTIVE)
        active_ids = [t.id for t in active_tasks]
        assert task_id in active_ids

    def test_transition_someday_to_active(self, app_instance, qtbot):
        """
        Test SOMEDAY → ACTIVE transition (review and activate).

        Verifies:
        - State changes to ACTIVE
        - History event logged
        - Task appears in focus queue
        """
        # Create someday task
        task = Task(
            title="Someday to Active",
            description="Decided to do this",
            base_priority=1,
            state=TaskState.SOMEDAY
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id

        # Activate the task
        app_instance.task_service.activate_task(task_id)
        QTest.qWait(100)

        # Verify state transition
        active_task = app_instance.task_service.get_task_by_id(task_id)
        assert active_task.state == TaskState.ACTIVE

        # Verify history logged
        events = app_instance.task_history_service.get_timeline(task_id)
        assert len(events) > 0

        # Verify in active queue
        active_tasks = app_instance.task_service.get_tasks_by_state(TaskState.ACTIVE)
        active_ids = [t.id for t in active_tasks]
        assert task_id in active_ids

    def test_transition_trash_to_active(self, app_instance, qtbot):
        """
        Test TRASH → ACTIVE transition (restore).

        Verifies:
        - State changes to ACTIVE
        - History event logged
        - Task appears in focus queue
        """
        # Create trashed task
        task = Task(
            title="Trash to Active",
            description="Restore this task",
            base_priority=2,
            state=TaskState.TRASH
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id

        # Restore the task
        app_instance.task_service.restore_task(task_id)
        QTest.qWait(100)

        # Verify state transition
        active_task = app_instance.task_service.get_task_by_id(task_id)
        assert active_task.state == TaskState.ACTIVE

        # Verify history logged
        events = app_instance.task_history_service.get_timeline(task_id)
        assert len(events) > 0

        # Verify in active queue
        active_tasks = app_instance.task_service.get_tasks_by_state(TaskState.ACTIVE)
        active_ids = [t.id for t in active_tasks]
        assert task_id in active_ids

    def test_transition_completed_to_active(self, app_instance, qtbot):
        """
        Test COMPLETED → ACTIVE transition (undo/restore).

        Verifies:
        - State changes to ACTIVE
        - completed_at timestamp cleared
        - History event logged
        - Task appears in focus queue
        """
        # Create and complete task
        task = Task(
            title="Completed to Active",
            description="Undo completion",
            base_priority=2,
            due_date=date.today() + timedelta(days=1),
            state=TaskState.ACTIVE
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id

        # Complete it
        app_instance.task_service.complete_task(task_id)
        QTest.qWait(100)

        # Verify completed
        completed_task = app_instance.task_service.get_task_by_id(task_id)
        assert completed_task.state == TaskState.COMPLETED

        # Restore to active
        app_instance.task_service.uncomplete_task(task_id)
        QTest.qWait(100)

        # Verify state transition
        active_task = app_instance.task_service.get_task_by_id(task_id)
        assert active_task.state == TaskState.ACTIVE
        assert active_task.completed_at is None

        # Verify history logged
        events = app_instance.task_history_service.get_timeline(task_id)
        assert len(events) >= 2  # Should have both complete and uncomplete events

        # Verify in active queue
        active_tasks = app_instance.task_service.get_tasks_by_state(TaskState.ACTIVE)
        active_ids = [t.id for t in active_tasks]
        assert task_id in active_ids

    def test_multiple_state_transitions(self, app_instance, qtbot):
        """
        Test multiple state transitions on same task.

        Workflow:
        1. Create ACTIVE task
        2. Defer it (ACTIVE → DEFERRED)
        3. Activate it (DEFERRED → ACTIVE)
        4. Move to Someday (ACTIVE → SOMEDAY)
        5. Activate again (SOMEDAY → ACTIVE)
        6. Complete it (ACTIVE → COMPLETED)
        7. Verify full history chain
        """
        # Step 1: Create active task
        task = Task(
            title="Multiple Transitions",
            description="Will go through many states",
            base_priority=2,
            due_date=date.today() + timedelta(days=10),
            state=TaskState.ACTIVE
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id
        QTest.qWait(50)

        # Step 2: Defer
        app_instance.task_service.defer_task(task_id, start_date=date.today() + timedelta(days=2))
        QTest.qWait(50)
        assert app_instance.task_service.get_task_by_id(task_id).state == TaskState.DEFERRED

        # Step 3: Activate
        app_instance.task_service.activate_task(task_id)
        QTest.qWait(50)
        assert app_instance.task_service.get_task_by_id(task_id).state == TaskState.ACTIVE

        # Step 4: Move to Someday
        app_instance.task_service.move_to_someday(task_id)
        QTest.qWait(50)
        assert app_instance.task_service.get_task_by_id(task_id).state == TaskState.SOMEDAY

        # Step 5: Activate again
        app_instance.task_service.activate_task(task_id)
        QTest.qWait(50)
        assert app_instance.task_service.get_task_by_id(task_id).state == TaskState.ACTIVE

        # Step 6: Complete
        app_instance.task_service.complete_task(task_id)
        QTest.qWait(50)
        assert app_instance.task_service.get_task_by_id(task_id).state == TaskState.COMPLETED

        # Step 7: Verify history chain
        events = app_instance.task_history_service.get_timeline(task_id)
        assert len(events) >= 6, f"Should have at least 6 events, got {len(events)}"

        # Verify chronological order
        for i in range(len(events) - 1):
            assert events[i].event_timestamp <= events[i+1].event_timestamp, "Events should be chronological"

    def test_state_transition_with_dependencies(self, app_instance, qtbot):
        """
        Test state transitions preserve dependencies.

        Workflow:
        1. Create task A and B where B depends on A
        2. Complete A
        3. Defer B
        4. Reactivate B
        5. Verify dependency still exists
        6. Complete B
        """
        # Create task A
        task_a = Task(
            title="Task A - Prerequisite",
            description="Blocker task",
            base_priority=3,
            due_date=date.today() + timedelta(days=1),
            state=TaskState.ACTIVE
        )
        task_a_id_obj = app_instance.task_service.create_task(task_a)
        task_a_id = task_a_id_obj.id

        # Create task B
        task_b = Task(
            title="Task B - Dependent",
            description="Depends on A",
            base_priority=3,
            due_date=date.today() + timedelta(days=2),
            state=TaskState.ACTIVE
        )
        task_b_id_obj = app_instance.task_service.create_task(task_b)
        task_b_id = task_b_id_obj.id

        # Add dependency
        app_instance.dependency_dao.add_dependency(task_b_id, task_a_id)
        QTest.qWait(50)

        # Complete A
        app_instance.task_service.complete_task(task_a_id)
        QTest.qWait(50)

        # Defer B
        app_instance.task_service.defer_task(task_b_id, start_date=date.today() + timedelta(days=1))
        QTest.qWait(50)
        assert app_instance.task_service.get_task_by_id(task_b_id).state == TaskState.DEFERRED

        # Reactivate B
        app_instance.task_service.activate_task(task_b_id)
        QTest.qWait(50)
        assert app_instance.task_service.get_task_by_id(task_b_id).state == TaskState.ACTIVE

        # Verify dependency still exists
        dependencies = app_instance.dependency_dao.get_dependencies(task_b_id)
        blocking_task_ids = [dep.blocking_task_id for dep in dependencies]
        assert task_a_id in blocking_task_ids, "Dependency should persist across state changes"

        # Complete B
        app_instance.task_service.complete_task(task_b_id)
        QTest.qWait(50)
        assert app_instance.task_service.get_task_by_id(task_b_id).state == TaskState.COMPLETED
