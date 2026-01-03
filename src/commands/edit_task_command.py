"""Edit Task Command for undo/redo functionality."""

from typing import Optional
import copy

from src.commands.base_command import Command
from src.models.task import Task
from src.database.task_dao import TaskDAO


class EditTaskCommand(Command):
    """Command to edit task properties."""

    def __init__(self, task_dao: TaskDAO, task_id: int, new_task: Task):
        self.task_dao = task_dao
        self.task_id = task_id
        self.new_task = new_task
        self.original_task: Optional[Task] = None

    def execute(self) -> bool:
        task = self.task_dao.get_by_id(self.task_id)
        if not task:
            return False

        # Save original task for undo
        self.original_task = copy.deepcopy(task)

        # Apply new values (preserve ID)
        self.new_task.id = self.task_id

        # Update in database
        return self.task_dao.update(self.new_task) is not None

    def undo(self) -> bool:
        if not self.original_task:
            return False

        # Restore original task
        return self.task_dao.update(self.original_task) is not None

    def get_description(self) -> str:
        if self.original_task:
            return f"Edit task: {self.original_task.title}"
        return f"Edit task (ID: {self.task_id})"
