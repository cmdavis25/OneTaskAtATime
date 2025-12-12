"""
Database migration script for Phase 3.

Adds the comparison_losses column to existing databases.
Run this once before launching the Phase 3 application.
"""

import sqlite3
from pathlib import Path


def migrate_database():
    """Add comparison_losses column to tasks table."""
    # Database path
    resources_dir = Path(__file__).parent / "resources"
    db_path = resources_dir / "onetaskatatime.db"

    if not db_path.exists():
        print(f"No database found at {db_path}")
        print("Database will be created automatically on first run.")
        return

    print(f"Migrating database: {db_path}")

    # Connect to database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'comparison_losses' in columns:
            print("[OK] Database already migrated (comparison_losses column exists)")
            return

        # Add the new column
        print("Adding comparison_losses column to tasks table...")
        cursor.execute("""
            ALTER TABLE tasks
            ADD COLUMN comparison_losses INTEGER DEFAULT 0
        """)

        conn.commit()
        print("[OK] Migration complete!")
        print("  - Added comparison_losses column")
        print("  - All existing tasks have comparison_losses = 0")

    except sqlite3.Error as e:
        print(f"[ERROR] Migration failed: {e}")
        conn.rollback()

    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("OneTaskAtATime - Phase 3 Database Migration")
    print("=" * 60)
    print()
    migrate_database()
    print()
    print("You can now run the application with: python -m src.main")
    print("=" * 60)
