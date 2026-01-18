"""
Unit tests for ComparisonService - Elo rating system.

Tests the core Elo-based priority adjustment system including:
- Elo rating calculations
- K-factor handling (new vs established tasks)
- Same-tier comparison validation
- Comparison recording
- Priority reset
- Shared Elo for recurring tasks
"""

import pytest
import sqlite3
import math
from datetime import date
from src.models.task import Task
from src.models.enums import TaskState
from src.database.schema import DatabaseSchema
from src.database.task_dao import TaskDAO
from src.database.comparison_dao import ComparisonDAO
from src.database.settings_dao import SettingsDAO


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
def task_dao(db_connection):
    """Create TaskDAO instance."""
    return TaskDAO(db_connection.get_connection())


@pytest.fixture
def comparison_dao(db_connection):
    """Create ComparisonDAO instance."""
    return ComparisonDAO(db_connection.get_connection())


@pytest.fixture
def settings_dao(db_connection):
    """Create SettingsDAO instance."""
    return SettingsDAO(db_connection.get_connection())


@pytest.fixture
def comparison_service(db_connection):
    """Create ComparisonService instance."""
    from src.services.comparison_service import ComparisonService
    return ComparisonService(db_connection)


class TestEloRatingCalculations:
    """Test Elo rating calculations."""

    def test_initial_elo_rating_is_1500(self, task_dao):
        """Test that new tasks start with Elo rating of 1500."""
        task = Task(title="Test Task", base_priority=2)
        created = task_dao.create(task)

        assert created.elo_rating == 1500.0
        assert created.comparison_count == 0

    def test_winner_gains_elo_loser_loses_elo(self, comparison_service, task_dao):
        """Test that winner gains Elo and loser loses Elo."""
        task1 = Task(title="Winner", base_priority=2, due_date=date.today())
        task2 = Task(title="Loser", base_priority=2, due_date=date.today())

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)

        initial_elo = 1500.0

        winner, loser = comparison_service.record_comparison(task1, task2)

        assert winner.elo_rating > initial_elo
        assert loser.elo_rating < initial_elo

    def test_equal_elo_gives_expected_change(self, comparison_service, task_dao):
        """Test Elo change when both tasks have equal ratings."""
        task1 = Task(title="Winner", base_priority=2, due_date=date.today())
        task2 = Task(title="Loser", base_priority=2, due_date=date.today())

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)

        # When ratings are equal, expected score is 0.5
        # New task K-factor is 32, so change = 32 * (1 - 0.5) = 16
        winner, loser = comparison_service.record_comparison(task1, task2)

        # With equal ratings and new K-factor (32):
        # Winner: 1500 + 32 * (1 - 0.5) = 1500 + 16 = 1516
        # Loser: 1500 + 32 * (0 - 0.5) = 1500 - 16 = 1484
        assert winner.elo_rating == 1516.0
        assert loser.elo_rating == 1484.0

    def test_k_factor_new_task(self, comparison_service, task_dao, settings_dao):
        """Test that new tasks use higher K-factor (32)."""
        task1 = Task(title="Winner", base_priority=2, due_date=date.today())
        task2 = Task(title="Loser", base_priority=2, due_date=date.today())

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)

        # Both tasks have 0 comparisons (< 10 threshold)
        winner, loser = comparison_service.record_comparison(task1, task2)

        # K-factor 32 applied, equal ratings = 16 point change
        assert abs(winner.elo_rating - 1516.0) < 0.01
        assert abs(loser.elo_rating - 1484.0) < 0.01

    def test_k_factor_established_task(self, comparison_service, task_dao):
        """Test that established tasks use lower K-factor (16)."""
        task1 = Task(title="Winner", base_priority=2, due_date=date.today(),
                     comparison_count=15)  # Above threshold
        task2 = Task(title="Loser", base_priority=2, due_date=date.today(),
                     comparison_count=15)  # Above threshold

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)

        winner, loser = comparison_service.record_comparison(task1, task2)

        # K-factor 16 applied, equal ratings = 8 point change
        assert abs(winner.elo_rating - 1508.0) < 0.01
        assert abs(loser.elo_rating - 1492.0) < 0.01

    def test_comparison_count_increments(self, comparison_service, task_dao):
        """Test that comparison count increments for both tasks."""
        task1 = Task(title="Task 1", base_priority=2, due_date=date.today())
        task2 = Task(title="Task 2", base_priority=2, due_date=date.today())

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)

        assert task1.comparison_count == 0
        assert task2.comparison_count == 0

        winner, loser = comparison_service.record_comparison(task1, task2)

        assert winner.comparison_count == 1
        assert loser.comparison_count == 1

    def test_higher_rated_task_wins_smaller_gain(self, comparison_service, task_dao):
        """Test that higher-rated task wins less when beating lower-rated opponent."""
        # Create tasks with different Elo ratings
        task1 = Task(title="Strong", base_priority=2, due_date=date.today(),
                     elo_rating=1700.0, comparison_count=15)
        task2 = Task(title="Weak", base_priority=2, due_date=date.today(),
                     elo_rating=1300.0, comparison_count=15)

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)

        initial_winner_elo = task1.elo_rating
        initial_loser_elo = task2.elo_rating

        winner, loser = comparison_service.record_comparison(task1, task2)

        # Higher-rated task should gain less when winning
        winner_gain = winner.elo_rating - initial_winner_elo
        loser_loss = initial_loser_elo - loser.elo_rating

        # Expected score for 1700 vs 1300 is very high (~0.91)
        # So winner gains very little, loser loses less
        assert winner_gain < 5.0  # Small gain for expected win
        assert loser_loss > 0  # Loser still loses

    def test_lower_rated_task_wins_larger_gain(self, comparison_service, task_dao):
        """Test that lower-rated task gains more from upset victory."""
        # Create tasks with different Elo ratings
        task1 = Task(title="Weak Upset", base_priority=2, due_date=date.today(),
                     elo_rating=1300.0, comparison_count=15)
        task2 = Task(title="Strong Loss", base_priority=2, due_date=date.today(),
                     elo_rating=1700.0, comparison_count=15)

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)

        initial_winner_elo = task1.elo_rating

        winner, loser = comparison_service.record_comparison(task1, task2)

        # Lower-rated task should gain more from upset
        winner_gain = winner.elo_rating - initial_winner_elo

        # Expected score for 1300 vs 1700 is very low (~0.09)
        # So winner gains a lot for unexpected win
        assert winner_gain > 10.0  # Large gain for upset


class TestSameTierValidation:
    """Test that comparisons only allowed within same priority tier."""

    def test_cannot_compare_different_base_priorities(self, comparison_service, task_dao):
        """Test that comparing tasks with different base_priority raises error."""
        task1 = Task(title="High Priority", base_priority=3, due_date=date.today())
        task2 = Task(title="Low Priority", base_priority=1, due_date=date.today())

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)

        with pytest.raises(ValueError, match="Cannot compare tasks with different base priorities"):
            comparison_service.record_comparison(task1, task2)

    def test_can_compare_same_base_priority(self, comparison_service, task_dao):
        """Test that comparing tasks with same base_priority works."""
        task1 = Task(title="Task A", base_priority=2, due_date=date.today())
        task2 = Task(title="Task B", base_priority=2, due_date=date.today())

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)

        # Should not raise
        winner, loser = comparison_service.record_comparison(task1, task2)
        assert winner is not None
        assert loser is not None


class TestComparisonRecording:
    """Test comparison recording in database."""

    def test_comparison_recorded_in_database(self, comparison_service, comparison_dao, task_dao):
        """Test that comparisons are saved to database."""
        task1 = Task(title="Winner", base_priority=2, due_date=date.today())
        task2 = Task(title="Loser", base_priority=2, due_date=date.today())

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)

        comparison_service.record_comparison(task1, task2)

        comparisons = comparison_dao.get_all_comparisons()
        assert len(comparisons) == 1
        assert comparisons[0][1] == task1.id  # winner_id
        assert comparisons[0][2] == task2.id  # loser_id

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

    def test_record_multiple_comparisons_batch(self, comparison_service, task_dao):
        """Test batch recording of multiple comparisons."""
        task1 = Task(title="Task 1", base_priority=2, due_date=date.today())
        task2 = Task(title="Task 2", base_priority=2, due_date=date.today())
        task3 = Task(title="Task 3", base_priority=2, due_date=date.today())

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)
        task3 = task_dao.create(task3)

        results = [
            (task1, task2),
            (task1, task3),
        ]

        comparison_service.record_multiple_comparisons(results)

        # Both losers should have updated Elo
        updated_task2 = task_dao.get_by_id(task2.id)
        updated_task3 = task_dao.get_by_id(task3.id)

        assert updated_task2.elo_rating < 1500.0
        assert updated_task3.elo_rating < 1500.0


class TestComparisonHistory:
    """Test comparison history retrieval."""

    def test_get_task_comparison_history(self, comparison_service, task_dao):
        """Test retrieving comparison history for a task."""
        task1 = Task(title="Winner", base_priority=2, due_date=date.today())
        task2 = Task(title="Loser", base_priority=2, due_date=date.today())

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)

        comparison_service.record_comparison(task1, task2)

        # Check loser's history
        history = comparison_service.get_task_comparison_history(task2.id)
        assert len(history) == 1
        assert history[0]['outcome'] == 'lost'
        assert history[0]['other_task_title'] == 'Winner'

        # Check winner's history
        history = comparison_service.get_task_comparison_history(task1.id)
        assert len(history) == 1
        assert history[0]['outcome'] == 'won'
        assert history[0]['other_task_title'] == 'Loser'

    def test_history_for_nonexistent_task(self, comparison_service):
        """Test getting history for nonexistent task."""
        history = comparison_service.get_task_comparison_history(99999)
        assert len(history) == 0


class TestPriorityReset:
    """Test resetting Elo ratings and comparison history."""

    def test_reset_single_task(self, comparison_service, task_dao):
        """Test resetting a single task's Elo rating."""
        task1 = Task(title="Winner", base_priority=2, due_date=date.today())
        task2 = Task(title="Loser", base_priority=2, due_date=date.today())

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)

        # Task2 loses multiple comparisons
        comparison_service.record_comparison(task1, task2)
        comparison_service.record_comparison(task1, task2)

        assert task_dao.get_by_id(task2.id).elo_rating < 1500.0
        assert task_dao.get_by_id(task2.id).comparison_count == 2

        # Reset task2
        reset_task = comparison_service.reset_task_priority_adjustment(task2.id)

        assert reset_task.elo_rating == 1500.0
        assert reset_task.comparison_count == 0

    def test_reset_deletes_comparison_history(self, comparison_service, comparison_dao, task_dao):
        """Test that resetting deletes comparison history."""
        task1 = Task(title="Winner", base_priority=2, due_date=date.today())
        task2 = Task(title="Loser", base_priority=2, due_date=date.today())

        task1 = task_dao.create(task1)
        task2 = task_dao.create(task2)

        comparison_service.record_comparison(task1, task2)

        # Verify comparison exists
        assert len(comparison_dao.get_all_comparisons()) == 1

        # Reset task2
        comparison_service.reset_task_priority_adjustment(task2.id)

        # Comparison history should be deleted
        assert len(comparison_dao.get_all_comparisons()) == 0

    def test_reset_all_priority_adjustments(self, comparison_service, task_dao):
        """Test resetting all tasks' Elo ratings."""
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
        assert count >= 2  # At least 2 tasks were modified

        # Verify all tasks are reset
        for task_id in [task1.id, task2.id, task3.id]:
            task = task_dao.get_by_id(task_id)
            assert task.elo_rating == 1500.0
            assert task.comparison_count == 0

    def test_reset_nonexistent_task(self, comparison_service):
        """Test resetting nonexistent task returns None."""
        result = comparison_service.reset_task_priority_adjustment(99999)
        assert result is None


class TestEloChangePreview:
    """Test Elo change preview calculation."""

    def test_preview_win_against_equal_opponent(self, comparison_service, task_dao):
        """Test preview for winning against equal-rated opponent."""
        task = Task(title="Task", base_priority=2, comparison_count=0)
        task = task_dao.create(task)

        preview = comparison_service.calculate_elo_change_preview(task, 1500.0)

        # Against equal opponent with new K-factor (32)
        # Expected: 0.5, Win change: 32 * (1 - 0.5) = 16
        assert abs(preview['if_win'] - 16.0) < 0.01
        assert abs(preview['if_lose'] - (-16.0)) < 0.01
        assert abs(preview['expected_score'] - 0.5) < 0.01
        assert preview['k_factor'] == 32

    def test_preview_win_against_weaker_opponent(self, comparison_service, task_dao):
        """Test preview for winning against weaker opponent."""
        task = Task(title="Task", base_priority=2, elo_rating=1600.0, comparison_count=15)
        task = task_dao.create(task)

        preview = comparison_service.calculate_elo_change_preview(task, 1400.0)

        # Stronger task has higher expected score, so wins less
        assert preview['if_win'] < 10.0  # Small gain expected
        assert preview['if_lose'] < -10.0  # Larger loss if upset


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_comparison_without_ids_raises_error(self, comparison_service):
        """Test that comparing tasks without IDs raises error."""
        task1 = Task(title="Winner", base_priority=2)
        task2 = Task(title="Loser", base_priority=2)

        with pytest.raises(ValueError, match="Both tasks must have IDs"):
            comparison_service.record_comparison(task1, task2)

    def test_comparison_with_one_id_missing(self, comparison_service, task_dao):
        """Test that comparing when one task has no ID raises error."""
        task1 = Task(title="Has ID", base_priority=2)
        task1 = task_dao.create(task1)

        task2 = Task(title="No ID", base_priority=2)

        with pytest.raises(ValueError, match="Both tasks must have IDs"):
            comparison_service.record_comparison(task1, task2)


class TestSharedEloForRecurringTasks:
    """Test shared Elo rating synchronization for recurring tasks."""

    def test_shared_elo_updates_parent(self, comparison_service, task_dao):
        """Test that shared Elo updates parent task."""
        # Create parent recurring task
        parent = Task(
            title="Parent Task",
            base_priority=2,
            due_date=date.today(),
            is_recurring=True,
            share_elo_rating=True
        )
        parent = task_dao.create(parent)

        # Create child task with shared Elo
        child = Task(
            title="Child Task",
            base_priority=2,
            due_date=date.today(),
            recurrence_parent_id=parent.id,
            share_elo_rating=True
        )
        child = task_dao.create(child)

        # Create another task to compare against
        other = Task(title="Other", base_priority=2, due_date=date.today())
        other = task_dao.create(other)

        # Child wins comparison
        comparison_service.record_comparison(child, other)

        # Child should have updated Elo
        updated_child = task_dao.get_by_id(child.id)
        assert updated_child.elo_rating > 1500.0

        # Parent should also have updated shared Elo
        updated_parent = task_dao.get_by_id(parent.id)
        assert updated_parent.shared_elo_rating == updated_child.elo_rating
