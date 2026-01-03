"""Delegate Task Command for undo/redo functionality."""

from datetime import date
from typing import Optional

from src.commands.base_command import Command
from src.models.enums import TaskState
from src.database.task_dao import TaskDAO


class DelegateTaskCommand(Command):
    """Command to delegate a task to someone else."""

    def __init__(self, task_dao: TaskDAO, task_id: int, delegated_to: str, follow_up_date: date):
        self.task_dao = task_dao
        self.task_id = task_id
        self.new_delegated_to = delegated_to
        self.new_follow_up_date = follow_up_date
        self.original_state: Optional[TaskState] = None
        self.original_delegated_to: Optional[str] = None
        self.original_follow_up_date: Optional[date] = None
        self.task_title: Optional[str] = None

    def execute(self) -> bool:
        task = self.task_dao.get_by_id(self.task_id)
        if not task:
            return False

        self.original_state = task.state
        self.original_delegated_to = task.delegated_to
        self.original_follow_up_date = task.follow_up_date
        self.task_title = task.title

        task.state = TaskState.DELEGATED
        task.delegated_to = self.new_delegated_to
        task.follow_up_date = self.new_follow_up_date

        return self.task_dao.update(task) is not None

    def undo(self) -> bool:
        task = self.task_dao.get_by_id(self.task_id)
        if not task:
            return False

        task.state = self.original_state
        task.delegated_to = self.original_delegated_to
        task.follow_up_date = self.original_follow_up_date

        return self.task_dao.update(task) is not None

    def get_description(self) -> str:
        if self.task_title:
            return f"Delegate task: {self.task_title} (to {self.new_delegated_to})"
        return f"Delegate task (ID: {self.task_id})"
