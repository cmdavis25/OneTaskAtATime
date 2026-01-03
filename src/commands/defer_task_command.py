"""Defer Task Command for undo/redo functionality."""

from datetime import date
from typing import Optional

from src.commands.base_command import Command
from src.models.task import Task
from src.models.enums import TaskState
from src.database.task_dao import TaskDAO


class DeferTaskCommand(Command):
    """Command to defer a task with a start date."""

    def __init__(self, task_dao: TaskDAO, task_id: int, start_date: date, reason: Optional[str] = None):
        self.task_dao = task_dao
        self.task_id = task_id
        self.new_start_date = start_date
        self.reason = reason
        self.original_state: Optional[TaskState] = None
        self.original_start_date: Optional[date] = None
        self.task_title: Optional[str] = None

    def execute(self) -> bool:
        task = self.task_dao.get_by_id(self.task_id)
        if not task:
            return False

        self.original_state = task.state
        self.original_start_date = task.start_date
        self.task_title = task.title

        task.state = TaskState.DEFERRED
        task.start_date = self.new_start_date

        return self.task_dao.update(task) is not None

    def undo(self) -> bool:
        task = self.task_dao.get_by_id(self.task_id)
        if not task:
            return False

        task.state = self.original_state
        task.start_date = self.original_start_date

        return self.task_dao.update(task) is not None

    def get_description(self) -> str:
        if self.task_title:
            return f"Defer task: {self.task_title} (until {self.new_start_date})"
        return f"Defer task (ID: {self.task_id})"
