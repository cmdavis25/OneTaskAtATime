"""
Large Dataset Generator for Performance Testing

Generates realistic large datasets (10,000+ tasks) with varied distributions
matching real-world usage patterns for performance benchmarking.
"""

import random
import sqlite3
from datetime import datetime, date, timedelta
from typing import List, Tuple

from src.models.task import Task
from src.models.enums import TaskState, Priority
from src.database.task_dao import TaskDAO
from src.database.context_dao import ContextDAO
from src.database.dependency_dao import DependencyDAO
from src.database.task_history_dao import TaskHistoryDAO


class LargeDatasetGenerator:
    """
    Generate realistic large datasets for performance testing.

    Provides methods to create thousands of tasks with:
    - Realistic title and description content
    - Weighted priority distribution (more medium than high/low)
    - Varied due dates and states
    - Dependencies (15% of tasks have dependencies)
    - Task history events
    - Contexts and tags
    """

    # Sample task titles by category
    WORK_TITLES = [
        "Review pull request",
        "Update documentation",
        "Fix bug in authentication",
        "Implement new feature",
        "Refactor codebase",
        "Write unit tests",
        "Deploy to production",
        "Database migration",
        "Code review session",
        "Team meeting",
        "Client presentation",
        "Performance optimization",
        "Security audit",
        "API integration",
        "Design mockups"
    ]

    HOME_TITLES = [
        "Grocery shopping",
        "Pay bills",
        "Clean garage",
        "Schedule dentist appointment",
        "Organize photos",
        "Plan vacation",
        "Call family",
        "Exercise routine",
        "Meal prep",
        "Home repairs",
        "Garden maintenance",
        "Update insurance",
        "Tax preparation",
        "Vehicle maintenance",
        "Declutter closet"
    ]

    LEARNING_TITLES = [
        "Read technical book",
        "Watch online course",
        "Practice coding problems",
        "Learn new framework",
        "Attend workshop",
        "Research topic",
        "Write blog post",
        "Complete tutorial",
        "Study documentation",
        "Review concepts",
        "Build side project",
        "Experiment with library",
        "Follow tutorial series",
        "Take notes on lecture",
        "Practice new skill"
    ]

    DESCRIPTIONS = [
        "High priority task that needs attention soon",
        "Low priority, can be done later",
        "Requires careful planning and execution",
        "Quick task, should take < 30 minutes",
        "Complex task with multiple steps",
        "Waiting on external dependencies",
        "Follow-up from previous meeting",
        "Recurring task that needs regular attention",
        "One-time task with clear deliverable",
        "Exploratory task to gather information"
    ]

    def __init__(self, db_connection: sqlite3.Connection):
        """
        Initialize generator with database connection.

        Args:
            db_connection: SQLite database connection
        """
        self.db_connection = db_connection
        self.task_dao = TaskDAO(db_connection)
        self.context_dao = ContextDAO(db_connection)
        self.dependency_dao = DependencyDAO(db_connection)
        self.task_history_dao = TaskHistoryDAO(db_connection)

    def generate_tasks(self, count: int) -> List[int]:
        """
        Generate N tasks with realistic distributions.

        Distribution:
        - 60% ACTIVE
        - 15% DEFERRED
        - 10% DELEGATED
        - 5% SOMEDAY
        - 10% COMPLETED

        Priority distribution:
        - 20% HIGH
        - 60% MEDIUM
        - 20% LOW

        Args:
            count: Number of tasks to generate

        Returns:
            List of task IDs
        """
        print(f"Generating {count} tasks...")

        task_ids = []
        state_distribution = [
            (TaskState.ACTIVE, 0.60),
            (TaskState.DEFERRED, 0.15),
            (TaskState.DELEGATED, 0.10),
            (TaskState.SOMEDAY, 0.05),
            (TaskState.COMPLETED, 0.10)
        ]

        priority_distribution = [
            (Priority.HIGH, 0.20),
            (Priority.MEDIUM, 0.60),
            (Priority.LOW, 0.20)
        ]

        # Create contexts first
        contexts = self._create_contexts()

        for i in range(count):
            # Select state based on distribution
            state = self._weighted_choice(state_distribution)

            # Select priority based on distribution
            priority = self._weighted_choice(priority_distribution)

            # Generate task
            task = Task(
                title=self._generate_title(i),
                description=self._generate_description(),
                priority=priority,
                due_date=self._random_due_date(state),
                state=state,
                context_id=random.choice(contexts) if contexts else None,
                elo_rating=random.gauss(1500, 200),  # Normal distribution around 1500
                comparison_count=random.randint(0, 50),
                created_at=datetime.now() - timedelta(days=random.randint(0, 365))
            )

            # Add state-specific fields
            if state == TaskState.DEFERRED:
                task.start_date = self._random_start_date()
            elif state == TaskState.DELEGATED:
                task.delegated_to = self._random_person()
                task.follow_up_date = self._random_follow_up_date()
            elif state == TaskState.COMPLETED:
                task.completed_at = datetime.now() - timedelta(days=random.randint(0, 180))

            # Create task
            task_id = self.task_dao.create(task)
            task_ids.append(task_id)

            # Progress indicator
            if (i + 1) % 1000 == 0:
                print(f"  Created {i + 1}/{count} tasks...")

        print(f"✓ Generated {count} tasks")
        return task_ids

    def generate_history_events(self, task_ids: List[int], events_per_task: int = 10):
        """
        Generate realistic task history for each task.

        Args:
            task_ids: List of task IDs to generate history for
            events_per_task: Average number of events per task
        """
        print(f"Generating history events for {len(task_ids)} tasks...")

        event_types = [
            "CREATED", "UPDATED", "PRIORITY_CHANGED", "DUE_DATE_CHANGED",
            "DEFERRED", "ACTIVATED", "DELEGATED", "COMPLETED"
        ]

        for i, task_id in enumerate(task_ids):
            # Vary number of events
            num_events = random.randint(1, events_per_task * 2)

            for j in range(num_events):
                event_type = random.choice(event_types)
                timestamp = datetime.now() - timedelta(days=random.randint(0, 365))

                self.task_history_dao.log_event(
                    task_id=task_id,
                    event_type=event_type,
                    description=f"{event_type} event",
                    timestamp=timestamp
                )

            if (i + 1) % 1000 == 0:
                print(f"  Processed {i + 1}/{len(task_ids)} tasks...")

        print(f"✓ Generated history for {len(task_ids)} tasks")

    def generate_dependencies(self, task_ids: List[int], dependency_ratio: float = 0.15):
        """
        Create dependency graph with specified ratio.

        Args:
            task_ids: List of task IDs
            dependency_ratio: Fraction of tasks that should have dependencies (default 0.15)
        """
        print(f"Generating dependencies for {int(len(task_ids) * dependency_ratio)} tasks...")

        num_dependent_tasks = int(len(task_ids) * dependency_ratio)
        dependent_tasks = random.sample(task_ids, num_dependent_tasks)

        dependencies_created = 0
        for dependent_id in dependent_tasks:
            # Each dependent task depends on 1-3 other tasks
            num_dependencies = random.randint(1, 3)

            # Select prerequisite tasks (must be different from dependent)
            possible_prereqs = [tid for tid in task_ids if tid != dependent_id]
            prerequisites = random.sample(possible_prereqs, min(num_dependencies, len(possible_prereqs)))

            for prerequisite_id in prerequisites:
                try:
                    self.dependency_dao.add_dependency(dependent_id, prerequisite_id)
                    dependencies_created += 1
                except Exception:
                    # May fail if creates circular dependency - ignore
                    pass

        print(f"✓ Created {dependencies_created} dependencies")

    def generate_complete_dataset(self, task_count: int) -> Tuple[List[int], int, int]:
        """
        Generate complete dataset with tasks, history, and dependencies.

        Args:
            task_count: Number of tasks to generate

        Returns:
            Tuple of (task_ids, num_history_events, num_dependencies)
        """
        print(f"\n=== Generating Complete Dataset ({task_count} tasks) ===\n")

        # Generate tasks
        task_ids = self.generate_tasks(task_count)

        # Generate history (average 10 events per task)
        self.generate_history_events(task_ids, events_per_task=10)
        num_history_events = task_count * 10

        # Generate dependencies (15% of tasks)
        self.generate_dependencies(task_ids, dependency_ratio=0.15)
        num_dependencies = int(task_count * 0.15 * 2)  # Approx

        print(f"\n=== Dataset Generation Complete ===")
        print(f"  Tasks: {len(task_ids)}")
        print(f"  History Events: ~{num_history_events}")
        print(f"  Dependencies: ~{num_dependencies}")
        print()

        return task_ids, num_history_events, num_dependencies

    # Helper Methods

    def _create_contexts(self) -> List[int]:
        """Create sample contexts and return their IDs."""
        contexts = [
            ("Work", "Office and work-related tasks"),
            ("Home", "Personal and home tasks"),
            ("Errands", "Tasks requiring leaving the house"),
            ("Online", "Tasks that can be done online"),
            ("Phone", "Tasks requiring phone calls")
        ]

        context_ids = []
        for name, description in contexts:
            context_id = self.context_dao.create(name, description)
            context_ids.append(context_id)

        return context_ids

    def _weighted_choice(self, choices: List[Tuple]):
        """Select item based on weighted probabilities."""
        items, weights = zip(*choices)
        return random.choices(items, weights=weights)[0]

    def _generate_title(self, index: int) -> str:
        """Generate realistic task title."""
        category = random.choice([self.WORK_TITLES, self.HOME_TITLES, self.LEARNING_TITLES])
        base_title = random.choice(category)
        return f"{base_title} #{index + 1}"

    def _generate_description(self) -> str:
        """Generate task description."""
        return random.choice(self.DESCRIPTIONS)

    def _random_due_date(self, state: TaskState) -> datetime:
        """Generate random due date based on task state."""
        if state == TaskState.COMPLETED:
            # Completed tasks have past due dates
            return datetime.now() - timedelta(days=random.randint(1, 180))
        elif state == TaskState.SOMEDAY:
            # Someday tasks may not have due dates or have distant ones
            return None if random.random() < 0.3 else datetime.now() + timedelta(days=random.randint(30, 365))
        else:
            # Active/deferred/delegated have future due dates (or overdue)
            return datetime.now() + timedelta(days=random.randint(-10, 90))

    def _random_start_date(self) -> datetime:
        """Generate random start date for deferred tasks."""
        return datetime.now() + timedelta(days=random.randint(1, 60))

    def _random_follow_up_date(self) -> datetime:
        """Generate random follow-up date for delegated tasks."""
        return datetime.now() + timedelta(days=random.randint(1, 30))

    def _random_person(self) -> str:
        """Generate random person name for delegation."""
        names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry"]
        return random.choice(names)
