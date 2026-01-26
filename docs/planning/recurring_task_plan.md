# Recurring Task Implementation Plan

## Overview
Add recurring task functionality to OneTaskAtATime that:
- Shows only the CURRENT instance in Task List (no clutter)
- Creates next occurrence ON COMPLETION of current instance
- Supports CUSTOM/ADVANCED recurrence patterns
- Offers CONFIGURABLE Elo handling (shared vs independent per task)

## Design Principles
- Preserve single-task focus philosophy
- Keep flat task structure (no hierarchies)
- Minimal UI clutter
- Each recurring task is a separate Task instance linked by series ID

---

## Implementation Steps

### Phase 1: Data Model & Schema

#### 1.1 Add Recurrence Fields to Task Model
**File:** [src/models/task.py](../../src/models/task.py)

Add fields to `Task` dataclass (after line 81):
```python
# Recurrence fields
is_recurring: bool = False
recurrence_pattern: Optional[str] = None  # JSON string
recurrence_parent_id: Optional[int] = None  # Series anchor
share_elo_rating: bool = False  # Configurable Elo sharing
shared_elo_rating: Optional[float] = None  # Shared pool if enabled
shared_comparison_count: Optional[int] = None  # Shared count
recurrence_end_date: Optional[date] = None  # Optional stop date
occurrence_count: int = 0  # Tracks iteration number
```

#### 1.2 Create RecurrencePattern Model
**File:** [src/models/recurrence_pattern.py](../../src/models/recurrence_pattern.py) (NEW)

Define structured pattern model with types:
- `RecurrenceType` enum: DAILY, WEEKLY, MONTHLY, YEARLY, CUSTOM
- `RecurrencePattern` dataclass with fields:
  - `type`: Pattern type
  - `interval`: Every N days/weeks/months
  - `days_of_week`: For weekly (list of 0-6)
  - `day_of_month`: For monthly (1-31)
  - `week_of_month`: For monthly Nth weekday patterns
  - `weekday_of_month`: Day of week for Nth patterns
  - `custom_expression`: Cron-like or natural language
- Methods:
  - `to_json()`: Serialize for database
  - `from_json()`: Deserialize from database
  - `calculate_next_date(from_date)`: Core date calculation

**Pattern Examples:**
- Daily: `{"type": "daily", "interval": 1}`
- Every 2 weeks on Tuesday: `{"type": "weekly", "interval": 2, "days_of_week": [1]}`
- Monthly on 15th: `{"type": "monthly", "interval": 1, "day_of_month": 15}`
- Quarterly: `{"type": "monthly", "interval": 3, "day_of_month": 1}`

#### 1.3 Update Database Schema
**File:** [src/database/schema.py](../../src/database/schema.py)

Add columns to tasks table (in `get_create_tables_sql()`):
```sql
is_recurring INTEGER DEFAULT 0,
recurrence_pattern TEXT,
recurrence_parent_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
share_elo_rating INTEGER DEFAULT 0,
shared_elo_rating REAL,
shared_comparison_count INTEGER,
recurrence_end_date DATE,
occurrence_count INTEGER DEFAULT 0
```

Add indexes:
```sql
CREATE INDEX IF NOT EXISTS idx_tasks_is_recurring ON tasks(is_recurring);
CREATE INDEX IF NOT EXISTS idx_tasks_recurrence_parent ON tasks(recurrence_parent_id);
```

Create migration method:
```python
@staticmethod
def migrate_to_recurring_tasks(db_connection: sqlite3.Connection) -> None:
    """Add recurring task columns to existing database."""
```

#### 1.4 Update TaskDAO
**File:** [src/database/task_dao.py](../../src/database/task_dao.py)

Update all CRUD methods to handle new fields:
- Add recurrence fields to INSERT statements
- Add recurrence fields to SELECT mapping
- Add recurrence fields to UPDATE statements

---

### Phase 2: Recurrence Logic

#### 2.1 Create RecurrenceService
**File:** [src/services/recurrence_service.py](../../src/services/recurrence_service.py) (NEW)

Core service with method:
```python
def calculate_next_occurrence_date(pattern: RecurrencePattern, from_date: date) -> date:
    """Calculate next date based on pattern type."""
```

Logic for each type:
- **DAILY**: `from_date + timedelta(days=interval)`
- **WEEKLY**: Add weeks, adjust to target weekday
- **MONTHLY**: Use `dateutil.relativedelta` for month arithmetic
  - Support "Nth weekday" patterns (e.g., 2nd Tuesday)
- **YEARLY**: Add years
- **CUSTOM**: Parse cron-like expression or use library

**Dependency:** Add `python-dateutil` to requirements.txt

#### 2.2 Enhance TaskService.complete_task()
**File:** [src/services/task_service.py](../../src/services/task_service.py)

Modify existing `complete_task()` method (around line 102):
```python
def complete_task(self, task_id: int) -> Optional[Task]:
    """Mark task complete. Generate next occurrence if recurring."""
    task = self.task_dao.get_by_id(task_id)
    if not task:
        return None

    task.mark_completed()
    completed_task = self.task_dao.update(task)

    # NEW: Handle recurring logic
    if task.is_recurring:
        self._generate_next_occurrence(completed_task)

    return completed_task
```

#### 2.3 Add _generate_next_occurrence() Helper
**File:** [src/services/task_service.py](../../src/services/task_service.py)

Add new private method:
```python
def _generate_next_occurrence(self, completed_task: Task) -> Optional[Task]:
    """
    Generate next occurrence of recurring task.

    Steps:
    1. Check if series should end (recurrence_end_date)
    2. Parse recurrence pattern from JSON
    3. Calculate next due date
    4. Clone task with new due date
    5. Handle Elo rating based on share_elo_rating flag:
       - If True: Copy shared_elo_rating from parent
       - If False: Reset to 1500.0 (independent)
    6. Increment occurrence_count
    7. Save new task instance

    Returns newly created task or None if series ended.
    """
```

---

### Phase 3: Elo Synchronization

#### 3.1 Update ComparisonService
**File:** [src/services/comparison_service.py](../../src/services/comparison_service.py)

Modify `record_comparison()` to handle shared Elo:
```python
def record_comparison(self, winner: Task, loser: Task) -> Tuple[Task, Task]:
    """Record comparison and update Elo ratings."""
    # ... existing Elo calculation ...

    # NEW: If share_elo_rating=True, update shared pool
    if winner.share_elo_rating:
        winner.shared_elo_rating = winner.elo_rating
        winner.shared_comparison_count = winner.comparison_count

        # Update parent's shared pool
        if winner.recurrence_parent_id:
            parent = self.task_dao.get_by_id(winner.recurrence_parent_id)
            if parent:
                parent.shared_elo_rating = winner.elo_rating
                parent.shared_comparison_count = winner.comparison_count
                self.task_dao.update(parent)

    # Same for loser...
```

---

### Phase 4: UI Implementation

#### 4.1 Add Recurrence Section to Task Form
**File:** [src/ui/task_form_enhanced.py](../../src/ui/task_form_enhanced.py)

After "Priority & Urgency" group (around line 200), add:
```python
# === Recurrence ===
recurrence_group = QGroupBox("Recurrence")
recurrence_layout = QFormLayout()

# Enable recurrence checkbox
self.is_recurring_check = QCheckBox("Make this a recurring task")
self.is_recurring_check.stateChanged.connect(self._on_recurring_toggled)

# Pattern type selector
self.recurrence_type_combo = QComboBox()
# Items: Daily, Weekly, Monthly, Yearly, Custom...

# Interval spinner (every N days/weeks/months)
self.recurrence_interval_spin = QSpinBox()

# Advanced pattern button (opens dialog)
self.recurrence_details_btn = QPushButton("Advanced Pattern...")
self.recurrence_details_btn.clicked.connect(self._on_recurrence_details_clicked)

# Elo sharing checkbox
self.share_elo_check = QCheckBox("Share priority rating across all occurrences")

# End date (optional)
self.has_recurrence_end_check = QCheckBox("Stop recurring after")
self.recurrence_end_date_edit = QLineEdit()  # YYYY-MM-DD
self.recurrence_end_calendar_btn = QPushButton("📅")
```

Event handlers:
- `_on_recurring_toggled()`: Enable/disable controls, validate due date exists
- `_on_recurrence_type_changed()`: Update interval label (day/week/month)
- `_on_recurrence_details_clicked()`: Open advanced pattern dialog
- `_on_recurrence_end_toggled()`: Enable/disable end date field

Validation:
- Recurring tasks MUST have due date
- End date must be after due date

#### 4.2 Create Advanced Pattern Dialog
**File:** [src/ui/recurrence_pattern_dialog.py](../../src/ui/recurrence_pattern_dialog.py) (NEW)

Modal dialog for complex patterns:
- **Weekly tab**: Checkboxes for Mon-Sun selection
- **Monthly tab**: Radio buttons for:
  - "Day of month" (1-31)
  - "Nth weekday" (e.g., 2nd Tuesday)
- **Custom tab**: Text field for cron-like expression with validation
- **Preview**: Show next 5 occurrence dates

Methods:
- `_init_ui()`: Create tabs and controls
- `get_pattern()`: Build RecurrencePattern from UI
- `_load_pattern()`: Populate UI from existing pattern

#### 4.3 Add Recurrence Indicator Column in Task List
**File:** [src/ui/task_list_view.py](../../src/ui/task_list_view.py)

Add a dedicated "Recurring" column (early in column order, before Title):
- Display 🔁 symbol for recurring tasks, empty for non-recurring
- Add tooltip on hover showing recurrence pattern in human-readable format
  - Examples:
    - "Every 2 days"
    - "Every week on Tuesday"
    - "Monthly on the 15th"
    - "Every 3 months on the 1st"
    - "Custom pattern: [expression]"
- Parse pattern from JSON and generate readable string

Helper method to add:
```python
def _format_recurrence_pattern(pattern_json: str) -> str:
    """Convert JSON pattern to human-readable string for tooltip."""
    pattern = RecurrencePattern.from_json(pattern_json)

    if pattern.type == RecurrenceType.DAILY:
        return f"Every {pattern.interval} day(s)"
    elif pattern.type == RecurrenceType.WEEKLY:
        days = [DAY_NAMES[d] for d in pattern.days_of_week]
        return f"Every {pattern.interval} week(s) on {', '.join(days)}"
    elif pattern.type == RecurrenceType.MONTHLY:
        if pattern.day_of_month:
            return f"Monthly on the {pattern.day_of_month}th"
        else:
            return f"Monthly on {pattern.week_of_month}th {WEEKDAY_NAMES[pattern.weekday_of_month]}"
    elif pattern.type == RecurrenceType.YEARLY:
        return f"Every {pattern.interval} year(s)"
    else:
        return f"Custom pattern: {pattern.custom_expression}"
```

Column configuration:
- Width: Fixed narrow width (40-50px) to fit symbol
- Alignment: Center
- Sort: Allow sorting to group recurring tasks together

---

### Phase 5: Edit & Delete Handling

#### 5.1 Add Edit Scope Dialog
**File:** [src/ui/edit_scope_dialog.py](../../src/ui/edit_scope_dialog.py) (NEW)

When editing a recurring task, ask user:
- "Edit only this occurrence" → Break from series
- "Edit this and future occurrences" → Update parent pattern
- "Edit all occurrences" → Update all tasks in series

#### 5.2 Add Delete Scope Dialog
**File:** [src/ui/delete_scope_dialog.py](../../src/ui/delete_scope_dialog.py) (NEW)

When deleting a recurring task, ask user:
- "Delete only this occurrence"
- "Delete entire recurring series"

#### 5.3 Update TaskService Methods
**File:** [src/services/task_service.py](../../src/services/task_service.py)

Add methods:
```python
def update_recurring_task(task: Task, edit_scope: str) -> Task:
    """Update recurring task with scope: 'this' | 'future' | 'all'."""

def delete_recurring_task(task_id: int, delete_scope: str) -> bool:
    """Delete recurring task with scope: 'this' | 'series'."""
```

---

### Phase 6: Testing

#### 6.1 Unit Tests
**File:** [tests/test_recurrence_service.py](../../tests/test_recurrence_service.py) (NEW)

Test date calculations:
- Daily patterns (every 1, 2, 7 days)
- Weekly patterns (specific days, multiple days)
- Monthly patterns (day of month, Nth weekday)
- Edge cases (month boundaries, leap years, Feb 29)

#### 6.2 Integration Tests
**File:** [tests/test_recurring_task_flow.py](../../tests/test_recurring_task_flow.py) (NEW)

Test workflows:
- Create recurring task → Complete → Verify next created
- Complete with shared Elo → Verify Elo transferred
- Complete with independent Elo → Verify reset to 1500
- Edit task with different scopes
- Delete task with different scopes
- End date stopping recurrence

---

## Critical Files Summary

| File | Change Type | Description |
|------|-------------|-------------|
| [src/models/task.py](../../src/models/task.py) | Modify | Add 8 recurrence fields to Task dataclass |
| [src/models/recurrence_pattern.py](../../src/models/recurrence_pattern.py) | Create | Define RecurrencePattern model with JSON serialization |
| [src/database/schema.py](../../src/database/schema.py) | Modify | Add 8 columns + 2 indexes, create migration |
| [src/database/task_dao.py](../../src/database/task_dao.py) | Modify | Update CRUD to handle new fields |
| [src/services/recurrence_service.py](../../src/services/recurrence_service.py) | Create | Core date calculation logic |
| [src/services/task_service.py](../../src/services/task_service.py) | Modify | Add recurrence generation on completion |
| [src/services/comparison_service.py](../../src/services/comparison_service.py) | Modify | Sync shared Elo across series |
| [src/ui/task_form_enhanced.py](../../src/ui/task_form_enhanced.py) | Modify | Add recurrence controls section |
| [src/ui/recurrence_pattern_dialog.py](../../src/ui/recurrence_pattern_dialog.py) | Create | Advanced pattern configuration dialog |
| [src/ui/task_list_view.py](../../src/ui/task_list_view.py) | Modify | Add 🔁 icon for recurring tasks |
| [src/ui/edit_scope_dialog.py](../../src/ui/edit_scope_dialog.py) | Create | Edit scope selector (this/future/all) |
| [src/ui/delete_scope_dialog.py](../../src/ui/delete_scope_dialog.py) | Create | Delete scope selector (this/series) |
| [tests/test_recurrence_service.py](../../tests/test_recurrence_service.py) | Create | Unit tests for date calculations |
| [tests/test_recurring_task_flow.py](../../tests/test_recurring_task_flow.py) | Create | Integration tests for workflows |

---

## Edge Cases Handled

1. **No due date:** Recurring checkbox disabled unless due date set
2. **End date validation:** Must be after due date
3. **Late completion:** Next occurrence calculated from completion date (not original due date)
4. **Series ended:** No new occurrence if past recurrence_end_date
5. **Parent deleted:** ON DELETE CASCADE removes all child occurrences
6. **Elo synchronization:** Shared pool updated atomically across comparisons
7. **Edit break-away:** "Edit only this" sets is_recurring=False

---

## Dependencies

Add to `requirements.txt`:
```
python-dateutil>=2.8.0  # For robust month/year arithmetic
```

Optional (for custom patterns):
```
python-crontab>=2.6.0  # For cron expression parsing
```

---

## User Experience Flow

### Creating a Recurring Task
1. User creates task with due date
2. Checks "Make this a recurring task"
3. Selects pattern type (Daily/Weekly/Monthly/Custom)
4. Configures interval (e.g., every 2 weeks)
5. Clicks "Advanced Pattern..." for complex rules
6. Chooses Elo sharing preference
7. Optionally sets end date
8. Saves task

### Completing a Recurring Task
1. User marks current instance complete in Focus Mode
2. System immediately creates next occurrence with:
   - New due date calculated from pattern
   - Same title, description, priority, context, tags
   - Elo rating: shared pool OR reset to 1500
   - Incremented occurrence_count
3. Next occurrence appears in Task List (current instance moves to completed)

### Editing a Recurring Task
1. User opens recurring task for editing
2. Dialog asks: "Edit this / this + future / all occurrences?"
3. Changes applied per scope
4. If "this only," task breaks away from series

### Deleting a Recurring Task
1. User deletes recurring task
2. Dialog asks: "Delete this occurrence / entire series?"
3. Deletion applied per scope

---

## Future Enhancements (Out of Scope)

- Skip specific dates (holidays)
- Reminder notifications before next occurrence
- Recurrence templates library
- Completion rate analytics
- Flexible anchor (due date vs completion date toggle)
