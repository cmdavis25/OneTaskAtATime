"""
Complete Task Command for undo/redo functionality.

Handles completing a task with full state preservation for undo.
"""

from datetime import datetime, date
from typing import Optional, List

from src.commands.base_command import Command
from src.models.task import Task
from src.models.enums import TaskState
from src.models.dependency import Dependency
from src.models.recurrence_pattern import RecurrencePattern
from src.database.task_dao import TaskDAO
from src.database.dependency_dao import DependencyDAO
from src.services.recurrence_service import RecurrenceService


class CompleteTaskCommand(Command):
    """
    Command to complete a task.

    Captures task state before completion to enable undo.
    When a task is completed, removes it from all dependencies where it was blocking other tasks.
    """

    def __init__(self, task_dao: TaskDAO, task_id: int, dependency_dao: Optional[DependencyDAO] = None):
        """
        Initialize the command.

        Args:
            task_dao: TaskDAO for database operations
            task_id: ID of task to complete
            dependency_dao: Optional DependencyDAO for removing dependencies
        """
        self.task_dao = task_dao
        self.dependency_dao = dependency_dao
        self.task_id = task_id
        self.original_state: Optional[TaskState] = None
        self.original_completed_at: Optional[datetime] = None
        self.task_title: Optional[str] = None
        self.removed_dependencies: List[Dependency] = []
        self.spawned_recurring_task_id: Optional[int] = None  # Track spawned task for undo

    def execute(self) -> bool:
        """
        Execute the command - mark task as completed.

        Also removes this task from all dependencies where it was blocking other tasks.

        Returns:
            True if successful, False otherwise
        """
        task = self.task_dao.get_by_id(self.task_id)
        if not task:
            return False

        # Save original state for undo
        self.original_state = task.state
        self.original_completed_at = task.completed_at
        self.task_title = task.title

        # Mark as completed
        task.state = TaskState.COMPLETED
        task.completed_at = datetime.now()

        # Update in database
        updated_task = self.task_dao.update(task)
        if updated_task is None:
            return False

        # Remove this task from all dependencies where it was blocking other tasks
        if self.dependency_dao:
            blocking_deps = self.dependency_dao.get_blocking_tasks(self.task_id)
            self.removed_dependencies = blocking_deps.copy()

            for dep in blocking_deps:
                self.dependency_dao.delete(dep.id)

        # Handle recurring task logic - spawn next occurrence if applicable
        if updated_task.is_recurring:
            next_task = self._generate_next_occurrence(updated_task)
            if next_task:
                self.spawned_recurring_task_id = next_task.id

        return True

    def undo(self) -> bool:
        """
        Undo the command - restore previous state.

        Also restores any dependencies that were removed when the task was completed.

        Returns:
            True if successful, False otherwise
        """
        task = self.task_dao.get_by_id(self.task_id)
        if not task:
            return False

        # Restore original state
        task.state = self.original_state
        task.completed_at = self.original_completed_at

        # Update in database
        updated_task = self.task_dao.update(task)
        if updated_task is None:
            return False

        # Restore dependencies that were removed
        if self.dependency_dao and self.removed_dependencies:
            for dep in self.removed_dependencies:
                # Create new dependency with same task IDs (ID will be auto-assigned)
                restored_dep = Dependency(
                    blocked_task_id=dep.blocked_task_id,
                    blocking_task_id=dep.blocking_task_id
                )
                self.dependency_dao.create(restored_dep)

        # Delete spawned recurring task if one was created
        if self.spawned_recurring_task_id:
            self.task_dao.delete(self.spawned_recurring_task_id)
            self.spawned_recurring_task_id = None

        return True

    def _generate_next_occurrence(self, completed_task: Task) -> Optional[Task]:
        """
        Generate next occurrence of recurring task.

        Args:
            completed_task: The task that was just completed

        Returns:
            Newly created task or None if series ended
        """
        if not completed_task.is_recurring or not completed_task.recurrence_pattern:
            return None

        # Parse recurrence pattern
        try:
            pattern = RecurrencePattern.from_json(completed_task.recurrence_pattern)
        except (ValueError, KeyError) as e:
            print(f"Error parsing recurrence pattern for task {completed_task.id}: {e}")
            return None

        # Calculate next due date from the original due date (or today if no due date)
        completion_date = date.today()
        base_date = completed_task.due_date if completed_task.due_date else completion_date
        next_due_date = RecurrenceService.calculate_next_occurrence_date(pattern, base_date)

        # Check if the next due date would exceed the end date
        if completed_task.recurrence_end_date and next_due_date > completed_task.recurrence_end_date:
            return None

        # Check if we've reached the maximum number of occurrences
        if completed_task.max_occurrences and completed_task.occurrence_count + 1 >= completed_task.max_occurrences:
            return None

        # Get shared Elo values if applicable
        shared_elo, shared_count = RecurrenceService.get_shared_elo_values(completed_task)

        # Clone task for next occurrence
        next_task = RecurrenceService.clone_task_for_next_occurrence(
            completed_task,
            next_due_date,
            shared_elo=shared_elo,
            shared_comparison_count=shared_count
        )

        # Create the next occurrence in database
        created_task = self.task_dao.create(next_task)

        return created_task

    def get_description(self) -> str:
        """
        Get human-readable description.

        Returns:
            Description string
        """
        if self.task_title:
            return f"Complete task: {self.task_title}"
        return f"Complete task (ID: {self.task_id})"
