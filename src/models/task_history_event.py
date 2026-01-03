"""
Task History Event model for OneTaskAtATime.

Represents a single event in a task's complete audit trail.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.models.enums import TaskEventType


@dataclass
class TaskHistoryEvent:
    """
    Represents a single event in a task's history.

    Used to build comprehensive audit logs and timeline views showing
    all changes made to a task over its lifetime.

    Attributes:
        id: Unique identifier (database primary key)
        task_id: ID of the task this event belongs to
        event_type: Type of event (created, edited, completed, etc.)
        event_timestamp: When the event occurred
        old_value: Previous state before the event (JSON serialized)
        new_value: New state after the event (JSON serialized)
        changed_by: Who/what initiated the change (user, system, scheduler)
        context_data: Additional metadata about the event
    """
    task_id: int
    event_type: TaskEventType
    id: Optional[int] = None
    event_timestamp: datetime = field(default_factory=datetime.now)
    old_value: Optional[str] = None  # JSON serialized
    new_value: Optional[str] = None  # JSON serialized
    changed_by: str = "user"  # user, system, scheduler
    context_data: Optional[str] = None  # Additional metadata

    def __post_init__(self):
        """Convert string event_type to enum if needed."""
        if isinstance(self.event_type, str):
            self.event_type = TaskEventType(self.event_type)
