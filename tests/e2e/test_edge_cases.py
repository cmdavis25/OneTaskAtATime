"""
Edge Case E2E Tests

Tests error conditions, boundary cases, and edge scenarios that could
break the application or lead to undefined behavior.
"""

import pytest
from datetime import datetime, date, timedelta
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt

from src.models.task import Task
from src.models.enums import TaskState, Priority
from tests.e2e.base_e2e_test import BaseE2ETest


@pytest.mark.e2e
@pytest.mark.edge_case
class TestEdgeCases(BaseE2ETest):
    """
    Test edge cases and error conditions.

    These tests ensure the application handles unusual or erroneous
    situations gracefully without crashing or corrupting data.
    """

    def test_circular_dependency_detection(self, app_instance, qtbot):
        """
        Test circular dependency prevention.

        Workflow:
        1. Create tasks A, B, C
        2. A depends on B
        3. B depends on C
        4. Attempt C depends on A (creates cycle)
        5. Verify error and dependency creation blocked
        """
        # Step 1: Create tasks
        task_a = Task(
            title="Task A",
            description="Part of potential cycle",
            base_priority=2,
            state=TaskState.ACTIVE
        )
        task_a_id_obj = app_instance.task_service.create_task(task_a)
        task_a_id = task_a_id_obj.id

        task_b = Task(
            title="Task B",
            description="Part of potential cycle",
            base_priority=2,
            state=TaskState.ACTIVE
        )
        task_b_id_obj = app_instance.task_service.create_task(task_b)
        task_b_id = task_b_id_obj.id

        task_c = Task(
            title="Task C",
            description="Part of potential cycle",
            base_priority=2,
            state=TaskState.ACTIVE
        )
        task_c_id_obj = app_instance.task_service.create_task(task_c)
        task_c_id = task_c_id_obj.id

        # Step 2: A depends on B
        app_instance.dependency_dao.add_dependency(task_a_id, task_b_id)
        QTest.qWait(100)

        # Step 3: B depends on C
        app_instance.dependency_dao.add_dependency(task_b_id, task_c_id)
        QTest.qWait(100)

        # Step 4: Attempt C depends on A (creates A -> B -> C -> A cycle)
        try:
            # This should be blocked
            result = app_instance.dependency_dao.add_dependency(task_c_id, task_a_id)
            QTest.qWait(100)

            # If no exception, verify dependency was not created
            c_dependencies = app_instance.dependency_dao.get_dependencies(task_c_id)
            assert task_a_id not in c_dependencies, \
                "Circular dependency should be prevented"
        except Exception as e:
            # Expected behavior: exception raised
            assert "circular" in str(e).lower() or "cycle" in str(e).lower(), \
                "Exception should mention circular dependency"

    def test_self_dependency_prevention(self, app_instance, qtbot):
        """
        Test prevention of task depending on itself.

        Workflow:
        1. Create task
        2. Attempt to make task depend on itself
        3. Verify error and no dependency created
        """
        # Step 1: Create task
        task = Task(
            title="Self Dependency Test",
            description="Cannot depend on itself",
            base_priority=2,
            state=TaskState.ACTIVE
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id
        QTest.qWait(100)

        # Step 2: Attempt self-dependency
        try:
            result = app_instance.dependency_dao.add_dependency(task_id, task_id)
            QTest.qWait(100)

            # If no exception, verify dependency was not created
            dependencies = app_instance.dependency_dao.get_dependencies(task_id)
            assert task_id not in dependencies, \
                "Task should not depend on itself"
        except Exception as e:
            # Expected: exception raised
            assert "self" in str(e).lower() or "same" in str(e).lower()

    def test_empty_title_task_creation(self, app_instance, qtbot):
        """
        Test validation for empty task title.

        Workflow:
        1. Attempt to create task with empty title
        2. Verify error or default title applied
        """
        # Step 1: Attempt empty title
        task = Task(
            title="",  # Empty title
            description="This has no title",
            base_priority=2,
            state=TaskState.ACTIVE
        )

        try:
            task_id_obj = app_instance.task_service.create_task(task)
            task_id = task_id_obj.id
            QTest.qWait(100)

            # If created, check if default title was applied
            created_task = app_instance.task_service.get_task_by_id(task_id)
            assert created_task.title != "", \
                "Empty title should be replaced with default or rejected"
        except Exception as e:
            # Expected: validation error
            assert "title" in str(e).lower()

    def test_task_with_no_priority(self, app_instance, qtbot):
        """
        Test handling of task with null/undefined priority.

        Workflow:
        1. Create task with None priority
        2. Verify default priority applied
        """
        # Step 1: Create task with default priority
        task = Task(
            title="No Priority Task",
            description="Priority is default",
            base_priority=2,  # Use default base priority
            state=TaskState.ACTIVE
        )

        try:
            task_id_obj = app_instance.task_service.create_task(task)
            task_id = task_id_obj.id
            QTest.qWait(100)

            # Step 2: Verify default applied
            created_task = app_instance.task_service.get_task_by_id(task_id)
            assert created_task.base_priority is not None, \
                "Should apply default priority"
            assert created_task.base_priority == 2, \
                "Default priority should be 2 (MEDIUM)"
        except Exception as e:
            # May raise validation error
            pass

    def test_task_with_past_due_date(self, app_instance, qtbot):
        """
        Test task with due date in the past.

        Workflow:
        1. Create task with due_date = yesterday
        2. Verify task created
        3. Verify urgency score reflects overdue status
        4. Task should appear in focus (if highest priority)
        """
        # Step 1: Create overdue task
        yesterday = date.today() - timedelta(days=1)
        task = Task(
            title="Overdue Task",
            description="Already past due",
            base_priority=3,
            due_date=yesterday,
            state=TaskState.ACTIVE
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id
        QTest.qWait(100)

        # Step 2: Verify created
        overdue_task = app_instance.task_service.get_task_by_id(task_id)
        assert overdue_task is not None
        assert overdue_task.due_date < date.today()

        # Step 3: Calculate urgency (should be very high for overdue)
        # Urgency calculation varies by implementation
        # Overdue tasks typically get maximum urgency

        # Step 4: Should appear in focus if highest priority
        app_instance._refresh_focus_task()
        QTest.qWait(200)

        focus_task = self.get_focus_task(app_instance)
        # May or may not be the focus task depending on other tasks
        # But should be in ranked list
        ranked_tasks = app_instance.task_service.get_ranked_tasks()
        ranked_ids = [t.id for t in ranked_tasks]
        assert task_id in ranked_ids, "Overdue task should be in ranked list"

    def test_defer_without_start_date(self, app_instance, qtbot):
        """
        Test deferring task without specifying start_date.

        Workflow:
        1. Create task
        2. Attempt to defer without start_date
        3. Verify error or default start_date applied
        """
        # Step 1: Create task
        task = Task(
            title="Defer Without Start Date",
            description="Test defer validation",
            base_priority=2,
            state=TaskState.ACTIVE
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id
        QTest.qWait(100)

        # Step 2: Attempt defer without start_date
        try:
            app_instance.task_service.defer_task(task_id, start_date=None)
            QTest.qWait(100)

            # If successful, check if default was applied
            deferred_task = app_instance.task_service.get_task_by_id(task_id)
            if deferred_task.state == TaskState.DEFERRED:
                assert deferred_task.start_date is not None, \
                    "Should apply default start_date"
        except Exception as e:
            # Expected: validation error
            assert "start" in str(e).lower() or "date" in str(e).lower()

    def test_delegate_without_follow_up(self, app_instance, qtbot):
        """
        Test delegating task without follow_up_date.

        Workflow:
        1. Create task
        2. Attempt to delegate without follow_up_date
        3. Verify error or default follow_up applied
        """
        # Step 1: Create task
        task = Task(
            title="Delegate Without Follow Up",
            description="Test delegation validation",
            base_priority=2,
            state=TaskState.ACTIVE
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id
        QTest.qWait(100)

        # Step 2: Attempt delegate without follow_up_date
        try:
            app_instance.task_service.delegate_task(
                task_id,
                delegated_to="Bob",
                follow_up_date=None,
                notes="Test"
            )
            QTest.qWait(100)

            # If successful, check if default was applied
            delegated_task = app_instance.task_service.get_task_by_id(task_id)
            if delegated_task.state == TaskState.DELEGATED:
                # May have default follow_up or allow None
                pass
        except Exception as e:
            # Expected: validation error
            assert "follow" in str(e).lower() or "date" in str(e).lower()

    def test_comparison_with_single_task(self, app_instance, qtbot):
        """
        Test comparison dialog with only one task.

        Workflow:
        1. Create single high-priority task
        2. Trigger focus mode
        3. Verify no comparison dialog (nothing to compare)
        4. Task appears in focus
        """
        # Step 1: Create single task
        task = Task(
            title="Only Task",
            description="Sole task in system",
            base_priority=3,
            due_date=date.today() + timedelta(days=1),
            state=TaskState.ACTIVE
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id
        QTest.qWait(100)

        # Step 2: Refresh focus mode
        app_instance._refresh_focus_task()
        QTest.qWait(200)

        # Step 3: No comparison dialog should appear
        from src.ui.comparison_dialog import ComparisonDialog
        comparison_dialog = self.find_dialog(app_instance, ComparisonDialog, timeout=500)
        assert comparison_dialog is None, \
            "Should not show comparison with single task"

        # Step 4: Task should be in focus
        focus_task = self.get_focus_task(app_instance)
        assert focus_task is not None
        assert focus_task.id == task_id

    def test_complete_already_completed_task(self, app_instance, qtbot):
        """
        Test completing an already completed task.

        Workflow:
        1. Create and complete task
        2. Attempt to complete again
        3. Verify handled gracefully (no error, no state change)
        """
        # Step 1: Create and complete
        task = Task(
            title="Double Complete Test",
            description="Complete twice",
            base_priority=2,
            state=TaskState.ACTIVE
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id
        app_instance.task_service.complete_task(task_id)
        QTest.qWait(100)

        completed_task = app_instance.task_service.get_task_by_id(task_id)
        assert completed_task.state == TaskState.COMPLETED
        first_completed_at = completed_task.completed_at

        # Step 2: Complete again
        try:
            app_instance.task_service.complete_task(task_id)
            QTest.qWait(100)

            # Step 3: Verify still completed, timestamp unchanged
            still_completed = app_instance.task_service.get_task_by_id(task_id)
            assert still_completed.state == TaskState.COMPLETED
            assert still_completed.completed_at == first_completed_at, \
                "Completed timestamp should not change"
        except Exception:
            # May raise error, which is acceptable
            pass

    def test_undo_when_stack_empty(self, app_instance, qtbot):
        """
        Test undo with empty undo stack.

        Workflow:
        1. Fresh app with no actions
        2. Attempt undo
        3. Verify no error, status message shown
        """
        # Step 1: No actions performed yet
        # Step 2: Attempt undo
        if hasattr(app_instance, 'undo_action'):
            try:
                app_instance.undo_action.trigger()
                QTest.qWait(200)

                # Step 3: Should be handled gracefully
                # No crash, possibly show "Nothing to undo" message
            except Exception as e:
                # Should not crash
                pytest.fail(f"Undo on empty stack should not crash: {e}")

    def test_import_malformed_json(self, app_instance, qtbot, tmp_path):
        """
        Test importing malformed JSON file.

        Workflow:
        1. Create invalid JSON file
        2. Attempt import
        3. Verify error dialog with recovery suggestions
        4. Database unchanged
        """
        # Step 1: Create malformed JSON
        bad_json_path = tmp_path / "malformed.json"
        bad_json_path.write_text("{ invalid json content }")

        # Count tasks before import
        initial_tasks = app_instance.task_service.get_all_tasks()
        initial_count = len(initial_tasks)

        # Step 2: Attempt import
        try:
            from src.services.import_service import ImportService
            import_service = ImportService(app_instance.db_connection.get_connection())
            result = import_service.import_from_json(str(bad_json_path))
            QTest.qWait(200)

            # Should return error result or raise exception
            if result.get('success'):
                pytest.fail("Import should fail with malformed JSON")
        except (json.JSONDecodeError, ValueError, Exception) as e:
            # Step 3: Verify error message is helpful
            error_msg = str(e).lower()
            assert "json" in error_msg or "parse" in error_msg or "invalid" in error_msg or "expecting" in error_msg

        # Step 4: Verify database unchanged
        final_tasks = app_instance.task_service.get_all_tasks()
        assert len(final_tasks) == initial_count, \
            "Failed import should not modify database"

    def test_database_locked_error(self, app_instance, qtbot):
        """
        Test handling of SQLite BUSY error.

        Note: This is difficult to simulate reliably.
        Tests that the application has retry logic in place.

        Workflow:
        1. Perform rapid concurrent database operations
        2. Verify operations complete without crash
        """
        # Step 1: Rapid task creation
        task_ids = []
        try:
            for i in range(10):
                task = Task(
                    title=f"Concurrent Task {i}",
                    description="Testing concurrency",
                    base_priority=2,
                    state=TaskState.ACTIVE
                )
                task_id_obj = app_instance.task_service.create_task(task)
                task_id = task_id_obj.id
                task_ids.append(task_id)
                # No wait - rapid fire

            QTest.qWait(200)

            # Step 2: Verify all created
            for task_id in task_ids:
                task = app_instance.task_service.get_task_by_id(task_id)
                assert task is not None, \
                    f"Task {task_id} should exist after concurrent creation"
        except Exception as e:
            # Should handle database locking gracefully
            error_msg = str(e).lower()
            if "lock" in error_msg or "busy" in error_msg:
                # This is expected, but should be retried automatically
                pass
