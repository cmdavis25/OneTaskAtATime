# Phase 9: Testing & QA - Implementation Plan

## Executive Summary

Phase 9 focuses on comprehensive testing and quality assurance to ensure OneTaskAtATime is production-ready. Based on the implementation_plan.md objectives, this phase delivers:

1. **End-to-End (E2E) Tests** - Critical workflow testing across all task states
2. **Performance Testing** - Validation with 10,000+ tasks
3. **Bug Fixing Sprint** - Address issues discovered during testing
4. **Stability & Quality** - Memory leak detection, crash recovery, edge cases

**Current State**: Phase 8 complete with 33 test files, 313 test functions, strong unit test coverage
**Target**: Production-stable application ready for Phase 10 release

---

## Phase 9 Objectives (from implementation_plan.md)

```markdown
### Phase 9: Testing & QA
- E2E tests for critical flows
- Performance testing (10,000+ tasks)
- Bug fixing sprint

**Deliverable**: Stable, tested application
```

---

## Current Test Coverage Analysis

**Existing Tests** (33 files, 313 test functions):
- ✅ Unit tests: Strong coverage of DAOs, services, algorithms
- ✅ Basic UI tests: Widget initialization, basic interactions
- ✅ Integration tests: Phase 8 workflows (../../test_phase8_workflows.py)
- ❌ E2E tests: **NOT IMPLEMENTED** - Critical gap
- ❌ Performance tests: **NOT IMPLEMENTED** - Critical gap
- ❌ Stress tests: No long-running session tests
- ❌ Load tests: No large dataset tests

**Coverage Gaps Identified**:
1. No complete user journey tests (create → defer → complete)
2. No cross-state transition testing (all 6 task states)
3. No resurfacing system end-to-end tests
4. No comparison/ranking full workflow tests
5. No large dataset performance validation
6. No memory leak testing
7. No crash recovery testing

---

## Implementation Plan

### STEP 1: End-to-End (E2E) Test Suite (4-5 days)

#### 1.1 E2E Test Framework Setup

**Create E2E Test Infrastructure** - [tests/e2e/](../../tests/e2e/) (NEW directory)

**Base Class**: [tests/e2e/base_e2e_test.py](../../tests/e2e/base_e2e_test.py) (~150 lines)

```python
class BaseE2ETest:
    """Base class for E2E tests with application lifecycle management"""

    @pytest.fixture
    def app_instance(self, qtbot, tmp_path):
        """Launch full application with temporary database"""
        db_path = tmp_path / "test_e2e.db"
        app = MainWindow(db_path=str(db_path))
        qtbot.addWidget(app)
        app.show()
        yield app
        app.close()

    @pytest.fixture
    def seeded_app(self, app_instance):
        """Application with pre-seeded test data"""
        # Create 50 tasks with varied states
        # Create contexts, tags, dependencies
        return app_instance
```

**Purpose**: Reusable fixtures for full application testing

#### 1.2 Critical User Journey Tests

**Create E2E Test File**: [tests/e2e/test_core_workflows.py](../../tests/e2e/test_core_workflows.py) (~600 lines)

**Test Cases** (15 tests):

1. **test_new_user_complete_journey**
   - Launch app → First run wizard → Create first task → Complete task → See next task
   - **Validates**: Onboarding, Focus Mode, task ranking

2. **test_task_lifecycle_active_to_completed**
   - Create task → Set priority/due date → Complete → Verify state → Check history
   - **Validates**: Task creation, priority system, completion, history tracking

3. **test_task_lifecycle_defer_workflow**
   - Create task → Defer with start date → Wait (mock time) → Task auto-activates → Complete
   - **Validates**: Deferral, resurfacing, state transitions

4. **test_task_lifecycle_delegate_workflow**
   - Create task → Delegate with follow-up → Mock time passage → Review delegated → Activate → Complete
   - **Validates**: Delegation, follow-up reminders, review dialogs

5. **test_task_lifecycle_someday_workflow**
   - Create task → Move to Someday → Mock time → Review Someday dialog → Activate → Complete
   - **Validates**: Someday state, periodic review, activation

6. **test_comparison_ranking_workflow**
   - Create 3 high-priority tasks with same due date → Trigger comparison → Select winner → Verify Focus Mode
   - **Validates**: Elo comparison system, tie resolution, ranking

7. **test_dependency_blocking_workflow**
   - Create task A → Create task B that depends on A → Verify B hidden in Focus → Complete A → Verify B appears
   - **Validates**: Dependency system, blocking logic, Focus Mode filtering

8. **test_defer_with_blocker_workflow**
   - Create task → Defer with blocker reason → Create blocker task → Complete blocker → Original activates
   - **Validates**: Blocker creation, dependency linking, compound commands

9. **test_defer_with_subtasks_workflow**
   - Create task → Defer with subtasks → Break down into 3 subtasks → Complete all → Original task deferred
   - **Validates**: Subtask breakdown, dependency creation, inheritance

10. **test_undo_redo_complete_workflow**
    - Create task → Complete → Undo → Verify restored → Redo → Verify completed
    - **Validates**: Undo/redo system, state preservation

11. **test_context_filtering_workflow**
    - Create tasks with different contexts → Filter by context → Verify Focus Mode respects filter
    - **Validates**: Context filtering, Focus Mode filter integration

12. **test_project_tag_filtering_workflow**
    - Create tasks with different tags → Filter by tag → Verify Task List filtering
    - **Validates**: Project tag filtering, multi-select behavior

13. **test_export_import_workflow**
    - Create 10 tasks → Export to JSON → Clear database → Import → Verify all tasks restored
    - **Validates**: Data export/import, ID remapping, integrity

14. **test_notification_system_workflow**
    - Create deferred task → Mock time → Notification appears → Click notification → Task activates
    - **Validates**: Notification generation, in-app panel, action handling

15. **test_keyboard_shortcuts_workflow**
    - Navigate to Focus Mode → Use Alt+C to complete → Alt+D to defer → Verify actions work
    - **Validates**: Keyboard shortcuts, Focus Mode actions

**Implementation Pattern**:
```python
def test_task_lifecycle_active_to_completed(app_instance, qtbot):
    """Test complete journey from creation to completion"""

    # Step 1: Create task via UI
    qtbot.mouseClick(app_instance.new_task_button, Qt.LeftButton)
    task_dialog = app_instance.findChild(EnhancedTaskFormDialog)
    task_dialog.title_input.setText("Write Phase 9 tests")
    task_dialog.priority_combo.setCurrentIndex(2)  # High
    qtbot.mouseClick(task_dialog.save_button, Qt.LeftButton)

    # Step 2: Verify task appears in Focus Mode
    focus_mode = app_instance.focus_mode
    assert focus_mode.current_task is not None
    assert focus_mode.current_task.title == "Write Phase 9 tests"

    # Step 3: Complete task
    qtbot.mouseClick(focus_mode.complete_button, Qt.LeftButton)

    # Step 4: Verify state changed
    task_service = app_instance.task_service
    completed_task = task_service.get_by_id(focus_mode.current_task.id)
    assert completed_task.state == TaskState.COMPLETED
    assert completed_task.completed_at is not None

    # Step 5: Verify history recorded
    history_service = app_instance.task_history_service
    events = history_service.get_timeline(completed_task.id)
    assert any(e.event_type == TaskEventType.COMPLETED for e in events)
```

#### 1.3 Cross-State Transition Matrix Tests

**Create E2E Test File**: [tests/e2e/test_state_transitions.py](../../tests/e2e/test_state_transitions.py) (~400 lines)

**Test Cases** (12 tests):

Test all valid state transitions:
- ACTIVE → COMPLETED
- ACTIVE → DEFERRED
- ACTIVE → DELEGATED
- ACTIVE → SOMEDAY
- ACTIVE → TRASH
- DEFERRED → ACTIVE (../../resurfacing)
- DELEGATED → ACTIVE (follow-up)
- SOMEDAY → ACTIVE (review)
- TRASH → ACTIVE (../../restore)
- COMPLETED → ACTIVE (undo/restore)

**Purpose**: Ensure all state transitions work correctly with proper side effects (history, notifications, Elo updates)

#### 1.4 Resurfacing System E2E Tests

**Create E2E Test File**: [tests/e2e/test_resurfacing_system.py](../../tests/e2e/test_resurfacing_system.py) (~350 lines)

**Test Cases** (8 tests):

1. **test_deferred_task_auto_activation**
   - Create task with start_date = tomorrow → Mock time forward → Verify auto-activated

2. **test_delegated_task_follow_up_notification**
   - Delegate task with follow_up = today → Verify notification created → Review dialog appears

3. **test_someday_periodic_review_trigger**
   - Create someday task → Mock 7 days → Verify review dialog triggered

4. **test_multiple_deferred_tasks_batch_activation**
   - Create 5 deferred tasks with same start_date → Mock time → All activate together

5. **test_notification_panel_integration**
   - Trigger notification → Verify appears in panel → Mark as read → Verify state change

6. **test_postpone_pattern_intervention**
   - Postpone same task 3 times → Verify intervention dialog appears with suggestions

7. **test_scheduler_recovery_after_restart**
   - Create deferred task → Close app → Reopen → Verify scheduler restarts and processes task

8. **test_resurfacing_with_dependencies**
   - Deferred task with blocking dependency → Dependency completes → Task activates on schedule

---

### STEP 2: Performance Testing (3-4 days)

#### 2.1 Large Dataset Generation

**Create Performance Test Utilities**: [tests/performance/](../../tests/performance/) (NEW directory)

**Data Generator**: [tests/performance/data_generator.py](../../tests/performance/data_generator.py) (~200 lines)

```python
class LargeDatasetGenerator:
    """Generate realistic large datasets for performance testing"""

    def generate_tasks(self, count: int, db_connection) -> List[Task]:
        """Generate N tasks with realistic distributions"""
        tasks = []
        for i in range(count):
            task = Task(
                title=f"Task {i}: {self._generate_realistic_title()}",
                description=self._generate_description(),
                priority=random.choice([1, 1, 2, 2, 2, 3]),  # Weighted
                due_date=self._random_due_date(),
                state=self._weighted_state(),
                elo_rating=random.gauss(1500, 200),
                comparison_count=random.randint(0, 50)
            )
            tasks.append(task)
        return tasks

    def generate_history_events(self, task_ids: List[int],
                                events_per_task: int = 10):
        """Generate realistic task history"""
        # Create varied event types with realistic timestamps

    def generate_dependencies(self, task_ids: List[int],
                             dependency_ratio: float = 0.15):
        """Create dependency graph (15% of tasks have dependencies)"""
```

**Purpose**: Create realistic test data matching production scenarios

#### 2.2 Performance Benchmark Tests

**Create Performance Test File**: [tests/performance/test_performance_benchmarks.py](../../tests/performance/test_performance_benchmarks.py) (~400 lines)

**Test Cases** (10 tests):

1. **test_focus_mode_with_10k_tasks**
   - Generate 10,000 tasks → Measure Focus Mode load time
   - **Acceptance**: < 500ms to display focus task

2. **test_task_list_rendering_10k_tasks**
   - Load 10,000 tasks in Task List View → Measure render time
   - **Acceptance**: < 2 seconds initial load (with QTableView model/view optimization)

3. **test_ranking_algorithm_10k_tasks**
   - 10,000 tasks → Calculate importance scores → Find top task
   - **Acceptance**: < 200ms to rank all tasks

4. **test_comparison_with_100_tied_tasks**
   - 100 tasks with identical importance → Trigger comparison resolution
   - **Acceptance**: Comparison dialog appears instantly

5. **test_export_10k_tasks_to_json**
   - Export 10,000 tasks + history + dependencies
   - **Acceptance**: < 5 seconds

6. **test_import_10k_tasks_from_json**
   - Import 10,000 tasks with ID remapping
   - **Acceptance**: < 10 seconds

7. **test_task_history_query_1k_events**
   - Task with 1,000 history events → Load timeline
   - **Acceptance**: < 200ms to fetch and display

8. **test_dependency_graph_with_1k_nodes**
   - 1,000 tasks with 150 dependencies → Render graph
   - **Acceptance**: < 3 seconds to build and display

9. **test_search_10k_tasks**
   - Search for term in 10,000 tasks (title + description)
   - **Acceptance**: < 300ms to return results

10. **test_undo_stack_with_50_operations**
    - Perform 50 operations → Undo all → Redo all
    - **Acceptance**: Each operation < 100ms

**Implementation Pattern**:
```python
@pytest.mark.performance
def test_focus_mode_with_10k_tasks(qtbot, tmp_path):
    """Benchmark Focus Mode performance with large dataset"""

    # Setup
    db_path = tmp_path / "perf_test.db"
    generator = LargeDatasetGenerator(db_path)
    tasks = generator.generate_tasks(10000)

    # Launch app
    app = MainWindow(db_path=str(db_path))
    qtbot.addWidget(app)

    # Measure Focus Mode load
    start = time.perf_counter()
    app.focus_mode.refresh_focus_task()
    elapsed = time.perf_counter() - start

    # Assert performance
    assert elapsed < 0.5, f"Focus Mode took {elapsed:.2f}s (limit: 0.5s)"
    assert app.focus_mode.current_task is not None
```

#### 2.3 Memory Leak Testing

**Create Memory Test File**: [tests/performance/test_memory_leaks.py](../../tests/performance/test_memory_leaks.py) (~250 lines)

**Test Cases** (5 tests):

1. **test_focus_mode_refresh_memory**
   - Refresh Focus Mode 1,000 times → Measure memory growth
   - **Acceptance**: < 10% memory increase

2. **test_dialog_open_close_memory**
   - Open/close TaskFormDialog 500 times → Check for leaks
   - **Acceptance**: No accumulated objects

3. **test_undo_stack_memory**
   - Perform 500 undoable operations → Verify stack pruning works
   - **Acceptance**: Stack size limited to 50

4. **test_notification_accumulation**
   - Generate 1,000 notifications → Verify old notifications cleared
   - **Acceptance**: Only recent N notifications stored

5. **test_long_running_session**
   - Simulate 8-hour session with realistic operations
   - **Acceptance**: Memory stable after initial load

**Tools**: Use `tracemalloc` for memory profiling

---

### STEP 3: Stress & Edge Case Testing (2-3 days)

#### 3.1 Edge Case Tests

**Create Edge Case Test File**: [tests/e2e/test_edge_cases.py](../../tests/e2e/test_edge_cases.py) (~400 lines)

**Test Cases** (12 tests):

1. **test_circular_dependency_detection**
   - Create A depends on B, B depends on C, attempt C depends on A
   - **Expected**: Error dialog, dependency creation blocked

2. **test_self_dependency_prevention**
   - Attempt to create task depending on itself
   - **Expected**: Error dialog, operation blocked

3. **test_empty_title_task_creation**
   - Attempt to create task with empty title
   - **Expected**: Validation error, task not created

4. **test_task_with_no_priority**
   - Edge case: Task with null/undefined priority
   - **Expected**: Default to Medium priority

5. **test_task_with_past_due_date**
   - Create task with due_date = yesterday
   - **Expected**: Task created, urgency score reflects overdue status

6. **test_defer_without_start_date**
   - Attempt to defer task without specifying start_date
   - **Expected**: Validation error or default to today

7. **test_delegate_without_follow_up**
   - Attempt to delegate without follow_up_date
   - **Expected**: Validation error, delegation blocked

8. **test_comparison_with_single_task**
   - Only 1 task exists, trigger comparison
   - **Expected**: No comparison needed, Focus Mode shows task

9. **test_complete_already_completed_task**
   - Complete task twice
   - **Expected**: Second attempt ignored or handled gracefully

10. **test_undo_when_stack_empty**
    - Attempt undo with empty stack
    - **Expected**: No error, status message "Nothing to undo"

11. **test_import_malformed_json**
    - Import JSON with invalid structure
    - **Expected**: Error dialog with recovery suggestions

12. **test_database_locked_error**
    - Simulate SQLite BUSY error
    - **Expected**: Retry logic or user-friendly error

#### 3.2 Concurrency Tests

**Create Concurrency Test File**: [tests/e2e/test_concurrency.py](../../tests/e2e/test_concurrency.py) (~200 lines)

**Test Cases** (4 tests):

1. **test_resurfacing_during_user_action**
   - User completing task while resurfacing job activates deferred task
   - **Expected**: Both operations complete correctly

2. **test_notification_during_dialog**
   - Notification appears while dialog is open
   - **Expected**: Notification queued, appears after dialog closes

3. **test_multiple_comparison_dialogs**
   - Attempt to open comparison dialog when one already open
   - **Expected**: Second attempt blocked

4. **test_scheduler_and_ui_thread_interaction**
   - Background scheduler modifies task state while UI displays it
   - **Expected**: UI refreshes correctly, no race conditions

---

### STEP 4: Crash Recovery & Stability (2 days)

#### 4.1 Database Integrity Tests

**Create Integrity Test File**: [tests/integration/test_database_integrity.py](../../tests/integration/test_database_integrity.py) (~250 lines)

**Test Cases** (6 tests):

1. **test_database_recovery_after_crash**
   - Simulate crash during write → Reopen database → Verify integrity
   - **Expected**: No corruption, transaction rolled back

2. **test_foreign_key_constraints**
   - Delete task with dependencies → Verify cascading deletes work
   - **Expected**: Related records properly cleaned up

3. **test_database_backup_restore**
   - Create data → Backup → Corrupt database → Restore
   - **Expected**: Data fully restored

4. **test_schema_migration**
   - Open database with old schema version → Verify auto-migration
   - **Expected**: Schema updated, data preserved

5. **test_concurrent_writes**
   - Simulate multiple operations writing simultaneously
   - **Expected**: SQLite handles locking, no data loss

6. **test_database_size_limits**
   - Fill database to large size (100MB+)
   - **Expected**: Performance remains acceptable

#### 4.2 Error Recovery Tests

**Create Error Recovery Test File**: [tests/integration/test_error_recovery.py](../../tests/integration/test_error_recovery.py) (~200 lines)

**Test Cases** (5 tests):

1. **test_recovery_from_export_failure**
   - Trigger export error (disk full) → Verify app continues working

2. **test_recovery_from_import_failure**
   - Import invalid data → Error dialog → Verify app state unchanged

3. **test_scheduler_failure_recovery**
   - Scheduler job throws exception → Verify scheduler continues

4. **test_missing_settings_recovery**
   - Delete settings table → Restart app → Verify defaults applied

5. **test_corrupted_task_recovery**
   - Task with invalid state → Verify app handles gracefully

---

### STEP 5: Bug Fixing Sprint (5-7 days)

#### 5.1 Bug Discovery Phase

**Process**:
1. Run all E2E tests → Document failures
2. Run performance tests → Identify bottlenecks
3. Manual exploratory testing → Find UX issues
4. Review PHASE8_STATUS.md "Known Issues" section

**Bug Tracking**: Create `docs/PHASE9_BUGS.md`

Format:
```markdown
## Bugs Discovered

### Critical (Blocks Release)
- [ ] BUG-001: Focus Mode crashes with 10,000 tasks
- [ ] BUG-002: Database corruption on forced shutdown

### High (Impacts Core Features)
- [ ] BUG-003: Undo fails for defer with dependencies
- [ ] BUG-004: Comparison dialog freezes with 100+ ties

### Medium (UX Issues)
- [ ] BUG-005: Task List scrolls to top after edit
- [ ] BUG-006: Keyboard shortcuts don't work in some dialogs

### Low (Minor Issues)
- [ ] BUG-007: Tooltip text cut off in dark theme
- [ ] BUG-008: Window position slightly off on multi-monitor
```

#### 5.2 Bug Fixing Priority

**Week 1 (Days 1-3)**: Critical bugs only
- Database integrity issues
- Application crashes
- Data loss scenarios

**Week 2 (Days 4-5)**: High priority bugs
- Core feature failures
- Performance bottlenecks
- Undo/redo issues

**Week 3 (Days 6-7)**: Medium/Low bugs (time permitting)
- UX polish
- Edge case handling
- Visual glitches

#### 5.3 Regression Prevention

**After Each Bug Fix**:
1. Write regression test
2. Add to CI test suite
3. Update documentation if behavior changed
4. Verify fix doesn't break other tests

---

### STEP 6: Testing Infrastructure Improvements (2 days)

#### 6.1 Test Fixtures & Utilities

**Create Test Utilities**: [tests/utils/](../../tests/utils/) (NEW directory)

**Files to Create**:
1. [tests/utils/test_data_factory.py](../../tests/utils/test_data_factory.py) - Factory for creating test tasks, contexts, tags
2. [tests/utils/time_mocker.py](../../tests/utils/time_mocker.py) - Mock datetime for resurfacing tests
3. [tests/utils/performance_profiler.py](../../tests/utils/performance_profiler.py) - Decorators for timing tests
4. [tests/utils/database_seeder.py](../../tests/utils/database_seeder.py) - Pre-seed databases with realistic data

**Purpose**: Reduce test boilerplate, improve test maintainability

#### 6.2 Test Configuration

**Create pytest Configuration**: [pytest.ini](../../pytest.ini) (NEW)

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (database required)
    e2e: End-to-end tests (full app, slow)
    performance: Performance benchmarks
    slow: Tests that take > 5 seconds

addopts =
    -v
    --tb=short
    --strict-markers
    --durations=10

# Performance test timeout
timeout = 300
```

**Purpose**: Organize tests, enable selective test runs

#### 6.3 Continuous Integration (Optional)

**Create GitHub Actions Workflow**: [.github/workflows/tests.yml](.github/workflows/tests.yml) (NEW)

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pytest tests/ -m "unit or integration" --cov=src
      - run: pytest tests/e2e/ -m "not slow"
```

**Purpose**: Automated testing on every commit

---

### STEP 7: Documentation & Test Reports (2 days)

#### 7.1 Test Coverage Report

**Generate Coverage Report**:
```bash
pytest --cov=src --cov-report=html --cov-report=term
```

**Create Coverage Summary**: [docs/TEST_COVERAGE.md](docs/TEST_COVERAGE.md) (~200 lines)

Contents:
- Overall coverage percentage (target: 80%+)
- Per-module coverage breakdown
- Uncovered critical paths
- Justification for uncovered code

#### 7.2 Performance Test Results

**Create Performance Report**: [docs/PERFORMANCE_RESULTS.md](docs/PERFORMANCE_RESULTS.md) (~300 lines)

Contents:
- Benchmark results for all performance tests
- Comparison to acceptance criteria
- Bottlenecks identified
- Optimization recommendations

#### 7.3 Phase 9 Status Report

**Create Status Report**: [PHASE9_STATUS.md](../phase_reports/PHASE9_STATUS.md) (~600 lines)

Follow [phase_progress_report_instructions.md](phase_progress_report_instructions.md) format:

Sections:
1. Overview - What was accomplished
2. Deliverables Completed - E2E tests, performance tests, bug fixes
3. Test Coverage - Statistics and breakdown
4. Performance Results - Benchmark summary
5. Bugs Fixed - List of resolved issues
6. Known Issues - Remaining low-priority bugs
7. Verification Checklist - How to run tests
8. What's Next: Phase 10 - Release preparation
9. Key Files Created - Test files manifest
10. Success Criteria Met - Compare to objectives

---

## Implementation Sequence

### Week 1: E2E Foundation (5 days)
- **Days 1-2**: E2E framework setup, core workflow tests (15 tests)
- **Days 3-4**: State transition tests, resurfacing E2E tests (20 tests)
- **Day 5**: Review and fix failing tests

### Week 2: Performance & Edge Cases (5 days)
- **Days 1-2**: Large dataset generation, performance benchmarks (10 tests)
- **Days 3-4**: Memory leak tests, edge case tests (17 tests)
- **Day 5**: Concurrency and stability tests (10 tests)

### Week 3: Bug Fixing Sprint (7 days)
- **Days 1-3**: Critical bug fixes (database, crashes, data loss)
- **Days 4-5**: High-priority bug fixes (features, performance)
- **Days 6-7**: Medium/low bug fixes, polish

### Week 4: Infrastructure & Documentation (4 days)
- **Days 1-2**: Test utilities, CI setup, regression tests
- **Days 3-4**: Coverage reports, performance reports, Phase 9 status

**Total Duration**: 21 days (3 weeks)

---

## Critical Files to Create/Modify

### NEW Test Files (15 files)

**E2E Tests** (6 files):
1. [tests/e2e/base_e2e_test.py](../../tests/e2e/base_e2e_test.py) (~150 lines)
2. [tests/e2e/test_core_workflows.py](../../tests/e2e/test_core_workflows.py) (~600 lines) - 15 tests
3. [tests/e2e/test_state_transitions.py](../../tests/e2e/test_state_transitions.py) (~400 lines) - 12 tests
4. [tests/e2e/test_resurfacing_system.py](../../tests/e2e/test_resurfacing_system.py) (~350 lines) - 8 tests
5. [tests/e2e/test_edge_cases.py](../../tests/e2e/test_edge_cases.py) (~400 lines) - 12 tests
6. [tests/e2e/test_concurrency.py](../../tests/e2e/test_concurrency.py) (~200 lines) - 4 tests

**Performance Tests** (3 files):
7. [tests/performance/data_generator.py](../../tests/performance/data_generator.py) (~200 lines)
8. [tests/performance/test_performance_benchmarks.py](../../tests/performance/test_performance_benchmarks.py) (~400 lines) - 10 tests
9. [tests/performance/test_memory_leaks.py](../../tests/performance/test_memory_leaks.py) (~250 lines) - 5 tests

**Integration Tests** (2 files):
10. [tests/integration/test_database_integrity.py](../../tests/integration/test_database_integrity.py) (~250 lines) - 6 tests
11. [tests/integration/test_error_recovery.py](../../tests/integration/test_error_recovery.py) (~200 lines) - 5 tests

**Test Utilities** (4 files):
12. [tests/utils/test_data_factory.py](../../tests/utils/test_data_factory.py) (~150 lines)
13. [tests/utils/time_mocker.py](../../tests/utils/time_mocker.py) (~100 lines)
14. [tests/utils/performance_profiler.py](../../tests/utils/performance_profiler.py) (~100 lines)
15. [tests/utils/database_seeder.py](../../tests/utils/database_seeder.py) (~150 lines)

### NEW Configuration Files (2 files)

16. [pytest.ini](pytest.ini) - Test configuration
17. [.github/workflows/tests.yml](.github/workflows/tests.yml) - CI configuration (optional)

### NEW Documentation Files (4 files)

18. [docs/PHASE9_BUGS.md](docs/PHASE9_BUGS.md) - Bug tracking during sprint
19. [docs/TEST_COVERAGE.md](docs/TEST_COVERAGE.md) - Coverage report
20. [docs/PERFORMANCE_RESULTS.md](docs/PERFORMANCE_RESULTS.md) - Performance benchmark results
21. [PHASE9_STATUS.md](../phase_reports/PHASE9_STATUS.md) - Phase completion report

**Total New Files**: 21 files
**Total New Test Cases**: ~87 tests
**Total New Lines**: ~4,500 lines

---

## Success Criteria

### Functional Requirements

**E2E Test Coverage**:
- ✅ All 6 task states have E2E tests
- ✅ All critical user journeys tested (15 workflows)
- ✅ State transition matrix complete (12 transitions)
- ✅ Resurfacing system fully tested (8 scenarios)
- ✅ Edge cases covered (12 scenarios)

**Performance Validation**:
- ✅ Focus Mode < 500ms with 10,000 tasks
- ✅ Task List rendering < 2s with 10,000 tasks
- ✅ Ranking algorithm < 200ms for 10,000 tasks
- ✅ Export/Import < 10s for large datasets
- ✅ No memory leaks in long-running sessions

**Bug Fixing**:
- ✅ All critical bugs fixed (data loss, crashes)
- ✅ All high-priority bugs fixed (core features)
- ✅ Regression tests added for all fixes
- ✅ Known issues documented for low-priority bugs

### Non-Functional Requirements

**Test Quality**:
- ✅ 80%+ code coverage (measured with pytest-cov)
- ✅ All tests pass consistently (no flaky tests)
- ✅ Test execution time < 10 minutes for full suite
- ✅ Performance tests have clear acceptance criteria

**Documentation**:
- ✅ Phase 9 status report complete
- ✅ Test coverage report generated
- ✅ Performance results documented
- ✅ Bug tracking document maintained

**Stability**:
- ✅ No crashes during 8-hour stress test
- ✅ Database integrity maintained under load
- ✅ Error recovery mechanisms tested
- ✅ Scheduler recovery after restart verified

---

## Risk Mitigation

**Risk: E2E tests are flaky**
- Mitigation: Use qtbot.waitUntil() for async operations, proper fixtures cleanup, deterministic test data

**Risk: Performance tests fail on slower machines**
- Mitigation: Set generous acceptance criteria, document test machine specs, allow tolerance ranges

**Risk: Bug fixing sprint uncovers major issues**
- Mitigation: Prioritize ruthlessly (critical only), consider rolling to Phase 10 if low-impact

**Risk: Test suite becomes too slow**
- Mitigation: Use pytest markers to run subsets, parallelize with pytest-xdist, optimize fixtures

**Risk: Memory leak tests are unreliable**
- Mitigation: Use tracemalloc with clear baselines, run multiple iterations, document acceptable growth

**Risk: CI setup is too complex**
- Mitigation: Start with local testing, CI is optional for v1.0, can add in future phase

---

## Testing Best Practices

1. **Isolation**: Each test creates its own database (tmp_path fixture)
2. **Determinism**: Mock time/random for predictable results
3. **Clarity**: Descriptive test names and comments explaining what's being validated
4. **Speed**: Fast unit tests, slower E2E tests marked with @pytest.mark.slow
5. **Maintenance**: Shared fixtures in conftest.py, reusable utilities
6. **Documentation**: Each test has docstring explaining purpose
7. **Assertions**: Clear failure messages with context

---

## Phase 9 Deliverable

**Stable, tested application** ready for Phase 10 release preparation:

- ✅ Comprehensive E2E test coverage (87+ tests)
- ✅ Performance validated with 10,000+ task datasets
- ✅ All critical and high-priority bugs fixed
- ✅ Memory leak testing passed
- ✅ Database integrity verified
- ✅ Test coverage report > 80%
- ✅ Performance benchmark results documented
- ✅ CI pipeline ready (optional)
- ✅ Phase 9 status report complete

**Next Phase**: Phase 10 will focus on release preparation (installer, user docs, demo video)

---

## Notes

- Phase 8 already has strong unit test foundation (313 tests), Phase 9 focuses on integration/E2E
- Use pytest markers (@pytest.mark.e2e, @pytest.mark.performance) for selective test runs
- Performance tests should run on consistent hardware for reliable benchmarks
- Bug fixing sprint is intentionally longer (7 days) to handle discovered issues
- Some low-priority bugs may be deferred to post-v1.0 if time-constrained
- Memory leak testing requires Python 3.10+ tracemalloc features
- E2E tests will use qtbot from pytest-qt for Qt widget interaction
- Time mocking is critical for resurfacing tests (use freezegun or custom time service)
- Database seeder should create realistic distributions (not all high priority)
- CI setup is optional for Phase 9, can be added incrementally

**End of Phase 9 Plan**
