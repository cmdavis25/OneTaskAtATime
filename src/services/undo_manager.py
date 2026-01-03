"""
Undo/Redo Manager for OneTaskAtATime.

Manages the undo/redo stack using the Command pattern.
"""

from typing import List, Optional
from PyQt5.QtCore import QObject, pyqtSignal

from src.commands.base_command import Command


class UndoManager(QObject):
    """
    Manager for undo/redo operations.

    Maintains stacks of executed and undone commands, providing
    undo/redo functionality with configurable stack size limits.
    """

    # Signals emitted when undo/redo state changes
    can_undo_changed = pyqtSignal(bool)
    can_redo_changed = pyqtSignal(bool)

    def __init__(self, max_stack_size: int = 50):
        """
        Initialize the Undo Manager.

        Args:
            max_stack_size: Maximum number of commands to keep in history
        """
        super().__init__()
        self.undo_stack: List[Command] = []
        self.redo_stack: List[Command] = []
        self.max_stack_size = max_stack_size

    def execute_command(self, command: Command) -> bool:
        """
        Execute a command and add it to the undo stack.

        Args:
            command: Command to execute

        Returns:
            True if command executed successfully, False otherwise
        """
        if command.execute():
            # Add to undo stack
            self.undo_stack.append(command)

            # Clear redo stack (new action invalidates redo history)
            self.redo_stack.clear()

            # Limit stack size
            if len(self.undo_stack) > self.max_stack_size:
                self.undo_stack.pop(0)

            # Emit signals
            self.can_undo_changed.emit(True)
            self.can_redo_changed.emit(False)

            return True

        return False

    def undo(self) -> bool:
        """
        Undo the last command.

        Returns:
            True if undo succeeded, False if nothing to undo or undo failed
        """
        if not self.can_undo():
            return False

        command = self.undo_stack.pop()

        if command.undo():
            # Move to redo stack
            self.redo_stack.append(command)

            # Emit signals
            self.can_undo_changed.emit(self.can_undo())
            self.can_redo_changed.emit(True)

            return True
        else:
            # Undo failed, put command back
            self.undo_stack.append(command)
            return False

    def redo(self) -> bool:
        """
        Redo the last undone command.

        Returns:
            True if redo succeeded, False if nothing to redo or redo failed
        """
        if not self.can_redo():
            return False

        command = self.redo_stack.pop()

        if command.execute():
            # Move back to undo stack
            self.undo_stack.append(command)

            # Emit signals
            self.can_undo_changed.emit(True)
            self.can_redo_changed.emit(self.can_redo())

            return True
        else:
            # Redo failed, put command back
            self.redo_stack.append(command)
            return False

    def can_undo(self) -> bool:
        """
        Check if undo is available.

        Returns:
            True if there are commands to undo
        """
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """
        Check if redo is available.

        Returns:
            True if there are commands to redo
        """
        return len(self.redo_stack) > 0

    def get_undo_description(self) -> Optional[str]:
        """
        Get description of the command that would be undone.

        Returns:
            Description string, or None if nothing to undo
        """
        if self.can_undo():
            return self.undo_stack[-1].get_description()
        return None

    def get_redo_description(self) -> Optional[str]:
        """
        Get description of the command that would be redone.

        Returns:
            Description string, or None if nothing to redo
        """
        if self.can_redo():
            return self.redo_stack[-1].get_description()
        return None

    def clear(self):
        """Clear all undo/redo history."""
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.can_undo_changed.emit(False)
        self.can_redo_changed.emit(False)

    def get_undo_count(self) -> int:
        """Get number of commands in undo stack."""
        return len(self.undo_stack)

    def get_redo_count(self) -> int:
        """Get number of commands in redo stack."""
        return len(self.redo_stack)
