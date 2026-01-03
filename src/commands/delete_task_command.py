"""Delete Task Command for undo/redo functionality."""

from typing import Optional
import copy

from src.commands.base_command import Command
from src.models.task import Task
from src.database.task_dao import TaskDAO


class DeleteTaskCommand(Command):
    """Command to delete a task (move to trash)."""

    def __init__(self, task_dao: TaskDAO, task_id: int):
        self.task_dao = task_dao
        self.task_id = task_id
        self.deleted_task: Optional[Task] = None

    def execute(self) -> bool:
        task = self.task_dao.get_by_id(self.task_id)
        if not task:
            return False

        # Save complete task for potential undo
        self.deleted_task = copy.deepcopy(task)

        # Delete from database
        return self.task_dao.delete(self.task_id)

    def undo(self) -> bool:
        if not self.deleted_task:
            return False

        # Restore the deleted task
        # Note: This recreates the task, so ID might change
        restored_task = self.task_dao.create(self.deleted_task)
        return restored_task is not None

    def get_description(self) -> str:
        if self.deleted_task:
            return f"Delete task: {self.deleted_task.title}"
        return f"Delete task (ID: {self.task_id})"
