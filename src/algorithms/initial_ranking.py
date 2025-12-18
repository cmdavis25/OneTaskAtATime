"""
Initial Ranking Algorithm for New Tasks.

This module handles the sequential ranking of new tasks (comparison_count = 0)
to prevent them from being "buried in the middle" of their priority band.
"""

from typing import List, Tuple, Optional
import random
from ..models.task import Task


def get_new_tasks_in_priority_band(
    tasks: List[Task],
    base_priority: int,
    active_only: bool = True,
    limit: int = None
) -> List[Task]:
    """
    Get new tasks (comparison_count = 0) within a specific priority band.

    Args:
        tasks: List of all tasks
        base_priority: Priority band to check (1=Low, 2=Medium, 3=High)
        active_only: If True, only return tasks in ACTIVE state (default: True)
        limit: Maximum number of tasks to return; if more exist, randomly select (default: None)

    Returns:
        List of new tasks in the specified priority band
    """
    from ..models.enums import TaskState

    new_tasks = [
        task for task in tasks
        if task.base_priority == base_priority and task.comparison_count == 0
    ]

    # Filter to Active state only if requested
    if active_only:
        new_tasks = [t for t in new_tasks if t.state == TaskState.ACTIVE]

    # Apply limit with random selection if needed
    if limit is not None and len(new_tasks) > limit:
        random.shuffle(new_tasks)
        new_tasks = new_tasks[:limit]

    return new_tasks


def get_top_task_in_band(tasks: List[Task], base_priority: int, active_only: bool = True) -> Optional[Task]:
    """
    Get the task with highest Elo rating in a priority band.

    Args:
        tasks: List of all tasks
        base_priority: Priority band to check (1=Low, 2=Medium, 3=High)
        active_only: If True, only consider tasks in ACTIVE state (default: True)

    Returns:
        Task with highest Elo in band, or None if no tasks
    """
    from ..models.enums import TaskState

    band_tasks = [t for t in tasks if t.base_priority == base_priority]

    if active_only:
        band_tasks = [t for t in band_tasks if t.state == TaskState.ACTIVE]

    if not band_tasks:
        return None
    return max(band_tasks, key=lambda t: t.elo_rating)


def get_bottom_task_in_band(tasks: List[Task], base_priority: int, active_only: bool = True) -> Optional[Task]:
    """
    Get the task with lowest Elo rating in a priority band.

    Args:
        tasks: List of all tasks
        base_priority: Priority band to check (1=Low, 2=Medium, 3=High)
        active_only: If True, only consider tasks in ACTIVE state (default: True)

    Returns:
        Task with lowest Elo in band, or None if no tasks
    """
    from ..models.enums import TaskState

    band_tasks = [t for t in tasks if t.base_priority == base_priority]

    if active_only:
        band_tasks = [t for t in band_tasks if t.state == TaskState.ACTIVE]

    if not band_tasks:
        return None
    return min(band_tasks, key=lambda t: t.elo_rating)


def get_ranking_candidates(
    all_tasks: List[Task],
    new_tasks: List[Task],
    base_priority: int,
    active_only: bool = True
) -> List[Task]:
    """
    Get the list of tasks to be ranked in sequential ranking dialog.

    Includes up to 5 tasks total:
    - Up to 3 new tasks in the priority band (randomly selected if more)
    - Top-ranked existing task in the band (highest Elo)
    - Bottom-ranked existing task in the band (lowest Elo)

    Args:
        all_tasks: List of all tasks in the system
        new_tasks: List of new tasks (comparison_count = 0) in the band
        base_priority: Priority band being ranked
        active_only: If True, only include tasks in ACTIVE state (default: True)

    Returns:
        List of candidate tasks for ranking, randomized
    """
    from ..models.enums import TaskState

    # Limit to 3 new tasks maximum (randomly selected if more)
    limited_new_tasks = list(new_tasks)
    if len(limited_new_tasks) > 3:
        random.shuffle(limited_new_tasks)
        limited_new_tasks = limited_new_tasks[:3]

    candidates = limited_new_tasks  # Start with new tasks

    # Get existing tasks in the band (excluding new tasks)
    existing_tasks = [
        t for t in all_tasks
        if t.base_priority == base_priority and t.comparison_count > 0
    ]

    # Filter to Active state only if requested
    if active_only:
        existing_tasks = [t for t in existing_tasks if t.state == TaskState.ACTIVE]

    if existing_tasks:
        # Add top-ranked existing task
        top_task = max(existing_tasks, key=lambda t: t.elo_rating)
        candidates.append(top_task)

        # Add bottom-ranked existing task (if different from top)
        bottom_task = min(existing_tasks, key=lambda t: t.elo_rating)
        if bottom_task.id != top_task.id:
            candidates.append(bottom_task)

    # Randomize order for presentation
    random.shuffle(candidates)

    return candidates


def calculate_elo_from_rank_position(
    rank_position: int,
    total_tasks: int,
    top_elo: float,
    bottom_elo: float
) -> float:
    """
    Calculate Elo rating by interpolating based on rank position.

    Linear interpolation between top and bottom Elo ratings.
    Rank position 0 (first) gets top_elo, last position gets bottom_elo.

    Args:
        rank_position: Position in ranked list (0 = first/highest)
        total_tasks: Total number of tasks in ranked list
        top_elo: Elo rating of the top task
        bottom_elo: Elo rating of the bottom task

    Returns:
        Interpolated Elo rating for this position
    """
    if total_tasks == 1:
        # Only one task, give it the middle value
        return (top_elo + bottom_elo) / 2.0

    # Linear interpolation from top to bottom
    # rank_position / (total_tasks - 1) gives ratio from 0.0 (top) to 1.0 (bottom)
    ratio = rank_position / (total_tasks - 1)
    return top_elo - (ratio * (top_elo - bottom_elo))


def assign_elo_ratings_from_ranking(
    ranked_tasks: List[Task],
    existing_top_elo: Optional[float] = None,
    existing_bottom_elo: Optional[float] = None,
    base_priority: int = 2
) -> List[Tuple[Task, float]]:
    """
    Assign Elo ratings to tasks based on their ranked order.

    Uses linear interpolation between the top and bottom existing tasks' Elo ratings.
    If no existing tasks, uses the default Elo range for the priority band.

    Args:
        ranked_tasks: List of tasks in user's preferred rank order (first = highest priority)
        existing_top_elo: Elo rating of top existing task in band (if any)
        existing_bottom_elo: Elo rating of bottom existing task in band (if any)
        base_priority: Priority band (1=Low, 2=Medium, 3=High)

    Returns:
        List of (task, new_elo) tuples
    """
    if not ranked_tasks:
        return []

    # Determine Elo range for interpolation
    if existing_top_elo is not None and existing_bottom_elo is not None:
        # Use existing task Elo range
        top_elo = existing_top_elo
        bottom_elo = existing_bottom_elo
    else:
        # No existing tasks - use default range centered at 1500
        # Give new tasks a spread of ±200 around default
        top_elo = 1700.0
        bottom_elo = 1300.0

    # Assign Elo ratings based on rank position
    results = []
    total_tasks = len(ranked_tasks)

    for position, task in enumerate(ranked_tasks):
        new_elo = calculate_elo_from_rank_position(
            position,
            total_tasks,
            top_elo,
            bottom_elo
        )
        results.append((task, new_elo))

    return results


def check_for_new_tasks(all_tasks: List[Task], active_only: bool = True) -> Tuple[bool, int, List[Task]]:
    """
    Check if there are new tasks needing initial ranking.

    Returns information about the highest priority band with new tasks.
    Limits to 3 new tasks maximum via random selection.

    Args:
        all_tasks: List of all tasks in the system
        active_only: If True, only consider tasks in ACTIVE state (default: True)

    Returns:
        Tuple of (has_new_tasks, priority_band, new_tasks_list)
        - has_new_tasks: True if there are new tasks in any band
        - priority_band: Highest priority band with new tasks (3, 2, 1, or 0 if none)
        - new_tasks_list: List of up to 3 new tasks in that band
    """
    # Check priority bands from high to low
    for priority in [3, 2, 1]:
        new_tasks = get_new_tasks_in_priority_band(all_tasks, priority, active_only=active_only, limit=3)
        if new_tasks:
            return (True, priority, new_tasks)

    return (False, 0, [])
