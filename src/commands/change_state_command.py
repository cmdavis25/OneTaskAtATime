"""Change State Command for undo/redo functionality."""

from typing import Optional

from src.commands.base_command import Command
from src.models.enums import TaskState
from src.database.task_dao import TaskDAO


class ChangeStateCommand(Command):
    """
    Command to change task state.

    Handles generic state changes (Active, Someday/Maybe, Trash) that don't
    require additional parameters like defer/delegate do.
    """

    def __init__(self, task_dao: TaskDAO, task_id: int, new_state: TaskState):
        """
        Initialize the command.

        Args:
            task_dao: TaskDAO for database operations
            task_id: ID of task to change state
            new_state: Target state to change to
        """
        self.task_dao = task_dao
        self.task_id = task_id
        self.new_state = new_state
        self.original_state: Optional[TaskState] = None
        self.task_title: Optional[str] = None

    def execute(self) -> bool:
        """
        Execute the command - change task state.

        Returns:
            True if successful, False otherwise
        """
        task = self.task_dao.get_by_id(self.task_id)
        if not task:
            return False

        # Save original state for undo
        self.original_state = task.state
        self.task_title = task.title

        # Change state
        task.state = self.new_state

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

        # Update in database
        updated_task = self.task_dao.update(task)
        return updated_task is not None

    def get_description(self) -> str:
        """
        Get human-readable description.

        Returns:
            Description string
        """
        state_name_map = {
            TaskState.ACTIVE: "Activate",
            TaskState.DEFERRED: "Defer",
            TaskState.DELEGATED: "Delegate",
            TaskState.SOMEDAY: "Move to Someday/Maybe",
            TaskState.COMPLETED: "Complete",
            TaskState.TRASH: "Move to Trash"
        }

        state_name = state_name_map.get(self.new_state, f"Change to {self.new_state.value}")

        if self.task_title:
            return f"{state_name}: {self.task_title}"
        return f"{state_name} (ID: {self.task_id})"
