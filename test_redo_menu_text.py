"""
Test script to verify Redo menu text updates correctly.
"""

import sys
import sqlite3
from PyQt5.QtWidgets import QApplication
from src.database.schema import DatabaseSchema
from src.services.undo_manager import UndoManager
from src.commands.defer_task_command import DeferTaskCommand
from src.database.task_dao import TaskDAO
from src.models.task import Task
from src.models.enums import TaskState
from datetime import date, timedelta


def test_redo_menu_text():
    """Test that redo description is correctly retrieved from UndoManager."""
    print("=== Testing Redo Menu Text ===\n")

    # Setup
    conn = sqlite3.connect(":memory:")
    DatabaseSchema.initialize_database(conn)
    task_dao = TaskDAO(conn)
    undo_manager = UndoManager()

    # Create a test task
    task = task_dao.create(Task(
        title="Test Task for Redo",
        state=TaskState.ACTIVE,
        base_priority=2
    ))
    task_id = task.id
    print(f"Created task: '{task.title}' (ID: {task_id})")

    # Create and execute a defer command
    start_date = date.today() + timedelta(days=1)
    defer_command = DeferTaskCommand(
        task_dao,
        task_id,
        start_date,
        "Testing redo menu"
    )

    print(f"\nExecuting defer command...")
    undo_manager.execute_command(defer_command)

    # Verify undo description
    undo_desc = undo_manager.get_undo_description()
    print(f"[OK] Undo description: '{undo_desc}'")
    assert undo_desc is not None, "Undo description should not be None"

    # Undo the command
    print(f"\nUndoing defer command...")
    undo_manager.undo()

    # Verify redo description
    redo_desc = undo_manager.get_redo_description()
    print(f"[OK] Redo description: '{redo_desc}'")
    assert redo_desc is not None, "Redo description should not be None"
    assert redo_desc == undo_desc, f"Redo description should match undo description"

    # Redo the command
    print(f"\nRedoing defer command...")
    undo_manager.redo()

    # Verify redo description is now None (nothing to redo)
    redo_desc_after = undo_manager.get_redo_description()
    print(f"[OK] Redo description after redo: {redo_desc_after}")
    assert redo_desc_after is None, "Redo description should be None after redo"

    # Cleanup
    conn.close()

    print("\n=== All Tests PASSED ===")


if __name__ == "__main__":
    # Create minimal QApplication for Qt functionality
    app = QApplication(sys.argv)
    test_redo_menu_text()
    sys.exit(0)
