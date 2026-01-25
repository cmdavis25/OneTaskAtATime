"""
Analyze test failures systematically.
"""
import subprocess
import sys
import json

# List of all failed tests
failures = [
    "tests/integration/test_database_integrity.py::TestDatabaseIntegrity::test_foreign_key_constraints",
    "tests/integration/test_database_integrity.py::TestDatabaseIntegrity::test_transaction_rollback",
    "tests/integration/test_database_integrity.py::TestDatabaseIntegrity::test_schema_consistency",
    "tests/integration/test_error_recovery.py::TestErrorRecovery::test_recovery_from_export_failure",
    "tests/integration/test_error_recovery.py::TestErrorRecovery::test_recovery_from_import_failure",
    "tests/integration/test_error_recovery.py::TestErrorRecovery::test_missing_settings_recovery",
    "tests/performance/test_memory_leaks.py::TestMemoryLeaks::test_focus_mode_refresh_memory",
    "tests/performance/test_memory_leaks.py::TestMemoryLeaks::test_dialog_open_close_memory",
    "tests/performance/test_memory_leaks.py::TestMemoryLeaks::test_undo_stack_memory",
    "tests/performance/test_memory_leaks.py::TestMemoryLeaks::test_notification_accumulation",
    "tests/performance/test_memory_leaks.py::TestMemoryLeaks::test_long_running_session",
    "tests/performance/test_performance_benchmarks.py::TestPerformanceBenchmarks::test_comparison_with_100_tied_tasks",
    "tests/performance/test_performance_benchmarks.py::TestPerformanceBenchmarks::test_task_history_query_1k_events",
    "tests/performance/test_performance_benchmarks.py::TestPerformanceBenchmarks::test_dependency_graph_with_1k_nodes",
    "tests/performance/test_performance_benchmarks.py::TestPerformanceBenchmarks::test_undo_stack_with_50_operations",
    "tests/test_task_dao.py::TestTaskDAO::test_task_model_methods",
    "tests/test_ui_context_management.py::test_delete_context",
    "tests/test_ui_project_tag_management.py::test_delete_tag",
    "tests/ui/test_analytics_view.py::TestDataRefresh::test_refresh_button_calls_refresh_data",
    "tests/ui/test_analytics_view.py::TestEmptyState::test_handles_empty_database_gracefully",
    "tests/ui/test_main_window.py::TestKeyboardShortcuts::test_ctrl_1_shows_focus_mode",
    "tests/ui/test_main_window.py::TestKeyboardShortcuts::test_ctrl_2_shows_task_list",
    "tests/ui/test_main_window.py::TestKeyboardShortcuts::test_f5_refreshes_current_view",
    "tests/ui/test_main_window.py::TestTaskActions::test_complete_task_updates_status",
    "tests/ui/test_main_window.py::TestTaskActions::test_trash_task_moves_to_trash",
    "tests/ui/test_main_window.py::TestTaskActions::test_someday_task_moves_to_someday",
    "tests/ui/test_main_window.py::TestDialogInvocations::test_manage_contexts_opens_dialog",
    "tests/ui/test_main_window.py::TestDialogInvocations::test_manage_project_tags_opens_dialog",
    "tests/ui/test_main_window.py::TestDialogInvocations::test_show_settings_opens_dialog",
    "tests/ui/test_main_window.py::TestUndoRedo::test_undo_action_enabled_after_command",
    "tests/ui/test_main_window.py::TestUndoRedo::test_redo_action_enabled_after_undo",
    "tests/ui/test_main_window.py::TestUndoRedo::test_undo_reverses_task_completion",
    "tests/ui/test_main_window.py::TestUndoRedo::test_redo_reapplies_task_completion",
    "tests/ui/test_main_window.py::TestCloseEvent::test_close_saves_geometry",
    "tests/ui/test_main_window.py::TestDeleteTrashTasks::test_delete_trash_tasks_confirmation",
    "tests/ui/test_main_window.py::TestNotificationPanel::test_notification_action_open_focus",
    "tests/ui/test_notification_panel.py::TestNotificationCount::test_count_updates_when_notification_added",
    "tests/ui/test_postpone_dialog.py::TestDeferMode::test_defer_dialog_date_picker_visible",
    "tests/ui/test_postpone_dialog.py::TestDelegateMode::test_delegate_dialog_person_field_visible",
    "tests/ui/test_postpone_dialog.py::TestDelegateMode::test_delegate_dialog_followup_date_visible",
    "tests/ui/test_sequential_ranking_dialog.py::TestTaskRankingItem::test_selection_mode_indicator",
    "tests/ui/test_sequential_ranking_dialog.py::TestTaskRankingItem::test_movement_mode_indicator",
    "tests/ui/test_subtask_breakdown_dialog.py::TestEditingTasks::test_double_click_edits_task",
]

# Run each test and collect error messages
results = {}
for i, test in enumerate(failures):
    print(f"Analyzing {i+1}/{len(failures)}: {test}")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test, "-s", "--tb=line", "-v"],
        capture_output=True,
        text=True,
        timeout=30
    )

    output = result.stdout + result.stderr

    # Extract the assertion or error line
    error_lines = []
    for line in output.split('\n'):
        if ('assert' in line.lower() or 'error' in line.lower() or
            'exception' in line.lower() or 'where' in line or '+' in line[:3]):
            error_lines.append(line.strip())

    results[test] = {
        'error': '\n'.join(error_lines[-10:]) if error_lines else "Unknown error"
    }

# Write results
with open("failure_analysis.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"\nAnalysis complete. Results written to failure_analysis.json")
print(f"Total failures analyzed: {len(results)}")
