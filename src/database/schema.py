"""
SQLite database schema for OneTaskAtATime application.

This module defines all database tables, indexes, and schema management.
Based on the GTD-inspired task management system with flat structure and tags.
"""

from typing import List
import sqlite3


class DatabaseSchema:
    """Manages the database schema creation and migrations."""

    # Schema version for migration tracking
    CURRENT_VERSION = 1

    @staticmethod
    def get_create_tables_sql() -> List[str]:
        """
        Returns SQL statements to create all database tables.

        Tables:
        1. tasks - Main task storage
        2. contexts - Work environment filters (e.g., @computer, @phone)
        3. project_tags - Project organization tags
        4. task_project_tags - Many-to-many relationship for tasks and projects
        5. dependencies - Task dependencies (blockers)
        6. task_comparisons - History of comparison-based priority adjustments
        7. postpone_history - Track when/why tasks were postponed
        8. settings - Application configuration
        """
        return [
            # Table 1: Contexts (work environment filters)
            """
            CREATE TABLE IF NOT EXISTS contexts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,

            # Table 2: Project Tags
            """
            CREATE TABLE IF NOT EXISTS project_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                color TEXT,  -- Hex color code for UI display
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,

            # Table 3: Tasks (main table)
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,

                -- Priority system
                base_priority INTEGER NOT NULL DEFAULT 2 CHECK(base_priority IN (1, 2, 3)),
                -- 1=Low, 2=Medium, 3=High
                priority_adjustment REAL DEFAULT 0.0,
                -- DEPRECATED: Accumulated penalty from comparisons (use elo_rating instead)
                comparison_count INTEGER DEFAULT 0,
                -- Total number of comparisons (renamed from comparison_losses)
                elo_rating REAL DEFAULT 1500.0,
                -- Elo rating for tiered priority refinement within base_priority bands

                -- Urgency system (based on due date)
                due_date DATE,
                -- NULL = no due date

                -- Task state
                state TEXT NOT NULL DEFAULT 'active' CHECK(state IN (
                    'active', 'deferred', 'delegated', 'someday', 'completed', 'trash'
                )),

                -- Deferred task fields
                start_date DATE,
                -- When deferred task becomes actionable

                -- Delegated task fields
                delegated_to TEXT,
                -- Person/system task is delegated to
                follow_up_date DATE,
                -- When to follow up on delegated task

                -- Completion tracking
                completed_at TIMESTAMP,

                -- Organization
                context_id INTEGER,
                -- Single context per task (optional)

                -- Resurfacing tracking
                last_resurfaced_at TIMESTAMP,
                -- Last time this task was shown to user
                resurface_count INTEGER DEFAULT 0,
                -- How many times task has been resurfaced

                -- Recurrence fields
                is_recurring INTEGER DEFAULT 0,
                -- Whether this task repeats on completion (0=False, 1=True)
                recurrence_pattern TEXT,
                -- JSON string defining recurrence rules
                recurrence_parent_id INTEGER,
                -- ID of the first task in recurring series
                share_elo_rating INTEGER DEFAULT 0,
                -- Whether Elo rating is shared across series (0=False, 1=True)
                shared_elo_rating REAL,
                -- Shared Elo pool (if share_elo_rating is True)
                shared_comparison_count INTEGER,
                -- Shared comparison count across series
                recurrence_end_date DATE,
                -- Optional date when recurrence stops
                occurrence_count INTEGER DEFAULT 0,
                -- Number of times this task has recurred

                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (context_id) REFERENCES contexts(id) ON DELETE SET NULL,
                FOREIGN KEY (recurrence_parent_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
            """,

            # Table 4: Task-Project Tags (many-to-many)
            """
            CREATE TABLE IF NOT EXISTS task_project_tags (
                task_id INTEGER NOT NULL,
                project_tag_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                PRIMARY KEY (task_id, project_tag_id),
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (project_tag_id) REFERENCES project_tags(id) ON DELETE CASCADE
            )
            """,

            # Table 5: Dependencies (task blockers)
            """
            CREATE TABLE IF NOT EXISTS dependencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                blocked_task_id INTEGER NOT NULL,
                -- The task that is blocked
                blocking_task_id INTEGER NOT NULL,
                -- The task that must complete first
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (blocked_task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (blocking_task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                CHECK (blocked_task_id != blocking_task_id)
                -- Prevent self-dependencies
            )
            """,

            # Table 6: Task Comparisons (priority adjustment history)
            """
            CREATE TABLE IF NOT EXISTS task_comparisons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                winner_task_id INTEGER NOT NULL,
                loser_task_id INTEGER NOT NULL,
                adjustment_amount REAL NOT NULL,
                -- Amount subtracted from loser
                compared_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (winner_task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (loser_task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
            """,

            # Table 7: Postpone History (track delay reasons)
            """
            CREATE TABLE IF NOT EXISTS postpone_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                reason_type TEXT NOT NULL CHECK(reason_type IN (
                    'multiple_subtasks', 'blocker', 'dependency', 'not_ready', 'other'
                )),
                reason_notes TEXT,
                -- User's explanation
                action_taken TEXT,
                -- What was done: 'broke_down', 'created_blocker', 'added_dependency', 'deferred', 'none'
                postponed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
            """,

            # Table 8: Settings (application configuration)
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                value_type TEXT NOT NULL CHECK(value_type IN ('string', 'integer', 'float', 'boolean', 'json')),
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,

            # Table 9: Task History (comprehensive audit log)
            """
            CREATE TABLE IF NOT EXISTS task_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                event_type TEXT NOT NULL CHECK(event_type IN (
                    'created', 'edited', 'completed', 'deferred', 'delegated',
                    'activated', 'moved_to_someday', 'moved_to_trash', 'restored',
                    'priority_changed', 'due_date_changed', 'dependency_added',
                    'dependency_removed', 'tag_added', 'tag_removed',
                    'context_changed', 'comparison_won', 'comparison_lost'
                )),
                event_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                old_value TEXT,  -- JSON serialized
                new_value TEXT,  -- JSON serialized
                changed_by TEXT DEFAULT 'user',
                context_data TEXT,  -- Additional metadata
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
            """
        ]

    @staticmethod
    def get_create_indexes_sql() -> List[str]:
        """Returns SQL statements to create database indexes for performance."""
        return [
            # Tasks table indexes
            "CREATE INDEX IF NOT EXISTS idx_tasks_state ON tasks(state)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_start_date ON tasks(start_date)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_follow_up_date ON tasks(follow_up_date)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_context_id ON tasks(context_id)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_base_priority ON tasks(base_priority)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_is_recurring ON tasks(is_recurring)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_recurrence_parent ON tasks(recurrence_parent_id)",

            # Dependencies indexes
            "CREATE INDEX IF NOT EXISTS idx_dependencies_blocked_task ON dependencies(blocked_task_id)",
            "CREATE INDEX IF NOT EXISTS idx_dependencies_blocking_task ON dependencies(blocking_task_id)",

            # Task comparisons index
            "CREATE INDEX IF NOT EXISTS idx_comparisons_winner ON task_comparisons(winner_task_id)",
            "CREATE INDEX IF NOT EXISTS idx_comparisons_loser ON task_comparisons(loser_task_id)",

            # Postpone history index
            "CREATE INDEX IF NOT EXISTS idx_postpone_task_id ON postpone_history(task_id)",

            # Task-project tags index (already has PRIMARY KEY, but index for reverse lookup)
            "CREATE INDEX IF NOT EXISTS idx_task_project_tags_project ON task_project_tags(project_tag_id)",

            # Task history indexes
            "CREATE INDEX IF NOT EXISTS idx_task_history_task_id ON task_history(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_history_timestamp ON task_history(event_timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_task_history_type ON task_history(event_type)"
        ]

    @staticmethod
    def get_default_settings() -> List[tuple]:
        """
        Returns default application settings as (key, value, value_type, description) tuples.
        """
        return [
            ('comparison_decrement', '0.5', 'float',
             'Amount to subtract from loser priority in comparisons'),
            ('someday_review_days', '7', 'integer',
             'Days between automatic someday task reviews'),
            ('delegated_remind_days', '1', 'integer',
             'Days before follow-up date to remind about delegated tasks'),
            ('deferred_check_hours', '1', 'integer',
             'Hours between checks for deferred tasks becoming active'),
            ('theme', 'light', 'string',
             'UI theme (light/dark)'),
            ('enable_notifications', 'true', 'boolean',
             'Enable Windows toast notifications'),
            ('score_epsilon', '0.01', 'float',
             'Threshold for considering task scores equal (for tie detection)'),
            ('elo_k_factor', '16', 'integer',
             'Elo rating adjustment sensitivity for established tasks'),
            ('elo_k_factor_new', '32', 'integer',
             'Elo rating adjustment sensitivity for new tasks (first 10 comparisons)'),
            ('elo_new_task_threshold', '10', 'integer',
             'Number of comparisons before task uses base K-factor instead of new K-factor'),

            # Resurfacing intervals
            ('delegated_check_time', '09:00', 'string',
             'Time of day to check delegated tasks'),
            ('someday_review_time', '18:00', 'string',
             'Preferred time for someday review'),
            ('last_someday_review_at', 'null', 'string',
             'Last someday review timestamp'),
            ('postpone_analysis_time', '18:00', 'string',
             'Time of day to analyze postponement patterns'),

            # Notification preferences
            ('enable_toast_notifications', 'true', 'boolean',
             'Enable Windows toast notifications'),
            ('enable_inapp_notifications', 'true', 'boolean',
             'Enable in-app notification panel'),
            ('notification_retention_days', '30', 'integer',
             'Days to keep old notifications'),
            ('notify_deferred_activation', 'true', 'boolean',
             'Notify when deferred tasks activate'),
            ('notify_delegated_followup', 'true', 'boolean',
             'Notify for delegated follow-ups'),
            ('notify_someday_review', 'true', 'boolean',
             'Notify for someday reviews'),
            ('notify_postpone_intervention', 'true', 'boolean',
             'Notify for postponement patterns'),

            # Intervention thresholds
            ('postpone_intervention_threshold', '3', 'integer',
             'Postponements before intervention'),
            ('postpone_pattern_days', '7', 'integer',
             'Days window for pattern detection'),

            # Onboarding and help system
            ('onboarding_completed', 'false', 'boolean',
             'Whether first-run onboarding has been completed'),
            ('tutorial_shown', 'false', 'boolean',
             'Whether interactive tutorial has been shown'),
            ('undo_stack_max_size', '50', 'integer',
             'Maximum number of undo operations to keep in history')
        ]

    @staticmethod
    def initialize_database(db_connection: sqlite3.Connection) -> None:
        """
        Initialize the database with schema and default data.

        Args:
            db_connection: Active SQLite database connection
        """
        cursor = db_connection.cursor()

        # Create all tables
        for sql in DatabaseSchema.get_create_tables_sql():
            cursor.execute(sql)

        # Create all indexes
        for sql in DatabaseSchema.get_create_indexes_sql():
            cursor.execute(sql)

        # Insert default settings
        for key, value, value_type, description in DatabaseSchema.get_default_settings():
            cursor.execute(
                """
                INSERT OR IGNORE INTO settings (key, value, value_type, description)
                VALUES (?, ?, ?, ?)
                """,
                (key, value, value_type, description)
            )

        db_connection.commit()

    @staticmethod
    def get_schema_version(db_connection: sqlite3.Connection) -> int:
        """
        Get the current schema version from the database.

        Args:
            db_connection: Active SQLite database connection

        Returns:
            Schema version number, or 0 if not set
        """
        cursor = db_connection.cursor()
        try:
            result = cursor.execute(
                "SELECT value FROM settings WHERE key = 'schema_version'"
            ).fetchone()
            if result:
                return int(result[0])
        except sqlite3.OperationalError:
            # Table doesn't exist yet
            pass
        return 0

    @staticmethod
    def set_schema_version(db_connection: sqlite3.Connection, version: int) -> None:
        """
        Set the schema version in the database.

        Args:
            db_connection: Active SQLite database connection
            version: Version number to set
        """
        cursor = db_connection.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO settings (key, value, value_type, description)
            VALUES ('schema_version', ?, 'integer', 'Database schema version')
            """,
            (str(version),)
        )
        db_connection.commit()

    @staticmethod
    def migrate_to_elo_system(db_connection: sqlite3.Connection) -> None:
        """
        Migrate existing database to Elo rating system.

        This migration:
        1. Adds elo_rating column if it doesn't exist
        2. Renames comparison_losses to comparison_count (via data migration)
        3. Converts priority_adjustment values to Elo ratings
        4. Adds Elo-related settings

        Args:
            db_connection: Active SQLite database connection
        """
        cursor = db_connection.cursor()

        # Check if migration is already complete
        try:
            cursor.execute("SELECT elo_rating FROM tasks LIMIT 1")
            migration_done = True
        except sqlite3.OperationalError:
            migration_done = False

        if migration_done:
            return  # Already migrated

        print("Migrating database to Elo rating system...")

        # Step 1: Add new columns
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN elo_rating REAL DEFAULT 1500.0")
        except sqlite3.OperationalError:
            pass  # Column already exists

        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN comparison_count INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Step 2: Migrate data from old system to new system (only if old column exists)
        try:
            cursor.execute("""
                SELECT id, base_priority, priority_adjustment, comparison_losses
                FROM tasks
            """)

            tasks = cursor.fetchall()
            for task_id, base_priority, priority_adjustment, comparison_losses in tasks:
                # Convert priority_adjustment to Elo deficit
                # Old system: effective_priority = base - adjustment (0 to ~1.0)
                # Map adjustment [0.0, 1.0] to Elo deficit [0, 500]
                elo_deficit = priority_adjustment * 500 if priority_adjustment else 0
                elo_rating = 1500 - elo_deficit

                # Estimate comparison_count (assume 50% win rate before losses)
                comparison_count = comparison_losses * 2 if comparison_losses else 0

                cursor.execute("""
                    UPDATE tasks
                    SET elo_rating = ?, comparison_count = ?
                    WHERE id = ?
                """, (elo_rating, comparison_count, task_id))
        except sqlite3.OperationalError:
            # Old column doesn't exist - this is a fresh database, no migration needed
            pass

        # Step 3: Add Elo settings
        elo_settings = [
            ('elo_k_factor', '16', 'integer',
             'Elo rating adjustment sensitivity for established tasks'),
            ('elo_k_factor_new', '32', 'integer',
             'Elo rating adjustment sensitivity for new tasks (first 10 comparisons)'),
            ('elo_new_task_threshold', '10', 'integer',
             'Number of comparisons before task uses base K-factor instead of new K-factor')
        ]

        for key, value, value_type, description in elo_settings:
            cursor.execute("""
                INSERT OR IGNORE INTO settings (key, value, value_type, description)
                VALUES (?, ?, ?, ?)
            """, (key, value, value_type, description))

        db_connection.commit()
        print("Migration to Elo rating system complete.")

    @staticmethod
    def migrate_to_recurring_tasks(db_connection: sqlite3.Connection) -> None:
        """
        Migrate existing database to support recurring tasks.

        This migration:
        1. Adds recurrence-related columns to tasks table
        2. Creates indexes for recurrence queries
        3. Updates schema version

        Args:
            db_connection: Active SQLite database connection
        """
        cursor = db_connection.cursor()

        # Check if migration is already complete
        try:
            cursor.execute("SELECT is_recurring FROM tasks LIMIT 1")
            migration_done = True
        except sqlite3.OperationalError:
            migration_done = False

        if migration_done:
            return  # Already migrated

        print("Migrating database to support recurring tasks...")

        # Add new columns to tasks table
        recurrence_columns = [
            "ALTER TABLE tasks ADD COLUMN is_recurring INTEGER DEFAULT 0",
            "ALTER TABLE tasks ADD COLUMN recurrence_pattern TEXT",
            "ALTER TABLE tasks ADD COLUMN recurrence_parent_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE",
            "ALTER TABLE tasks ADD COLUMN share_elo_rating INTEGER DEFAULT 0",
            "ALTER TABLE tasks ADD COLUMN shared_elo_rating REAL",
            "ALTER TABLE tasks ADD COLUMN shared_comparison_count INTEGER",
            "ALTER TABLE tasks ADD COLUMN recurrence_end_date DATE",
            "ALTER TABLE tasks ADD COLUMN occurrence_count INTEGER DEFAULT 0"
        ]

        for sql in recurrence_columns:
            try:
                cursor.execute(sql)
            except sqlite3.OperationalError as e:
                # Column might already exist
                if "duplicate column name" not in str(e).lower():
                    raise

        # Create indexes for recurrence queries
        recurrence_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_tasks_is_recurring ON tasks(is_recurring)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_recurrence_parent ON tasks(recurrence_parent_id)"
        ]

        for sql in recurrence_indexes:
            cursor.execute(sql)

        db_connection.commit()
        print("Migration to recurring tasks complete.")

    @staticmethod
    def migrate_to_notification_system(db_connection: sqlite3.Connection) -> None:
        """
        Migrate database to support notification system (Phase 6).

        This migration:
        1. Creates notifications table
        2. Adds indexes for performance
        3. Adds Phase 6 settings

        Args:
            db_connection: Active SQLite database connection
        """
        cursor = db_connection.cursor()

        # Check if migration is already complete
        try:
            cursor.execute("SELECT id FROM notifications LIMIT 1")
            migration_done = True
        except sqlite3.OperationalError:
            migration_done = False

        if migration_done:
            return  # Already migrated

        print("Migrating database to support notification system...")

        # Create notifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL CHECK(type IN ('info', 'warning', 'error')),
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_read INTEGER DEFAULT 0,
                action_type TEXT,
                action_data TEXT,
                dismissed_at TIMESTAMP
            )
        """)

        # Add indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_is_read
            ON notifications(is_read)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_dismissed
            ON notifications(dismissed_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_created
            ON notifications(created_at)
        """)

        # Add Phase 6 settings (if they don't already exist)
        phase6_settings = [
            ('delegated_check_time', '09:00', 'string', 'Time of day to check delegated tasks'),
            ('someday_review_time', '18:00', 'string', 'Preferred time for someday review'),
            ('last_someday_review_at', 'null', 'string', 'Last someday review timestamp'),
            ('postpone_analysis_time', '18:00', 'string', 'Time of day to analyze postponement patterns'),
            ('enable_toast_notifications', 'true', 'boolean', 'Enable Windows toast notifications'),
            ('enable_inapp_notifications', 'true', 'boolean', 'Enable in-app notification panel'),
            ('notification_retention_days', '30', 'integer', 'Days to keep old notifications'),
            ('notify_deferred_activation', 'true', 'boolean', 'Notify when deferred tasks activate'),
            ('notify_delegated_followup', 'true', 'boolean', 'Notify for delegated follow-ups'),
            ('notify_someday_review', 'true', 'boolean', 'Notify for someday reviews'),
            ('notify_postpone_intervention', 'true', 'boolean', 'Notify for postponement patterns'),
            ('postpone_intervention_threshold', '3', 'integer', 'Postponements before intervention'),
            ('postpone_pattern_days', '7', 'integer', 'Days window for pattern detection')
        ]

        for key, value, value_type, description in phase6_settings:
            cursor.execute("""
                INSERT OR IGNORE INTO settings (key, value, value_type, description)
                VALUES (?, ?, ?, ?)
            """, (key, value, value_type, description))

        db_connection.commit()
        print("Migration to notification system complete.")
