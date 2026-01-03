"""Export service for backing up application data.

Provides JSON export and SQLite database backup functionality.
"""
import json
import shutil
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path


class ExportService:
    """Service for exporting application data."""

    APP_VERSION = "1.0.0"
    SCHEMA_VERSION = 1

    def __init__(self, db_connection: sqlite3.Connection):
        """Initialize export service.

        Args:
            db_connection: Database connection
        """
        self.db_connection = db_connection

    def export_to_json(
        self,
        filepath: str,
        include_settings: bool = True,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> Dict[str, Any]:
        """Export all data to structured JSON file.

        Args:
            filepath: Destination file path for JSON export
            include_settings: Whether to include settings in export
            progress_callback: Optional callback(message, percent) for progress updates

        Returns:
            Dictionary with export results:
            {
                'success': bool,
                'filepath': str,
                'task_count': int,
                'context_count': int,
                'tag_count': int,
                'dependency_count': int,
                'comparison_count': int,
                'history_count': int,
                'notification_count': int,
                'error': str (if success=False)
            }
        """
        try:
            if progress_callback:
                progress_callback("Starting export...", 0)

            # Build export data structure
            export_data = {
                "metadata": {
                    "export_date": datetime.now().isoformat(),
                    "app_version": self.APP_VERSION,
                    "schema_version": self.SCHEMA_VERSION,
                    "export_type": "full"
                }
            }

            # Export each table
            total_steps = 8
            current_step = 0

            if progress_callback:
                progress_callback("Exporting contexts...", int((current_step / total_steps) * 100))
            export_data["contexts"] = self._export_contexts()
            current_step += 1

            if progress_callback:
                progress_callback("Exporting project tags...", int((current_step / total_steps) * 100))
            export_data["project_tags"] = self._export_project_tags()
            current_step += 1

            if progress_callback:
                progress_callback("Exporting tasks...", int((current_step / total_steps) * 100))
            export_data["tasks"] = self._export_tasks()
            current_step += 1

            if progress_callback:
                progress_callback("Exporting dependencies...", int((current_step / total_steps) * 100))
            export_data["dependencies"] = self._export_dependencies()
            current_step += 1

            if progress_callback:
                progress_callback("Exporting task comparisons...", int((current_step / total_steps) * 100))
            export_data["task_comparisons"] = self._export_task_comparisons()
            current_step += 1

            if progress_callback:
                progress_callback("Exporting postpone history...", int((current_step / total_steps) * 100))
            export_data["postpone_history"] = self._export_postpone_history()
            current_step += 1

            if progress_callback:
                progress_callback("Exporting notifications...", int((current_step / total_steps) * 100))
            export_data["notifications"] = self._export_notifications()
            current_step += 1

            if include_settings:
                if progress_callback:
                    progress_callback("Exporting settings...", int((current_step / total_steps) * 100))
                export_data["settings"] = self._export_settings()
            current_step += 1

            # Write to file
            if progress_callback:
                progress_callback("Writing to file...", 95)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            if progress_callback:
                progress_callback("Export complete!", 100)

            return {
                'success': True,
                'filepath': filepath,
                'task_count': len(export_data['tasks']),
                'context_count': len(export_data['contexts']),
                'tag_count': len(export_data['project_tags']),
                'dependency_count': len(export_data['dependencies']),
                'comparison_count': len(export_data['task_comparisons']),
                'history_count': len(export_data['postpone_history']),
                'notification_count': len(export_data['notifications'])
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def export_database_backup(self, dest_filepath: str) -> Dict[str, Any]:
        """Create SQLite database file backup.

        Args:
            dest_filepath: Destination path for database backup

        Returns:
            Dictionary with backup results:
            {
                'success': bool,
                'filepath': str,
                'size_bytes': int,
                'error': str (if success=False)
            }
        """
        try:
            # Get current database file path
            cursor = self.db_connection.cursor()
            cursor.execute("PRAGMA database_list")
            db_info = cursor.fetchone()
            source_path = db_info[2]  # File path is third column

            # Copy database file
            shutil.copy2(source_path, dest_filepath)

            # Get file size
            file_size = Path(dest_filepath).stat().st_size

            return {
                'success': True,
                'filepath': dest_filepath,
                'size_bytes': file_size
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _export_contexts(self) -> List[Dict]:
        """Export all contexts."""
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT id, name, description FROM contexts ORDER BY id")

        contexts = []
        for row in cursor.fetchall():
            contexts.append({
                'id': row[0],
                'name': row[1],
                'description': row[2]
            })

        return contexts

    def _export_project_tags(self) -> List[Dict]:
        """Export all project tags."""
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT id, name, description FROM project_tags ORDER BY id")

        tags = []
        for row in cursor.fetchall():
            tags.append({
                'id': row[0],
                'name': row[1],
                'description': row[2]
            })

        return tags

    def _export_tasks(self) -> List[Dict]:
        """Export all tasks with relationships."""
        cursor = self.db_connection.cursor()
        cursor.execute("""
            SELECT
                id, title, description, state, base_priority, urgency,
                elo_rating, comparison_count, context_id, due_date,
                start_date, delegated_to, delegated_date, delegated_notes,
                someday_notes, created_at, updated_at, last_state_change
            FROM tasks
            ORDER BY id
        """)

        tasks = []
        for row in cursor.fetchall():
            task = {
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'state': row[3],
                'base_priority': row[4],
                'urgency': row[5],
                'elo_rating': row[6],
                'comparison_count': row[7],
                'context_id': row[8],
                'due_date': row[9],
                'start_date': row[10],
                'delegated_to': row[11],
                'delegated_date': row[12],
                'delegated_notes': row[13],
                'someday_notes': row[14],
                'created_at': row[15],
                'updated_at': row[16],
                'last_state_change': row[17]
            }

            # Get associated project tags
            tag_cursor = self.db_connection.cursor()
            tag_cursor.execute(
                "SELECT project_tag_id FROM task_project_tags WHERE task_id = ?",
                (task['id'],)
            )
            task['project_tag_ids'] = [r[0] for r in tag_cursor.fetchall()]

            tasks.append(task)

        return tasks

    def _export_dependencies(self) -> List[Dict]:
        """Export all task dependencies."""
        cursor = self.db_connection.cursor()
        cursor.execute("""
            SELECT task_id, depends_on_task_id, created_at
            FROM dependencies
            ORDER BY task_id, depends_on_task_id
        """)

        dependencies = []
        for row in cursor.fetchall():
            dependencies.append({
                'task_id': row[0],
                'depends_on_task_id': row[1],
                'created_at': row[2]
            })

        return dependencies

    def _export_task_comparisons(self) -> List[Dict]:
        """Export all task comparisons."""
        cursor = self.db_connection.cursor()
        cursor.execute("""
            SELECT
                id, task_a_id, task_b_id, winner_task_id,
                task_a_elo_before, task_a_elo_after,
                task_b_elo_before, task_b_elo_after,
                comparison_date
            FROM task_comparisons
            ORDER BY id
        """)

        comparisons = []
        for row in cursor.fetchall():
            comparisons.append({
                'id': row[0],
                'task_a_id': row[1],
                'task_b_id': row[2],
                'winner_task_id': row[3],
                'task_a_elo_before': row[4],
                'task_a_elo_after': row[5],
                'task_b_elo_before': row[6],
                'task_b_elo_after': row[7],
                'comparison_date': row[8]
            })

        return comparisons

    def _export_postpone_history(self) -> List[Dict]:
        """Export postpone history."""
        cursor = self.db_connection.cursor()
        cursor.execute("""
            SELECT
                id, task_id, postponed_at, reason, action_taken,
                blocker_task_id, next_action_task_id
            FROM postpone_history
            ORDER BY id
        """)

        history = []
        for row in cursor.fetchall():
            history.append({
                'id': row[0],
                'task_id': row[1],
                'postponed_at': row[2],
                'reason': row[3],
                'action_taken': row[4],
                'blocker_task_id': row[5],
                'next_action_task_id': row[6]
            })

        return history

    def _export_notifications(self) -> List[Dict]:
        """Export notifications."""
        cursor = self.db_connection.cursor()
        cursor.execute("""
            SELECT
                id, notification_type, title, message, severity,
                is_read, action_type, action_data, created_at, read_at
            FROM notifications
            ORDER BY id
        """)

        notifications = []
        for row in cursor.fetchall():
            notifications.append({
                'id': row[0],
                'notification_type': row[1],
                'title': row[2],
                'message': row[3],
                'severity': row[4],
                'is_read': row[5],
                'action_type': row[6],
                'action_data': row[7],
                'created_at': row[8],
                'read_at': row[9]
            })

        return notifications

    def _export_settings(self) -> Dict[str, Any]:
        """Export settings as dictionary."""
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT key, value, value_type FROM settings ORDER BY key")

        settings = {}
        for row in cursor.fetchall():
            key, value, value_type = row
            # Store with type info for proper restoration
            settings[key] = {
                'value': value,
                'type': value_type
            }

        return settings
