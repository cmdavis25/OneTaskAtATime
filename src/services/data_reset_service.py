"""Data reset service for nuclear reset of application data.

Provides comprehensive data deletion with transaction safety.
"""
import sqlite3
from typing import Dict, Any


class DataResetService:
    """Service for resetting application data."""

    def __init__(self, db_connection: sqlite3.Connection):
        """Initialize data reset service.

        Args:
            db_connection: Database connection
        """
        self.db_connection = db_connection

    def get_reset_summary(self) -> Dict[str, int]:
        """Get counts of all data that will be deleted.

        Returns:
            Dictionary with counts for each table:
            {
                'tasks': int,
                'contexts': int,
                'project_tags': int,
                'dependencies': int,
                'comparisons': int,
                'history': int,
                'notifications': int,
                'settings': int
            }
        """
        cursor = self.db_connection.cursor()
        summary = {}

        # Count each table
        cursor.execute("SELECT COUNT(*) FROM tasks")
        summary['tasks'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM contexts")
        summary['contexts'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM project_tags")
        summary['project_tags'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM dependencies")
        summary['dependencies'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM task_comparisons")
        summary['comparisons'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM postpone_history")
        summary['history'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM notifications")
        summary['notifications'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM settings")
        summary['settings'] = cursor.fetchone()[0]

        return summary

    def reset_all_data(
        self,
        include_contexts: bool = True,
        include_tags: bool = True,
        reset_settings: bool = False
    ) -> Dict[str, Any]:
        """Nuclear reset - delete all data from the database.

        Args:
            include_contexts: Whether to delete contexts
            include_tags: Whether to delete project tags
            reset_settings: Whether to reset settings to defaults

        Returns:
            Dictionary with reset results:
            {
                'success': bool,
                'deleted': Dict[str, int],  # counts of deleted items
                'error': str (if success=False)
            }
        """
        try:
            # Begin transaction
            self.db_connection.execute("BEGIN TRANSACTION")

            deleted_counts = {}

            try:
                cursor = self.db_connection.cursor()

                # Delete in dependency order (reverse of foreign keys)

                # 1. Task comparisons (references tasks)
                cursor.execute("DELETE FROM task_comparisons")
                deleted_counts['comparisons'] = cursor.rowcount

                # 2. Postpone history (references tasks)
                cursor.execute("DELETE FROM postpone_history")
                deleted_counts['history'] = cursor.rowcount

                # 3. Notifications
                cursor.execute("DELETE FROM notifications")
                deleted_counts['notifications'] = cursor.rowcount

                # 4. Task-tag associations (references tasks and project_tags)
                cursor.execute("DELETE FROM task_project_tags")
                deleted_counts['task_tags'] = cursor.rowcount

                # 5. Dependencies (references tasks)
                cursor.execute("DELETE FROM dependencies")
                deleted_counts['dependencies'] = cursor.rowcount

                # 6. Tasks (must be deleted before contexts and tags if cascading)
                cursor.execute("DELETE FROM tasks")
                deleted_counts['tasks'] = cursor.rowcount

                # 7. Project tags (only if requested)
                if include_tags:
                    cursor.execute("DELETE FROM project_tags")
                    deleted_counts['project_tags'] = cursor.rowcount
                else:
                    deleted_counts['project_tags'] = 0

                # 8. Contexts (only if requested)
                if include_contexts:
                    cursor.execute("DELETE FROM contexts")
                    deleted_counts['contexts'] = cursor.rowcount
                else:
                    deleted_counts['contexts'] = 0

                # 9. Settings (only if requested)
                if reset_settings:
                    cursor.execute("DELETE FROM settings")
                    deleted_counts['settings'] = cursor.rowcount
                else:
                    deleted_counts['settings'] = 0

                # Commit transaction
                self.db_connection.commit()

                return {
                    'success': True,
                    'deleted': deleted_counts
                }

            except Exception as e:
                # Rollback on error
                self.db_connection.rollback()
                raise e

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def reset_task_data_only(self) -> Dict[str, Any]:
        """Reset only task data, preserving contexts and tags.

        This is a safer reset that keeps organizational structures.

        Returns:
            Dictionary with reset results
        """
        return self.reset_all_data(
            include_contexts=False,
            include_tags=False,
            reset_settings=False
        )

    def get_total_items_to_delete(
        self,
        include_contexts: bool = True,
        include_tags: bool = True,
        reset_settings: bool = False
    ) -> int:
        """Calculate total number of items that will be deleted.

        Args:
            include_contexts: Whether contexts will be deleted
            include_tags: Whether tags will be deleted
            reset_settings: Whether settings will be reset

        Returns:
            Total count of items to be deleted
        """
        summary = self.get_reset_summary()

        total = (
            summary['tasks'] +
            summary['dependencies'] +
            summary['comparisons'] +
            summary['history'] +
            summary['notifications']
        )

        if include_contexts:
            total += summary['contexts']

        if include_tags:
            total += summary['project_tags']

        if reset_settings:
            total += summary['settings']

        return total
