"""
Test script for dependency filter in Task List View.

This script verifies that the dependency filter checkbox works correctly.
"""

import sys
from datetime import date, timedelta
from PyQt5.QtWidgets import QApplication
from src.database.connection import DatabaseConnection
from src.ui.task_list_view import TaskListView
from src.services.task_service import TaskService
from src.models.task import Task
from src.models.enums import TaskState


def setup_test_data(db_connection):
    """Create test tasks with and without dependencies."""
    task_service = TaskService(db_connection)

    # Create some tasks without dependencies
    task1 = Task(
        title="Task 1 - No Dependencies",
        description="This task has no blockers",
        base_priority=2,
        state=TaskState.ACTIVE,
        due_date=date.today() + timedelta(days=7)
    )
    created_task1 = task_service.create_task(task1)

    task2 = Task(
        title="Task 2 - No Dependencies",
        description="This task also has no blockers",
        base_priority=3,
        state=TaskState.ACTIVE,
        due_date=date.today() + timedelta(days=5)
    )
    created_task2 = task_service.create_task(task2)

    # Create a task that will be a blocker
    blocker_task = Task(
        title="Blocker Task",
        description="This task blocks other tasks",
        base_priority=3,
        state=TaskState.ACTIVE,
        due_date=date.today() + timedelta(days=3)
    )
    created_blocker = task_service.create_task(blocker_task)

    # Create a task with dependencies
    blocked_task = Task(
        title="Blocked Task - Has Dependencies",
        description="This task is blocked by the blocker task",
        base_priority=2,
        state=TaskState.ACTIVE,
        due_date=date.today() + timedelta(days=10)
    )
    created_blocked = task_service.create_task(blocked_task)

    # Add dependency
    from src.database.dependency_dao import DependencyDAO
    from src.models.dependency import Dependency

    dependency_dao = DependencyDAO(db_connection.get_connection())
    dependency = Dependency(
        blocked_task_id=created_blocked.id,
        blocking_task_id=created_blocker.id
    )
    dependency_dao.create(dependency)

    print(f"Created test tasks:")
    print(f"  - {created_task1.title} (ID: {created_task1.id}) - No dependencies")
    print(f"  - {created_task2.title} (ID: {created_task2.id}) - No dependencies")
    print(f"  - {created_blocker.title} (ID: {created_blocker.id}) - No dependencies (but blocks others)")
    print(f"  - {created_blocked.title} (ID: {created_blocked.id}) - HAS DEPENDENCIES (blocked by {created_blocker.id})")
    print(f"\nTo test:")
    print(f"  1. Check the 'Hide tasks with dependencies' checkbox")
    print(f"  2. Verify that '{created_blocked.title}' is hidden")
    print(f"  3. Verify that the other 3 tasks are still visible")
    print(f"  4. Uncheck the checkbox to show all tasks again")


def main():
    """Run the test."""
    app = QApplication(sys.argv)

    # Get database connection (it's a singleton)
    db_connection = DatabaseConnection()

    # Setup test data
    setup_test_data(db_connection)

    # Create and show the Task List View
    task_list = TaskListView(db_connection)
    task_list.setWindowTitle("Task List - Dependency Filter Test")
    task_list.resize(1200, 600)
    task_list.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
