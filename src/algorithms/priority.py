"""
Priority and urgency calculation algorithms for OneTaskAtATime.

This module implements the core task scoring system:
- Effective Priority = Base Priority - Priority Adjustment
- Urgency = 1-3 based on days until due date
- Importance = Effective Priority × Urgency
"""

from datetime import date
from typing import List, Optional
from ..models.task import Task


def calculate_urgency(task: Task, today: Optional[date] = None) -> float:
    """
    Calculate urgency score (1-3) based on days until due date.

    Algorithm:
    - Tasks with no due date get urgency = 1.0 (lowest)
    - Task with earliest due date (including overdue) gets urgency = 3.0 (highest)
    - Other tasks scored on normalized scale (latest due date = 1.0)

    Args:
        task: The task to calculate urgency for
        today: Reference date (defaults to today)

    Returns:
        Urgency score between 1.0 and 3.0
    """
    if today is None:
        today = date.today()

    # No due date = lowest urgency
    if task.due_date is None:
        return 1.0

    # Calculate days remaining (negative if overdue)
    days_remaining = (task.due_date - today).days

    return float(days_remaining)


def calculate_urgency_for_tasks(tasks: List[Task], today: Optional[date] = None) -> dict[int, float]:
    """
    Calculate urgency scores for a list of tasks using normalization.

    This function must be called with all candidate tasks to properly normalize urgency.
    The task with the earliest due date gets 3.0, latest gets 1.0.

    Args:
        tasks: List of tasks to score
        today: Reference date (defaults to today)

    Returns:
        Dictionary mapping task.id to urgency score
    """
    if today is None:
        today = date.today()

    urgency_scores = {}

    # Separate tasks with and without due dates
    tasks_with_dates = [t for t in tasks if t.due_date is not None]
    tasks_without_dates = [t for t in tasks if t.due_date is None]

    # Tasks without due dates get lowest urgency
    for task in tasks_without_dates:
        if task.id is not None:
            urgency_scores[task.id] = 1.0

    # If no tasks have due dates, we're done
    if not tasks_with_dates:
        return urgency_scores

    # Calculate days remaining for all tasks with due dates
    days_remaining_list = []
    for task in tasks_with_dates:
        days = (task.due_date - today).days  # type: ignore
        days_remaining_list.append((task, days))

    # If only one task has a due date, it gets max urgency
    if len(days_remaining_list) == 1:
        task, _ = days_remaining_list[0]
        if task.id is not None:
            urgency_scores[task.id] = 3.0
        return urgency_scores

    # Find min and max days remaining
    min_days = min(days for _, days in days_remaining_list)
    max_days = max(days for _, days in days_remaining_list)

    # If all tasks have same due date
    if min_days == max_days:
        for task, _ in days_remaining_list:
            if task.id is not None:
                urgency_scores[task.id] = 3.0
        return urgency_scores

    # Normalize: earliest (lowest days) = 3.0, latest (highest days) = 1.0
    for task, days in days_remaining_list:
        if task.id is not None:
            # Linear interpolation from [min_days, max_days] to [3.0, 1.0]
            normalized = 3.0 - ((days - min_days) / (max_days - min_days)) * 2.0
            urgency_scores[task.id] = normalized

    return urgency_scores


def calculate_effective_priority(task: Task) -> float:
    """
    Calculate effective priority after adjustments.

    Effective Priority = Base Priority - Priority Adjustment

    Args:
        task: The task to calculate effective priority for

    Returns:
        Effective priority (always >= 1.0 due to Zeno's Paradox constraint)
    """
    return task.get_effective_priority()


def calculate_importance(task: Task, urgency: float) -> float:
    """
    Calculate importance score (Effective Priority × Urgency).

    Args:
        task: The task to score
        urgency: Pre-calculated urgency score

    Returns:
        Importance score (max = 9.0 for High priority + max urgency)
    """
    effective_priority = calculate_effective_priority(task)
    return effective_priority * urgency


def calculate_importance_for_tasks(tasks: List[Task], today: Optional[date] = None) -> dict[int, float]:
    """
    Calculate importance scores for a list of tasks.

    This is the primary scoring function for ranking tasks.

    Args:
        tasks: List of tasks to score
        today: Reference date (defaults to today)

    Returns:
        Dictionary mapping task.id to importance score
    """
    # First calculate urgency for all tasks (requires normalization)
    urgency_scores = calculate_urgency_for_tasks(tasks, today)

    # Then calculate importance
    importance_scores = {}
    for task in tasks:
        if task.id is not None:
            urgency = urgency_scores.get(task.id, 1.0)
            importance_scores[task.id] = calculate_importance(task, urgency)

    return importance_scores


def get_task_score_breakdown(task: Task, urgency: float) -> dict:
    """
    Get detailed breakdown of task scoring for debugging/display.

    Args:
        task: The task to analyze
        urgency: Pre-calculated urgency score

    Returns:
        Dictionary with scoring components
    """
    effective_priority = calculate_effective_priority(task)
    importance = calculate_importance(task, urgency)

    return {
        'task_id': task.id,
        'title': task.title,
        'base_priority': task.base_priority,
        'priority_adjustment': task.priority_adjustment,
        'effective_priority': effective_priority,
        'urgency': urgency,
        'importance': importance,
        'due_date': task.due_date.isoformat() if task.due_date else None,
    }
