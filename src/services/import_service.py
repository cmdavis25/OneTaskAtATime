"""Import service for restoring application data.

Provides JSON import and database restoration with validation and ID conflict resolution.
"""
import json
import shutil
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path


class ImportService:
    """Service for importing application data."""

    SUPPORTED_SCHEMA_VERSION = 1

    def __init__(self, db_connection: sqlite3.Connection):
        """Initialize import service.

        Args:
            db_connection: Database connection
        """
        self.db_connection = db_connection
        self._id_mappings = {}  # old_id -> new_id mappings for merge mode

    def import_from_json(
        self,
        filepath: str,
        merge_mode: bool = False,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> Dict[str, Any]:
        """Import data from JSON file with validation.

        Args:
            filepath: Source JSON file path
            merge_mode: If True, merge with existing data (remap IDs on conflict).
                       If False, replace all existing data.
            progress_callback: Optional callback(message, percent) for progress updates

        Returns:
            Dictionary with import results:
            {
                'success': bool,
                'task_count': int,
                'context_count': int,
                'tag_count': int,
                'warnings': List[str],
                'error': str (if success=False)
            }
        """
        try:
            if progress_callback:
                progress_callback("Loading import file...", 0)

            # Load and validate JSON
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            validation_result = self._validate_import_data(data)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error']
                }

            if progress_callback:
                progress_callback("Validation complete...", 5)

            # Begin transaction
            self.db_connection.execute("BEGIN TRANSACTION")

            try:
                warnings = []
                total_steps = 8 if merge_mode else 9
                current_step = 1

                # Clear existing data if replace mode
                if not merge_mode:
                    if progress_callback:
                        progress_callback("Clearing existing data...", int((current_step / total_steps) * 100))
                    self._clear_all_data()
                    current_step += 1

                # Reset ID mappings for merge mode
                self._id_mappings = {
                    'contexts': {},
                    'project_tags': {},
                    'tasks': {}
                }

                # Import in dependency order
                if progress_callback:
                    progress_callback("Importing contexts...", int((current_step / total_steps) * 100))
                context_count = self._import_contexts(data.get('contexts', []), merge_mode)
                current_step += 1

                if progress_callback:
                    progress_callback("Importing project tags...", int((current_step / total_steps) * 100))
                tag_count = self._import_project_tags(data.get('project_tags', []), merge_mode)
                current_step += 1

                if progress_callback:
                    progress_callback("Importing tasks...", int((current_step / total_steps) * 100))
                task_count = self._import_tasks(data.get('tasks', []), merge_mode)
                current_step += 1

                if progress_callback:
                    progress_callback("Importing dependencies...", int((current_step / total_steps) * 100))
                dep_count = self._import_dependencies(data.get('dependencies', []), merge_mode)
                current_step += 1

                if progress_callback:
                    progress_callback("Importing task comparisons...", int((current_step / total_steps) * 100))
                comp_count = self._import_task_comparisons(data.get('task_comparisons', []), merge_mode)
                current_step += 1

                if progress_callback:
                    progress_callback("Importing postpone history...", int((current_step / total_steps) * 100))
                hist_count = self._import_postpone_history(data.get('postpone_history', []), merge_mode)
                current_step += 1

                if progress_callback:
                    progress_callback("Importing notifications...", int((current_step / total_steps) * 100))
                notif_count = self._import_notifications(data.get('notifications', []), merge_mode)
                current_step += 1

                # Import settings if present and not merge mode
                if 'settings' in data and not merge_mode:
                    if progress_callback:
                        progress_callback("Importing settings...", int((current_step / total_steps) * 100))
                    self._import_settings(data['settings'])

                # Commit transaction
                self.db_connection.commit()

                if progress_callback:
                    progress_callback("Import complete!", 100)

                return {
                    'success': True,
                    'task_count': task_count,
                    'context_count': context_count,
                    'tag_count': tag_count,
                    'dependency_count': dep_count,
                    'comparison_count': comp_count,
                    'history_count': hist_count,
                    'notification_count': notif_count,
                    'warnings': warnings
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

    def _validate_import_data(self, data: Dict) -> Dict[str, Any]:
        """Validate JSON structure and schema version.

        Args:
            data: Parsed JSON data

        Returns:
            Dictionary with validation results:
            {'valid': bool, 'error': str (if not valid)}
        """
        # Check metadata
        if 'metadata' not in data:
            return {'valid': False, 'error': 'Missing metadata section'}

        metadata = data['metadata']

        # Check schema version
        schema_version = metadata.get('schema_version')
        if schema_version is None:
            return {'valid': False, 'error': 'Missing schema_version in metadata'}

        if schema_version > self.SUPPORTED_SCHEMA_VERSION:
            return {
                'valid': False,
                'error': f'Unsupported schema version {schema_version}. '
                        f'This application supports up to version {self.SUPPORTED_SCHEMA_VERSION}. '
                        f'Please upgrade the application.'
            }

        # Check required sections
        required_sections = ['contexts', 'project_tags', 'tasks']
        for section in required_sections:
            if section not in data:
                return {'valid': False, 'error': f'Missing required section: {section}'}

        return {'valid': True}

    def _clear_all_data(self):
        """Clear all data from the database (for replace mode).

        Deletes in dependency order to avoid foreign key violations.
        """
        cursor = self.db_connection.cursor()

        # Delete in reverse dependency order
        cursor.execute("DELETE FROM task_comparisons")
        cursor.execute("DELETE FROM postpone_history")
        cursor.execute("DELETE FROM notifications")
        cursor.execute("DELETE FROM task_project_tags")
        cursor.execute("DELETE FROM dependencies")
        cursor.execute("DELETE FROM tasks")
        cursor.execute("DELETE FROM project_tags")
        cursor.execute("DELETE FROM contexts")

    def _import_contexts(self, contexts_data: List[Dict], merge_mode: bool) -> int:
        """Import contexts with ID conflict resolution.

        Args:
            contexts_data: List of context dictionaries
            merge_mode: Whether to remap IDs on conflict

        Returns:
            Number of contexts imported
        """
        cursor = self.db_connection.cursor()
        count = 0

        for context in contexts_data:
            old_id = context['id']
            name = context['name']
            description = context.get('description')

            if merge_mode:
                # Check for ID conflict
                cursor.execute("SELECT id FROM contexts WHERE id = ?", (old_id,))
                if cursor.fetchone():
                    # ID conflict - insert with new ID
                    cursor.execute(
                        "INSERT INTO contexts (name, description) VALUES (?, ?)",
                        (name, description)
                    )
                    new_id = cursor.lastrowid
                    self._id_mappings['contexts'][old_id] = new_id
                else:
                    # No conflict - use original ID
                    cursor.execute(
                        "INSERT INTO contexts (id, name, description) VALUES (?, ?, ?)",
                        (old_id, name, description)
                    )
                    self._id_mappings['contexts'][old_id] = old_id
            else:
                # Replace mode - use original IDs
                cursor.execute(
                    "INSERT INTO contexts (id, name, description) VALUES (?, ?, ?)",
                    (old_id, name, description)
                )

            count += 1

        return count

    def _import_project_tags(self, tags_data: List[Dict], merge_mode: bool) -> int:
        """Import project tags with ID conflict resolution."""
        cursor = self.db_connection.cursor()
        count = 0

        for tag in tags_data:
            old_id = tag['id']
            name = tag['name']
            description = tag.get('description')

            if merge_mode:
                cursor.execute("SELECT id FROM project_tags WHERE id = ?", (old_id,))
                if cursor.fetchone():
                    cursor.execute(
                        "INSERT INTO project_tags (name, description) VALUES (?, ?)",
                        (name, description)
                    )
                    new_id = cursor.lastrowid
                    self._id_mappings['project_tags'][old_id] = new_id
                else:
                    cursor.execute(
                        "INSERT INTO project_tags (id, name, description) VALUES (?, ?, ?)",
                        (old_id, name, description)
                    )
                    self._id_mappings['project_tags'][old_id] = old_id
            else:
                cursor.execute(
                    "INSERT INTO project_tags (id, name, description) VALUES (?, ?, ?)",
                    (old_id, name, description)
                )

            count += 1

        return count

    def _import_tasks(self, tasks_data: List[Dict], merge_mode: bool) -> int:
        """Import tasks with relationships and ID conflict resolution."""
        cursor = self.db_connection.cursor()
        count = 0

        for task in tasks_data:
            old_id = task['id']

            # Remap context_id if needed
            context_id = task.get('context_id')
            if context_id and merge_mode and context_id in self._id_mappings['contexts']:
                context_id = self._id_mappings['contexts'][context_id]

            # Prepare task data
            task_data = (
                task['title'],
                task.get('description'),
                task['state'],
                task['base_priority'],
                task.get('urgency'),
                task.get('elo_rating', 1500.0),
                task.get('comparison_count', 0),
                context_id,
                task.get('due_date'),
                task.get('start_date'),
                task.get('delegated_to'),
                task.get('delegated_date'),
                task.get('delegated_notes'),
                task.get('someday_notes'),
                task.get('created_at'),
                task.get('updated_at'),
                task.get('last_state_change')
            )

            if merge_mode:
                cursor.execute("SELECT id FROM tasks WHERE id = ?", (old_id,))
                if cursor.fetchone():
                    # ID conflict - insert with new ID
                    cursor.execute(
                        """INSERT INTO tasks (
                            title, description, state, base_priority, urgency,
                            elo_rating, comparison_count, context_id, due_date,
                            start_date, delegated_to, delegated_date, delegated_notes,
                            someday_notes, created_at, updated_at, last_state_change
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        task_data
                    )
                    new_id = cursor.lastrowid
                    self._id_mappings['tasks'][old_id] = new_id
                else:
                    # No conflict - use original ID
                    cursor.execute(
                        """INSERT INTO tasks (
                            id, title, description, state, base_priority, urgency,
                            elo_rating, comparison_count, context_id, due_date,
                            start_date, delegated_to, delegated_date, delegated_notes,
                            someday_notes, created_at, updated_at, last_state_change
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (old_id,) + task_data
                    )
                    self._id_mappings['tasks'][old_id] = old_id
            else:
                # Replace mode - use original ID
                cursor.execute(
                    """INSERT INTO tasks (
                        id, title, description, state, base_priority, urgency,
                        elo_rating, comparison_count, context_id, due_date,
                        start_date, delegated_to, delegated_date, delegated_notes,
                        someday_notes, created_at, updated_at, last_state_change
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (old_id,) + task_data
                )
                new_id = old_id

            # Import project tag associations
            if 'project_tag_ids' in task:
                final_task_id = self._id_mappings['tasks'].get(old_id, old_id) if merge_mode else old_id
                for tag_id in task['project_tag_ids']:
                    final_tag_id = self._id_mappings['project_tags'].get(tag_id, tag_id) if merge_mode else tag_id
                    cursor.execute(
                        "INSERT INTO task_project_tags (task_id, project_tag_id) VALUES (?, ?)",
                        (final_task_id, final_tag_id)
                    )

            count += 1

        return count

    def _import_dependencies(self, deps_data: List[Dict], merge_mode: bool) -> int:
        """Import task dependencies with ID remapping."""
        cursor = self.db_connection.cursor()
        count = 0

        for dep in deps_data:
            task_id = dep['task_id']
            depends_on_id = dep['depends_on_task_id']

            # Remap IDs if in merge mode
            if merge_mode:
                task_id = self._id_mappings['tasks'].get(task_id, task_id)
                depends_on_id = self._id_mappings['tasks'].get(depends_on_id, depends_on_id)

            cursor.execute(
                """INSERT INTO dependencies (task_id, depends_on_task_id, created_at)
                   VALUES (?, ?, ?)""",
                (task_id, depends_on_id, dep.get('created_at'))
            )
            count += 1

        return count

    def _import_task_comparisons(self, comps_data: List[Dict], merge_mode: bool) -> int:
        """Import task comparisons with ID remapping."""
        cursor = self.db_connection.cursor()
        count = 0

        for comp in comps_data:
            task_a_id = comp['task_a_id']
            task_b_id = comp['task_b_id']
            winner_id = comp['winner_task_id']

            # Remap IDs if in merge mode
            if merge_mode:
                task_a_id = self._id_mappings['tasks'].get(task_a_id, task_a_id)
                task_b_id = self._id_mappings['tasks'].get(task_b_id, task_b_id)
                winner_id = self._id_mappings['tasks'].get(winner_id, winner_id)

            cursor.execute(
                """INSERT INTO task_comparisons (
                    task_a_id, task_b_id, winner_task_id,
                    task_a_elo_before, task_a_elo_after,
                    task_b_elo_before, task_b_elo_after,
                    comparison_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (task_a_id, task_b_id, winner_id,
                 comp['task_a_elo_before'], comp['task_a_elo_after'],
                 comp['task_b_elo_before'], comp['task_b_elo_after'],
                 comp['comparison_date'])
            )
            count += 1

        return count

    def _import_postpone_history(self, hist_data: List[Dict], merge_mode: bool) -> int:
        """Import postpone history with ID remapping."""
        cursor = self.db_connection.cursor()
        count = 0

        for record in hist_data:
            task_id = record['task_id']
            blocker_id = record.get('blocker_task_id')
            next_action_id = record.get('next_action_task_id')

            # Remap IDs if in merge mode
            if merge_mode:
                task_id = self._id_mappings['tasks'].get(task_id, task_id)
                if blocker_id:
                    blocker_id = self._id_mappings['tasks'].get(blocker_id, blocker_id)
                if next_action_id:
                    next_action_id = self._id_mappings['tasks'].get(next_action_id, next_action_id)

            cursor.execute(
                """INSERT INTO postpone_history (
                    task_id, postponed_at, reason, action_taken,
                    blocker_task_id, next_action_task_id
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                (task_id, record['postponed_at'], record.get('reason'),
                 record.get('action_taken'), blocker_id, next_action_id)
            )
            count += 1

        return count

    def _import_notifications(self, notif_data: List[Dict], merge_mode: bool) -> int:
        """Import notifications."""
        cursor = self.db_connection.cursor()
        count = 0

        for notif in notif_data:
            cursor.execute(
                """INSERT INTO notifications (
                    notification_type, title, message, severity,
                    is_read, action_type, action_data, created_at, read_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (notif['notification_type'], notif['title'], notif['message'],
                 notif['severity'], notif['is_read'], notif.get('action_type'),
                 notif.get('action_data'), notif['created_at'], notif.get('read_at'))
            )
            count += 1

        return count

    def _import_settings(self, settings_data: Dict[str, Any]):
        """Import settings (replace mode only)."""
        cursor = self.db_connection.cursor()

        for key, setting in settings_data.items():
            value = setting['value']
            value_type = setting['type']

            cursor.execute(
                """INSERT OR REPLACE INTO settings (key, value, value_type, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (key, value, value_type, datetime.now().isoformat())
            )
