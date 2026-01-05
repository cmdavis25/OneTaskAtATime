"""Defer Task with Subtask Breakdown Command for undo/redo functionality."""

from datetime import date
from typing import Optional, List

from src.commands.base_command import Command
from src.models.task import Task
from src.models.enums import TaskState
from src.database.task_dao import TaskDAO


class DeferWithSubtasksCommand(Command):
    """
    Compound command to defer a task and break it into subtasks.

    This command handles:
    1. Deferring the task (changing state to DEFERRED and setting start_date)
    2. Creating subtasks from the breakdown
    3. Optionally moving the original task to TRASH

    On undo, it:
    1. Restores the task's original state and start_date
    2. Deletes all created subtasks
    """

    def __init__(
        self,
        task_dao: TaskDAO,
        task_id: int,
        start_date: date,
        subtask_titles: List[str],
        delete_original: bool = False,
        reason: Optional[str] = None
    ):
        """
        Initialize the command.

        Args:
            task_dao: Task data access object
            task_id: ID of task being deferred
            start_date: Date when task should become actionable
            subtask_titles: List of titles for new subtasks
            delete_original: If True, move original to TRASH; if False, keep it
            reason: Optional reason for deferring
        """
        self.task_dao = task_dao
        self.task_id = task_id
        self.new_start_date = start_date
        self.subtask_titles = subtask_titles
        self.delete_original = delete_original
        self.reason = reason

        # State to restore on undo
        self.original_state: Optional[TaskState] = None
        self.original_start_date: Optional[date] = None
        self.task_title: Optional[str] = None
        self.created_subtask_ids: List[int] = []

    def execute(self) -> bool:
        """Execute the defer and subtask breakdown."""
        # Get the original task
        original = self.task_dao.get_by_id(self.task_id)
        if not original:
            return False

        # Save original state only on first execution (not on redo)
        if self.original_state is None:
            self.original_state = original.state
            self.original_start_date = original.start_date
            self.task_title = original.title

        # On redo, restore subtasks from TRASH back to ACTIVE
        if len(self.created_subtask_ids) > 0:
            for subtask_id in self.created_subtask_ids:
                subtask = self.task_dao.get_by_id(subtask_id)
                if subtask and subtask.state == TaskState.TRASH:
                    subtask.state = TaskState.ACTIVE
                    self.task_dao.update(subtask)
        # On first execution, create subtasks
        else:
            # Create subtasks inheriting key fields
            for title in self.subtask_titles:
                # Skip empty titles
                if not title.strip():
                    continue

                subtask = Task(
                    title=title.strip(),
                    base_priority=original.base_priority,
                    due_date=original.due_date,
                    context_id=original.context_id,
                    state=TaskState.ACTIVE,
                    # Reset priority adjustment and comparison losses
                    priority_adjustment=0.0,
                    comparison_losses=0
                )

                # Create subtask
                created_subtask = self.task_dao.create(subtask)
                self.created_subtask_ids.append(created_subtask.id)

                # Copy project tags
                if original.project_tags:
                    self.task_dao._add_project_tags(created_subtask.id, original.project_tags)

        # Update original task
        original.state = TaskState.TRASH if self.delete_original else TaskState.DEFERRED
        original.start_date = self.new_start_date

        return self.task_dao.update(original) is not None

    def undo(self) -> bool:
        """Undo the defer and subtask breakdown."""
        # Restore the task's original state
        task = self.task_dao.get_by_id(self.task_id)
        if not task:
            return False

        task.state = self.original_state
        task.start_date = self.original_start_date

        if not self.task_dao.update(task):
            return False

        # Delete all created subtasks
        for subtask_id in self.created_subtask_ids:
            subtask = self.task_dao.get_by_id(subtask_id)
            if subtask:
                subtask.state = TaskState.TRASH
                self.task_dao.update(subtask)

        return True

    def get_description(self) -> str:
        """Get a human-readable description of this command."""
        count = len(self.subtask_titles)
        plural = 'subtask' if count == 1 else 'subtasks'
        if self.task_title:
            return f"Defer task with {count} {plural}: {self.task_title}"
        return f"Defer task with {count} {plural} (ID: {self.task_id})"
