"""Defer Task with Blocker Command for undo/redo functionality."""

from datetime import date
from typing import Optional

from src.commands.base_command import Command
from src.models.task import Task
from src.models.enums import TaskState
from src.database.task_dao import TaskDAO
from src.database.dependency_dao import DependencyDAO


class DeferWithBlockerCommand(Command):
    """
    Compound command to defer a task and create a blocker dependency.

    This command handles:
    1. Deferring the task (changing state to DEFERRED and setting start_date)
    2. Creating a dependency relationship with the blocker task

    On undo, it:
    1. Restores the task's original state and start_date
    2. Removes the dependency relationship
    3. Moves the blocker task to TRASH (if it was created as part of this workflow)
    """

    def __init__(
        self,
        task_dao: TaskDAO,
        dependency_dao: DependencyDAO,
        task_id: int,
        start_date: date,
        blocker_task_id: int,
        blocker_was_created: bool = True,
        reason: Optional[str] = None
    ):
        """
        Initialize the command.

        Args:
            task_dao: Task data access object
            dependency_dao: Dependency data access object
            task_id: ID of task being deferred
            start_date: Date when task should become actionable
            blocker_task_id: ID of the blocker task
            blocker_was_created: True if blocker was created by this workflow (default),
                               False if blocker was selected from existing tasks
            reason: Optional reason for deferring
        """
        self.task_dao = task_dao
        self.dependency_dao = dependency_dao
        self.task_id = task_id
        self.new_start_date = start_date
        self.blocker_task_id = blocker_task_id
        self.blocker_was_created = blocker_was_created
        self.reason = reason

        # State to restore on undo
        self.original_state: Optional[TaskState] = None
        self.original_start_date: Optional[date] = None
        self.task_title: Optional[str] = None
        self.dependency_id: Optional[int] = None
        self.blocker_original_state: Optional[TaskState] = None

    def execute(self) -> bool:
        """Execute the defer and blocker workflow."""
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

        # If blocker was created, save/restore its state
        if self.blocker_was_created:
            blocker_task = self.task_dao.get_by_id(self.blocker_task_id)
            if blocker_task:
                # Save original state only on first execution
                if self.blocker_original_state is None:
                    self.blocker_original_state = blocker_task.state
                # On redo, restore blocker from TRASH back to original state
                elif blocker_task.state == TaskState.TRASH:
                    blocker_task.state = self.blocker_original_state
                    self.task_dao.update(blocker_task)

        # Create dependency relationship
        from src.models.dependency import Dependency
        dependency = Dependency(
            blocked_task_id=self.task_id,
            blocking_task_id=self.blocker_task_id
        )

        try:
            created_dependency = self.dependency_dao.create(dependency)
            self.dependency_id = created_dependency.id
            return True
        except ValueError as e:
            # Circular dependency error - rollback task changes
            task.state = self.original_state
            task.start_date = self.original_start_date
            self.task_dao.update(task)
            return False

    def undo(self) -> bool:
        """Undo the defer and blocker workflow."""
        # Restore the task's original state
        task = self.task_dao.get_by_id(self.task_id)
        if not task:
            return False

        task.state = self.original_state
        task.start_date = self.original_start_date

        if not self.task_dao.update(task):
            return False

        # Remove the dependency relationship
        if self.dependency_id:
            self.dependency_dao.delete(self.dependency_id)

        # If blocker was created as part of this workflow, move it to TRASH
        if self.blocker_was_created:
            blocker_task = self.task_dao.get_by_id(self.blocker_task_id)
            if blocker_task:
                blocker_task.state = TaskState.TRASH
                self.task_dao.update(blocker_task)

        return True

    def get_description(self) -> str:
        """Get a human-readable description of this command."""
        if self.task_title:
            return f"Defer task with blocker: {self.task_title} (until {self.new_start_date})"
        return f"Defer task with blocker (ID: {self.task_id})"
