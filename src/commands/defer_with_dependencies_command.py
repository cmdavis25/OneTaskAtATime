"""Defer Task with Dependencies Command for undo/redo functionality."""

from datetime import date
from typing import Optional, List

from src.commands.base_command import Command
from src.models.task import Task
from src.models.enums import TaskState
from src.database.task_dao import TaskDAO
from src.database.dependency_dao import DependencyDAO


class DeferWithDependenciesCommand(Command):
    """
    Compound command to defer a task and add dependencies.

    This command handles:
    1. Deferring the task (changing state to DEFERRED and setting start_date)
    2. Creating dependency relationships with existing tasks

    On undo, it:
    1. Restores the task's original state and start_date
    2. Removes all created dependency relationships
    """

    def __init__(
        self,
        task_dao: TaskDAO,
        dependency_dao: DependencyDAO,
        task_id: int,
        start_date: date,
        dependency_task_ids: List[int],
        reason: Optional[str] = None
    ):
        """
        Initialize the command.

        Args:
            task_dao: Task data access object
            dependency_dao: Dependency data access object
            task_id: ID of task being deferred
            start_date: Date when task should become actionable
            dependency_task_ids: List of task IDs that block this task
            reason: Optional reason for deferring
        """
        self.task_dao = task_dao
        self.dependency_dao = dependency_dao
        self.task_id = task_id
        self.new_start_date = start_date
        self.dependency_task_ids = dependency_task_ids
        self.reason = reason

        # State to restore on undo
        self.original_state: Optional[TaskState] = None
        self.original_start_date: Optional[date] = None
        self.task_title: Optional[str] = None
        self.created_dependency_ids: List[int] = []

    def execute(self) -> bool:
        """Execute the defer and dependency creation."""
        # Get and update the task being deferred
        task = self.task_dao.get_by_id(self.task_id)
        if not task:
            return False

        # Save original state only on first execution (not on redo)
        if self.original_state is None:
            self.original_state = task.state
            self.original_start_date = task.start_date
            self.task_title = task.title

        task.state = TaskState.DEFERRED
        task.start_date = self.new_start_date

        if not self.task_dao.update(task):
            return False

        # On redo, recreate dependencies that were removed by undo
        if len(self.created_dependency_ids) > 0:
            # Dependencies were already created, just need to recreate them
            from src.models.dependency import Dependency
            temp_ids = []
            for blocking_task_id in self.dependency_task_ids:
                try:
                    dependency = Dependency(
                        blocked_task_id=self.task_id,
                        blocking_task_id=blocking_task_id
                    )
                    created_dependency = self.dependency_dao.create(dependency)
                    temp_ids.append(created_dependency.id)
                except ValueError:
                    # Circular dependency or duplicate - skip this one but continue
                    continue
            self.created_dependency_ids = temp_ids
        # On first execution, create dependencies
        else:
            # Create dependency relationships
            from src.models.dependency import Dependency
            for blocking_task_id in self.dependency_task_ids:
                try:
                    dependency = Dependency(
                        blocked_task_id=self.task_id,
                        blocking_task_id=blocking_task_id
                    )
                    created_dependency = self.dependency_dao.create(dependency)
                    self.created_dependency_ids.append(created_dependency.id)
                except ValueError:
                    # Circular dependency or duplicate - skip this one but continue
                    continue

        # Return success if at least one dependency was created
        return len(self.created_dependency_ids) > 0

    def undo(self) -> bool:
        """Undo the defer and dependency creation."""
        # Restore the task's original state
        task = self.task_dao.get_by_id(self.task_id)
        if not task:
            return False

        task.state = self.original_state
        task.start_date = self.original_start_date

        if not self.task_dao.update(task):
            return False

        # Remove all created dependency relationships
        for dependency_id in self.created_dependency_ids:
            self.dependency_dao.delete(dependency_id)

        return True

    def get_description(self) -> str:
        """Get a human-readable description of this command."""
        count = len(self.dependency_task_ids)
        plural = 'dependency' if count == 1 else 'dependencies'
        if self.task_title:
            return f"Defer task with {count} {plural}: {self.task_title}"
        return f"Defer task with {count} {plural} (ID: {self.task_id})"
