"""
Database migration script for recurring tasks feature.

Run this script to add recurring task columns to your existing database.
"""

import sys
import sqlite3
import os


def main():
    """Run the recurring tasks migration."""
    print("=" * 60)
    print("OneTaskAtATime - Recurring Tasks Migration")
    print("=" * 60)
    print()

    # Connect directly to database without initialization
    db_path = os.path.join("resources", "onetaskatatime.db")

    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found at {db_path}")
        print("Please make sure you have run the application at least once.")
        return 1

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    try:
        # Check if migration is already complete
        try:
            cursor.execute("SELECT is_recurring FROM tasks LIMIT 1")
            print("[OK] Database already has recurring task columns.")
            print("No migration needed.")
            return 0
        except sqlite3.OperationalError:
            pass  # Columns don't exist, proceed with migration

        print("Running migration...")
        print()

        # Add new columns to tasks table
        recurrence_columns = [
            ("is_recurring", "ALTER TABLE tasks ADD COLUMN is_recurring INTEGER DEFAULT 0"),
            ("recurrence_pattern", "ALTER TABLE tasks ADD COLUMN recurrence_pattern TEXT"),
            ("recurrence_parent_id", "ALTER TABLE tasks ADD COLUMN recurrence_parent_id INTEGER"),
            ("share_elo_rating", "ALTER TABLE tasks ADD COLUMN share_elo_rating INTEGER DEFAULT 0"),
            ("shared_elo_rating", "ALTER TABLE tasks ADD COLUMN shared_elo_rating REAL"),
            ("shared_comparison_count", "ALTER TABLE tasks ADD COLUMN shared_comparison_count INTEGER"),
            ("recurrence_end_date", "ALTER TABLE tasks ADD COLUMN recurrence_end_date DATE"),
            ("occurrence_count", "ALTER TABLE tasks ADD COLUMN occurrence_count INTEGER DEFAULT 0"),
        ]

        for col_name, sql in recurrence_columns:
            try:
                print(f"  Adding column: {col_name}")
                cursor.execute(sql)
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"    (already exists, skipping)")
                else:
                    raise

        # Create indexes for recurrence queries
        print()
        print("Creating indexes...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_tasks_is_recurring ON tasks(is_recurring)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_recurrence_parent ON tasks(recurrence_parent_id)",
        ]

        for sql in indexes:
            cursor.execute(sql)

        connection.commit()
        print()
        print("[SUCCESS] Migration completed successfully!")
        print()
        print("Your database now supports recurring tasks.")
        print("You can now create tasks that repeat automatically.")
        return 0

    except Exception as e:
        print()
        print(f"[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        connection.rollback()
        return 1

    finally:
        connection.close()


if __name__ == "__main__":
    sys.exit(main())
