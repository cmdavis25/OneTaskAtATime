"""
Base Command class for undo/redo pattern.

Defines the interface for all undoable commands in OneTaskAtATime.
"""

from abc import ABC, abstractmethod


class Command(ABC):
    """
    Base class for undoable commands.

    All commands that support undo/redo must inherit from this class
    and implement the execute(), undo(), and get_description() methods.
    """

    @abstractmethod
    def execute(self) -> bool:
        """
        Execute the command.

        Returns:
            True if command executed successfully, False otherwise
        """
        pass

    @abstractmethod
    def undo(self) -> bool:
        """
        Undo the command, reverting to previous state.

        Returns:
            True if undo succeeded, False otherwise
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """
        Get human-readable description of the command.

        Returns:
            Description string (e.g., 'Complete task: Buy groceries')
        """
        pass
