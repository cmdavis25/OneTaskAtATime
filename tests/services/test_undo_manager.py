"""
Unit tests for UndoManager.

Tests undo/redo functionality and command execution.
"""

import pytest
from unittest.mock import Mock

from src.services.undo_manager import UndoManager
from src.commands.base_command import Command


class MockCommand(Command):
    """Mock command for testing."""

    def __init__(self, should_succeed=True):
        self.should_succeed = should_succeed
        self.execute_count = 0
        self.undo_count = 0

    def execute(self):
        self.execute_count += 1
        return self.should_succeed

    def undo(self):
        self.undo_count += 1
        return self.should_succeed

    def get_description(self):
        return "Mock command"


@pytest.fixture
def undo_manager():
    """Create UndoManager instance."""
    return UndoManager(max_stack_size=10)


def test_execute_command_adds_to_stack(undo_manager):
    """Test that executing command adds it to undo stack."""
    cmd = MockCommand()

    assert undo_manager.execute_command(cmd)
    assert undo_manager.can_undo()
    assert not undo_manager.can_redo()
    assert undo_manager.get_undo_count() == 1


def test_undo_restores_state(undo_manager):
    """Test that undo works correctly."""
    cmd = MockCommand()

    undo_manager.execute_command(cmd)
    assert cmd.execute_count == 1

    assert undo_manager.undo()
    assert cmd.undo_count == 1
    assert undo_manager.can_redo()
    assert not undo_manager.can_undo()


def test_redo_reapplies_command(undo_manager):
    """Test that redo works correctly."""
    cmd = MockCommand()

    undo_manager.execute_command(cmd)
    undo_manager.undo()

    assert undo_manager.redo()
    assert cmd.execute_count == 2  # Executed twice (initial + redo)


def test_new_command_clears_redo_stack(undo_manager):
    """Test that new command clears redo history."""
    cmd1 = MockCommand()
    cmd2 = MockCommand()

    undo_manager.execute_command(cmd1)
    undo_manager.undo()

    assert undo_manager.can_redo()

    undo_manager.execute_command(cmd2)

    assert not undo_manager.can_redo()


def test_max_stack_size_enforced(undo_manager):
    """Test that stack size limit is enforced."""
    for i in range(15):
        cmd = MockCommand()
        undo_manager.execute_command(cmd)

    assert undo_manager.get_undo_count() == 10  # Max is 10


def test_get_undo_description(undo_manager):
    """Test getting undo description."""
    cmd = MockCommand()

    undo_manager.execute_command(cmd)

    description = undo_manager.get_undo_description()
    assert description == "Mock command"


def test_clear_removes_all_history(undo_manager):
    """Test clearing undo/redo history."""
    cmd = MockCommand()

    undo_manager.execute_command(cmd)
    undo_manager.undo()

    undo_manager.clear()

    assert not undo_manager.can_undo()
    assert not undo_manager.can_redo()
    assert undo_manager.get_undo_count() == 0
    assert undo_manager.get_redo_count() == 0


def test_failed_execute_not_added_to_stack(undo_manager):
    """Test that failed commands are not added to stack."""
    cmd = MockCommand(should_succeed=False)

    assert not undo_manager.execute_command(cmd)
    assert not undo_manager.can_undo()
