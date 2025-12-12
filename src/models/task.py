"""
Task data model for OneTaskAtATime application.

The Task model represents a single actionable item in the GTD system.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List
from .enums import TaskState, Priority


@dataclass
class Task:
    """
    Represents a single task in the OneTaskAtATime system.

    Attributes:
        id: Unique identifier (None for unsaved tasks)
        title: Task description/name
        description: Optional detailed notes
        base_priority: Priority level (1=Low, 2=Medium, 3=High)
        priority_adjustment: Cumulative adjustment from comparisons
        due_date: Optional deadline for urgency calculation
        state: Current task state (active, deferred, etc.)
        start_date: When deferred task becomes actionable
        delegated_to: Person/system task is assigned to
        follow_up_date: When to check on delegated task
        completed_at: Timestamp of completion
        context_id: Single context for filtering (optional)
        last_resurfaced_at: Last time task was shown to user
        resurface_count: Number of times task has been resurfaced
        created_at: Creation timestamp
        updated_at: Last modification timestamp
        project_tags: List of project tag IDs (loaded separately)
        blocking_task_ids: List of task IDs this task depends on
    """

    # Core fields
    title: str
    id: Optional[int] = None

    # Priority system
    base_priority: int = 2  # Default to Medium
    priority_adjustment: float = 0.0

    # Urgency system
    due_date: Optional[date] = None

    # Task state
    state: TaskState = TaskState.ACTIVE

    # Optional fields
    description: Optional[str] = None

    # Deferred task fields
    start_date: Optional[date] = None

    # Delegated task fields
    delegated_to: Optional[str] = None
    follow_up_date: Optional[date] = None

    # Completion tracking
    completed_at: Optional[datetime] = None

    # Organization
    context_id: Optional[int] = None

    # Resurfacing tracking
    last_resurfaced_at: Optional[datetime] = None
    resurface_count: int = 0

    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Related data (not stored directly in tasks table)
    project_tags: List[int] = field(default_factory=list)
    blocking_task_ids: List[int] = field(default_factory=list)

    def get_effective_priority(self) -> float:
        """
        Calculate the effective priority after adjustments.

        Returns:
            Base priority minus accumulated adjustments
        """
        return float(self.base_priority) - self.priority_adjustment

    def get_priority_enum(self) -> Priority:
        """
        Get the Priority enum for the base priority value.

        Returns:
            Priority enum (LOW, MEDIUM, HIGH)
        """
        return Priority(self.base_priority)

    def is_active(self) -> bool:
        """Check if task is in active state."""
        return self.state == TaskState.ACTIVE

    def is_completed(self) -> bool:
        """Check if task is completed."""
        return self.state == TaskState.COMPLETED

    def is_blocked(self) -> bool:
        """
        Check if task has unresolved dependencies.

        Note: This requires checking if blocking tasks are completed.
        The DAO layer should populate blocking_task_ids.
        """
        return len(self.blocking_task_ids) > 0

    def can_be_shown_in_focus_mode(self) -> bool:
        """
        Determine if task should appear in Focus Mode.

        Returns:
            True if task is active and not blocked
        """
        return self.is_active() and not self.is_blocked()

    def mark_completed(self) -> None:
        """Mark task as completed with current timestamp."""
        self.state = TaskState.COMPLETED
        self.completed_at = datetime.now()

    def defer_until(self, start_date: date) -> None:
        """
        Defer task until a specific date.

        Args:
            start_date: Date when task becomes actionable
        """
        self.state = TaskState.DEFERRED
        self.start_date = start_date

    def delegate_to(self, person: str, follow_up_date: date) -> None:
        """
        Delegate task to someone with a follow-up date.

        Args:
            person: Name of person/system task is delegated to
            follow_up_date: When to check on progress
        """
        self.state = TaskState.DELEGATED
        self.delegated_to = person
        self.follow_up_date = follow_up_date

    def move_to_someday(self) -> None:
        """Move task to someday/maybe list."""
        self.state = TaskState.SOMEDAY

    def move_to_trash(self) -> None:
        """Move task to trash."""
        self.state = TaskState.TRASH

    def record_resurface(self) -> None:
        """Record that this task was resurfaced to the user."""
        self.last_resurfaced_at = datetime.now()
        self.resurface_count += 1

    def __str__(self) -> str:
        """String representation of task."""
        return f"Task({self.id}): {self.title} [{self.state.value}]"

    def __repr__(self) -> str:
        """Developer representation of task."""
        return (
            f"Task(id={self.id}, title='{self.title}', "
            f"priority={self.base_priority}, state={self.state.value})"
        )
