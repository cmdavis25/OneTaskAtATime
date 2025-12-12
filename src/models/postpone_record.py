"""
PostponeRecord data model for OneTaskAtATime application.

Tracks when and why tasks are postponed to surface blockers.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from .enums import PostponeReasonType, ActionTaken


@dataclass
class PostponeRecord:
    """
    Records when a user postpones a task and what action was taken.

    This helps identify patterns in task avoidance and ensures proper
    follow-up actions (breaking down tasks, creating blockers, etc.).

    Attributes:
        id: Unique identifier (None for unsaved records)
        task_id: ID of postponed task
        reason_type: Category of postponement reason
        reason_notes: User's explanation
        action_taken: What the system did in response
        postponed_at: Timestamp of postponement
    """

    task_id: int
    reason_type: PostponeReasonType
    id: Optional[int] = None
    reason_notes: Optional[str] = None
    action_taken: ActionTaken = ActionTaken.NONE
    postponed_at: Optional[datetime] = None

    def __str__(self) -> str:
        """String representation of postpone record."""
        return f"Postpone: Task {self.task_id} - {self.reason_type.value}"

    def __repr__(self) -> str:
        """Developer representation of postpone record."""
        return (
            f"PostponeRecord(id={self.id}, task_id={self.task_id}, "
            f"reason={self.reason_type.value}, action={self.action_taken.value})"
        )
