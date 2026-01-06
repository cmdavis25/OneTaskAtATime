"""
Script to check for duplicate dependencies in the database.
"""

from src.database.connection import DatabaseConnection
from src.database.dependency_dao import DependencyDAO
from src.database.task_dao import TaskDAO

# Connect to database
db_wrapper = DatabaseConnection()
db_conn = db_wrapper.get_connection()

dependency_dao = DependencyDAO(db_conn)
task_dao = TaskDAO(db_conn)

# Get all tasks
tasks = task_dao.get_all()

print("Checking for duplicate dependencies...")
print("=" * 80)

duplicates_found = False

for task in tasks:
    if not task.id:
        continue

    # Get dependencies for this task
    dependencies = dependency_dao.get_dependencies_for_task(task.id)

    if not dependencies:
        continue

    # Check for duplicates by comparing blocking_task_ids
    blocking_ids = [dep.blocking_task_id for dep in dependencies]
    unique_blocking_ids = set(blocking_ids)

    if len(blocking_ids) != len(unique_blocking_ids):
        duplicates_found = True
        print(f"\nDUPLICATES FOUND for Task ID {task.id}: {task.title}")
        print(f"   Total dependencies: {len(blocking_ids)}")
        print(f"   Unique blocking tasks: {len(unique_blocking_ids)}")
        print(f"   Dependency records:")
        for dep in dependencies:
            print(f"      - Dependency ID: {dep.id}, Blocking Task ID: {dep.blocking_task_id}")

if not duplicates_found:
    print("\nNo duplicate dependencies found in database!")
else:
    print("\n" + "=" * 80)
    print("Run this SQL to see duplicate dependency records:")
    print("  SELECT blocked_task_id, blocking_task_id, COUNT(*)")
    print("  FROM dependencies")
    print("  GROUP BY blocked_task_id, blocking_task_id")
    print("  HAVING COUNT(*) > 1;")

# Database connection is managed by singleton, no need to close
