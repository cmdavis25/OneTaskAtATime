"""
Recurrence service for handling recurring task logic.

This service manages the generation of next occurrences for recurring tasks,
including date calculation and Elo rating handling.
"""

from datetime import date
from typing import Optional
from ..models.task import Task
from ..models.recurrence_pattern import RecurrencePattern
from ..models.enums import TaskState


class RecurrenceService:
    """Service for managing recurring task logic."""

    @staticmethod
    def calculate_next_occurrence_date(pattern: RecurrencePattern, from_date: date) -> date:
        """
        Calculate the next occurrence date based on the pattern.

        Args:
            pattern: RecurrencePattern defining the recurrence rules
            from_date: Reference date (typically task completion date)

        Returns:
            The next occurrence date
        """
        return pattern.calculate_next_date(from_date)

    @staticmethod
    def should_continue_recurrence(task: Task, completion_date: date) -> bool:
        """
        Determine if recurring task series should continue.

        Args:
            task: The completed recurring task
            completion_date: Date when task was completed

        Returns:
            True if another occurrence should be created, False otherwise
        """
        if not task.is_recurring:
            return False

        # Check if end date has been reached
        if task.recurrence_end_date and completion_date >= task.recurrence_end_date:
            return False

        return True

    @staticmethod
    def clone_task_for_next_occurrence(
        task: Task,
        next_due_date: date,
        shared_elo: Optional[float] = None,
        shared_comparison_count: Optional[int] = None
    ) -> Task:
        """
        Create a new task instance for the next occurrence.

        Args:
            task: The completed recurring task
            next_due_date: Due date for the next occurrence
            shared_elo: Shared Elo rating if applicable
            shared_comparison_count: Shared comparison count if applicable

        Returns:
            New Task object for the next occurrence
        """
        # Clone the task with a new due date
        next_task = Task(
            title=task.title,
            description=task.description,
            base_priority=task.base_priority,
            due_date=next_due_date,
            state=TaskState.ACTIVE,  # Always create new occurrences as ACTIVE
            context_id=task.context_id,

            # Recurrence fields
            is_recurring=task.is_recurring,
            recurrence_pattern=task.recurrence_pattern,
            recurrence_parent_id=task.recurrence_parent_id or task.id,
            share_elo_rating=task.share_elo_rating,
            recurrence_end_date=task.recurrence_end_date,
            max_occurrences=task.max_occurrences,
            occurrence_count=task.occurrence_count + 1,

            # Handle Elo rating based on sharing preference
            elo_rating=shared_elo if task.share_elo_rating and shared_elo is not None else 1500.0,
            comparison_count=shared_comparison_count if task.share_elo_rating and shared_comparison_count is not None else 0,

            # Store shared pool values
            shared_elo_rating=shared_elo if task.share_elo_rating else None,
            shared_comparison_count=shared_comparison_count if task.share_elo_rating else None,

            # Copy project tags (will be set after creation)
            project_tags=task.project_tags.copy() if task.project_tags else []
        )

        return next_task

    @staticmethod
    def get_shared_elo_values(task: Task) -> tuple[Optional[float], Optional[int]]:
        """
        Get the shared Elo rating and comparison count for a task.

        Args:
            task: The recurring task

        Returns:
            Tuple of (shared_elo_rating, shared_comparison_count)
        """
        if not task.share_elo_rating:
            return None, None

        # Use the current task's Elo if shared values are set
        if task.shared_elo_rating is not None:
            return task.shared_elo_rating, task.shared_comparison_count

        # Otherwise use current task's values as the starting point
        return task.elo_rating, task.comparison_count

    @staticmethod
    def format_recurrence_pattern(pattern_json: Optional[str]) -> str:
        """
        Convert JSON pattern to human-readable string.

        Args:
            pattern_json: JSON string representation of recurrence pattern

        Returns:
            Human-readable description of the pattern
        """
        if not pattern_json:
            return ""

        try:
            pattern = RecurrencePattern.from_json(pattern_json)
            return pattern.to_human_readable()
        except (ValueError, KeyError):
            return "Invalid pattern"
