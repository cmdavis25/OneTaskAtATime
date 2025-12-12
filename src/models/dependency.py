"""
Dependency data model for OneTaskAtATime application.

Represents task dependencies (blockers).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Dependency:
    """
    Represents a dependency relationship between two tasks.

    A dependency means the blocked_task cannot be worked on until
    the blocking_task is completed.

    Attributes:
        id: Unique identifier (None for unsaved dependencies)
        blocked_task_id: ID of task that is waiting
        blocking_task_id: ID of task that must complete first
        created_at: Timestamp when dependency was created
    """

    blocked_task_id: int
    blocking_task_id: int
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    def __str__(self) -> str:
        """String representation of dependency."""
        return f"Dependency: Task {self.blocked_task_id} blocked by Task {self.blocking_task_id}"

    def __repr__(self) -> str:
        """Developer representation of dependency."""
        return (
            f"Dependency(id={self.id}, blocked={self.blocked_task_id}, "
            f"blocking={self.blocking_task_id})"
        )
