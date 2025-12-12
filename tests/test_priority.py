"""
Unit tests for priority and urgency calculation algorithms.
"""

import pytest
from datetime import date, timedelta
from src.models.task import Task
from src.models.enums import TaskState, Priority
from src.algorithms.priority import (
    calculate_urgency,
    calculate_urgency_for_tasks,
    calculate_effective_priority,
    calculate_importance,
    calculate_importance_for_tasks,
    get_task_score_breakdown
)


class TestUrgencyCalculation:
    """Test urgency score calculation."""

    def test_no_due_date_returns_lowest_urgency(self):
        """Task with no due date should get urgency = 1.0"""
        task = Task(title="Test Task", id=1)
        urgency = calculate_urgency(task)
        assert urgency == 1.0

    def test_urgency_for_tasks_with_no_due_dates(self):
        """All tasks without due dates get urgency = 1.0"""
        tasks = [
            Task(title="Task 1", id=1),
            Task(title="Task 2", id=2),
            Task(title="Task 3", id=3)
        ]
        urgencies = calculate_urgency_for_tasks(tasks)
        assert urgencies[1] == 1.0
        assert urgencies[2] == 1.0
        assert urgencies[3] == 1.0

    def test_single_task_with_due_date_gets_max_urgency(self):
        """Single task with due date gets urgency = 3.0"""
        task = Task(title="Task 1", id=1, due_date=date.today() + timedelta(days=5))
        urgencies = calculate_urgency_for_tasks([task])
        assert urgencies[1] == 3.0

    def test_earliest_due_date_gets_highest_urgency(self):
        """Task with earliest due date gets urgency = 3.0"""
        today = date.today()
        tasks = [
            Task(title="Task 1", id=1, due_date=today + timedelta(days=1)),  # Earliest
            Task(title="Task 2", id=2, due_date=today + timedelta(days=5)),
            Task(title="Task 3", id=3, due_date=today + timedelta(days=10))  # Latest
        ]
        urgencies = calculate_urgency_for_tasks(tasks, today)

        # Earliest gets 3.0
        assert urgencies[1] == 3.0
        # Latest gets 1.0
        assert urgencies[3] == 1.0
        # Middle is interpolated
        assert 1.0 < urgencies[2] < 3.0

    def test_overdue_task_gets_highest_urgency(self):
        """Overdue task should get highest urgency (3.0)"""
        today = date.today()
        tasks = [
            Task(title="Overdue", id=1, due_date=today - timedelta(days=3)),  # Overdue
            Task(title="Soon", id=2, due_date=today + timedelta(days=2)),
            Task(title="Later", id=3, due_date=today + timedelta(days=7))
        ]
        urgencies = calculate_urgency_for_tasks(tasks, today)

        # Overdue is earliest (most urgent)
        assert urgencies[1] == 3.0
        assert urgencies[3] == 1.0

    def test_same_due_date_all_get_max_urgency(self):
        """Tasks with same due date all get urgency = 3.0"""
        due = date.today() + timedelta(days=3)
        tasks = [
            Task(title="Task 1", id=1, due_date=due),
            Task(title="Task 2", id=2, due_date=due),
            Task(title="Task 3", id=3, due_date=due)
        ]
        urgencies = calculate_urgency_for_tasks(tasks)
        assert urgencies[1] == 3.0
        assert urgencies[2] == 3.0
        assert urgencies[3] == 3.0

    def test_mixed_tasks_with_and_without_dates(self):
        """Mix of tasks with/without due dates"""
        today = date.today()
        tasks = [
            Task(title="No date 1", id=1),
            Task(title="Due soon", id=2, due_date=today + timedelta(days=1)),
            Task(title="No date 2", id=3),
            Task(title="Due later", id=4, due_date=today + timedelta(days=10))
        ]
        urgencies = calculate_urgency_for_tasks(tasks, today)

        # No dates get 1.0
        assert urgencies[1] == 1.0
        assert urgencies[3] == 1.0

        # With dates: earliest = 3.0, latest = 1.0
        assert urgencies[2] == 3.0
        assert urgencies[4] == 1.0


class TestEffectivePriority:
    """Test effective priority calculation."""

    def test_no_adjustment_returns_base_priority(self):
        """Effective priority = base priority when adjustment is 0"""
        task = Task(title="Test", base_priority=3, priority_adjustment=0.0)
        assert calculate_effective_priority(task) == 3.0

    def test_with_adjustment_subtracts_correctly(self):
        """Effective priority = base - adjustment"""
        task = Task(title="Test", base_priority=3, priority_adjustment=0.5)
        assert calculate_effective_priority(task) == 2.5

    def test_adjustment_never_drops_below_one(self):
        """Priority adjustment should never exceed base - 1"""
        # Per Zeno's Paradox, adjustment approaches but never reaches 1.0
        task = Task(title="Test", base_priority=3, priority_adjustment=0.875)
        assert calculate_effective_priority(task) == 2.125
        assert calculate_effective_priority(task) >= 1.0


class TestImportanceCalculation:
    """Test importance score calculation."""

    def test_importance_is_priority_times_urgency(self):
        """Importance = Effective Priority × Urgency"""
        task = Task(title="Test", base_priority=3, priority_adjustment=0.0)
        urgency = 2.0
        importance = calculate_importance(task, urgency)
        assert importance == 6.0  # 3.0 * 2.0

    def test_max_importance_score(self):
        """Max importance = 9.0 (High priority × max urgency)"""
        task = Task(title="Test", base_priority=3, priority_adjustment=0.0)
        urgency = 3.0
        importance = calculate_importance(task, urgency)
        assert importance == 9.0

    def test_adjusted_priority_affects_importance(self):
        """Priority adjustment reduces importance score"""
        task = Task(title="Test", base_priority=3, priority_adjustment=0.5)
        urgency = 3.0
        importance = calculate_importance(task, urgency)
        assert importance == 7.5  # 2.5 * 3.0

    def test_importance_for_multiple_tasks(self):
        """Calculate importance for multiple tasks"""
        today = date.today()
        tasks = [
            Task(
                title="High + Soon",
                id=1,
                base_priority=3,
                due_date=today + timedelta(days=1)
            ),
            Task(
                title="Low + Later",
                id=2,
                base_priority=1,
                due_date=today + timedelta(days=10)
            ),
            Task(
                title="Medium + No date",
                id=3,
                base_priority=2
            )
        ]
        importance_scores = calculate_importance_for_tasks(tasks, today)

        # High priority + earliest date should have highest importance
        assert importance_scores[1] > importance_scores[2]
        assert importance_scores[1] > importance_scores[3]


class TestScoreBreakdown:
    """Test score breakdown for debugging."""

    def test_score_breakdown_includes_all_fields(self):
        """Score breakdown should include all scoring components"""
        task = Task(
            title="Test Task",
            id=1,
            base_priority=3,
            priority_adjustment=0.5,
            due_date=date(2024, 6, 15)
        )
        urgency = 2.5
        breakdown = get_task_score_breakdown(task, urgency)

        assert breakdown['task_id'] == 1
        assert breakdown['title'] == "Test Task"
        assert breakdown['base_priority'] == 3
        assert breakdown['priority_adjustment'] == 0.5
        assert breakdown['effective_priority'] == 2.5
        assert breakdown['urgency'] == 2.5
        assert breakdown['importance'] == 6.25  # 2.5 * 2.5
        assert breakdown['due_date'] == '2024-06-15'

    def test_score_breakdown_no_due_date(self):
        """Score breakdown handles tasks without due dates"""
        task = Task(title="Test", id=1, base_priority=2)
        urgency = 1.0
        breakdown = get_task_score_breakdown(task, urgency)

        assert breakdown['due_date'] is None
        assert breakdown['urgency'] == 1.0
