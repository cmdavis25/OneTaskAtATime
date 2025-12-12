"""
TaskComparison data model for OneTaskAtATime application.

Tracks comparison history for priority conflict resolution.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TaskComparison:
    """
    Records a single comparison event between two tasks.

    When multiple tasks have equal priority scores, the user is presented
    with a side-by-side comparison. The winner keeps their priority, while
    the loser has their priority_adjustment incremented.

    Attributes:
        id: Unique identifier (None for unsaved comparisons)
        winner_task_id: ID of task chosen as higher priority
        loser_task_id: ID of task chosen as lower priority
        adjustment_amount: Amount subtracted from loser's priority
        compared_at: Timestamp of comparison
    """

    winner_task_id: int
    loser_task_id: int
    adjustment_amount: float
    id: Optional[int] = None
    compared_at: Optional[datetime] = None

    def __str__(self) -> str:
        """String representation of comparison."""
        return f"Comparison: Task {self.winner_task_id} > Task {self.loser_task_id} (-{self.adjustment_amount})"

    def __repr__(self) -> str:
        """Developer representation of comparison."""
        return (
            f"TaskComparison(id={self.id}, winner={self.winner_task_id}, "
            f"loser={self.loser_task_id}, adjustment={self.adjustment_amount})"
        )
