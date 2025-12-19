"""
Test script to verify filter persistence functionality.

This script tests that filter state is properly saved and loaded
for both Focus Mode and Task List View.
"""

import sys
import io

# Fix Windows console encoding issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.database.connection import DatabaseConnection
from src.database.settings_dao import SettingsDAO


def test_focus_mode_persistence():
    """Test Focus Mode filter persistence."""
    print("Testing Focus Mode filter persistence...")

    db_conn = DatabaseConnection()
    settings_dao = SettingsDAO(db_conn.get_connection())

    # Test 1: Save context filter
    settings_dao.set('focus_mode.context_filter', 1, 'integer', 'Focus Mode context filter')
    loaded_context = settings_dao.get('focus_mode.context_filter', None)
    assert loaded_context == 1, f"Expected 1, got {loaded_context}"
    print("✓ Context filter save/load works")

    # Test 2: Save tag filters
    settings_dao.set('focus_mode.tag_filters', [1, 2, 3], 'json', 'Focus Mode tag filters')
    loaded_tags = settings_dao.get('focus_mode.tag_filters', [])
    assert loaded_tags == [1, 2, 3], f"Expected [1, 2, 3], got {loaded_tags}"
    print("✓ Tag filters save/load works")

    # Test 3: Clear filters
    settings_dao.delete('focus_mode.context_filter')
    settings_dao.delete('focus_mode.tag_filters')
    assert settings_dao.get('focus_mode.context_filter', None) is None
    assert settings_dao.get('focus_mode.tag_filters', []) == []
    print("✓ Filter deletion works")

    db_conn.close()
    print("Focus Mode persistence tests passed!\n")


def test_task_list_persistence():
    """Test Task List View filter persistence."""
    print("Testing Task List View filter persistence...")

    db_conn = DatabaseConnection()
    settings_dao = SettingsDAO(db_conn.get_connection())

    # Test 1: Save context filters (multiple)
    settings_dao.set('task_list.context_filters', [1, 2, "NONE"], 'json', 'Task List context filters')
    loaded_contexts = settings_dao.get('task_list.context_filters', [])
    assert loaded_contexts == [1, 2, "NONE"], f"Expected [1, 2, 'NONE'], got {loaded_contexts}"
    print("✓ Context filters save/load works")

    # Test 2: Save tag filters
    settings_dao.set('task_list.tag_filters', [5, 6], 'json', 'Task List tag filters')
    loaded_tags = settings_dao.get('task_list.tag_filters', [])
    assert loaded_tags == [5, 6], f"Expected [5, 6], got {loaded_tags}"
    print("✓ Tag filters save/load works")

    # Test 3: Save search text
    settings_dao.set('task_list.search_text', 'test search', 'string', 'Task List search text')
    loaded_search = settings_dao.get('task_list.search_text', '')
    assert loaded_search == 'test search', f"Expected 'test search', got {loaded_search}"
    print("✓ Search text save/load works")

    # Test 4: Save state filters
    settings_dao.set('task_list.state_filters', ['active', 'deferred'], 'json', 'Task List state filters')
    loaded_states = settings_dao.get('task_list.state_filters', None)
    assert loaded_states == ['active', 'deferred'], f"Expected ['active', 'deferred'], got {loaded_states}"
    print("✓ State filters save/load works")

    # Test 5: Clear all filters
    settings_dao.delete('task_list.context_filters')
    settings_dao.delete('task_list.tag_filters')
    settings_dao.delete('task_list.search_text')
    settings_dao.delete('task_list.state_filters')
    assert settings_dao.get('task_list.context_filters', []) == []
    assert settings_dao.get('task_list.tag_filters', []) == []
    assert settings_dao.get('task_list.search_text', '') == ''
    print("✓ Filter deletion works")

    db_conn.close()
    print("Task List View persistence tests passed!\n")


if __name__ == '__main__':
    print("=" * 60)
    print("Filter Persistence Test Suite")
    print("=" * 60)
    print()

    try:
        test_focus_mode_persistence()
        test_task_list_persistence()

        print("=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
