"""
Seed data script for development and testing.

Populates the database with sample data to test the application.
"""

import sqlite3
from datetime import date, timedelta
from .schema import DatabaseSchema
from .task_dao import TaskDAO
from .context_dao import ContextDAO
from .project_tag_dao import ProjectTagDAO
from .dependency_dao import DependencyDAO
from ..models import Task, Context, ProjectTag, TaskState, Dependency


def seed_database(db_connection: sqlite3.Connection, clear_existing: bool = False) -> None:
    """
    Populate the database with sample data.

    Args:
        db_connection: Active SQLite database connection
        clear_existing: If True, clear all existing data before seeding
    """
    if clear_existing:
        clear_all_data(db_connection)

    # Initialize DAOs
    task_dao = TaskDAO(db_connection)
    context_dao = ContextDAO(db_connection)
    project_tag_dao = ProjectTagDAO(db_connection)
    dependency_dao = DependencyDAO(db_connection)

    print("Seeding database with sample data...")

    # Create contexts
    print("Creating contexts...")
    contexts = [
        Context(name="@computer", description="Tasks requiring a computer"),
        Context(name="@phone", description="Tasks that can be done on phone"),
        Context(name="@errands", description="Tasks outside the house"),
        Context(name="@home", description="Tasks at home"),
        Context(name="@office", description="Tasks at the office"),
    ]
    created_contexts = {c.name: context_dao.create(c) for c in contexts}
    print(f"  Created {len(created_contexts)} contexts")

    # Create project tags
    print("Creating project tags...")
    tags = [
        ProjectTag(name="Work", description="Work-related tasks", color="#3498db"),
        ProjectTag(name="Personal", description="Personal tasks", color="#2ecc71"),
        ProjectTag(name="Learning", description="Educational tasks", color="#9b59b6"),
        ProjectTag(name="Health", description="Health and fitness", color="#e74c3c"),
        ProjectTag(name="Home", description="Home improvement", color="#f39c12"),
    ]
    created_tags = {t.name: project_tag_dao.create(t) for t in tags}
    print(f"  Created {len(created_tags)} project tags")

    # Create tasks
    print("Creating tasks...")
    today = date.today()

    # Active tasks with various priorities and due dates
    tasks = [
        # High priority, urgent tasks
        Task(
            title="Review pull request #142",
            description="Code review for authentication refactor",
            base_priority=3,
            due_date=today + timedelta(days=1),
            state=TaskState.ACTIVE,
            context_id=created_contexts["@computer"].id,
            project_tags=[created_tags["Work"].id]
        ),
        Task(
            title="Prepare presentation for Monday meeting",
            description="Create slides on Q4 roadmap",
            base_priority=3,
            due_date=today + timedelta(days=2),
            state=TaskState.ACTIVE,
            context_id=created_contexts["@computer"].id,
            project_tags=[created_tags["Work"].id]
        ),

        # Medium priority tasks
        Task(
            title="Update project documentation",
            description="Document new API endpoints",
            base_priority=2,
            due_date=today + timedelta(days=5),
            state=TaskState.ACTIVE,
            context_id=created_contexts["@computer"].id,
            project_tags=[created_tags["Work"].id]
        ),
        Task(
            title="Schedule dentist appointment",
            description="6-month checkup",
            base_priority=2,
            due_date=today + timedelta(days=7),
            state=TaskState.ACTIVE,
            context_id=created_contexts["@phone"].id,
            project_tags=[created_tags["Health"].id]
        ),
        Task(
            title="Buy groceries",
            description="Milk, eggs, bread, vegetables",
            base_priority=2,
            due_date=today + timedelta(days=2),
            state=TaskState.ACTIVE,
            context_id=created_contexts["@errands"].id,
            project_tags=[created_tags["Personal"].id]
        ),

        # Low priority tasks
        Task(
            title="Read 'Clean Code' chapter 5",
            description="Continue reading on software craftsmanship",
            base_priority=1,
            due_date=today + timedelta(days=10),
            state=TaskState.ACTIVE,
            context_id=created_contexts["@home"].id,
            project_tags=[created_tags["Learning"].id]
        ),
        Task(
            title="Organize desk drawer",
            description="File papers and throw out old receipts",
            base_priority=1,
            state=TaskState.ACTIVE,
            context_id=created_contexts["@home"].id,
            project_tags=[created_tags["Personal"].id]
        ),

        # Deferred tasks
        Task(
            title="Plan summer vacation",
            description="Research destinations and book flights",
            base_priority=2,
            start_date=today + timedelta(days=30),
            state=TaskState.DEFERRED,
            context_id=created_contexts["@computer"].id,
            project_tags=[created_tags["Personal"].id]
        ),
        Task(
            title="Start tax preparation",
            description="Gather documents for tax filing",
            base_priority=3,
            start_date=today + timedelta(days=60),
            state=TaskState.DEFERRED,
            context_id=created_contexts["@home"].id,
            project_tags=[created_tags["Personal"].id]
        ),

        # Delegated tasks
        Task(
            title="Design mockups for new feature",
            description="Waiting on designer Alice",
            base_priority=2,
            delegated_to="Alice (Designer)",
            follow_up_date=today + timedelta(days=3),
            state=TaskState.DELEGATED,
            project_tags=[created_tags["Work"].id]
        ),

        # Someday/Maybe tasks
        Task(
            title="Learn Vue.js",
            description="Explore Vue.js for potential projects",
            base_priority=1,
            state=TaskState.SOMEDAY,
            project_tags=[created_tags["Learning"].id]
        ),
        Task(
            title="Build a personal website",
            description="Portfolio site with blog",
            base_priority=1,
            state=TaskState.SOMEDAY,
            project_tags=[created_tags["Personal"].id, created_tags["Learning"].id]
        ),

        # Tasks without due dates
        Task(
            title="Refactor database connection pool",
            description="Optimize connection handling",
            base_priority=2,
            state=TaskState.ACTIVE,
            context_id=created_contexts["@computer"].id,
            project_tags=[created_tags["Work"].id]
        ),
    ]

    created_tasks = []
    for task in tasks:
        created = task_dao.create(task)
        created_tasks.append(created)

    print(f"  Created {len(created_tasks)} tasks")

    # Create some dependencies
    print("Creating dependencies...")
    # Find specific tasks for dependencies
    review_pr = next(t for t in created_tasks if "pull request" in t.title)
    prepare_presentation = next(t for t in created_tasks if "presentation" in t.title)
    update_docs = next(t for t in created_tasks if "documentation" in t.title)

    dependencies = [
        # Documentation update should happen after PR review
        Dependency(blocked_task_id=update_docs.id, blocking_task_id=review_pr.id),
    ]

    for dep in dependencies:
        dependency_dao.create(dep)

    print(f"  Created {len(dependencies)} dependencies")

    # Add some priority adjustments (from comparisons)
    print("Adding priority adjustments...")
    # Simulate that some tasks have been compared and lost
    cursor = db_connection.cursor()

    # Task that lost comparison gets priority adjusted down
    organize_desk = next(t for t in created_tasks if "Organize desk" in t.title)
    cursor.execute(
        "UPDATE tasks SET priority_adjustment = ? WHERE id = ?",
        (0.5, organize_desk.id)
    )

    db_connection.commit()
    print("  Added priority adjustments")

    print("\nDatabase seeded successfully!")
    print(f"\nSummary:")
    print(f"  - {len(created_contexts)} contexts")
    print(f"  - {len(created_tags)} project tags")
    print(f"  - {len(created_tasks)} tasks")
    print(f"    • {len([t for t in created_tasks if t.state == TaskState.ACTIVE])} active")
    print(f"    • {len([t for t in created_tasks if t.state == TaskState.DEFERRED])} deferred")
    print(f"    • {len([t for t in created_tasks if t.state == TaskState.DELEGATED])} delegated")
    print(f"    • {len([t for t in created_tasks if t.state == TaskState.SOMEDAY])} someday")
    print(f"  - {len(dependencies)} dependencies")


def clear_all_data(db_connection: sqlite3.Connection) -> None:
    """
    Clear all data from the database while preserving schema and settings.

    Args:
        db_connection: Active SQLite database connection
    """
    cursor = db_connection.cursor()

    # Delete all data from tables (in correct order due to foreign keys)
    tables = [
        'task_comparisons',
        'postpone_history',
        'task_project_tags',
        'dependencies',
        'tasks',
        'project_tags',
        'contexts'
    ]

    for table in tables:
        cursor.execute(f"DELETE FROM {table}")

    db_connection.commit()
    print("Cleared existing data from database")


if __name__ == "__main__":
    """Run seed script directly for testing."""
    import sys
    import os

    # Add parent directory to path for imports
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

    from src.database.connection import get_db

    # Get database connection
    db = get_db()

    # Initialize schema
    DatabaseSchema.initialize_database(db)

    # Seed data
    seed_database(db, clear_existing=True)

    print("\nDatabase seeded! You can now run the application.")
