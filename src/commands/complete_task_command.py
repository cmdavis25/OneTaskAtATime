"""
Complete Task Command for undo/redo functionality.

Handles completing a task with full state preservation for undo.
"""

from datetime import datetime
from typing import Optional

from src.commands.base_command import Command
from src.models.task import Task
from src.models.enums import TaskState
from src.database.task_dao import TaskDAO


class CompleteTaskCommand(Command):
    """
    Command to complete a task.

    Captures task state before completion to enable undo.
    """

    def __init__(self, task_dao: TaskDAO, task_id: int):
        """
        Initialize the command.

        Args:
            task_dao: TaskDAO for database operations
            task_id: ID of task to complete
        """
        self.task_dao = task_dao
        self.task_id = task_id
        self.original_state: Optional[TaskState] = None
        self.original_completed_at: Optional[datetime] = None
        self.task_title: Optional[str] = None

    def execute(self) -> bool:
        """
        Execute the command - mark task as completed.

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
        return updated_task is not None

    def undo(self) -> bool:
        """
        Undo the command - restore previous state.

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
        return updated_task is not None

    def get_description(self) -> str:
        """
        Get human-readable description.

        Returns:
            Description string
        """
        if self.task_title:
            return f"Complete task: {self.task_title}"
        return f"Complete task (ID: {self.task_id})"
