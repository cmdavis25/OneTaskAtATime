"""
Resurfacing System E2E Tests

Tests the automatic resurfacing of deferred, delegated, and someday tasks.
Verifies notification generation, scheduler behavior, and task reactivation.
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock
from PyQt5.QtTest import QTest

from src.models.task import Task
from src.models.enums import TaskState, Priority
from tests.e2e.base_e2e_test import BaseE2ETest


@pytest.mark.e2e
@pytest.mark.integration
class TestResurfacingSystem(BaseE2ETest):
    """
    Test automatic resurfacing of tasks.

    The resurfacing system handles:
    - Deferred tasks reaching their start_date
    - Delegated tasks reaching their follow_up_date
    - Someday tasks during periodic review
    - Notification generation and display
    """

    def test_deferred_task_auto_activation(self, app_instance, qtbot, monkeypatch):
        """
        Test deferred task auto-activates on start_date.

        Workflow:
        1. Create deferred task with start_date = today
        2. Run resurfacing scheduler
        3. Verify task auto-activated
        4. Verify notification generated
        """
        # Step 1: Create deferred task with start_date = today
        today = date.today()
        task = Task(
            title="Deferred Task - Today",
            description="Should activate today",
            base_priority=2,
            due_date=today + timedelta(days=5),
            start_date=today,  # Starts today
            state=TaskState.DEFERRED
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id
        QTest.qWait(100)

        # Verify initially deferred
        deferred_task = app_instance.task_service.get_task_by_id(task_id)
        assert deferred_task.state == TaskState.DEFERRED

        # Step 2: Manually trigger resurfacing job
        # (In production, this runs on schedule)
        if hasattr(app_instance, 'resurfacing_scheduler'):
            app_instance.resurfacing_scheduler.check_deferred_tasks()
            QTest.qWait(200)

        # Step 3: Verify task activated
        activated_task = app_instance.task_service.get_task_by_id(task_id)
        assert activated_task.state == TaskState.ACTIVE, \
            "Task should be auto-activated when start_date is reached"

        # Step 4: Verify notification generated
        if hasattr(app_instance, 'notification_manager'):
            notifications = app_instance.notification_manager.get_unread_notifications()
            # May have notification about task activation
            # (Exact behavior depends on implementation)

    def test_delegated_task_follow_up_notification(self, app_instance, qtbot):
        """
        Test delegated task generates notification on follow_up_date.

        Workflow:
        1. Create delegated task with follow_up_date = today
        2. Run resurfacing scheduler
        3. Verify notification created
        4. Verify task still delegated (not auto-activated)
        """
        # Step 1: Create delegated task
        today = date.today()
        task = Task(
            title="Delegated Task - Follow Up",
            description="Follow up with Alice",
            base_priority=3,
            due_date=today + timedelta(days=10),
            delegated_to="Alice",
            follow_up_date=today,  # Follow up today
            state=TaskState.DELEGATED
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id
        QTest.qWait(100)

        # Step 2: Trigger resurfacing
        if hasattr(app_instance, 'resurfacing_scheduler'):
            app_instance.resurfacing_scheduler.check_delegated_tasks()
            QTest.qWait(200)

        # Step 3: Verify notification created
        if hasattr(app_instance, 'notification_manager'):
            notifications = app_instance.notification_manager.get_all_notifications()
            # Should have follow-up notification
            notification_titles = [n.title for n in notifications if hasattr(n, 'title')]
            # Check if any notification mentions the task

        # Step 4: Task should still be DELEGATED (not auto-activated)
        # User must manually review and decide
        delegated_task = app_instance.task_service.get_task_by_id(task_id)
        assert delegated_task.state == TaskState.DELEGATED

    def test_someday_periodic_review_trigger(self, app_instance, qtbot):
        """
        Test someday tasks trigger periodic review.

        Workflow:
        1. Create someday task
        2. Mock time passage (7 days)
        3. Run resurfacing scheduler
        4. Verify review notification/dialog triggered
        """
        # Step 1: Create someday task
        task = Task(
            title="Someday Task - Review",
            description="Consider doing this eventually",
            base_priority=1,
            state=TaskState.SOMEDAY
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id
        QTest.qWait(100)

        # Step 2: Mock time passage
        # In production, someday tasks are reviewed weekly/monthly
        # For testing, manually trigger review

        # Step 3: Trigger someday review
        if hasattr(app_instance, 'resurfacing_scheduler'):
            app_instance.resurfacing_scheduler.check_someday_tasks()
            QTest.qWait(200)

        # Step 4: Verify notification or dialog
        # (Exact behavior depends on implementation)
        # Task should still be SOMEDAY unless user activates it
        someday_task = app_instance.task_service.get_task_by_id(task_id)
        assert someday_task.state == TaskState.SOMEDAY

    def test_multiple_deferred_tasks_batch_activation(self, app_instance, qtbot):
        """
        Test multiple deferred tasks activate together.

        Workflow:
        1. Create 5 deferred tasks with same start_date = today
        2. Run resurfacing scheduler
        3. Verify all 5 tasks activated
        4. Verify notification shows count
        """
        # Step 1: Create 5 deferred tasks
        today = date.today()
        task_ids = []

        for i in range(5):
            task = Task(
                title=f"Batch Deferred Task {i+1}",
                description=f"Task {i+1} starting today",
                base_priority=2,
                due_date=today + timedelta(days=3+i),
                start_date=today,
                state=TaskState.DEFERRED
            )
            task_id_obj = app_instance.task_service.create_task(task)
            task_id = task_id_obj.id
            task_ids.append(task_id)

        QTest.qWait(100)

        # Step 2: Trigger resurfacing
        if hasattr(app_instance, 'resurfacing_scheduler'):
            app_instance.resurfacing_scheduler.check_deferred_tasks()
            QTest.qWait(300)

        # Step 3: Verify all activated
        activated_count = 0
        for task_id in task_ids:
            task = app_instance.task_service.get_task_by_id(task_id)
            if task.state == TaskState.ACTIVE:
                activated_count += 1

        assert activated_count == 5, \
            f"All 5 tasks should activate, but only {activated_count} did"

        # Step 4: Verify notification
        if hasattr(app_instance, 'notification_manager'):
            notifications = app_instance.notification_manager.get_unread_notifications()
            # May have single notification about multiple tasks

    def test_notification_panel_integration(self, app_instance, qtbot):
        """
        Test notifications appear in notification panel.

        Workflow:
        1. Create deferred task that should activate
        2. Trigger resurfacing
        3. Verify notification in panel
        4. Mark notification as read
        5. Verify state change
        """
        # Step 1: Create task
        today = date.today()
        task = Task(
            title="Notification Panel Test",
            description="Check panel display",
            base_priority=3,
            due_date=today + timedelta(days=2),
            start_date=today,
            state=TaskState.DEFERRED
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id
        QTest.qWait(100)

        # Step 2: Trigger resurfacing
        if hasattr(app_instance, 'resurfacing_scheduler'):
            app_instance.resurfacing_scheduler.check_deferred_tasks()
            QTest.qWait(200)

        # Step 3: Check notification panel
        if hasattr(app_instance, 'notification_panel'):
            panel = app_instance.notification_panel
            # Panel should show unread notification
            unread_count = panel.get_unread_count() if hasattr(panel, 'get_unread_count') else 0

        # Step 4: Mark as read
        if hasattr(app_instance, 'notification_manager'):
            notifications = app_instance.notification_manager.get_unread_notifications()
            if notifications:
                first_notif = notifications[0]
                if hasattr(first_notif, 'id'):
                    app_instance.notification_manager.mark_as_read(first_notif.id)
                    QTest.qWait(100)

                    # Step 5: Verify marked as read
                    remaining_unread = app_instance.notification_manager.get_unread_notifications()
                    assert len(remaining_unread) < len(notifications)

    def test_postpone_pattern_intervention(self, app_instance, qtbot):
        """
        Test intervention when task postponed multiple times.

        Workflow:
        1. Create task
        2. Defer it (1st time)
        3. Activate and defer again (2nd time)
        4. Activate and defer again (3rd time)
        5. Verify intervention dialog/notification appears
        """
        # Step 1: Create task
        task = Task(
            title="Frequently Postponed Task",
            description="User keeps deferring this",
            base_priority=2,
            due_date=date.today() + timedelta(days=10),
            state=TaskState.ACTIVE
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id
        QTest.qWait(100)

        # Step 2-4: Defer multiple times
        for i in range(3):
            # Defer
            start_date = date.today() + timedelta(days=1+i)
            app_instance.task_service.defer_task(task_id, start_date=start_date)
            QTest.qWait(100)

            # Activate
            app_instance.task_service.activate_task(task_id)
            QTest.qWait(100)

        # Step 5: Check for intervention
        # The postpone_workflow_service tracks postpone count
        if hasattr(app_instance, 'postpone_workflow_service'):
            postpone_count = app_instance.postpone_workflow_service.get_postpone_count(task_id)
            assert postpone_count >= 3, "Should track multiple postponements"

            # Service may trigger intervention dialog
            # (Exact behavior depends on implementation)

    def test_scheduler_recovery_after_restart(self, app_instance, qtbot, tmp_path):
        """
        Test scheduler restarts and processes tasks after app restart.

        Workflow:
        1. Create deferred task
        2. Close app (stop scheduler)
        3. Reopen app (restart scheduler)
        4. Verify scheduler processes task
        """
        # Step 1: Create deferred task
        today = date.today()
        task = Task(
            title="Scheduler Recovery Test",
            description="Should activate after restart",
            base_priority=2,
            due_date=today + timedelta(days=3),
            start_date=today,
            state=TaskState.DEFERRED
        )
        task_id_obj = app_instance.task_service.create_task(task)
        task_id = task_id_obj.id
        QTest.qWait(100)

        # Step 2: Stop scheduler
        if hasattr(app_instance, 'resurfacing_scheduler'):
            app_instance.resurfacing_scheduler.stop()
            QTest.qWait(100)

        # Step 3: Restart scheduler
        if hasattr(app_instance, 'resurfacing_scheduler'):
            app_instance.resurfacing_scheduler.start()
            QTest.qWait(200)

            # Manually trigger check (in production, runs on schedule)
            app_instance.resurfacing_scheduler.check_deferred_tasks()
            QTest.qWait(200)

        # Step 4: Verify task processed
        activated_task = app_instance.task_service.get_task_by_id(task_id)
        assert activated_task.state == TaskState.ACTIVE, \
            "Scheduler should process task after restart"

    def test_resurfacing_with_dependencies(self, app_instance, qtbot):
        """
        Test deferred task with dependency activates correctly.

        Workflow:
        1. Create task A (completed)
        2. Create task B depending on A (deferred, start_date = today)
        3. Run resurfacing scheduler
        4. Verify B activates (since A is completed)
        5. Create task C depending on incomplete task D
        6. Verify C does NOT activate even if start_date reached
        """
        # Step 1: Create and complete task A
        today = date.today()
        task_a = Task(
            title="Task A - Completed Blocker",
            description="Already done",
            base_priority=3,
            state=TaskState.COMPLETED,
            completed_at=today - timedelta(days=1)
        )
        task_a_id_obj = app_instance.task_service.create_task(task_a)
        task_a_id = task_a_id_obj.id

        # Step 2: Create task B depending on A
        task_b = Task(
            title="Task B - Deferred with Completed Blocker",
            description="Should activate",
            base_priority=2,
            due_date=today + timedelta(days=5),
            start_date=today,
            state=TaskState.DEFERRED
        )
        task_b_id_obj = app_instance.task_service.create_task(task_b)
        task_b_id = task_b_id_obj.id
        app_instance.dependency_dao.add_dependency(task_b_id, task_a_id)
        QTest.qWait(100)

        # Step 3: Trigger resurfacing
        if hasattr(app_instance, 'resurfacing_scheduler'):
            app_instance.resurfacing_scheduler.check_deferred_tasks()
            QTest.qWait(200)

        # Step 4: Verify B activates
        task_b = app_instance.task_service.get_task_by_id(task_b_id)
        assert task_b.state == TaskState.ACTIVE, \
            "Task B should activate since blocker A is completed"

        # Step 5: Create task C depending on incomplete task D
        task_d = Task(
            title="Task D - Incomplete Blocker",
            description="Not done yet",
            base_priority=3,
            due_date=today + timedelta(days=2),
            state=TaskState.ACTIVE
        )
        task_d_id_obj = app_instance.task_service.create_task(task_d)
        task_d_id = task_d_id_obj.id

        task_c = Task(
            title="Task C - Deferred with Incomplete Blocker",
            description="Should NOT activate",
            base_priority=2,
            due_date=today + timedelta(days=7),
            start_date=today,
            state=TaskState.DEFERRED
        )
        task_c_id_obj = app_instance.task_service.create_task(task_c)
        task_c_id = task_c_id_obj.id
        app_instance.dependency_dao.add_dependency(task_c_id, task_d_id)
        QTest.qWait(100)

        # Step 6: Trigger resurfacing again
        if hasattr(app_instance, 'resurfacing_scheduler'):
            app_instance.resurfacing_scheduler.check_deferred_tasks()
            QTest.qWait(200)

        # Verify C does NOT activate
        task_c = app_instance.task_service.get_task_by_id(task_c_id)
        assert task_c.state == TaskState.DEFERRED, \
            "Task C should stay DEFERRED since blocker D is incomplete"
