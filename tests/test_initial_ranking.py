"""
Tests for initial ranking algorithm.

Tests the sequential ranking system that prevents new tasks from being
buried in the middle of their priority band.
"""

import pytest
from datetime import date
from src.models.task import Task
from src.models.enums import TaskState
from src.algorithms.initial_ranking import (
    get_new_tasks_in_priority_band,
    get_top_task_in_band,
    get_bottom_task_in_band,
    get_ranking_candidates,
    calculate_elo_from_rank_position,
    assign_elo_ratings_from_ranking,
    check_for_new_tasks
)


def create_task(title: str, base_priority: int, elo_rating: float = 1500.0, comparison_count: int = 0, state: TaskState = TaskState.ACTIVE) -> Task:
    """Helper to create a test task."""
    task = Task(
        title=title,
        state=state,
        base_priority=base_priority
    )
    task.elo_rating = elo_rating
    task.comparison_count = comparison_count
    task.id = hash(title) % 10000  # Generate a simple ID for testing
    return task


class TestGetNewTasksInPriorityBand:
    """Tests for get_new_tasks_in_priority_band."""

    def test_filters_by_priority_band(self):
        """Should only return tasks from specified priority band."""
        tasks = [
            create_task("High New", 3, comparison_count=0),
            create_task("Medium New", 2, comparison_count=0),
            create_task("Low New", 1, comparison_count=0),
        ]

        high_new = get_new_tasks_in_priority_band(tasks, 3)
        assert len(high_new) == 1
        assert high_new[0].title == "High New"

    def test_filters_by_comparison_count(self):
        """Should only return tasks with comparison_count = 0."""
        tasks = [
            create_task("New Task", 2, comparison_count=0),
            create_task("Existing Task", 2, comparison_count=5),
        ]

        new_tasks = get_new_tasks_in_priority_band(tasks, 2)
        assert len(new_tasks) == 1
        assert new_tasks[0].title == "New Task"

    def test_returns_empty_when_no_new_tasks(self):
        """Should return empty list when no new tasks in band."""
        tasks = [
            create_task("Existing 1", 2, comparison_count=5),
            create_task("Existing 2", 2, comparison_count=10),
        ]

        new_tasks = get_new_tasks_in_priority_band(tasks, 2)
        assert len(new_tasks) == 0

    def test_filters_non_active_tasks(self):
        """Should filter out non-active tasks when active_only=True."""
        tasks = [
            create_task("Active New", 2, comparison_count=0, state=TaskState.ACTIVE),
            create_task("Completed New", 2, comparison_count=0, state=TaskState.COMPLETED),
            create_task("Deferred New", 2, comparison_count=0, state=TaskState.DEFERRED),
        ]

        new_tasks = get_new_tasks_in_priority_band(tasks, 2, active_only=True)
        assert len(new_tasks) == 1
        assert new_tasks[0].title == "Active New"

    def test_includes_non_active_when_disabled(self):
        """Should include all tasks when active_only=False."""
        tasks = [
            create_task("Active New", 2, comparison_count=0, state=TaskState.ACTIVE),
            create_task("Completed New", 2, comparison_count=0, state=TaskState.COMPLETED),
        ]

        new_tasks = get_new_tasks_in_priority_band(tasks, 2, active_only=False)
        assert len(new_tasks) == 2

    def test_limits_to_specified_count(self):
        """Should limit returned tasks when limit parameter is provided."""
        tasks = [
            create_task(f"New {i}", 2, comparison_count=0) for i in range(10)
        ]

        new_tasks = get_new_tasks_in_priority_band(tasks, 2, limit=3)
        assert len(new_tasks) == 3


class TestGetTopBottomTasks:
    """Tests for getting top and bottom tasks in a band."""

    def test_get_top_task_by_elo(self):
        """Should return task with highest Elo in band."""
        tasks = [
            create_task("Low Elo", 2, elo_rating=1400.0),
            create_task("High Elo", 2, elo_rating=1600.0),
            create_task("Medium Elo", 2, elo_rating=1500.0),
        ]

        top = get_top_task_in_band(tasks, 2)
        assert top is not None
        assert top.title == "High Elo"

    def test_get_bottom_task_by_elo(self):
        """Should return task with lowest Elo in band."""
        tasks = [
            create_task("Low Elo", 2, elo_rating=1400.0),
            create_task("High Elo", 2, elo_rating=1600.0),
            create_task("Medium Elo", 2, elo_rating=1500.0),
        ]

        bottom = get_bottom_task_in_band(tasks, 2)
        assert bottom is not None
        assert bottom.title == "Low Elo"

    def test_returns_none_when_no_tasks_in_band(self):
        """Should return None when no tasks in specified band."""
        tasks = [
            create_task("High Priority", 3, elo_rating=1500.0),
        ]

        top = get_top_task_in_band(tasks, 2)
        bottom = get_bottom_task_in_band(tasks, 2)

        assert top is None
        assert bottom is None

    def test_filters_non_active_tasks(self):
        """Should filter out non-active tasks when active_only=True."""
        tasks = [
            create_task("Active Low", 2, elo_rating=1400.0, comparison_count=5, state=TaskState.ACTIVE),
            create_task("Completed High", 2, elo_rating=1600.0, comparison_count=5, state=TaskState.COMPLETED),
        ]

        # With active_only=True, should only see Active task
        top = get_top_task_in_band(tasks, 2, active_only=True)
        assert top is not None
        assert top.title == "Active Low"  # Only active task

    def test_includes_non_active_when_disabled(self):
        """Should include all tasks when active_only=False."""
        tasks = [
            create_task("Active Low", 2, elo_rating=1400.0, comparison_count=5, state=TaskState.ACTIVE),
            create_task("Completed High", 2, elo_rating=1600.0, comparison_count=5, state=TaskState.COMPLETED),
        ]

        # With active_only=False, should see the highest Elo
        top = get_top_task_in_band(tasks, 2, active_only=False)
        assert top is not None
        assert top.title == "Completed High"


class TestGetRankingCandidates:
    """Tests for get_ranking_candidates."""

    def test_includes_new_tasks(self):
        """Should include all new tasks in candidates."""
        new_tasks = [
            create_task("New 1", 2, comparison_count=0),
            create_task("New 2", 2, comparison_count=0),
        ]
        all_tasks = new_tasks + [
            create_task("Existing", 2, elo_rating=1500.0, comparison_count=5),
        ]

        candidates = get_ranking_candidates(all_tasks, new_tasks, 2)

        # Should have both new tasks (order randomized)
        new_titles = [t.title for t in candidates if t.comparison_count == 0]
        assert "New 1" in new_titles
        assert "New 2" in new_titles

    def test_includes_top_and_bottom_existing(self):
        """Should include top and bottom existing tasks."""
        new_tasks = [
            create_task("New", 2, comparison_count=0),
        ]
        all_tasks = new_tasks + [
            create_task("Top", 2, elo_rating=1700.0, comparison_count=5),
            create_task("Middle", 2, elo_rating=1500.0, comparison_count=5),
            create_task("Bottom", 2, elo_rating=1300.0, comparison_count=5),
        ]

        candidates = get_ranking_candidates(all_tasks, new_tasks, 2)

        # Should have new task + top + bottom
        existing_titles = [t.title for t in candidates if t.comparison_count > 0]
        assert "Top" in existing_titles
        assert "Bottom" in existing_titles
        assert "Middle" not in existing_titles  # Should exclude middle task

    def test_handles_single_existing_task(self):
        """Should handle case where only one existing task exists."""
        new_tasks = [
            create_task("New", 2, comparison_count=0),
        ]
        all_tasks = new_tasks + [
            create_task("Only Existing", 2, elo_rating=1500.0, comparison_count=5),
        ]

        candidates = get_ranking_candidates(all_tasks, new_tasks, 2)

        # Should have new task + one existing (not duplicated)
        assert len(candidates) == 2

    def test_handles_no_existing_tasks(self):
        """Should handle case where no existing tasks exist."""
        new_tasks = [
            create_task("New 1", 2, comparison_count=0),
            create_task("New 2", 2, comparison_count=0),
        ]
        all_tasks = new_tasks

        candidates = get_ranking_candidates(all_tasks, new_tasks, 2)

        # Should only have new tasks
        assert len(candidates) == 2
        assert all(t.comparison_count == 0 for t in candidates)

    def test_limits_new_tasks_to_three(self):
        """Should limit to 3 new tasks when more are provided."""
        new_tasks = [
            create_task(f"New {i}", 2, comparison_count=0) for i in range(10)
        ]
        all_tasks = new_tasks

        candidates = get_ranking_candidates(all_tasks, new_tasks, 2)

        # Should have exactly 3 new tasks
        new_in_candidates = [t for t in candidates if t.comparison_count == 0]
        assert len(new_in_candidates) == 3

    def test_max_five_tasks_total(self):
        """Should return max 5 tasks (3 new + top + bottom)."""
        new_tasks = [
            create_task(f"New {i}", 2, comparison_count=0) for i in range(10)
        ]
        all_tasks = new_tasks + [
            create_task("Top", 2, elo_rating=1700.0, comparison_count=5),
            create_task("Bottom", 2, elo_rating=1300.0, comparison_count=5),
        ]

        candidates = get_ranking_candidates(all_tasks, new_tasks, 2)

        # Should have max 5 tasks total
        assert len(candidates) <= 5

    def test_filters_non_active_existing_tasks(self):
        """Should filter out non-active existing tasks when active_only=True."""
        new_tasks = [
            create_task("New", 2, comparison_count=0, state=TaskState.ACTIVE),
        ]
        all_tasks = new_tasks + [
            create_task("Active Top", 2, elo_rating=1700.0, comparison_count=5, state=TaskState.ACTIVE),
            create_task("Completed High", 2, elo_rating=1800.0, comparison_count=5, state=TaskState.COMPLETED),
            create_task("Active Bottom", 2, elo_rating=1300.0, comparison_count=5, state=TaskState.ACTIVE),
        ]

        candidates = get_ranking_candidates(all_tasks, new_tasks, 2, active_only=True)

        # Should only include active existing tasks
        existing = [t for t in candidates if t.comparison_count > 0]
        assert all(t.state == TaskState.ACTIVE for t in existing)
        assert len(existing) == 2  # Top and bottom active tasks


class TestCalculateEloFromRankPosition:
    """Tests for Elo calculation from rank position."""

    def test_first_position_gets_top_elo(self):
        """First ranked task should get top Elo rating."""
        elo = calculate_elo_from_rank_position(0, 3, 1700.0, 1300.0)
        assert elo == 1700.0

    def test_last_position_gets_bottom_elo(self):
        """Last ranked task should get bottom Elo rating."""
        elo = calculate_elo_from_rank_position(2, 3, 1700.0, 1300.0)
        assert elo == 1300.0

    def test_middle_position_interpolates(self):
        """Middle ranked task should get interpolated Elo rating."""
        elo = calculate_elo_from_rank_position(1, 3, 1700.0, 1300.0)
        assert elo == 1500.0  # Exactly halfway

    def test_single_task_gets_midpoint(self):
        """Single task should get midpoint of range."""
        elo = calculate_elo_from_rank_position(0, 1, 1700.0, 1300.0)
        assert elo == 1500.0


class TestAssignEloRatingsFromRanking:
    """Tests for assigning Elo ratings based on ranking."""

    def test_assigns_ratings_in_rank_order(self):
        """Should assign highest Elo to first ranked task."""
        tasks = [
            create_task("First", 2, comparison_count=0),
            create_task("Second", 2, comparison_count=0),
            create_task("Third", 2, comparison_count=0),
        ]

        assignments = assign_elo_ratings_from_ranking(
            tasks,
            existing_top_elo=1700.0,
            existing_bottom_elo=1300.0,
            base_priority=2
        )

        # First task should have highest Elo
        assert assignments[0][0].title == "First"
        assert assignments[0][1] == 1700.0

        # Last task should have lowest Elo
        assert assignments[2][0].title == "Third"
        assert assignments[2][1] == 1300.0

        # Middle task should be interpolated
        assert assignments[1][0].title == "Second"
        assert assignments[1][1] == 1500.0

    def test_uses_default_range_when_no_existing_tasks(self):
        """Should use default Elo range when no existing tasks."""
        tasks = [
            create_task("Only", 2, comparison_count=0),
        ]

        assignments = assign_elo_ratings_from_ranking(
            tasks,
            existing_top_elo=None,
            existing_bottom_elo=None,
            base_priority=2
        )

        # Should use default range (1300-1700, midpoint 1500)
        assert len(assignments) == 1
        assert assignments[0][1] == 1500.0

    def test_handles_empty_list(self):
        """Should handle empty task list."""
        assignments = assign_elo_ratings_from_ranking([], base_priority=2)
        assert len(assignments) == 0


class TestCheckForNewTasks:
    """Tests for checking if there are new tasks."""

    def test_detects_new_tasks_in_highest_band(self):
        """Should detect new tasks in highest priority band."""
        tasks = [
            create_task("High New", 3, comparison_count=0),
            create_task("Medium New", 2, comparison_count=0),
        ]

        has_new, priority, new_tasks = check_for_new_tasks(tasks)

        assert has_new is True
        assert priority == 3  # Should return highest band
        assert len(new_tasks) == 1
        assert new_tasks[0].title == "High New"

    def test_returns_false_when_no_new_tasks(self):
        """Should return False when all tasks have been ranked."""
        tasks = [
            create_task("Existing 1", 3, comparison_count=5),
            create_task("Existing 2", 2, comparison_count=10),
        ]

        has_new, priority, new_tasks = check_for_new_tasks(tasks)

        assert has_new is False
        assert priority == 0
        assert len(new_tasks) == 0

    def test_prioritizes_high_over_medium(self):
        """Should return high priority new tasks before medium."""
        tasks = [
            create_task("Medium New", 2, comparison_count=0),
            create_task("High New", 3, comparison_count=0),
        ]

        has_new, priority, new_tasks = check_for_new_tasks(tasks)

        assert has_new is True
        assert priority == 3
        assert all(t.base_priority == 3 for t in new_tasks)
