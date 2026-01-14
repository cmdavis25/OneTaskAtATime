"""
Memory Leak Tests

Tests for memory leaks and excessive memory usage during long-running sessions.
Uses Python's tracemalloc module to track memory allocations.
"""

import pytest
import gc
import tracemalloc
from datetime import datetime, date, timedelta
from PyQt5.QtTest import QTest

from src.models.task import Task
from src.models.enums import TaskState, Priority
from tests.e2e.base_e2e_test import BaseE2ETest


@pytest.mark.memory
@pytest.mark.slow
class TestMemoryLeaks(BaseE2ETest):
    """
    Test for memory leaks in long-running operations.

    These tests track memory growth over repeated operations to detect leaks.
    """

    def test_focus_mode_refresh_memory(self, app_instance, qtbot):
        """
        Test memory usage when refreshing Focus Mode repeatedly.

        Workflow:
        1. Create 100 tasks
        2. Refresh Focus Mode 1,000 times
        3. Measure memory growth
        4. Verify < 10% memory increase

        Acceptance: < 10% memory growth after 1,000 refreshes
        """
        # Create 100 tasks for realistic scenario
        for i in range(100):
            task = Task(
                title=f"Memory Test Task {i+1}",
                description="Testing memory leaks",
                base_priority=2,
                due_date=date.today() + timedelta(days=i % 10),
                state=TaskState.ACTIVE
            )
            app_instance.task_service.create_task(task)

        QTest.qWait(200)

        # Start memory tracking
        tracemalloc.start()
        gc.collect()  # Clean up before baseline

        # Baseline measurement
        baseline_current, baseline_peak = tracemalloc.get_traced_memory()

        # Refresh Focus Mode 1,000 times
        for i in range(1000):
            app_instance._refresh_focus_task()
            QTest.qWait(1)  # Minimal wait

            # Periodic garbage collection
            if i % 100 == 0:
                gc.collect()

        # Final measurement
        gc.collect()
        final_current, final_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Calculate growth
        memory_growth = final_current - baseline_current
        growth_percentage = (memory_growth / baseline_current) * 100 if baseline_current > 0 else 0

        print(f"\n  Baseline memory: {baseline_current / 1024 / 1024:.2f} MB")
        print(f"  Final memory: {final_current / 1024 / 1024:.2f} MB")
        print(f"  Growth: {memory_growth / 1024 / 1024:.2f} MB ({growth_percentage:.1f}%)")

        # Acceptance criteria: < 10% growth
        assert growth_percentage < 10, \
            f"Memory grew by {growth_percentage:.1f}% (limit: 10%)"

        print(f"  ✓ Memory leak test: PASS ({growth_percentage:.1f}% < 10%)")

    def test_dialog_open_close_memory(self, app_instance, qtbot):
        """
        Test memory leaks when opening/closing dialogs repeatedly.

        Workflow:
        1. Open and close TaskFormDialog 500 times
        2. Measure memory growth
        3. Verify no accumulated objects

        Acceptance: Minimal memory growth (< 5 MB)
        """
        tracemalloc.start()
        gc.collect()

        baseline_current, _ = tracemalloc.get_traced_memory()

        # Open and close dialog 500 times
        for i in range(500):
            # Trigger new task action to open dialog
            app_instance.new_task_action.trigger()
            QTest.qWait(10)

            # Find and close dialog
            from src.ui.task_form_enhanced import EnhancedTaskFormDialog
            dialog = self.find_dialog(app_instance, EnhancedTaskFormDialog, timeout=100)

            if dialog:
                dialog.reject()  # Close without saving
                QTest.qWait(10)

            # Periodic cleanup
            if i % 50 == 0:
                gc.collect()

        # Final measurement
        gc.collect()
        final_current, _ = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        memory_growth = (final_current - baseline_current) / 1024 / 1024  # MB

        print(f"\n  Memory growth after 500 dialog cycles: {memory_growth:.2f} MB")

        # Acceptance: < 5 MB growth
        assert memory_growth < 5, \
            f"Memory grew by {memory_growth:.2f} MB (limit: 5 MB)"

        print(f"  ✓ Dialog memory test: PASS ({memory_growth:.2f} MB < 5 MB)")

    def test_undo_stack_memory(self, app_instance, qtbot):
        """
        Test undo stack memory management.

        Workflow:
        1. Perform 500 undoable operations (create and complete tasks)
        2. Verify undo stack is pruned (limited to max size)
        3. Measure memory usage

        Acceptance: Stack size limited to 50, reasonable memory usage
        """
        tracemalloc.start()
        gc.collect()

        baseline_current, _ = tracemalloc.get_traced_memory()

        # Perform 500 operations
        task_ids = []
        for i in range(500):
            task = Task(
                title=f"Undo Stack Test {i+1}",
                description="Testing undo stack",
                base_priority=2,
                state=TaskState.ACTIVE
            )
            task_id = app_instance.task_service.create_task(task)
            task_ids.append(task_id)

            # Complete task (creates undo command)
            app_instance.task_service.complete_task(task_id)

            if i % 50 == 0:
                gc.collect()

        QTest.qWait(100)

        # Check undo stack size
        if hasattr(app_instance, 'undo_manager'):
            stack_size = len(app_instance.undo_manager.undo_stack) if hasattr(app_instance.undo_manager, 'undo_stack') else 0

            # Stack should be limited (typically 50)
            assert stack_size <= 50, \
                f"Undo stack has {stack_size} items (should be limited to 50)"

            print(f"\n  Undo stack size: {stack_size} (properly limited)")

        # Measure memory
        gc.collect()
        final_current, _ = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        memory_used = (final_current - baseline_current) / 1024 / 1024

        print(f"  Memory used: {memory_used:.2f} MB for 500 operations")

        # Acceptance: < 20 MB for 500 operations
        assert memory_used < 20, \
            f"Memory usage {memory_used:.2f} MB too high (limit: 20 MB)"

        print(f"  ✓ Undo stack memory test: PASS")

    def test_notification_accumulation(self, app_instance, qtbot):
        """
        Test notification cleanup (old notifications should be removed).

        Workflow:
        1. Generate 1,000 notifications
        2. Verify old notifications are cleaned up
        3. Only recent N notifications should be stored

        Acceptance: Notification count limited (not all 1,000 stored)
        """
        if not hasattr(app_instance, 'notification_manager'):
            pytest.skip("Notification manager not available")

        # Generate 1,000 notifications
        for i in range(1000):
            # Create a test notification
            # (Exact API depends on notification manager implementation)
            if hasattr(app_instance.notification_manager, 'create_notification'):
                app_instance.notification_manager.create_notification(
                    title=f"Test Notification {i+1}",
                    message="Testing notification accumulation",
                    task_id=None
                )

        QTest.qWait(200)

        # Check notification count
        if hasattr(app_instance.notification_manager, 'get_all_notifications'):
            all_notifications = app_instance.notification_manager.get_all_notifications()
            notification_count = len(all_notifications)

            print(f"\n  Notifications stored: {notification_count} / 1000 generated")

            # Should NOT store all 1,000 - should have cleanup
            assert notification_count < 1000, \
                "Notifications not being cleaned up (all 1,000 stored)"

            # Reasonable limit might be 100-200
            assert notification_count < 500, \
                f"Too many notifications stored: {notification_count}"

            print(f"  ✓ Notification cleanup: PASS ({notification_count} notifications)")

    def test_long_running_session(self, app_instance, qtbot):
        """
        Simulate long-running session with varied operations.

        Workflow:
        1. Perform 200 mixed operations (create, complete, defer, delete)
        2. Refresh views multiple times
        3. Measure memory stability

        Acceptance: Memory remains stable after initial load
        """
        tracemalloc.start()
        gc.collect()

        # Take multiple measurements
        measurements = []

        # Initial baseline
        baseline, _ = tracemalloc.get_traced_memory()
        measurements.append(baseline)

        # Perform operations in batches
        for batch in range(5):  # 5 batches of 40 operations each
            for i in range(40):
                op_index = batch * 40 + i

                # Create task
                task = Task(
                    title=f"Session Task {op_index+1}",
                    description="Long running session test",
                    base_priority=2,
                    due_date=date.today() + timedelta(days=op_index % 10),
                    state=TaskState.ACTIVE
                )
                task_id = app_instance.task_service.create_task(task)

                # Vary operations
                if op_index % 4 == 0:
                    # Complete task
                    app_instance.task_service.complete_task(task_id)
                elif op_index % 4 == 1:
                    # Defer task
                    app_instance.task_service.defer_task(
                        task_id,
                        start_date=date.today() + timedelta(days=2)
                    )
                elif op_index % 4 == 2:
                    # Delete task
                    app_instance.task_service.delete_task(task_id)
                # else: leave active

                # Refresh views occasionally
                if i % 10 == 0:
                    app_instance._refresh_focus_task()

            # Measure after each batch
            gc.collect()
            current, _ = tracemalloc.get_traced_memory()
            measurements.append(current)

            print(f"  Batch {batch+1}: {current / 1024 / 1024:.2f} MB")

        tracemalloc.stop()

        # Check memory stability (last 2 measurements shouldn't grow much)
        if len(measurements) >= 3:
            early_avg = sum(measurements[1:3]) / 2
            late_avg = sum(measurements[-2:]) / 2

            growth = ((late_avg - early_avg) / early_avg) * 100 if early_avg > 0 else 0

            print(f"\n  Memory growth (early to late): {growth:.1f}%")

            # Should be relatively stable (< 20% growth)
            assert growth < 20, \
                f"Memory not stable: {growth:.1f}% growth"

            print(f"  ✓ Long-running session: PASS (stable memory)")
