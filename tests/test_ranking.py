"""
Unit tests for task ranking algorithms.
"""

import pytest
from datetime import date, timedelta
from src.models.task import Task
from src.models.enums import TaskState, Priority
from src.algorithms.ranking import (
    get_actionable_tasks,
    rank_tasks,
    get_top_ranked_tasks,
    get_next_focus_task,
    get_tied_tasks,
    has_tied_tasks,
    get_ranking_summary
)


class TestActionableTasksFilter:
    """Test filtering of actionable tasks."""

    def test_active_unblocked_task_is_actionable(self):
        """Active task with no blockers is actionable"""
        task = Task(title="Active Task", id=1, state=TaskState.ACTIVE)
        actionable = get_actionable_tasks([task])
        assert len(actionable) == 1
        assert actionable[0].id == 1

    def test_completed_task_not_actionable(self):
        """Completed tasks are not actionable"""
        task = Task(title="Done", id=1, state=TaskState.COMPLETED)
        actionable = get_actionable_tasks([task])
        assert len(actionable) == 0

    def test_deferred_task_not_actionable(self):
        """Deferred tasks are not actionable"""
        task = Task(title="Deferred", id=1, state=TaskState.DEFERRED)
        actionable = get_actionable_tasks([task])
        assert len(actionable) == 0

    def test_someday_task_not_actionable(self):
        """Someday tasks are not actionable"""
        task = Task(title="Someday", id=1, state=TaskState.SOMEDAY)
        actionable = get_actionable_tasks([task])
        assert len(actionable) == 0

    def test_trash_task_not_actionable(self):
        """Trash tasks are not actionable"""
        task = Task(title="Trash", id=1, state=TaskState.TRASH)
        actionable = get_actionable_tasks([task])
        assert len(actionable) == 0

    def test_blocked_task_not_actionable(self):
        """Tasks with dependencies are not actionable"""
        task = Task(
            title="Blocked",
            id=1,
            state=TaskState.ACTIVE,
            blocking_task_ids=[2, 3]  # Has dependencies
        )
        actionable = get_actionable_tasks([task])
        assert len(actionable) == 0

    def test_future_start_date_not_actionable(self):
        """Tasks with future start_date are not actionable"""
        future = date.today() + timedelta(days=5)
        task = Task(
            title="Future",
            id=1,
            state=TaskState.ACTIVE,
            start_date=future
        )
        actionable = get_actionable_tasks([task])
        assert len(actionable) == 0

    def test_past_start_date_is_actionable(self):
        """Tasks with past start_date are actionable"""
        past = date.today() - timedelta(days=5)
        task = Task(
            title="Ready",
            id=1,
            state=TaskState.ACTIVE,
            start_date=past
        )
        actionable = get_actionable_tasks([task])
        assert len(actionable) == 1

    def test_mixed_task_list(self):
        """Filter mixed list of tasks correctly"""
        tasks = [
            Task(title="Active 1", id=1, state=TaskState.ACTIVE),
            Task(title="Completed", id=2, state=TaskState.COMPLETED),
            Task(title="Active 2", id=3, state=TaskState.ACTIVE),
            Task(title="Blocked", id=4, state=TaskState.ACTIVE, blocking_task_ids=[1]),
            Task(title="Deferred", id=5, state=TaskState.DEFERRED)
        ]
        actionable = get_actionable_tasks(tasks)
        assert len(actionable) == 2
        assert {t.id for t in actionable} == {1, 3}


class TestTaskRanking:
    """Test task ranking by importance score."""

    def test_rank_empty_list(self):
        """Ranking empty list returns empty list"""
        ranked = rank_tasks([])
        assert ranked == []

    def test_rank_single_task(self):
        """Ranking single task returns it with score"""
        task = Task(title="Only Task", id=1, base_priority=2)
        ranked = rank_tasks([task])
        assert len(ranked) == 1
        assert ranked[0][0].id == 1
        assert ranked[0][1] > 0  # Has some score

    def test_rank_by_priority(self):
        """Higher priority tasks rank higher (same urgency)"""
        tasks = [
            Task(title="Low", id=1, base_priority=1),
            Task(title="High", id=2, base_priority=3),
            Task(title="Medium", id=3, base_priority=2)
        ]
        ranked = rank_tasks(tasks)

        # Should be sorted: High, Medium, Low
        assert ranked[0][0].id == 2
        assert ranked[1][0].id == 3
        assert ranked[2][0].id == 1

    def test_rank_by_urgency(self):
        """Earlier due dates rank higher (same priority)"""
        today = date.today()
        tasks = [
            Task(title="Later", id=1, base_priority=2, due_date=today + timedelta(days=10)),
            Task(title="Soon", id=2, base_priority=2, due_date=today + timedelta(days=1)),
            Task(title="Medium", id=3, base_priority=2, due_date=today + timedelta(days=5))
        ]
        ranked = rank_tasks(tasks, today)

        # Should be sorted by urgency: Soon, Medium, Later
        assert ranked[0][0].id == 2
        assert ranked[1][0].id == 3
        assert ranked[2][0].id == 1

    def test_rank_with_priority_adjustment(self):
        """Priority adjustment affects ranking"""
        tasks = [
            Task(title="High Adjusted", id=1, base_priority=3, priority_adjustment=1.0),
            Task(title="Medium", id=2, base_priority=2, priority_adjustment=0.0)
        ]
        ranked = rank_tasks(tasks)

        # High (3 - 1 = 2.0) should now tie or lose to Medium (2.0)
        # Check that adjustment had an effect
        score_1 = ranked[0][1]
        score_2 = ranked[1][1]
        assert abs(score_1 - score_2) < 0.5  # Should be close now


class TestTopRankedTasks:
    """Test getting top-ranked tasks (tie detection)."""

    def test_single_top_task(self):
        """Single task with clear top score"""
        tasks = [
            Task(title="Top", id=1, base_priority=3),
            Task(title="Lower", id=2, base_priority=1)
        ]
        top = get_top_ranked_tasks(tasks)
        assert len(top) == 1
        assert top[0].id == 1

    def test_multiple_tied_tasks(self):
        """Multiple tasks with same top score"""
        tasks = [
            Task(title="Tied 1", id=1, base_priority=2),
            Task(title="Tied 2", id=2, base_priority=2),
            Task(title="Lower", id=3, base_priority=1)
        ]
        top = get_top_ranked_tasks(tasks)
        assert len(top) == 2
        assert {t.id for t in top} == {1, 2}

    def test_epsilon_tolerance(self):
        """Tasks within epsilon are considered tied"""
        tasks = [
            Task(title="Task 1", id=1, base_priority=3, priority_adjustment=0.0),
            Task(title="Task 2", id=2, base_priority=3, priority_adjustment=0.005),  # Very small adjustment
            Task(title="Task 3", id=3, base_priority=2, priority_adjustment=0.0)
        ]
        top = get_top_ranked_tasks(tasks)
        # Tasks 1 and 2 should be considered tied (within epsilon)
        assert len(top) >= 2


class TestNextFocusTask:
    """Test getting the single next task for Focus Mode."""

    def test_single_active_task_returned(self):
        """Single active task is returned"""
        task = Task(title="Only Task", id=1, state=TaskState.ACTIVE)
        focus = get_next_focus_task([task])
        assert focus is not None
        assert focus.id == 1

    def test_no_active_tasks_returns_none(self):
        """No active tasks returns None"""
        tasks = [
            Task(title="Completed", id=1, state=TaskState.COMPLETED),
            Task(title="Deferred", id=2, state=TaskState.DEFERRED)
        ]
        focus = get_next_focus_task(tasks)
        assert focus is None

    def test_clear_winner_returned(self):
        """Task with highest importance is returned"""
        tasks = [
            Task(title="Low", id=1, state=TaskState.ACTIVE, base_priority=1),
            Task(title="High", id=2, state=TaskState.ACTIVE, base_priority=3),
            Task(title="Medium", id=3, state=TaskState.ACTIVE, base_priority=2)
        ]
        focus = get_next_focus_task(tasks)
        assert focus is not None
        assert focus.id == 2

    def test_tied_tasks_returns_none(self):
        """Multiple tied tasks returns None (requires comparison)"""
        tasks = [
            Task(title="Tied 1", id=1, state=TaskState.ACTIVE, base_priority=2),
            Task(title="Tied 2", id=2, state=TaskState.ACTIVE, base_priority=2)
        ]
        focus = get_next_focus_task(tasks)
        assert focus is None  # Tie requires user comparison

    def test_blocked_task_excluded(self):
        """Blocked tasks are not considered"""
        tasks = [
            Task(title="Blocked High", id=1, state=TaskState.ACTIVE,
                 base_priority=3, blocking_task_ids=[2]),
            Task(title="Lower but actionable", id=2, state=TaskState.ACTIVE,
                 base_priority=2)
        ]
        focus = get_next_focus_task(tasks)
        assert focus is not None
        assert focus.id == 2  # Unblocked task wins


class TestTieDetection:
    """Test tie detection helpers."""

    def test_no_tied_tasks(self):
        """Clear ranking has no ties"""
        tasks = [
            Task(title="High", id=1, state=TaskState.ACTIVE, base_priority=3),
            Task(title="Low", id=2, state=TaskState.ACTIVE, base_priority=1)
        ]
        assert has_tied_tasks(tasks) is False
        assert get_tied_tasks(tasks) == []

    def test_has_tied_tasks(self):
        """Detects tied tasks"""
        tasks = [
            Task(title="Tied 1", id=1, state=TaskState.ACTIVE, base_priority=2),
            Task(title="Tied 2", id=2, state=TaskState.ACTIVE, base_priority=2)
        ]
        assert has_tied_tasks(tasks) is True
        tied = get_tied_tasks(tasks)
        assert len(tied) == 2

    def test_single_task_no_tie(self):
        """Single task is not a tie"""
        task = Task(title="Only", id=1, state=TaskState.ACTIVE)
        assert has_tied_tasks([task]) is False
        assert get_tied_tasks([task]) == []


class TestRankingSummary:
    """Test ranking summary generation."""

    def test_summary_format(self):
        """Summary includes task info"""
        tasks = [
            Task(title="High Priority Task", id=1, state=TaskState.ACTIVE, base_priority=3),
            Task(title="Low Priority Task", id=2, state=TaskState.ACTIVE, base_priority=1)
        ]
        summary = get_ranking_summary(tasks)

        assert "Task Rankings" in summary
        assert "High Priority Task" in summary
        assert "Low Priority Task" in summary

    def test_summary_limits_to_top_n(self):
        """Summary respects top_n parameter"""
        tasks = [
            Task(title=f"Task {i}", id=i, state=TaskState.ACTIVE, base_priority=2)
            for i in range(1, 21)  # 20 tasks
        ]
        summary = get_ranking_summary(tasks, top_n=5)

        # Should mention showing top 5
        assert "top 5" in summary.lower()
