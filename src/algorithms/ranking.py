"""
Task ranking algorithms for OneTaskAtATime.

This module handles:
- Ranking tasks by importance score
- Detecting ties that require user comparison
- Filtering tasks eligible for Focus Mode
"""

from datetime import date
from typing import List, Optional, Tuple, Set
from ..models.task import Task
from ..models.enums import TaskState
from .priority import calculate_importance_for_tasks


# Epsilon for floating-point comparison (tasks within this range are "tied")
IMPORTANCE_EPSILON = 0.01


def get_actionable_tasks(
    tasks: List[Task],
    context_filter: Optional[int] = None,
    tag_filters: Optional[Set[int]] = None
) -> List[Task]:
    """
    Filter tasks that should appear in Focus Mode.

    Rules:
    - Must be in ACTIVE state
    - Must not have unresolved dependencies (not blocked)
    - Must not have a start_date in the future (deferred tasks should be DEFERRED state)
    - Must match context filter (if specified)
    - Must match at least one tag filter (if specified) - OR condition

    Args:
        tasks: List of all tasks
        context_filter: Optional context ID to filter by (single selection), or 'NONE' for tasks with no context
        tag_filters: Optional set of tag IDs to filter by (multiple selection with OR condition)

    Returns:
        List of tasks eligible for Focus Mode
    """
    actionable = []
    today = date.today()

    for task in tasks:
        # Must be active
        if task.state != TaskState.ACTIVE:
            continue

        # Must not be blocked
        if task.is_blocked():
            continue

        # If it has a start_date in the future, skip it
        # (These should be in DEFERRED state, but double-check)
        if task.start_date is not None and task.start_date > today:
            continue

        # Apply context filter (single selection)
        if context_filter is not None:
            if context_filter == "NONE":
                # Filter for tasks with no context
                if task.context_id is not None:
                    continue
            else:
                # Filter for tasks with specific context
                if task.context_id != context_filter:
                    continue

        # Apply tag filters (multiple selection with OR condition)
        if tag_filters:
            # Task must have at least one of the filtered tags
            if not task.project_tags or not any(tag_id in tag_filters for tag_id in task.project_tags):
                continue

        actionable.append(task)

    return actionable


def rank_tasks(tasks: List[Task], today: Optional[date] = None) -> List[Tuple[Task, float]]:
    """
    Rank tasks by importance score in descending order.

    Args:
        tasks: List of tasks to rank
        today: Reference date for urgency calculation (defaults to today)

    Returns:
        List of (task, importance_score) tuples, sorted highest to lowest
    """
    if not tasks:
        return []

    # Calculate importance for all tasks
    importance_scores = calculate_importance_for_tasks(tasks, today)

    # Create list of (task, score) tuples
    ranked = []
    for task in tasks:
        if task.id is not None:
            score = importance_scores.get(task.id, 0.0)
            ranked.append((task, score))

    # Sort by importance descending
    ranked.sort(key=lambda x: x[1], reverse=True)

    return ranked


def get_top_ranked_tasks(tasks: List[Task], today: Optional[date] = None) -> List[Task]:
    """
    Get all tasks tied for highest importance score.

    If multiple tasks have importance scores within IMPORTANCE_EPSILON of the top score,
    they are all considered "tied" and require user comparison.

    Args:
        tasks: List of tasks to rank
        today: Reference date for urgency calculation (defaults to today)

    Returns:
        List of tasks tied for top rank (could be 1 or many)
    """
    ranked = rank_tasks(tasks, today)

    if not ranked:
        return []

    # Get the top score
    top_score = ranked[0][1]

    # Find all tasks within epsilon of top score
    top_tasks = []
    for task, score in ranked:
        if abs(score - top_score) <= IMPORTANCE_EPSILON:
            top_tasks.append(task)
        else:
            # Since list is sorted, we can stop once score drops below threshold
            break

    return top_tasks


def get_next_focus_task(
    tasks: List[Task],
    today: Optional[date] = None,
    context_filter: Optional[int] = None,
    tag_filters: Optional[Set[int]] = None
) -> Optional[Task]:
    """
    Get the single next task to display in Focus Mode.

    Uses base_priority as tiebreaker for cross-tier ties.
    Returns None if multiple tasks in same tier are tied (requires comparison).

    Args:
        tasks: List of all tasks
        today: Reference date for urgency calculation (defaults to today)
        context_filter: Optional context ID to filter by (single selection)
        tag_filters: Optional set of tag IDs to filter by (OR condition)

    Returns:
        Single task to focus on, or None if tie requires resolution
    """
    # First filter to actionable tasks only
    actionable = get_actionable_tasks(tasks, context_filter, tag_filters)

    if not actionable:
        return None

    # Get top-ranked tasks
    top_tasks = get_top_ranked_tasks(actionable, today)

    if not top_tasks:
        return None

    # If exactly one task is on top, return it
    if len(top_tasks) == 1:
        return top_tasks[0]

    # Multiple tasks tied - check if they're in same tier
    tied_by_tier = get_tied_tasks(actionable, today, context_filter, tag_filters)
    if len(tied_by_tier) >= 2:
        # Multiple tasks in same tier → need comparison
        return None

    # Tied across different tiers → use base_priority as tiebreaker
    # Higher base_priority wins (3 > 2 > 1)
    return max(top_tasks, key=lambda t: t.base_priority)


def get_tied_tasks(
    tasks: List[Task],
    today: Optional[date] = None,
    context_filter: Optional[int] = None,
    tag_filters: Optional[Set[int]] = None
) -> List[Task]:
    """
    Get list of tasks tied for highest importance within same base_priority tier.

    Critical: Only returns tasks that are:
    1. Tied for top importance score (within epsilon)
    2. Have the SAME base_priority

    This ensures comparisons respect priority bands (High/Medium/Low separation).

    Args:
        tasks: List of all tasks
        today: Reference date for urgency calculation (defaults to today)
        context_filter: Optional context ID to filter by (single selection)
        tag_filters: Optional set of tag IDs to filter by (OR condition)

    Returns:
        List of tied tasks from same priority tier (empty if no ties)
    """
    # First filter to actionable tasks only
    actionable = get_actionable_tasks(tasks, context_filter, tag_filters)

    if len(actionable) < 2:
        return []

    # Get top-ranked tasks
    top_tasks = get_top_ranked_tasks(actionable, today)

    if len(top_tasks) < 2:
        return []

    # Group tied tasks by base_priority
    from collections import defaultdict
    by_priority = defaultdict(list)
    for task in top_tasks:
        by_priority[task.base_priority].append(task)

    # Return the highest priority tier with 2+ tasks
    # This ensures we compare within tiers, respecting the priority band system
    for priority in [3, 2, 1]:  # High, Medium, Low
        if len(by_priority[priority]) >= 2:
            return by_priority[priority]

    # No tier has 2+ tied tasks (tasks from different tiers, no comparison needed)
    return []


def has_tied_tasks(
    tasks: List[Task],
    today: Optional[date] = None,
    context_filter: Optional[int] = None,
    tag_filters: Optional[Set[int]] = None
) -> bool:
    """
    Check if there are tasks tied for top priority.

    Args:
        tasks: List of all tasks
        today: Reference date for urgency calculation (defaults to today)
        context_filter: Optional context ID to filter by (single selection)
        tag_filters: Optional set of tag IDs to filter by (OR condition)

    Returns:
        True if multiple tasks are tied for top rank
    """
    return len(get_tied_tasks(tasks, today, context_filter, tag_filters)) >= 2


def get_ranking_summary(tasks: List[Task], today: Optional[date] = None, top_n: int = 10) -> str:
    """
    Generate a human-readable ranking summary for debugging.

    Args:
        tasks: List of tasks to rank
        today: Reference date (defaults to today)
        top_n: Number of top tasks to include in summary

    Returns:
        Multi-line string summary of task rankings
    """
    actionable = get_actionable_tasks(tasks)
    ranked = rank_tasks(actionable, today)

    lines = [f"Task Rankings (showing top {top_n} of {len(ranked)} actionable tasks)"]
    lines.append("=" * 70)

    for i, (task, score) in enumerate(ranked[:top_n], 1):
        eff_pri = task.get_effective_priority()
        lines.append(
            f"{i:2d}. [{score:.2f}] {task.title[:40]:<40} "
            f"(Pri: {eff_pri:.2f}, Due: {task.due_date or 'None'})"
        )

    return "\n".join(lines)
