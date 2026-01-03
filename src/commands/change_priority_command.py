"""Change Priority Command for undo/redo functionality."""

from typing import Optional

from src.commands.base_command import Command
from src.models.enums import Priority
from src.database.task_dao import TaskDAO


class ChangePriorityCommand(Command):
    """Command to change task priority."""

    def __init__(self, task_dao: TaskDAO, task_id: int, new_priority: int):
        self.task_dao = task_dao
        self.task_id = task_id
        self.new_priority = new_priority
        self.original_priority: Optional[int] = None
        self.original_elo: Optional[float] = None
        self.original_comparison_count: Optional[int] = None
        self.task_title: Optional[str] = None

    def execute(self) -> bool:
        task = self.task_dao.get_by_id(self.task_id)
        if not task:
            return False

        # Save original values
        self.original_priority = task.base_priority
        self.original_elo = task.elo_rating
        self.original_comparison_count = task.comparison_count
        self.task_title = task.title

        # Change priority and reset Elo/comparisons
        task.base_priority = self.new_priority
        task.elo_rating = 1500.0  # Reset to default
        task.comparison_count = 0

        return self.task_dao.update(task) is not None

    def undo(self) -> bool:
        task = self.task_dao.get_by_id(self.task_id)
        if not task:
            return False

        # Restore original priority and Elo stats
        task.base_priority = self.original_priority
        task.elo_rating = self.original_elo
        task.comparison_count = self.original_comparison_count

        return self.task_dao.update(task) is not None

    def get_description(self) -> str:
        if self.task_title:
            old_name = Priority(self.original_priority).name if self.original_priority else "Unknown"
            new_name = Priority(self.new_priority).name
            return f"Change priority: {self.task_title} ({old_name} → {new_name})"
        return f"Change priority (ID: {self.task_id})"
