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
    Compound command to defer a task with dependencies.

    This command handles:
    1. Deferring the task (changing state to DEFERRED and setting start_date)
    2. Tracking dependency relationships (dependencies are created by DependencySelectionDialog)

    On undo, it:
    1. Restores the task's original state and start_date
    2. Removes all tracked dependency relationships
    3. Moves created blocking tasks to TRASH (if any were created during workflow)
    """

    def __init__(
        self,
        task_dao: TaskDAO,
        dependency_dao: DependencyDAO,
        task_id: int,
        start_date: date,
        dependency_task_ids: List[int],
        reason: Optional[str] = None,
        created_blocking_task_ids: Optional[List[int]] = None
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
            created_blocking_task_ids: List of task IDs created as blockers during workflow
        """
        self.task_dao = task_dao
        self.dependency_dao = dependency_dao
        self.task_id = task_id
        self.new_start_date = start_date
        self.dependency_task_ids = dependency_task_ids
        self.reason = reason
        self.created_blocking_task_ids = created_blocking_task_ids or []

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

        # On redo, restore created blocking tasks from TRASH and recreate dependencies
        if len(self.created_dependency_ids) > 0:
            # Restore created blocking tasks from TRASH
            for blocking_task_id in self.created_blocking_task_ids:
                blocking_task = self.task_dao.get_by_id(blocking_task_id)
                if blocking_task and blocking_task.state == TaskState.TRASH:
                    blocking_task.state = TaskState.ACTIVE
                    self.task_dao.update(blocking_task)

            # Recreate dependencies that were removed by undo
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
        # On first execution, dependencies already exist (created by DependencySelectionDialog)
        # Just get their IDs for undo tracking
        else:
            # Get existing dependency IDs for undo tracking
            # Dependencies were already created by the dialog, so we just need to track them
            existing_deps = self.dependency_dao.get_dependencies_for_task(self.task_id)
            # Only track dependencies for the blocking tasks we expect
            for dep in existing_deps:
                if dep.blocking_task_id in self.dependency_task_ids:
                    self.created_dependency_ids.append(dep.id)

        # Return success (task was deferred)
        return True

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

        # Move created blocking tasks to TRASH
        for blocking_task_id in self.created_blocking_task_ids:
            blocking_task = self.task_dao.get_by_id(blocking_task_id)
            if blocking_task:
                blocking_task.state = TaskState.TRASH
                self.task_dao.update(blocking_task)

        return True

    def get_description(self) -> str:
        """Get a human-readable description of this command."""
        count = len(self.dependency_task_ids)
        plural = 'dependency' if count == 1 else 'dependencies'
        if self.task_title:
            return f"Defer task with {count} {plural}: {self.task_title}"
        return f"Defer task with {count} {plural} (ID: {self.task_id})"
