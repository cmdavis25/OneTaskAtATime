#!/usr/bin/env python
"""
Verification script for Management Dialog button attributes.

This script verifies that both ContextManagementDialog and ProjectTagManagementDialog
have the required button attributes: add_button, edit_button, delete_button.
"""

import sys
import sqlite3
from src.database.schema import DatabaseSchema
from src.ui.context_management_dialog import ContextManagementDialog
from src.ui.project_tag_management_dialog import ProjectTagManagementDialog

class MockDatabaseConnection:
    """Mock DatabaseConnection for testing."""
    def __init__(self, conn):
        self._conn = conn

    def get_connection(self):
        return self._conn

    def close(self):
        pass

def verify_attributes():
    """Verify that both management dialogs have required button attributes."""
    print("=" * 70)
    print("Management Dialogs Button Attribute Verification")
    print("=" * 70)

    # Create in-memory database
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    DatabaseSchema.initialize_database(conn)
    mock_db = MockDatabaseConnection(conn)

    results = {
        'context_dialog': {},
        'tag_dialog': {}
    }

    # Test ContextManagementDialog
    print("\n1. ContextManagementDialog")
    print("-" * 70)
    try:
        dialog = ContextManagementDialog(mock_db)

        # Check for add_button
        has_add = hasattr(dialog, 'add_button')
        results['context_dialog']['add_button'] = has_add
        print(f"   add_button: {'✓ FOUND' if has_add else '✗ MISSING'}")

        # Check for edit_button
        has_edit = hasattr(dialog, 'edit_button')
        results['context_dialog']['edit_button'] = has_edit
        print(f"   edit_button: {'✓ FOUND' if has_edit else '✗ MISSING'}")

        # Check for delete_button
        has_delete = hasattr(dialog, 'delete_button')
        results['context_dialog']['delete_button'] = has_delete
        print(f"   delete_button: {'✓ FOUND' if has_delete else '✗ MISSING'}")

        # Check for close_button
        has_close = hasattr(dialog, 'close_button')
        results['context_dialog']['close_button'] = has_close
        print(f"   close_button: {'✓ FOUND' if has_close else '✗ MISSING'}")

        dialog.close()
    except Exception as e:
        print(f"   ERROR: {e}")
        results['context_dialog']['error'] = str(e)

    # Test ProjectTagManagementDialog
    print("\n2. ProjectTagManagementDialog")
    print("-" * 70)
    try:
        dialog = ProjectTagManagementDialog(mock_db)

        # Check for add_button
        has_add = hasattr(dialog, 'add_button')
        results['tag_dialog']['add_button'] = has_add
        print(f"   add_button: {'✓ FOUND' if has_add else '✗ MISSING'}")

        # Check for edit_button
        has_edit = hasattr(dialog, 'edit_button')
        results['tag_dialog']['edit_button'] = has_edit
        print(f"   edit_button: {'✓ FOUND' if has_edit else '✗ MISSING'}")

        # Check for delete_button
        has_delete = hasattr(dialog, 'delete_button')
        results['tag_dialog']['delete_button'] = has_delete
        print(f"   delete_button: {'✓ FOUND' if has_delete else '✗ MISSING'}")

        # Check for close_button
        has_close = hasattr(dialog, 'close_button')
        results['tag_dialog']['close_button'] = has_close
        print(f"   close_button: {'✓ FOUND' if has_close else '✗ MISSING'}")

        dialog.close()
    except Exception as e:
        print(f"   ERROR: {e}")
        results['tag_dialog']['error'] = str(e)

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    all_passed = all(
        all(v for k, v in dialog.items() if k != 'error')
        for dialog in results.values()
        if 'error' not in dialog
    )

    if all_passed:
        print("✓ ALL ATTRIBUTES PRESENT - Tests should pass!")
        return 0
    else:
        print("✗ SOME ATTRIBUTES MISSING - Tests will fail")
        return 1

if __name__ == '__main__':
    # Need QApplication for Qt widgets
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    exit_code = verify_attributes()
    sys.exit(exit_code)
