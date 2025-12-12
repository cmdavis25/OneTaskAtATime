"""
Tests for comparison functionality.

Tests the comparison-based priority adjustment system including:
- Exponential decay algorithm
- Comparison recording
- Priority adjustment reset
- Comparison history tracking
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import date, timedelta
from src.models.task import Task
from src.models.enums import TaskState
from src.database.schema import DatabaseSchema
from src.database.task_dao import TaskDAO
from src.database.comparison_dao import ComparisonDAO
from src.database.connection import DatabaseConnection


class MockDatabaseConnection:
    """Mock DatabaseConnection that wraps a raw sqlite3 connection for testing."""

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
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def raw_connection(temp_db):
    """Create a raw database connection for testing."""
    conn = sqlite3.connect(temp_db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    DatabaseSchema.initialize_database(conn)
    yield conn
    conn.close()


@pytest.fixture
def db_connection(raw_connection):
    """Create a mock DatabaseConnection for testing."""
    return MockDatabaseConnection(raw_connection)


@pytest.fixture
def task_dao(raw_connection):
    """Create TaskDAO with test database."""
    return TaskDAO(raw_connection)


@pytest.fixture
def comparison_dao(raw_connection):
    """Create ComparisonDAO with test database."""
    return ComparisonDAO(raw_connection)


@pytest.fixture
def comparison_service(db_connection):
    """Create ComparisonService with test database."""
    from src.services.comparison_service import ComparisonService
    return ComparisonService(db_connection)


class TestExponentialDecay:
    """Test the exponential decay algorithm for priority adjustment."""

    def test_first_loss_adjustment(self, comparison_service, task_dao):
        """Test that first comparison loss applies 0.5 adjustment."""
        task1 = Task(title="Winner", base_priority=2, due_date=date.today())
        task2 = Task(title="Loser", base_priority=2, due_date=date.today())

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)

        # Task2 loses comparison
        winner, loser = comparison_service.record_comparison(task1, task2)

        assert loser.comparison_losses == 1
        assert loser.priority_adjustment == 0.5
        assert loser.get_effective_priority() == 1.5

    def test_second_loss_adjustment(self, comparison_service, task_dao):
        """Test that second comparison loss applies 0.25 adjustment."""
        task1 = Task(title="Winner", base_priority=2, due_date=date.today())
        task2 = Task(title="Loser", base_priority=2, due_date=date.today())

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)

        # First loss
        comparison_service.record_comparison(task1, task2)
        # Second loss
        winner, loser = comparison_service.record_comparison(task1, task2)

        assert loser.comparison_losses == 2
        assert loser.priority_adjustment == 0.75  # 0.5 + 0.25
        assert loser.get_effective_priority() == 1.25

    def test_third_loss_adjustment(self, comparison_service, task_dao):
        """Test that third comparison loss applies 0.125 adjustment."""
        task1 = Task(title="Winner", base_priority=2, due_date=date.today())
        task2 = Task(title="Loser", base_priority=2, due_date=date.today())

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)

        # Three losses
        comparison_service.record_comparison(task1, task2)
        comparison_service.record_comparison(task1, task2)
        winner, loser = comparison_service.record_comparison(task1, task2)

        assert loser.comparison_losses == 3
        assert loser.priority_adjustment == 0.875  # 0.5 + 0.25 + 0.125
        assert loser.get_effective_priority() == 1.125

    def test_adjustment_never_reaches_one(self, comparison_service, task_dao):
        """Test that priority adjustment never reaches 1 (Zeno's Paradox)."""
        task1 = Task(title="Winner", base_priority=2, due_date=date.today())
        task2 = Task(title="Loser", base_priority=2, due_date=date.today())

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)

        # Many losses
        for _ in range(20):
            winner, loser = comparison_service.record_comparison(task1, task2)

        # Adjustment should be very close to 1 but never reach it
        assert loser.priority_adjustment < 1.0
        assert loser.priority_adjustment > 0.999999
        # Effective priority should never reach 1
        assert loser.get_effective_priority() > 1.0

    def test_high_priority_task_decay(self, comparison_service, task_dao):
        """Test that high priority tasks decay correctly."""
        task1 = Task(title="Winner", base_priority=3, due_date=date.today())
        task2 = Task(title="Loser", base_priority=3, due_date=date.today())

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)

        # First loss
        winner, loser = comparison_service.record_comparison(task1, task2)

        assert loser.comparison_losses == 1
        assert loser.priority_adjustment == 0.5
        assert loser.get_effective_priority() == 2.5


class TestComparisonRecording:
    """Test comparison recording in database."""

    def test_comparison_recorded_in_database(self, comparison_service, comparison_dao, task_dao):
        """Test that comparisons are saved to database."""
        task1 = Task(title="Winner", base_priority=2, due_date=date.today())
        task2 = Task(title="Loser", base_priority=2, due_date=date.today())

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)

        comparison_service.record_comparison(task1, task2)

        # Check database has record
        comparisons = comparison_dao.get_all_comparisons()
        assert len(comparisons) == 1
        assert comparisons[0][1] == task1.id  # winner_id
        assert comparisons[0][2] == task2.id  # loser_id
        assert comparisons[0][3] == 0.5       # adjustment_amount

    def test_multiple_comparisons_recorded(self, comparison_service, comparison_dao, task_dao):
        """Test that multiple comparisons are all recorded."""
        task1 = Task(title="Task 1", base_priority=2, due_date=date.today())
        task2 = Task(title="Task 2", base_priority=2, due_date=date.today())
        task3 = Task(title="Task 3", base_priority=2, due_date=date.today())

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)
        task3 = task_dao.create(task3)

        comparison_service.record_comparison(task1, task2)
        comparison_service.record_comparison(task1, task3)
        comparison_service.record_comparison(task2, task3)

        comparisons = comparison_dao.get_all_comparisons()
        assert len(comparisons) == 3

    def test_comparison_history_for_task(self, comparison_service, task_dao):
        """Test retrieving comparison history for a specific task."""
        task1 = Task(title="Winner", base_priority=2, due_date=date.today())
        task2 = Task(title="Loser", base_priority=2, due_date=date.today())

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)

        comparison_service.record_comparison(task1, task2)

        # Check history for loser
        history = comparison_service.get_task_comparison_history(task2.id)
        assert len(history) == 1
        assert history[0]['outcome'] == 'lost'
        assert history[0]['other_task_title'] == 'Winner'

        # Check history for winner
        history = comparison_service.get_task_comparison_history(task1.id)
        assert len(history) == 1
        assert history[0]['outcome'] == 'won'
        assert history[0]['other_task_title'] == 'Loser'


class TestPriorityReset:
    """Test resetting priority adjustments."""

    def test_reset_single_task(self, comparison_service, task_dao):
        """Test resetting a single task's priority adjustment."""
        task1 = Task(title="Winner", base_priority=2, due_date=date.today())
        task2 = Task(title="Loser", base_priority=2, due_date=date.today())

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)

        # Task2 loses
        comparison_service.record_comparison(task1, task2)
        comparison_service.record_comparison(task1, task2)

        assert task2.comparison_losses == 2
        assert task2.priority_adjustment == 0.75

        # Reset task2
        reset_task = comparison_service.reset_task_priority_adjustment(task2.id)

        assert reset_task.comparison_losses == 0
        assert reset_task.priority_adjustment == 0.0
        assert reset_task.get_effective_priority() == 2.0

    def test_reset_deletes_comparison_history(self, comparison_service, comparison_dao, task_dao):
        """Test that resetting a task deletes its comparison history."""
        task1 = Task(title="Winner", base_priority=2, due_date=date.today())
        task2 = Task(title="Loser", base_priority=2, due_date=date.today())

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)

        comparison_service.record_comparison(task1, task2)

        # Verify comparison exists
        comparisons = comparison_dao.get_all_comparisons()
        assert len(comparisons) == 1

        # Reset task2
        comparison_service.reset_task_priority_adjustment(task2.id)

        # Comparison history should be deleted
        comparisons = comparison_dao.get_all_comparisons()
        assert len(comparisons) == 0

    def test_reset_all_priority_adjustments(self, comparison_service, task_dao):
        """Test resetting all priority adjustments."""
        task1 = Task(title="Task 1", base_priority=2, due_date=date.today())
        task2 = Task(title="Task 2", base_priority=2, due_date=date.today())
        task3 = Task(title="Task 3", base_priority=2, due_date=date.today())

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)
        task3 = task_dao.create(task3)

        # Create comparisons
        comparison_service.record_comparison(task1, task2)
        comparison_service.record_comparison(task1, task3)

        # Reset all
        count = comparison_service.reset_all_priority_adjustments()
        assert count == 2  # Two tasks were reset

        # Verify all tasks are reset
        updated_task2 = task_dao.get_by_id(task2.id)
        updated_task3 = task_dao.get_by_id(task3.id)

        assert updated_task2.priority_adjustment == 0.0
        assert updated_task2.comparison_losses == 0
        assert updated_task3.priority_adjustment == 0.0
        assert updated_task3.comparison_losses == 0


class TestCalculateAdjustmentPreview:
    """Test previewing what the next adjustment would be."""

    def test_preview_first_loss(self, comparison_service, task_dao):
        """Test preview for a task with no losses."""
        task = Task(title="Task", base_priority=2, comparison_losses=0)
        preview = comparison_service.calculate_adjustment_preview(task)
        assert preview == 0.5

    def test_preview_second_loss(self, comparison_service, task_dao):
        """Test preview for a task with one loss."""
        task = Task(title="Task", base_priority=2, comparison_losses=1)
        preview = comparison_service.calculate_adjustment_preview(task)
        assert preview == 0.25

    def test_preview_third_loss(self, comparison_service, task_dao):
        """Test preview for a task with two losses."""
        task = Task(title="Task", base_priority=2, comparison_losses=2)
        preview = comparison_service.calculate_adjustment_preview(task)
        assert preview == 0.125


class TestMultipleComparisons:
    """Test recording multiple comparisons at once."""

    def test_record_multiple_comparisons(self, comparison_service, task_dao):
        """Test recording multiple comparison results."""
        task1 = Task(title="Task 1", base_priority=2, due_date=date.today())
        task2 = Task(title="Task 2", base_priority=2, due_date=date.today())
        task3 = Task(title="Task 3", base_priority=2, due_date=date.today())

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)
        task3 = task_dao.create(task3)

        # Simulate tournament-style comparisons
        results = [
            (task1, task2),  # task1 beats task2
            (task1, task3),  # task1 beats task3
        ]

        comparison_service.record_multiple_comparisons(results)

        # Check that both losers were adjusted
        updated_task2 = task_dao.get_by_id(task2.id)
        updated_task3 = task_dao.get_by_id(task3.id)

        assert updated_task2.comparison_losses == 1
        assert updated_task2.priority_adjustment == 0.5
        assert updated_task3.comparison_losses == 1
        assert updated_task3.priority_adjustment == 0.5


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_comparison_without_ids_raises_error(self, comparison_service):
        """Test that comparing tasks without IDs raises an error."""
        task1 = Task(title="Winner", base_priority=2)
        task2 = Task(title="Loser", base_priority=2)

        with pytest.raises(ValueError, match="Both tasks must have IDs"):
            comparison_service.record_comparison(task1, task2)

    def test_reset_nonexistent_task_returns_none(self, comparison_service):
        """Test that resetting a nonexistent task returns None."""
        result = comparison_service.reset_task_priority_adjustment(999999)
        assert result is None

    def test_comparison_history_for_nonexistent_task(self, comparison_service):
        """Test getting comparison history for nonexistent task."""
        history = comparison_service.get_task_comparison_history(999999)
        assert len(history) == 0
