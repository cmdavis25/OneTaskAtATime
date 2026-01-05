"""
Test script to verify that completing Task C removes it as a dependency from Tasks A and B.

Scenario:
- Task A depends on Task C (C blocks A)
- Task B depends on Task C (C blocks B)
- When Task C is marked as Complete, it should be removed as a dependency from both A and B
"""

import sqlite3
from src.database.schema import DatabaseSchema
from src.database.task_dao import TaskDAO
from src.database.dependency_dao import DependencyDAO
from src.models.task import Task
from src.models.dependency import Dependency
from src.models.enums import TaskState
from src.commands.complete_task_command import CompleteTaskCommand


def test_dependency_removal_on_completion():
    """Test that completing a blocking task removes it from all dependencies."""
    # Create in-memory database
    conn = sqlite3.connect(":memory:")
    DatabaseSchema.initialize_database(conn)

    task_dao = TaskDAO(conn)
    dependency_dao = DependencyDAO(conn)

    print("\n=== Testing Dependency Removal on Task Completion ===\n")

    # Create three tasks
    task_a = task_dao.create(Task(
        title="Task A",
        description="Depends on Task C",
        base_priority=2,
        state=TaskState.ACTIVE
    ))

    task_b = task_dao.create(Task(
        title="Task B",
        description="Also depends on Task C",
        base_priority=2,
        state=TaskState.ACTIVE
    ))

    task_c = task_dao.create(Task(
        title="Task C",
        description="Blocking both A and B",
        base_priority=2,
        state=TaskState.ACTIVE
    ))

    print(f"Created Task A (ID: {task_a.id})")
    print(f"Created Task B (ID: {task_b.id})")
    print(f"Created Task C (ID: {task_c.id})")

    # Create dependencies: A depends on C, B depends on C
    dep_a_c = dependency_dao.create(Dependency(
        blocked_task_id=task_a.id,
        blocking_task_id=task_c.id
    ))

    dep_b_c = dependency_dao.create(Dependency(
        blocked_task_id=task_b.id,
        blocking_task_id=task_c.id
    ))

    print(f"\nCreated dependency: Task A blocked by Task C (Dep ID: {dep_a_c.id})")
    print(f"Created dependency: Task B blocked by Task C (Dep ID: {dep_b_c.id})")

    # Verify initial state
    task_a_deps = dependency_dao.get_dependencies_for_task(task_a.id)
    task_b_deps = dependency_dao.get_dependencies_for_task(task_b.id)
    task_c_blocking = dependency_dao.get_blocking_tasks(task_c.id)

    print(f"\nBefore completion:")
    print(f"  Task A has {len(task_a_deps)} dependency/dependencies")
    print(f"  Task B has {len(task_b_deps)} dependency/dependencies")
    print(f"  Task C is blocking {len(task_c_blocking)} task(s)")

    assert len(task_a_deps) == 1, "Task A should have 1 dependency"
    assert len(task_b_deps) == 1, "Task B should have 1 dependency"
    assert len(task_c_blocking) == 2, "Task C should be blocking 2 tasks"

    # Complete Task C using the command
    print(f"\n>>> Completing Task C (ID: {task_c.id})...")
    complete_cmd = CompleteTaskCommand(task_dao, task_c.id, dependency_dao)
    success = complete_cmd.execute()

    assert success, "Task C completion should succeed"

    # Verify Task C is completed
    completed_task_c = task_dao.get_by_id(task_c.id)
    assert completed_task_c.state == TaskState.COMPLETED, "Task C should be in COMPLETED state"
    print(f"[OK] Task C marked as COMPLETED")

    # Verify dependencies are removed
    task_a_deps_after = dependency_dao.get_dependencies_for_task(task_a.id)
    task_b_deps_after = dependency_dao.get_dependencies_for_task(task_b.id)
    task_c_blocking_after = dependency_dao.get_blocking_tasks(task_c.id)

    print(f"\nAfter completion:")
    print(f"  Task A has {len(task_a_deps_after)} dependency/dependencies")
    print(f"  Task B has {len(task_b_deps_after)} dependency/dependencies")
    print(f"  Task C is blocking {len(task_c_blocking_after)} task(s)")

    assert len(task_a_deps_after) == 0, "Task A should have no dependencies after C is completed"
    assert len(task_b_deps_after) == 0, "Task B should have no dependencies after C is completed"
    assert len(task_c_blocking_after) == 0, "Task C should not be blocking any tasks after completion"

    print("\n[OK] All dependencies removed successfully!")

    # Test undo functionality
    print(f"\n>>> Testing undo...")
    success = complete_cmd.undo()
    assert success, "Undo should succeed"

    # Verify Task C is back to active
    restored_task_c = task_dao.get_by_id(task_c.id)
    assert restored_task_c.state == TaskState.ACTIVE, "Task C should be back to ACTIVE state"
    print(f"[OK] Task C restored to ACTIVE")

    # Verify dependencies are restored
    task_a_deps_restored = dependency_dao.get_dependencies_for_task(task_a.id)
    task_b_deps_restored = dependency_dao.get_dependencies_for_task(task_b.id)
    task_c_blocking_restored = dependency_dao.get_blocking_tasks(task_c.id)

    print(f"\nAfter undo:")
    print(f"  Task A has {len(task_a_deps_restored)} dependency/dependencies")
    print(f"  Task B has {len(task_b_deps_restored)} dependency/dependencies")
    print(f"  Task C is blocking {len(task_c_blocking_restored)} task(s)")

    assert len(task_a_deps_restored) == 1, "Task A should have 1 dependency after undo"
    assert len(task_b_deps_restored) == 1, "Task B should have 1 dependency after undo"
    assert len(task_c_blocking_restored) == 2, "Task C should be blocking 2 tasks after undo"

    print("\n[OK] All dependencies restored successfully!")
    print("\n=== Test PASSED ===\n")

    conn.close()


if __name__ == "__main__":
    test_dependency_removal_on_completion()
