# Phase 5: Dependency & Blocker System - Implementation Plan

## Executive Summary

Phase 5 completes the dependency and blocker management system by integrating the existing postpone dialog with actionable workflows. Most infrastructure (Dependency model/DAO, UI components, circular dependency detection) already exists. This phase focuses on:

1. **Creating PostponeHistoryDAO** - Persistence layer for tracking why tasks are postponed
2. **Implementing workflow handlers** - Turn postpone reasons into concrete actions
3. **Integrating workflows into UI** - Seamless user experience from postpone to resolution
4. **Adding visual indicators** - Show dependency status throughout the app
5. **Analytics & suggestions** - Help users identify patterns and take corrective action

## Design Decisions (User Confirmed)

**1. Subtask Breakdown - Original Task Handling**: ✅ **Option B**
- Let user decide via checkbox whether to delete original task
- Provides flexibility while defaulting to keep
- Checkbox labeled: "Delete original task after breakdown"

**2. Dependency Workflow Integration**: ✅ **Option A**
- Show DependencySelectionDialog immediately inline when DEPENDENCY reason selected
- Provides best UX and completes workflow in one flow
- Reuses existing full-featured dialog

**3. Blocker Creation - Task State**: ✅ **Option A**
- New blocker tasks start in ACTIVE state
- Rationale: Blockers typically need immediate attention to unblock yourself
- User can manually defer if needed via postpone dialog

**4. Postpone Recording Timing**: ✅ **Option B**
- Record postpone history AFTER state change succeeds
- Ensures data consistency (don't record failed operations)
- Implementation: Call `postpone_dao.create()` after `task_dao.update()` succeeds

**5. Scope Boundaries**: ✅ **All Features Included in Phase 5**
- Dependency graph visualization (text-based tree)
- Postpone analytics dashboard (statistics on postpone patterns)
- Smart suggestions ("You've postponed this 3 times...")
- These are core Phase 5 objectives, NOT deferred to Phase 8

## Current State Analysis

### What's Already Complete ✅
- **Dependency Model & DAO** with full CRUD and circular dependency detection
- **Dependency Selection Dialog** with two-pane interface and search
- **Postpone Dialog** that captures all reason types (BLOCKER, DEPENDENCY, MULTIPLE_SUBTASKS, etc.)
- **Postpone Model & Database Table** with all required fields
- **Focus Mode filtering** that excludes blocked tasks from appearing
- **Task forms** with dependency management section

### Critical Gap 🔴
- **No PostponeHistoryDAO** - Postpone records aren't being saved to database
- **No workflow execution** - Postpone reasons captured but not acted upon
- **TODO comments in task_service.py** - defer_task() and delegate_task() don't save postpone records

## Implementation Strategy

### Part A: Foundation Layer (Week 1)
Build the data persistence and service infrastructure

### Part B: Workflow Implementation (Week 2)
Implement the three core workflows triggered by postpone reasons

### Part C: UI Integration (Week 3)
Wire workflows into existing UI and add visual indicators

### Part D: Enhanced Features (Week 4)
Implement analytics, visualization, and smart suggestions

### Part E: Testing & Documentation (Week 5)
Comprehensive testing and documentation updates

---

## Detailed Implementation Steps

### STEP 1: Create PostponeHistoryDAO
**File**: [src/database/postpone_history_dao.py](src/database/postpone_history_dao.py) (NEW)

**Purpose**: Data access layer for postpone_history table

**Methods to implement**:
- `create(record: PostponeRecord) -> PostponeRecord` - Insert with auto-timestamp
- `get_by_id(record_id: int) -> Optional[PostponeRecord]` - Retrieve single record
- `get_by_task_id(task_id: int, limit: int = 50) -> List[PostponeRecord]` - Task history
- `get_by_reason_type(reason_type: PostponeReasonType, limit: int = 100)` - Analytics
- `get_recent(days: int = 7, limit: int = 100)` - Recent activity
- `delete_by_task_id(task_id: int) -> int` - Cleanup on task deletion
- `_row_to_postpone_record(row: sqlite3.Row) -> PostponeRecord` - Object mapping

**Pattern to follow**: Existing DAOs ([src/database/context_dao.py](src/database/context_dao.py), [src/database/comparison_dao.py](src/database/comparison_dao.py))

**Key considerations**:
- Records are append-only (no update method needed)
- Handle enum conversions (string ↔ PostponeReasonType/ActionTaken)
- Use ISO format for datetime fields
- Auto-set postponed_at to datetime.now() if not provided

---

### STEP 2: Create PostponeWorkflowService
**File**: [src/services/postpone_workflow_service.py](src/services/postpone_workflow_service.py) (NEW)

**Purpose**: Business logic coordinator for postpone-triggered workflows

**Core methods**:

```python
def record_postpone(task_id, reason, notes, action_taken) -> PostponeRecord
    """Save postpone event to history"""

def handle_blocker_workflow(task_id, notes, blocker_task_id=None,
                            new_blocker_title=None) -> Dict[str, Any]
    """
    Create blocker task (new or existing) and add dependency.
    Returns: {success: bool, blocker_task_id: int, message: str}
    """

def handle_dependency_workflow(task_id, notes,
                               dependency_task_ids: List[int]) -> Dict[str, Any]
    """
    Add existing tasks as dependencies.
    Returns: {success: bool, count: int, message: str}
    """

def handle_subtask_breakdown(original_task_id, notes, subtask_titles: List[str],
                             delete_original: bool = False) -> Dict[str, Any]
    """
    Break task into subtasks, optionally delete original.
    Copies: priority, due_date, context, project_tags
    Returns: {success: bool, task_ids: List[int], message: str}
    """

def get_postpone_history(task_id, limit=10) -> List[PostponeRecord]
    """Retrieve postpone history for analysis"""
```

**Design decisions**:
- All workflow methods return consistent result dictionaries
- Service coordinates between TaskDAO, DependencyDAO, and PostponeHistoryDAO
- Subtask breakdown moves original to TRASH (preserves history) rather than hard delete
- Error handling returns success=False with user-friendly messages

---

### STEP 3: Wire Postpone Recording into TaskService
**File**: [src/services/task_service.py](src/services/task_service.py) (MODIFY)

**Changes required**:

1. Add PostponeHistoryDAO initialization in `__init__`
2. Update `defer_task()` method to save postpone record:
   ```python
   # After successful task.defer_until()
   postpone_record = PostponeRecord(
       task_id=task_id,
       reason_type=reason,
       reason_notes=notes,
       action_taken=ActionTaken.DEFERRED
   )
   self.postpone_dao.create(postpone_record)
   ```

3. Update `delegate_task()` similarly with action_taken=DELEGATED

**Rationale**: Record postpone AFTER state change succeeds (data consistency)

---

### STEP 4: Create Blocker Selection Dialog
**File**: [src/ui/blocker_selection_dialog.py](src/ui/blocker_selection_dialog.py) (NEW)

**Purpose**: Prompt user to create or select blocking task

**UI Layout**:
```
┌─────────────────────────────────────────────────┐
│ Create Blocker for: [Task Title]                │
├─────────────────────────────────────────────────┤
│ What is blocking you?                           │
│                                                 │
│ ○ Create new task to address blocker            │
│   [Enter blocker task title_____________]       │
│                                                 │
│ ○ Select existing task as blocker               │
│   [Dropdown of existing tasks___________|▼]     │
│                                                 │
│ Additional notes:                               │
│ [Text area____________________________]         │
│                                                 │
│               [Cancel]  [Create Blocker]        │
└─────────────────────────────────────────────────┘
```

**Result format**:
```python
{
    'mode': 'new' | 'existing',
    'blocker_task_id': int,      # if mode='existing'
    'new_blocker_title': str,    # if mode='new'
    'notes': str
}
```

---

### STEP 5: Create Subtask Breakdown Dialog
**File**: [src/ui/subtask_breakdown_dialog.py](src/ui/subtask_breakdown_dialog.py) (NEW)

**Purpose**: Capture subtask titles and deletion preference

**UI Layout**:
```
┌─────────────────────────────────────────────────┐
│ Break Down Task: [Task Title]                   │
├─────────────────────────────────────────────────┤
│ Enter subtasks (one per line):                  │
│ ┌─────────────────────────────────────────────┐ │
│ │ Subtask 1                                   │ │
│ │ Subtask 2                                   │ │
│ │ Subtask 3                                   │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ [✓] Delete original task after breakdown        │
│                                                 │
│ Note: New tasks inherit priority, due date,     │
│       and tags from original task.              │
│                                                 │
│               [Cancel]  [Create Subtasks]       │
└─────────────────────────────────────────────────┘
```

**Result format**:
```python
{
    'subtask_titles': List[str],  # Non-empty lines only
    'delete_original': bool
}
```

---

### STEP 6: Update PostponeDialog to Trigger Workflows
**File**: [src/ui/postpone_dialog.py](src/ui/postpone_dialog.py) (MODIFY)

**Key changes**:

1. Add `db_connection` and `task` parameters to `__init__`
2. Add instance variables for workflow results:
   - `self.blocker_result = None`
   - `self.subtask_result = None`
3. Override `accept()` method to show follow-up dialogs:

```python
def accept(self):
    """Handle acceptance and trigger workflows based on reason."""
    if self.action_type == "defer":
        reason = self._get_selected_reason()

        if reason == PostponeReasonType.BLOCKER:
            # Show blocker selection dialog
            blocker_dialog = BlockerSelectionDialog(self.task, self.db_connection, self)
            if blocker_dialog.exec_() != QDialog.Accepted:
                return  # User canceled
            self.blocker_result = blocker_dialog.get_result()

        elif reason == PostponeReasonType.DEPENDENCY:
            # Reuse existing dependency selection dialog
            dep_dialog = DependencySelectionDialog(self.task, self.db_connection, self)
            if dep_dialog.exec_() != QDialog.Accepted:
                return
            # Dependencies saved by dialog, just record postpone

        elif reason == PostponeReasonType.MULTIPLE_SUBTASKS:
            # Show subtask breakdown dialog
            subtask_dialog = SubtaskBreakdownDialog(self.task, self)
            if subtask_dialog.exec_() != QDialog.Accepted:
                return
            self.subtask_result = subtask_dialog.get_result()

    super().accept()  # Close dialog
```

4. Update `get_result()` to include workflow results

**Design rationale**: Handle workflows inline (better UX) rather than requiring caller to manage workflow logic

---

### STEP 7: Update Focus Mode to Use PostponeWorkflowService
**File**: [src/ui/focus_mode.py](src/ui/focus_mode.py) (MODIFY)

**Changes**:

1. Pass `db_connection` and `task` object to postpone dialogs
2. Add `_handle_postpone_workflows(result)` method:

```python
def _handle_postpone_workflows(self, postpone_result: Dict[str, Any]):
    """Process workflow results from postpone dialog."""
    workflow_service = PostponeWorkflowService(self.db_connection)
    task_id = self.current_task.id
    notes = postpone_result.get('notes', '')

    # Handle blocker workflow
    if blocker_result := postpone_result.get('blocker_result'):
        result = workflow_service.handle_blocker_workflow(
            task_id, notes,
            blocker_task_id=blocker_result.get('blocker_task_id'),
            new_blocker_title=blocker_result.get('new_blocker_title')
        )
        if result['success']:
            QMessageBox.information(self, "Blocker Created", result['message'])

    # Handle subtask workflow
    if subtask_result := postpone_result.get('subtask_result'):
        result = workflow_service.handle_subtask_breakdown(
            task_id, notes,
            subtask_result['subtask_titles'],
            subtask_result['delete_original']
        )
        if result['success']:
            QMessageBox.information(self, "Tasks Created", result['message'])
```

3. Call this method in `_on_defer_clicked()` after task state update

---

### STEP 8: Add Dependency Indicators to Task List
**File**: [src/ui/task_list_view.py](src/ui/task_list_view.py) (MODIFY)

**Enhancements**:

1. Add "Dependencies" column showing blocking task count
2. Use visual indicator for blocked tasks (⛔ icon + red text)
3. Add tooltip showing titles of blocking tasks

```python
# In table population:
blocking_count = len(task.blocking_task_ids)
if blocking_count > 0:
    dep_item = QTableWidgetItem(f"⛔ {blocking_count}")
    dep_item.setForeground(Qt.red)

    # Tooltip with blocking task titles
    blocking_tasks = [self.task_dao.get_by_id(tid) for tid in task.blocking_task_ids]
    titles = [t.title for t in blocking_tasks if t]
    tooltip = "Blocked by:\n" + "\n".join(f"• {t}" for t in titles)
    dep_item.setToolTip(tooltip)
else:
    dep_item = QTableWidgetItem("—")
```

---

### STEP 9: Show Blocking Status in Focus Mode
**File**: [src/ui/focus_mode.py](src/ui/focus_mode.py) (MODIFY)

**Add metadata display**:

```python
# In task card creation:
if self.current_task.blocking_task_ids:
    blocked_by_label = QLabel("⛔ Blocked by:")
    blocked_by_label.setStyleSheet("font-weight: bold; color: #dc3545;")
    metadata_layout.addWidget(blocked_by_label)

    for tid in self.current_task.blocking_task_ids:
        blocking_task = self.task_dao.get_by_id(tid)
        if blocking_task:
            task_label = QLabel(f"  • {blocking_task.title}")
            metadata_layout.addWidget(task_label)
```

**Note**: Blocked tasks shouldn't normally appear in Focus Mode (filtered by `get_actionable_tasks()`), but this helps users understand why certain tasks aren't showing up.

---

### STEP 10: Unit Tests - PostponeHistoryDAO
**File**: [tests/test_postpone_history_dao.py](tests/test_postpone_history_dao.py) (NEW)

**Test coverage**:
- `test_create_postpone_record()` - Verify ID assigned and timestamp set
- `test_get_by_id()` - Retrieve single record
- `test_get_by_task_id()` - Filter by task, verify ordering
- `test_get_by_reason_type()` - Filter by reason
- `test_get_recent()` - Date range filtering
- `test_delete_by_task_id()` - Cleanup operation
- `test_enum_conversion()` - String ↔ Enum mapping

**Pattern**: Follow [tests/test_context_dao.py](tests/test_context_dao.py) structure

---

### STEP 11: Unit Tests - PostponeWorkflowService
**File**: [tests/test_postpone_workflow_service.py](tests/test_postpone_workflow_service.py) (NEW)

**Test coverage**:
- `test_record_postpone()` - Basic postpone recording
- `test_handle_blocker_workflow_new_task()` - Create new blocker
- `test_handle_blocker_workflow_existing_task()` - Use existing blocker
- `test_handle_dependency_workflow()` - Add dependencies
- `test_handle_dependency_workflow_circular()` - Detect circular deps
- `test_handle_subtask_breakdown_keep_original()` - Break down, keep original
- `test_handle_subtask_breakdown_delete_original()` - Break down, delete original
- `test_subtask_inherits_fields()` - Verify priority/tags copied

---

### STEP 12: Integration Tests
**File**: [tests/test_phase5_integration.py](tests/test_phase5_integration.py) (NEW)

**Test scenarios**:

1. **End-to-end blocker workflow**:
   - Create task → Defer with BLOCKER → Create blocker → Verify blocked

2. **End-to-end subtask breakdown**:
   - Create task with tags → Break down → Verify subtasks inherit fields

3. **Dependency chain**:
   - A depends on B depends on C → Complete C → A still blocked → Complete B → A actionable

4. **Circular dependency prevention**:
   - A depends on B → Attempt B depends on A → Should fail gracefully

---

### STEP 13: Unit Tests - Enhanced Features

**File**: [tests/test_dependency_graph_view.py](tests/test_dependency_graph_view.py) (NEW)

**Test coverage**:
- `test_build_tree_single_dependency()` - Simple case
- `test_build_tree_chain()` - A → B → C chain
- `test_build_tree_multiple_blockers()` - A blocked by B and C
- `test_circular_detection_in_tree()` - Prevent infinite loops
- `test_tree_formatting()` - Verify visual structure

**File**: [tests/test_postpone_suggestion_service.py](tests/test_postpone_suggestion_service.py) (NEW)

**Test coverage**:
- `test_repeated_blocker_suggestion()` - 3+ blocker postpones
- `test_repeated_dependency_suggestion()` - 3+ dependency postpones
- `test_repeated_subtask_suggestion()` - 2+ subtask postpones
- `test_stale_task_suggestion()` - 10+ total postpones
- `test_no_suggestions_fresh_task()` - New tasks have no suggestions
- `test_suggestion_priority_ordering()` - High priority first

**File**: [tests/test_analytics_view.py](tests/test_analytics_view.py) (NEW)

**Test coverage**:
- `test_reason_breakdown_calculation()` - Count by reason type
- `test_most_postponed_tasks()` - Top 10 by count
- `test_recent_activity_formatting()` - Display format
- `test_empty_history()` - Handle no data gracefully

---

### STEP 14: Documentation Updates

**Files to update**:

1. **[CLAUDE.md](CLAUDE.md)** - Add "Delay Handling Workflows" section documenting:
   - BLOCKER workflow (create task or select existing)
   - DEPENDENCY workflow (reuse dependency selection dialog)
   - MULTIPLE_SUBTASKS workflow (break down with field inheritance)

2. **[README.md](README.md)** - Update Phase 5 status to "✅ Complete"

3. **[PHASE5_STATUS.md](PHASE5_STATUS.md)** (NEW) - Create comprehensive status report following standard template

---

## Critical Files Summary

### New Files (13)
1. [src/database/postpone_history_dao.py](src/database/postpone_history_dao.py) - PostponeHistoryDAO
2. [src/services/postpone_workflow_service.py](src/services/postpone_workflow_service.py) - Workflow business logic
3. [src/services/postpone_suggestion_service.py](src/services/postpone_suggestion_service.py) - Smart suggestions
4. [src/ui/blocker_selection_dialog.py](src/ui/blocker_selection_dialog.py) - Blocker creation UI
5. [src/ui/subtask_breakdown_dialog.py](src/ui/subtask_breakdown_dialog.py) - Subtask breakdown UI
6. [src/ui/dependency_graph_view.py](src/ui/dependency_graph_view.py) - Dependency visualization
7. [src/ui/analytics_view.py](src/ui/analytics_view.py) - Postpone analytics dashboard
8. [tests/test_postpone_history_dao.py](tests/test_postpone_history_dao.py) - DAO tests
9. [tests/test_postpone_workflow_service.py](tests/test_postpone_workflow_service.py) - Service tests
10. [tests/test_postpone_suggestion_service.py](tests/test_postpone_suggestion_service.py) - Suggestion tests
11. [tests/test_phase5_integration.py](tests/test_phase5_integration.py) - Integration tests
12. [tests/test_dependency_graph_view.py](tests/test_dependency_graph_view.py) - Visualization tests
13. [PHASE5_STATUS.md](PHASE5_STATUS.md) - Phase report

### Modified Files (6)
1. [src/services/task_service.py](src/services/task_service.py) - Add postpone recording
2. [src/ui/postpone_dialog.py](src/ui/postpone_dialog.py) - Trigger workflows inline
3. [src/ui/focus_mode.py](src/ui/focus_mode.py) - Use workflow service
4. [src/ui/task_list_view.py](src/ui/task_list_view.py) - Add dependency indicators
5. [CLAUDE.md](CLAUDE.md) - Document workflows
6. [README.md](README.md) - Update phase status

**Estimated LOC**: ~3,800 lines (2,400 new code + 200 modified + 1,200 tests)

---

## Implementation Order

### Week 1: Foundation
- Day 1-2: PostponeHistoryDAO + unit tests
- Day 3-4: PostponeWorkflowService skeleton + basic methods
- Day 5: Wire postpone recording into TaskService

### Week 2: Core Workflows
- Day 1-2: Blocker workflow (service + dialog)
- Day 3: Dependency workflow (service integration)
- Day 4-5: Subtask breakdown (service + dialog)

### Week 3: UI Integration
- Day 1-2: Update PostponeDialog to trigger workflows
- Day 3: Update Focus Mode handlers
- Day 4-5: Add dependency indicators to Task List

### Week 4: Enhanced Features
- Day 1-2: Dependency graph visualization (tree builder + UI)
- Day 2-3: Postpone analytics dashboard (data queries + UI)
- Day 4-5: Smart suggestions service + UI integration

### Week 5: Testing & Documentation
- Day 1-2: Write all unit tests (DAO, services, suggestions)
- Day 2-3: Write integration tests + UI tests
- Day 4: Manual testing and bug fixes
- Day 5: Documentation updates and phase report

---

## Success Criteria

Phase 5 is complete when:

- ✅ PostponeHistoryDAO persists postpone records with full CRUD
- ✅ PostponeWorkflowService handles all three workflows (blocker, dependency, subtask)
- ✅ Postpone dialog triggers workflows inline based on selected reason
- ✅ Blocker workflow creates new/existing blocking tasks and dependencies
- ✅ Dependency workflow reuses existing dialog and adds dependencies
- ✅ Subtask workflow creates tasks with field inheritance and optional deletion
- ✅ Task List shows dependency count and tooltips
- ✅ Focus Mode displays blocking status in metadata
- ✅ Dependency graph visualization displays tree structure
- ✅ Analytics dashboard shows postpone statistics
- ✅ Smart suggestions detect patterns and offer actions
- ✅ Unit tests achieve 85%+ coverage on new code
- ✅ Integration tests validate end-to-end workflows
- ✅ Documentation updated (CLAUDE.md, README, PHASE5_STATUS.md)
- ✅ No regressions in existing functionality

---

## Technical Considerations

### Error Handling
All workflows return result dictionaries with `success` flag and user-friendly `message`:

```python
try:
    result = workflow_service.handle_blocker_workflow(...)
    if result['success']:
        QMessageBox.information(parent, "Success", result['message'])
    else:
        QMessageBox.warning(parent, "Failed", result['message'])
except ValueError as e:
    # Circular dependency or validation error
    QMessageBox.critical(parent, "Error", str(e))
```

### Circular Dependency Detection
Already implemented in `DependencyDAO._would_create_cycle()`. Workflows catch ValueError and show:
> "Cannot create dependency: This would create a circular dependency chain."

### Transaction Handling
For multi-step workflows (subtask breakdown), use explicit commits:

```python
try:
    # Multiple operations...
    self.db.commit()
    return {'success': True}
except Exception as e:
    self.db.rollback()
    return {'success': False, 'message': str(e)}
```

### Field Inheritance (Subtask Breakdown)
New subtasks inherit from original:
- `base_priority` (importance)
- `due_date` (urgency)
- `context_id` (environment filter)
- `project_tags` (organization)

Do NOT inherit:
- `comparison_losses` / `priority_adjustment` (reset for new tasks)
- `description` (each subtask has its own details)
- `delegated_to` / `follow_up_date` (delegation is per-task)

---

## UI/UX Guidelines

### User Feedback Messages
- Blocker: "Blocker created: 'Fix authentication bug' now blocks this task"
- Subtasks: "3 new tasks created, original task moved to trash"
- Dependencies: "2 dependencies added, task is now blocked"

### Confirmation Dialogs
For destructive actions (delete original), confirm:
> "Are you sure you want to move '[Task Title]' to trash? The subtasks will remain active."

### Visual Indicators
- ⛔ icon for blocked tasks (red text)
- — dash for tasks without dependencies (gray text)
- Tooltips showing blocking task titles

---

## Phase 5 Enhanced Features (Required)

### Feature A: Dependency Graph Visualization

**File**: [src/ui/dependency_graph_view.py](src/ui/dependency_graph_view.py) (NEW)

**Purpose**: Visual representation of task dependency chains

**Implementation approach**:
Text-based tree showing dependency chains with visual indicators:
```
Task: "Build authentication system"
  └─ Blocked by:
      ├─ "Design database schema" (ACTIVE)
      │   └─ Blocked by:
      │       └─ "Choose database" (COMPLETED ✓)
      └─ "Set up dev environment" (COMPLETED ✓)
```

**Display options**:
- Show for individual task (context menu in Task List: "Show Dependencies")
- Show for all blocked tasks (menu item: View → Dependency Graph)
- Export to text file for documentation

**Algorithm**:
```python
def build_dependency_tree(task_id: int, depth: int = 0, visited: Set[int] = None) -> str:
    """
    Recursively build text tree of dependencies.

    Args:
        task_id: Root task to visualize
        depth: Current depth (for indentation)
        visited: Set of visited task IDs (prevent infinite loops)

    Returns:
        Multi-line string with tree structure
    """
    # Get task
    # Check if visited (circular detection)
    # Build current line with indentation
    # Recursively process blocking tasks
    # Return formatted tree
```

**UI Integration**:
- Add menu item: View → Show Dependency Graph → For Current Task
- Add context menu in Task List: "Show Dependency Graph"
- Display in modal dialog with read-only text view

---

### Feature B: Postpone Analytics Dashboard

**File**: [src/ui/analytics_view.py](src/ui/analytics_view.py) (NEW)

**Purpose**: Show statistics about postpone patterns to help users identify issues

**Metrics to display**:

1. **Postpone Reason Breakdown** (Pie chart or bar chart):
   - Count by PostponeReasonType
   - Shows which reasons are most common

2. **Most Postponed Tasks** (Table):
   - Task title | Postpone count | Last reason | Last date
   - Sorted by count descending
   - Limited to top 10

3. **Recent Activity** (List):
   - Last 20 postpone events
   - Format: "[Date] [Task] - [Reason] → [Action Taken]"

4. **Average Time Between Postpones** (Summary stat):
   - Per task calculation
   - Shows if tasks are in "postpone loops"

**Implementation**:

```python
class AnalyticsView(QWidget):
    """Dashboard showing postpone analytics."""

    def __init__(self, db_connection: DatabaseConnection, parent=None):
        """Initialize analytics view."""
        self.postpone_dao = PostponeHistoryDAO(db_connection.get_connection())
        self.task_dao = TaskDAO(db_connection.get_connection())
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        """Create UI layout with sections for each metric."""
        # Create tab widget or sectioned layout
        # Section 1: Reason breakdown (bar chart using ASCII or simple QTableWidget)
        # Section 2: Most postponed tasks table
        # Section 3: Recent activity list
        # Section 4: Summary statistics

    def _load_data(self):
        """Load and calculate analytics."""
        # Query postpone_history for all records (or last N days)
        # Calculate statistics
        # Populate UI widgets

    def _calculate_reason_breakdown(self) -> Dict[str, int]:
        """Count postpones by reason type."""
        # Query all recent postpones
        # Group by reason_type
        # Return counts

    def _get_most_postponed_tasks(self, limit: int = 10) -> List[Dict]:
        """Get tasks postponed most frequently."""
        # Query postpone_history
        # Group by task_id, count
        # Join with tasks to get titles
        # Sort by count DESC, limit
```

**UI Integration**:
- Add menu item: View → Analytics Dashboard
- Add toolbar button (chart icon)
- Display in new tab or modal dialog

---

### Feature C: Smart Postpone Suggestions

**File**: [src/services/postpone_suggestion_service.py](src/services/postpone_suggestion_service.py) (NEW)

**Purpose**: Analyze postpone patterns and suggest actions

**Suggestion triggers**:

1. **Repeated Blocker Reason** (3+ times, same task):
   - Message: "You've postponed '[Task]' 3 times for 'blocker'. Would you like to create a dedicated blocker task?"
   - Action: Open blocker creation dialog pre-filled

2. **Repeated Dependency Reason** (3+ times, same task):
   - Message: "This task has been waiting on dependencies for 2 weeks. Review if dependencies are still relevant?"
   - Action: Open dependency selection dialog to review/remove

3. **Repeated Subtask Reason** (2+ times, same task):
   - Message: "You've indicated this task needs breaking down twice. Would you like to break it into subtasks now?"
   - Action: Open subtask breakdown dialog

4. **Stale Postpones** (task postponed >10 times):
   - Message: "This task has been postponed 12 times. Consider moving to Someday/Maybe or Trash?"
   - Action: Offer quick buttons for Someday or Trash

**Implementation**:

```python
class PostponeSuggestionService:
    """Analyzes postpone patterns and generates suggestions."""

    def __init__(self, db_connection: DatabaseConnection):
        self.postpone_dao = PostponeHistoryDAO(db_connection.get_connection())
        self.task_dao = TaskDAO(db_connection.get_connection())

    def get_suggestions_for_task(self, task_id: int) -> List[Dict[str, Any]]:
        """
        Analyze task's postpone history and return suggestions.

        Returns:
            List of suggestion dictionaries:
            {
                'type': 'repeated_blocker' | 'repeated_dependency' | 'stale',
                'message': str (user-facing message),
                'action': str (action identifier),
                'priority': 'high' | 'medium' | 'low'
            }
        """
        # Get postpone history for task
        # Analyze patterns
        # Generate suggestions based on triggers
        # Return sorted by priority

    def _analyze_reason_repetition(self, history: List[PostponeRecord]) -> Dict:
        """Check for repeated reasons."""
        # Count by reason_type
        # Check for thresholds (3+ blocker, 3+ dependency, 2+ subtasks)
        # Return analysis dict

    def _calculate_stale_score(self, history: List[PostponeRecord]) -> int:
        """Calculate how "stale" a task is based on postpone count."""
        return len(history)
```

**UI Integration**:

Show suggestions in two places:

1. **In Postpone Dialog** (before user selects reason):
   - If suggestions exist, show info box at top:
     ```
     ⚠️ Suggestion: You've postponed this task 3 times for 'blocker'.
     Would you like to create a blocker task now?
     [Yes, Create Blocker] [No, Continue]
     ```

2. **In Task Detail View** (when viewing task in Task List):
   - Show suggestions in side panel or banner
   - Allow user to dismiss or act on suggestions

**Example integration in PostponeDialog**:

```python
def __init__(self, task: Task, ...):
    # ... existing init ...
    self.suggestion_service = PostponeSuggestionService(db_connection)
    self._show_suggestions()

def _show_suggestions(self):
    """Display smart suggestions if any."""
    suggestions = self.suggestion_service.get_suggestions_for_task(self.task.id)
    if suggestions:
        # Show info box with top suggestion
        # Add "Act on Suggestion" button
```

---

## Risk Assessment

**High Risk** → Mitigation:
- Workflow chaining complexity → Use service layer with clear interfaces
- UI state management → Sequential dialog flow

**Medium Risk** → Mitigation:
- Circular dependency edge cases → Already handled by DependencyDAO
- Transaction failures → Add explicit rollback logic

**Low Risk**:
- Performance (existing indexes sufficient)
- UI confusion (clear labels and confirmations)
