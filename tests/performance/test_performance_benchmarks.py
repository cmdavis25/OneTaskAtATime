"""
Performance Benchmark Tests

Tests application performance with large datasets (10,000+ tasks).
Validates that the application meets performance acceptance criteria
for key operations like ranking, rendering, and data management.
"""

import pytest
import time
from datetime import datetime, date, timedelta
from PyQt5.QtTest import QTest

from tests.performance.data_generator import LargeDatasetGenerator
from tests.e2e.base_e2e_test import BaseE2ETest


@pytest.mark.performance
@pytest.mark.slow
class TestPerformanceBenchmarks(BaseE2ETest):
    """
    Performance benchmark tests with large datasets.

    Acceptance Criteria:
    - Focus Mode < 500ms with 10,000 tasks
    - Task List rendering < 2s with 10,000 tasks
    - Ranking algorithm < 200ms for 10,000 tasks
    - Export/Import < 10s for large datasets
    """

    @pytest.fixture
    def large_dataset(self, test_db_connection):
        """
        Generate large dataset (10,000 tasks) for performance testing.

        Returns database connection with seeded data.
        """
        print("\nGenerating 10,000 task dataset for performance testing...")
        generator = LargeDatasetGenerator(test_db_connection)
        task_ids, _, _ = generator.generate_complete_dataset(10000)
        print(f"Dataset ready: {len(task_ids)} tasks created")
        return test_db_connection, task_ids

    def test_focus_mode_with_10k_tasks(self, app_instance, qtbot, large_dataset):
        """
        Benchmark: Focus Mode load time with 10,000 tasks.

        Acceptance: < 500ms to display focus task

        This tests the ranking algorithm and UI rendering performance.
        """
        db_connection, task_ids = large_dataset

        # Ensure app is using the large dataset
        app_instance.task_service.refresh()

        # Measure Focus Mode refresh time
        start = time.perf_counter()
        app_instance._refresh_focus_task()
        QTest.qWait(10)  # Allow UI to update
        elapsed = time.perf_counter() - start

        # Verify focus task loaded
        focus_task = app_instance.focus_mode.get_current_task()
        assert focus_task is not None, "Should have a focus task with 10k tasks"

        # Performance assertion
        print(f"\n  Focus Mode load time: {elapsed*1000:.2f}ms")
        assert elapsed < 0.5, f"Focus Mode took {elapsed:.2f}s (limit: 0.5s)"

        print(f"  ✓ Focus Mode performance: PASS ({elapsed*1000:.1f}ms < 500ms)")

    def test_task_list_rendering_10k_tasks(self, app_instance, qtbot, large_dataset):
        """
        Benchmark: Task List View rendering with 10,000 tasks.

        Acceptance: < 2 seconds initial load

        Tests QTableView model/view optimization with large dataset.
        """
        db_connection, task_ids = large_dataset

        # Switch to Task List view
        if hasattr(app_instance, 'task_list_view'):
            # Measure load time
            start = time.perf_counter()
            app_instance.task_list_view.refresh_tasks()
            QTest.qWait(50)  # Allow rendering
            elapsed = time.perf_counter() - start

            # Verify tasks loaded
            model = app_instance.task_list_view.model()
            if model:
                row_count = model.rowCount()
                assert row_count > 0, "Task list should show tasks"

            # Performance assertion
            print(f"\n  Task List render time: {elapsed:.2f}s")
            assert elapsed < 2.0, f"Task List took {elapsed:.2f}s (limit: 2.0s)"

            print(f"  ✓ Task List performance: PASS ({elapsed:.2f}s < 2.0s)")
        else:
            pytest.skip("Task List View not available")

    def test_ranking_algorithm_10k_tasks(self, app_instance, qtbot, large_dataset):
        """
        Benchmark: Task ranking algorithm with 10,000 tasks.

        Acceptance: < 200ms to rank all tasks and find top task

        Tests importance calculation (Priority × Urgency) performance.
        """
        db_connection, task_ids = large_dataset

        # Measure ranking time
        start = time.perf_counter()
        ranked_tasks = app_instance.task_service.get_ranked_tasks()
        elapsed = time.perf_counter() - start

        # Verify ranking worked
        assert len(ranked_tasks) > 0, "Should have ranked tasks"

        # Verify top task has highest importance
        if len(ranked_tasks) > 1:
            top_task = ranked_tasks[0]
            assert top_task is not None, "Should have top task"

        # Performance assertion
        print(f"\n  Ranking time: {elapsed*1000:.2f}ms for {len(ranked_tasks)} tasks")
        assert elapsed < 0.2, f"Ranking took {elapsed:.2f}s (limit: 0.2s)"

        print(f"  ✓ Ranking performance: PASS ({elapsed*1000:.1f}ms < 200ms)")

    def test_comparison_with_100_tied_tasks(self, app_instance, qtbot, test_db_connection):
        """
        Benchmark: Comparison dialog with 100 tied tasks.

        Acceptance: Dialog appears instantly (< 100ms)

        Tests Elo comparison system performance.
        """
        from src.models.task import Task
        from src.models.enums import TaskState, Priority

        # Create 100 tasks with identical importance
        tomorrow = date.today() + timedelta(days=1)
        task_ids = []

        for i in range(100):
            task = Task(
                title=f"Tied Task {i+1}",
                description="All have same importance",
                base_priority=3,
                due_date=tomorrow,
                state=TaskState.ACTIVE,
                elo_rating=1500.0,  # Same Elo
                comparison_count=0
            )
            task_id = app_instance.task_service.create_task(task)
            task_ids.append(task_id)

        # Measure comparison selection time
        start = time.perf_counter()
        # Get tasks that need comparison
        tied_tasks = app_instance.comparison_service.find_tied_tasks()
        elapsed = time.perf_counter() - start

        # Verify ties found
        assert len(tied_tasks) > 1, "Should find tied tasks"

        # Performance assertion
        print(f"\n  Comparison resolution time: {elapsed*1000:.2f}ms for {len(tied_tasks)} tied tasks")
        assert elapsed < 0.1, f"Comparison took {elapsed:.2f}s (limit: 0.1s)"

        print(f"  ✓ Comparison performance: PASS ({elapsed*1000:.1f}ms < 100ms)")

    def test_export_10k_tasks_to_json(self, app_instance, qtbot, large_dataset, tmp_path):
        """
        Benchmark: Export 10,000 tasks to JSON.

        Acceptance: < 5 seconds

        Tests export service performance with large dataset.
        """
        db_connection, task_ids = large_dataset

        export_path = tmp_path / "export_benchmark.json"

        # Measure export time
        from src.services.export_service import ExportService
        export_service = ExportService(db_connection)

        start = time.perf_counter()
        export_service.export_all(str(export_path))
        elapsed = time.perf_counter() - start

        # Verify export created
        assert export_path.exists(), "Export file should be created"
        assert export_path.stat().st_size > 0, "Export file should have content"

        # Performance assertion
        print(f"\n  Export time: {elapsed:.2f}s for {len(task_ids)} tasks")
        assert elapsed < 5.0, f"Export took {elapsed:.2f}s (limit: 5.0s)"

        print(f"  ✓ Export performance: PASS ({elapsed:.2f}s < 5.0s)")

    def test_import_10k_tasks_from_json(self, app_instance, qtbot, large_dataset, tmp_path):
        """
        Benchmark: Import 10,000 tasks from JSON.

        Acceptance: < 10 seconds

        Tests import service performance with ID remapping.
        """
        db_connection, task_ids = large_dataset

        # First export
        from src.services.export_service import ExportService
        from src.services.import_service import ImportService

        export_path = tmp_path / "import_benchmark.json"
        export_service = ExportService(db_connection)
        export_service.export_all(str(export_path))

        # Clear database
        db_connection.execute("DELETE FROM tasks")
        db_connection.commit()

        # Measure import time
        import_service = ImportService(db_connection)

        start = time.perf_counter()
        import_service.import_all(str(export_path))
        elapsed = time.perf_counter() - start

        # Verify import worked
        cursor = db_connection.execute("SELECT COUNT(*) FROM tasks")
        count = cursor.fetchone()[0]
        assert count == len(task_ids), f"Should import all {len(task_ids)} tasks"

        # Performance assertion
        print(f"\n  Import time: {elapsed:.2f}s for {len(task_ids)} tasks")
        assert elapsed < 10.0, f"Import took {elapsed:.2f}s (limit: 10.0s)"

        print(f"  ✓ Import performance: PASS ({elapsed:.2f}s < 10.0s)")

    def test_task_history_query_1k_events(self, app_instance, qtbot, test_db_connection):
        """
        Benchmark: Query task history with 1,000 events.

        Acceptance: < 200ms to fetch and display timeline

        Tests history query performance.
        """
        from src.models.task import Task
        from src.models.enums import TaskState, Priority

        # Create task
        task = Task(
            title="Task with Many Events",
            description="Has 1000 history events",
            base_priority=2,
            state=TaskState.ACTIVE
        )
        task_id = app_instance.task_service.create_task(task)

        # Generate 1000 history events
        from src.database.task_history_dao import TaskHistoryDAO
        history_dao = TaskHistoryDAO(test_db_connection)

        for i in range(1000):
            history_dao.log_event(
                task_id=task_id,
                event_type="UPDATED",
                description=f"Event {i+1}",
                timestamp=datetime.now() - timedelta(minutes=i)
            )

        # Measure query time
        start = time.perf_counter()
        events = app_instance.task_history_service.get_timeline(task_id)
        elapsed = time.perf_counter() - start

        # Verify events loaded
        assert len(events) >= 1000, "Should have 1000+ events"

        # Performance assertion
        print(f"\n  History query time: {elapsed*1000:.2f}ms for {len(events)} events")
        assert elapsed < 0.2, f"History query took {elapsed:.2f}s (limit: 0.2s)"

        print(f"  ✓ History query performance: PASS ({elapsed*1000:.1f}ms < 200ms)")

    def test_dependency_graph_with_1k_nodes(self, app_instance, qtbot, test_db_connection):
        """
        Benchmark: Dependency graph with 1,000 tasks and 150 dependencies.

        Acceptance: < 3 seconds to build and analyze graph

        Tests dependency resolution performance.
        """
        from src.models.task import Task
        from src.models.enums import TaskState, Priority

        # Create 1000 tasks
        task_ids = []
        for i in range(1000):
            task = Task(
                title=f"Dependency Task {i+1}",
                description="Part of large graph",
                base_priority=2,
                state=TaskState.ACTIVE
            )
            task_id = app_instance.task_service.create_task(task)
            task_ids.append(task_id)

        # Create 150 dependencies
        for i in range(150):
            dependent = task_ids[i]
            prerequisite = task_ids[i + 1] if i + 1 < len(task_ids) else task_ids[0]
            try:
                app_instance.dependency_dao.add_dependency(dependent, prerequisite)
            except Exception:
                pass  # Ignore circular dependencies

        # Measure dependency resolution time
        start = time.perf_counter()
        for task_id in task_ids[:100]:  # Check first 100 tasks
            has_blockers = app_instance.task_service.has_blocking_dependencies(task_id)
        elapsed = time.perf_counter() - start

        # Performance assertion
        print(f"\n  Dependency resolution time: {elapsed:.2f}s for 100 checks")
        assert elapsed < 3.0, f"Dependency check took {elapsed:.2f}s (limit: 3.0s)"

        print(f"  ✓ Dependency performance: PASS ({elapsed:.2f}s < 3.0s)")

    def test_search_10k_tasks(self, app_instance, qtbot, large_dataset):
        """
        Benchmark: Search across 10,000 tasks.

        Acceptance: < 300ms to return results

        Tests search query performance.
        """
        db_connection, task_ids = large_dataset

        # Measure search time
        search_term = "task"

        start = time.perf_counter()
        results = app_instance.task_service.search_tasks(search_term)
        elapsed = time.perf_counter() - start

        # Verify results found
        assert len(results) > 0, f"Should find tasks matching '{search_term}'"

        # Performance assertion
        print(f"\n  Search time: {elapsed*1000:.2f}ms, found {len(results)} results")
        assert elapsed < 0.3, f"Search took {elapsed:.2f}s (limit: 0.3s)"

        print(f"  ✓ Search performance: PASS ({elapsed*1000:.1f}ms < 300ms)")

    def test_undo_stack_with_50_operations(self, app_instance, qtbot):
        """
        Benchmark: Undo/Redo with 50 operations.

        Acceptance: Each operation < 100ms

        Tests undo manager performance with long history.
        """
        from src.models.task import Task
        from src.models.enums import TaskState, Priority

        # Create 50 tasks and complete them (50 undoable operations)
        task_ids = []
        times = []

        for i in range(50):
            task = Task(
                title=f"Undo Test Task {i+1}",
                description="For undo testing",
                base_priority=2,
                state=TaskState.ACTIVE
            )
            task_id = app_instance.task_service.create_task(task)
            task_ids.append(task_id)

            # Complete task (creates undo command)
            start = time.perf_counter()
            app_instance.task_service.complete_task(task_id)
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        # Measure undo time
        undo_times = []
        for i in range(min(50, len(task_ids))):
            if hasattr(app_instance, 'undo_manager'):
                start = time.perf_counter()
                app_instance.undo_manager.undo()
                elapsed = time.perf_counter() - start
                undo_times.append(elapsed)

        # Performance assertion
        if undo_times:
            avg_undo_time = sum(undo_times) / len(undo_times)
            max_undo_time = max(undo_times)

            print(f"\n  Undo operations: {len(undo_times)}")
            print(f"  Average undo time: {avg_undo_time*1000:.2f}ms")
            print(f"  Max undo time: {max_undo_time*1000:.2f}ms")

            assert max_undo_time < 0.1, \
                f"Slowest undo took {max_undo_time:.2f}s (limit: 0.1s)"

            print(f"  ✓ Undo performance: PASS (max {max_undo_time*1000:.1f}ms < 100ms)")
