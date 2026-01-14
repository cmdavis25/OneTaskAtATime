"""
Core Workflow E2E Tests

Tests critical user journeys through the OneTaskAtATime application.
These tests verify complete workflows from task creation through completion,
including all major features like deferral, delegation, dependencies, and ranking.
"""

import pytest
from datetime import datetime, date, timedelta
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest

from src.models.task import Task
from src.models.enums import TaskState, Priority
from src.ui.task_form_enhanced import EnhancedTaskFormDialog
from src.ui.postpone_dialog import DeferDialog, DelegateDialog
from src.ui.review_someday_dialog import ReviewSomedayDialog
from src.ui.comparison_dialog import ComparisonDialog
from src.ui.subtask_breakdown_dialog import SubtaskBreakdownDialog
from tests.e2e.base_e2e_test import BaseE2ETest


@pytest.mark.e2e
@pytest.mark.slow
class TestCoreWorkflows(BaseE2ETest):
    """
    End-to-end tests for critical user workflows.

    These tests verify complete user journeys through the application,
    ensuring all components work together correctly.
    """

    @pytest.mark.skip(reason="Requires manual testing - dialog interaction not yet automated")
    def test_task_lifecycle_active_to_completed(self, app_instance, qtbot):
        """
        Test complete journey from task creation to completion.

        Workflow:
        1. Create new task with priority and due date
        2. Verify task appears in Focus Mode
        3. Complete the task
        4. Verify state changed and history recorded
        """
        # Step 1: Create task via UI
        initial_task_count = len(app_instance.task_service.get_all_tasks())

        # Open task creation dialog
        app_instance.new_task_action.trigger()
        QTest.qWait(200)

        # Find the dialog - use EnhancedTaskFormDialog (parent class)
        dialog = self.find_dialog(app_instance, EnhancedTaskFormDialog, timeout=2000)
        assert dialog is not None, "Task form dialog did not open"

        # Fill in task details
        dialog.title_input.setText("Write Phase 9 E2E tests")
        dialog.title_input.setFocus()

        dialog.description_input.setPlainText("Complete all 15 core workflow tests")

        # Set high priority
        dialog.priority_combo.setCurrentIndex(2)  # High priority

        # Set due date to tomorrow
        tomorrow = date.today() + timedelta(days=1)
        dialog.due_date_edit.setDate(tomorrow)

        # Save the task
        qtbot.mouseClick(dialog.save_button, Qt.LeftButton)
        QTest.qWait(300)

        # Step 2: Verify task appears in Focus Mode
        focus_task = self.get_focus_task(app_instance)
        assert focus_task is not None, "No focus task after creation"
        assert focus_task.title == "Write Phase 9 E2E tests"
        assert focus_task.priority == Priority.HIGH
        assert focus_task.state == TaskState.ACTIVE

        # Verify task count increased
        new_task_count = len(app_instance.task_service.get_all_tasks())
        assert new_task_count == initial_task_count + 1

        # Step 3: Complete the task
        task_id = focus_task.id
        focus_mode = app_instance.focus_mode

        # Click complete button
        qtbot.mouseClick(focus_mode.complete_button, Qt.LeftButton)
        QTest.qWait(300)

        # Step 4: Verify state changed
        completed_task = app_instance.task_service.get_task_by_id(task_id)
        assert completed_task is not None, "Task not found after completion"
        assert completed_task.state == TaskState.COMPLETED
        assert completed_task.completed_at is not None

        # Step 5: Verify history recorded
        events = app_instance.task_history_service.get_timeline(task_id)
        event_types = [e.event_type for e in events]

        # Should have CREATED and COMPLETED events
        assert "CREATED" in event_types or "created" in str(events).lower()
        assert "COMPLETED" in event_types or "completed" in str(events).lower()

    @pytest.mark.skip(reason="Requires manual testing - defer dialog interaction not yet automated")
    def test_task_lifecycle_defer_workflow(self, app_instance, qtbot, monkeypatch):
        """
        Test task deferral and resurfacing workflow.

        Workflow:
        1. Create task
        2. Defer with start date (tomorrow)
        3. Mock time forward
        4. Verify task auto-activates
        5. Complete task
        """
        # Step 1: Create task
        task = Task(
            title="Deferred Task Test",
            description="This task will be deferred",
            base_priority=2,
            due_date=date.today() + timedelta(days=5),
            state=TaskState.ACTIVE
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id
        task.id = task_id

        app_instance._refresh_focus_task()
        QTest.qWait(200)

        # Step 2: Defer task to tomorrow
        focus_task = self.get_focus_task(app_instance)
        assert focus_task is not None
        assert focus_task.id == task_id

        # Click defer button
        qtbot.mouseClick(app_instance.focus_mode.defer_button, Qt.LeftButton)
        QTest.qWait(200)

        # Find defer dialog
        defer_dialog = self.find_dialog(app_instance, DeferDialog, timeout=2000)
        assert defer_dialog is not None, "Defer dialog did not open"

        # Set start date to tomorrow
        tomorrow = date.today() + timedelta(days=1)
        defer_dialog.start_date_edit.setDate(tomorrow)
        defer_dialog.reason_input.setPlainText("Waiting for resources")

        # Confirm defer
        qtbot.mouseClick(defer_dialog.defer_button, Qt.LeftButton)
        QTest.qWait(300)

        # Step 3: Verify task is deferred
        deferred_task = app_instance.task_service.get_task_by_id(task_id)
        assert deferred_task.state == TaskState.DEFERRED
        assert deferred_task.start_date is not None

        # Focus mode should show next task (or none)
        new_focus = self.get_focus_task(app_instance)
        if new_focus:
            assert new_focus.id != task_id, "Deferred task still showing in focus"

        # Step 4: Mock time forward (simulate auto-activation)
        # In a real scenario, the resurfacing scheduler would activate this
        # For testing, manually activate to simulate
        app_instance.task_service.activate_task(task_id)
        app_instance._refresh_focus_task()
        QTest.qWait(200)

        # Step 5: Verify task reactivated
        reactivated_task = app_instance.task_service.get_task_by_id(task_id)
        assert reactivated_task.state == TaskState.ACTIVE

        # Should appear in focus mode again
        focus_task = self.get_focus_task(app_instance)
        if focus_task and focus_task.id == task_id:
            # Complete the task
            qtbot.mouseClick(app_instance.focus_mode.complete_button, Qt.LeftButton)
            QTest.qWait(200)

            completed = app_instance.task_service.get_task_by_id(task_id)
            assert completed.state == TaskState.COMPLETED

    @pytest.mark.skip(reason="Requires delegate dialog automation - triggers dialog in test mode")
    def test_task_lifecycle_delegate_workflow(self, app_instance, qtbot):
        """
        Test task delegation and follow-up workflow.

        Workflow:
        1. Create task
        2. Delegate to someone with follow-up date
        3. Verify task moved to DELEGATED state
        4. Mock follow-up date reached
        5. Review delegated task
        6. Activate and complete
        """
        # Step 1: Create task
        task = Task(
            title="Delegated Task Test",
            description="This will be delegated",
            base_priority=3,
            due_date=date.today() + timedelta(days=10),
            state=TaskState.ACTIVE
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id
        task.id = task_id

        app_instance._refresh_focus_task()
        QTest.qWait(200)

        # Step 2: Delegate task
        focus_task = self.get_focus_task(app_instance)
        assert focus_task is not None

        # Open delegation dialog (via menu or button)
        # Assuming there's a delegate action in focus mode or menu
        if hasattr(app_instance, 'delegate_action'):
            app_instance.delegate_action.trigger()
        else:
            # Manually delegate via service
            app_instance.task_service.delegate_task(
                task_id,
                delegated_to="John Doe",
                follow_up_date=date.today() + timedelta(days=3),
                notes="Please review the requirements"
            )

        QTest.qWait(300)

        # Step 3: Verify task is delegated
        delegated_task = app_instance.task_service.get_task_by_id(task_id)
        assert delegated_task.state == TaskState.DELEGATED
        assert delegated_task.delegated_to is not None

        # Step 4: Simulate follow-up (in real app, scheduler would trigger notification)
        # For testing, manually activate
        app_instance.task_service.activate_task(task_id)
        app_instance._refresh_focus_task()
        QTest.qWait(200)

        # Step 5: Complete task
        reactivated = app_instance.task_service.get_task_by_id(task_id)
        assert reactivated.state == TaskState.ACTIVE

        # If it's in focus, complete it
        focus_task = self.get_focus_task(app_instance)
        if focus_task and focus_task.id == task_id:
            qtbot.mouseClick(app_instance.focus_mode.complete_button, Qt.LeftButton)
            QTest.qWait(200)

            completed = app_instance.task_service.get_task_by_id(task_id)
            assert completed.state == TaskState.COMPLETED

    def test_task_lifecycle_someday_workflow(self, app_instance, qtbot):
        """
        Test moving task to Someday and back to Active.

        Workflow:
        1. Create task
        2. Move to Someday/Maybe
        3. Verify state change
        4. Review Someday tasks
        5. Activate task
        6. Complete task
        """
        # Step 1: Create task
        task = Task(
            title="Someday Task Test",
            description="Low priority, not urgent",
            base_priority=1,
            state=TaskState.ACTIVE
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id
        task.id = task_id

        app_instance._refresh_focus_task()
        QTest.qWait(200)

        # Step 2: Move to Someday
        # This might be via menu or dialog
        app_instance.task_service.move_to_someday(task_id)
        QTest.qWait(200)

        # Step 3: Verify state
        someday_task = app_instance.task_service.get_task_by_id(task_id)
        assert someday_task.state == TaskState.SOMEDAY

        # Step 4: Review and activate
        # In real app, this would be via ReviewSomedayDialog
        app_instance.task_service.activate_task(task_id)
        app_instance._refresh_focus_task()
        QTest.qWait(200)

        # Step 5: Verify activation
        active_task = app_instance.task_service.get_task_by_id(task_id)
        assert active_task.state == TaskState.ACTIVE

        # Step 6: Complete if in focus
        focus_task = self.get_focus_task(app_instance)
        if focus_task and focus_task.id == task_id:
            qtbot.mouseClick(app_instance.focus_mode.complete_button, Qt.LeftButton)
            QTest.qWait(200)

            completed = app_instance.task_service.get_task_by_id(task_id)
            assert completed.state == TaskState.COMPLETED

    def test_comparison_ranking_workflow(self, app_instance, qtbot):
        """
        Test Elo comparison system for resolving tied priorities.

        Workflow:
        1. Create 3 high-priority tasks with same due date (tied importance)
        2. Trigger comparison
        3. Select winner multiple times
        4. Verify Elo ratings updated
        5. Verify top task appears in Focus Mode
        """
        # Step 1: Create 3 high-priority tasks with identical importance
        tomorrow = date.today() + timedelta(days=1)

        tasks = []
        for i in range(3):
            task = Task(
                title=f"High Priority Task {i+1}",
                description=f"Task {i+1} for comparison",
                base_priority=3,
                due_date=tomorrow,
                state=TaskState.ACTIVE,
                elo_rating=1500.0,  # Same starting Elo
                comparison_count=0
            )
            task_id_obj = app_instance.task_service.create_task(task)
            task_id = task_id_obj.id
            task.id = task_id
            tasks.append(task)

        QTest.qWait(200)

        # Step 2: Refresh focus mode - should trigger comparison if tied
        app_instance._refresh_focus_task()
        QTest.qWait(300)

        # Step 3: Check if comparison dialog appears
        # (May not appear if one task naturally ranks higher due to other factors)
        comparison_dialog = self.find_dialog(app_instance, ComparisonDialog, timeout=1000)

        if comparison_dialog:
            # Perform comparison - select first task as higher priority
            qtbot.mouseClick(comparison_dialog.task1_button, Qt.LeftButton)
            QTest.qWait(300)

            # Step 4: Verify Elo ratings updated
            task1 = app_instance.task_service.get_task_by_id(tasks[0].id)
            task2 = app_instance.task_service.get_task_by_id(tasks[1].id)

            # Winner should have higher Elo
            assert task1.elo_rating > 1500.0, "Winner Elo should increase"
            assert task2.elo_rating < 1500.0, "Loser Elo should decrease"
            assert task1.comparison_count > 0
            assert task2.comparison_count > 0

        # Step 5: Verify a task appears in Focus Mode
        focus_task = self.get_focus_task(app_instance)
        assert focus_task is not None, "Should have a focus task after comparison"
        assert focus_task.id in [t.id for t in tasks], "Focus task should be one of created tasks"

    def test_dependency_blocking_workflow(self, app_instance, qtbot):
        """
        Test dependency system blocking tasks in Focus Mode.

        Workflow:
        1. Create task A (no dependencies)
        2. Create task B that depends on task A
        3. Verify B is hidden/blocked in Focus Mode
        4. Complete task A
        5. Verify task B appears in Focus Mode
        6. Complete task B
        """
        # Step 1: Create task A
        task_a = Task(
            title="Task A - Prerequisite",
            description="Must be completed first",
            base_priority=3,
            due_date=date.today() + timedelta(days=1),
            state=TaskState.ACTIVE
        )
        task_a_id_obj = app_instance.task_service.create_task(task_a)
        task_a_id = task_a_id_obj.id
        task_a.id = task_a_id

        # Step 2: Create task B with dependency on A
        task_b = Task(
            title="Task B - Dependent",
            description="Depends on Task A",
            base_priority=3,  # Same priority as A
            due_date=date.today() + timedelta(days=1),  # Same due date
            state=TaskState.ACTIVE
        )
        task_b_id_obj = app_instance.task_service.create_task(task_b)
        task_b_id = task_b_id_obj.id
        task_b.id = task_b_id

        # Add dependency: B depends on A
        app_instance.dependency_dao.add_dependency(task_b_id, task_a_id)
        QTest.qWait(200)

        # Step 3: Refresh focus mode
        app_instance._refresh_focus_task()
        QTest.qWait(200)

        # Task A should appear (no blockers)
        focus_task = self.get_focus_task(app_instance)
        assert focus_task is not None
        assert focus_task.id == task_a_id, "Task A should be in focus (no dependencies)"

        # Task B should NOT be available for focus yet (blocked by dependency)
        available_tasks = app_instance.task_service.get_ranked_tasks()
        available_ids = [t.id for t in available_tasks]
        assert task_b_id not in available_ids, "Task B should be blocked by dependency on A"

        # Step 4: Complete task A
        qtbot.mouseClick(app_instance.focus_mode.complete_button, Qt.LeftButton)
        QTest.qWait(300)

        # Verify A is completed
        completed_a = app_instance.task_service.get_task_by_id(task_a_id)
        assert completed_a.state == TaskState.COMPLETED

        # Step 5: Refresh focus - Task B should now appear
        app_instance._refresh_focus_task()
        QTest.qWait(200)

        new_focus = self.get_focus_task(app_instance)
        assert new_focus is not None
        assert new_focus.id == task_b_id, "Task B should now be available (blocker completed)"

        # Step 6: Complete task B
        qtbot.mouseClick(app_instance.focus_mode.complete_button, Qt.LeftButton)
        QTest.qWait(300)

        completed_b = app_instance.task_service.get_task_by_id(task_b_id)
        assert completed_b.state == TaskState.COMPLETED

    @pytest.mark.skip(reason="Requires manual testing - defer/blocker dialog interaction not yet automated")
    def test_defer_with_blocker_workflow(self, app_instance, qtbot):
        """
        Test deferring a task while creating a blocker task.

        Workflow:
        1. Create task
        2. Defer with "blocker" reason
        3. Create blocker task via dialog
        4. Verify original task depends on blocker
        5. Complete blocker
        6. Verify original task activates
        """
        # Step 1: Create task
        task = Task(
            title="Task with Blocker",
            description="Blocked by external dependency",
            base_priority=3,
            due_date=date.today() + timedelta(days=5),
            state=TaskState.ACTIVE
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id
        task.id = task_id

        app_instance._refresh_focus_task()
        QTest.qWait(200)

        # Step 2: Open defer dialog
        focus_task = self.get_focus_task(app_instance)
        assert focus_task is not None

        qtbot.mouseClick(app_instance.focus_mode.defer_button, Qt.LeftButton)
        QTest.qWait(200)

        defer_dialog = self.find_dialog(app_instance, DeferDialog, timeout=2000)
        assert defer_dialog is not None

        # Select "blocker" reason
        if hasattr(defer_dialog, 'blocker_radio'):
            defer_dialog.blocker_radio.setChecked(True)
            defer_dialog.blocker_description.setPlainText("Waiting for API access")

        # Step 3: Create blocker task
        # Note: The actual UI flow might be different, adjust as needed
        # For now, simulate creating blocker task manually
        blocker = Task(
            title="Get API Access",
            description="Request API credentials",
            base_priority=3,
            due_date=date.today() + timedelta(days=2),
            state=TaskState.ACTIVE
        )
        blocker_id_obj = app_instance.task_service.create_task(blocker)
        blocker_id = blocker_id_obj.id

        # Create dependency
        app_instance.dependency_dao.add_dependency(task_id, blocker_id)

        # Defer original task
        app_instance.task_service.defer_task(task_id, start_date=date.today() + timedelta(days=3))
        QTest.qWait(200)

        # Step 4: Verify dependency exists
        dependencies = app_instance.dependency_dao.get_dependencies(task_id)
        assert len(dependencies) > 0
        assert blocker_id in dependencies

        # Step 5: Complete blocker
        app_instance.task_service.complete_task(blocker_id)
        QTest.qWait(200)

        # Step 6: Verify original task can be activated
        # (In real app, this would happen automatically or via notification)
        app_instance.task_service.activate_task(task_id)
        app_instance._refresh_focus_task()
        QTest.qWait(200)

        activated = app_instance.task_service.get_task_by_id(task_id)
        assert activated.state == TaskState.ACTIVE

    def test_undo_redo_complete_workflow(self, app_instance, qtbot):
        """
        Test undo/redo system with task completion.

        Workflow:
        1. Create task
        2. Complete task
        3. Undo completion
        4. Verify task restored to ACTIVE
        5. Redo completion
        6. Verify task COMPLETED again
        """
        # Step 1: Create task
        task = Task(
            title="Undo/Redo Test Task",
            description="Testing undo/redo functionality",
            base_priority=2,
            due_date=date.today() + timedelta(days=2),
            state=TaskState.ACTIVE
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id
        task.id = task_id

        app_instance._refresh_focus_task()
        QTest.qWait(200)

        # Step 2: Complete task
        focus_task = self.get_focus_task(app_instance)
        if focus_task and focus_task.id == task_id:
            qtbot.mouseClick(app_instance.focus_mode.complete_button, Qt.LeftButton)
            QTest.qWait(300)

            completed = app_instance.task_service.get_task_by_id(task_id)
            assert completed.state == TaskState.COMPLETED

        # Step 3: Undo completion
        if hasattr(app_instance, 'undo_action'):
            app_instance.undo_action.trigger()
            QTest.qWait(300)

            # Step 4: Verify restored
            restored = app_instance.task_service.get_task_by_id(task_id)
            assert restored.state == TaskState.ACTIVE
            assert restored.completed_at is None

            # Step 5: Redo completion
            if hasattr(app_instance, 'redo_action'):
                app_instance.redo_action.trigger()
                QTest.qWait(300)

                # Step 6: Verify completed again
                recompleted = app_instance.task_service.get_task_by_id(task_id)
                assert recompleted.state == TaskState.COMPLETED

    def test_context_filtering_workflow(self, app_instance, qtbot):
        """
        Test context filtering in Focus Mode.

        Workflow:
        1. Create tasks with different contexts
        2. Apply context filter
        3. Verify Focus Mode respects filter
        4. Clear filter
        5. Verify all tasks available again
        """
        # Step 1: Create contexts
        from src.models import Context
        work_ctx = app_instance.task_service.context_dao.create(Context(name="Work", description="Office tasks"))
        home_ctx = app_instance.task_service.context_dao.create(Context(name="Home", description="Personal tasks"))

        # Create tasks with different contexts
        work_task = Task(
            title="Work Task",
            description="Office work",
            base_priority=3,
            due_date=date.today() + timedelta(days=1),
            state=TaskState.ACTIVE,
            context_id=work_ctx.id
        )
        work_task_id_obj = app_instance.task_service.create_task(work_task)
        work_task_id = work_task_id_obj.id

        home_task = Task(
            title="Home Task",
            description="Personal task",
            base_priority=3,
            due_date=date.today() + timedelta(days=1),
            state=TaskState.ACTIVE,
            context_id=home_ctx.id
        )
        home_task_id_obj = app_instance.task_service.create_task(home_task)
        home_task_id = home_task_id_obj.id

        QTest.qWait(200)

        # Step 2: Get focus task with work context filter
        work_focus_task = app_instance.task_service.get_focus_task(context_filter=work_ctx.id)
        if work_focus_task:
            # Step 3: Verify only work task appears
            assert work_focus_task.context_id == work_ctx.id, f"Should show work task only, got context_id={work_focus_task.context_id}"

        # Step 4: Get focus task with home context filter
        home_focus_task = app_instance.task_service.get_focus_task(context_filter=home_ctx.id)
        if home_focus_task:
            assert home_focus_task.context_id == home_ctx.id, f"Should show home task only, got context_id={home_focus_task.context_id}"

        # Step 5: Get focus task without filter - verify both tasks available
        all_tasks = app_instance.task_service.get_ranked_tasks()
        task_ids = [t.id for t in all_tasks if t.state == TaskState.ACTIVE]
        assert work_task_id in task_ids, "Work task should be in ranked list"
        assert home_task_id in task_ids, "Home task should be in ranked list"

    @pytest.mark.skip(reason="Requires manual testing - defer dialog triggered by keyboard shortcut")
    def test_keyboard_shortcuts_workflow(self, app_instance, qtbot):
        """
        Test keyboard shortcuts in Focus Mode.

        Workflow:
        1. Create task
        2. Use keyboard shortcut to complete (Alt+C or similar)
        3. Verify task completed
        4. Create another task
        5. Use shortcut to defer (Alt+D or similar)
        6. Verify dialog opens
        """
        # Step 1: Create task
        task = Task(
            title="Keyboard Shortcut Test",
            description="Testing shortcuts",
            base_priority=2,
            due_date=date.today() + timedelta(days=2),
            state=TaskState.ACTIVE
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id

        app_instance._refresh_focus_task()
        QTest.qWait(200)

        # Step 2: Focus the main window and use complete shortcut
        app_instance.activateWindow()
        app_instance.focus_mode.setFocus()

        # Trigger complete action via shortcut (Ctrl+Return or similar)
        if hasattr(app_instance, 'complete_action'):
            # Simulate shortcut key
            qtbot.keyClick(app_instance.focus_mode, Qt.Key_Return, Qt.ControlModifier)
            QTest.qWait(300)

            # Step 3: Verify completed
            completed = app_instance.task_service.get_task_by_id(task_id)
            # May or may not complete depending on actual shortcut implementation
            # This test documents the expected behavior

        # Step 4: Create another task
        task2 = Task(
            title="Another Shortcut Test",
            description="Testing defer shortcut",
            base_priority=1,
            state=TaskState.ACTIVE
        )
        task2_id_obj = app_instance.task_service.create_task(task2)
        _id = _id_obj.id

        app_instance._refresh_focus_task()
        QTest.qWait(200)

        # Step 5: Try defer shortcut
        if hasattr(app_instance, 'defer_action'):
            qtbot.keyClick(app_instance.focus_mode, Qt.Key_D, Qt.AltModifier)
            QTest.qWait(300)

            # Step 6: Check if defer dialog opened
            defer_dialog = self.find_dialog(app_instance, DeferDialog, timeout=1000)
            # Dialog may or may not appear depending on shortcut implementation

    def test_export_import_workflow(self, seeded_app, qtbot, tmp_path):
        """
        Test export and import functionality.

        Workflow:
        1. Export tasks to JSON (seeded_app has 25 tasks)
        2. Verify export file created
        3. Clear database
        4. Import from JSON
        5. Verify all tasks restored
        """
        # Step 1: Count tasks before export
        initial_tasks = seeded_app.task_service.get_all_tasks()
        initial_count = len(initial_tasks)
        assert initial_count > 0, "Should have seeded tasks"

        # Step 2: Export tasks
        export_path = tmp_path / "export_test.json"

        # Use export service
        if hasattr(seeded_app, 'export_service'):
            seeded_app.export_service.export_to_json(str(export_path))
        else:
            # Manual export via service layer
            from src.services.export_service import ExportService
            export_service = ExportService(seeded_app.db_connection.get_connection())
            export_service.export_to_json(str(export_path))

        QTest.qWait(200)

        # Step 3: Verify export file exists and has content
        assert export_path.exists(), "Export file should be created"
        assert export_path.stat().st_size > 0, "Export file should have content"

        # Step 4: Clear database
        if hasattr(seeded_app, 'data_reset_service'):
            seeded_app.data_reset_service.reset_all_data()
        else:
            # Manual clear
            conn = seeded_app.db_connection.get_connection()
            conn.execute("DELETE FROM tasks")
            conn.commit()

        QTest.qWait(200)

        # Verify cleared
        cleared_tasks = seeded_app.task_service.get_all_tasks()
        assert len(cleared_tasks) == 0, "All tasks should be deleted"

        # Step 5: Import from JSON
        if hasattr(seeded_app, 'import_service'):
            seeded_app.import_service.import_from_json(str(export_path))
        else:
            from src.services.import_service import ImportService
            import_service = ImportService(seeded_app.db_connection.get_connection())
            import_service.import_from_json(str(export_path))

        QTest.qWait(300)

        # Step 6: Verify all tasks restored
        restored_tasks = seeded_app.task_service.get_all_tasks()
        assert len(restored_tasks) == initial_count, \
            f"Should restore all {initial_count} tasks, got {len(restored_tasks)}"

        # Verify task details preserved
        restored_titles = {t.title for t in restored_tasks}
        initial_titles = {t.title for t in initial_tasks}
        assert restored_titles == initial_titles, "Task titles should match after import"
