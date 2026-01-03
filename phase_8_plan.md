# Phase 8: Polish & UX - Implementation Plan

## Executive Summary

Phase 8 transforms OneTaskAtATime from a feature-complete application into a production-ready, user-friendly desktop tool with professional UX polish. This phase adds:

1. **Comprehensive Task History** - Full audit log of all task changes with timeline view
2. **Enhanced Error Handling** - User-friendly error messages with recovery suggestions
3. **WCAG 2.1 AA Accessibility** - Full compliance with screen reader support, keyboard navigation, contrast ratios
4. **Keyboard Shortcuts** - Focus Mode action shortcuts (Complete, Defer, Delegate, etc.)
5. **Onboarding Flow** - First-time user tutorial and guided setup
6. **Help System** - Context-sensitive help, tooltips, and keyboard shortcut reference
7. **Undo/Redo System** - Basic undo for critical actions with Ctrl+Z/Ctrl+Y

**User-Confirmed Priorities:**
- ✅ Error handling and UX accessibility (highest priority)
- ✅ WCAG 2.1 AA compliance (full accessibility audit)
- ✅ Comprehensive audit log (complete task history)

**Total Estimated Effort**: 20-25 days

---

## Architecture Overview

### Current State
- **UI Components**: 20+ dialogs, Focus Mode, Task List, Settings (6 tabs)
- **Keyboard Shortcuts**: 9 shortcuts implemented (Ctrl+N, Ctrl+F, Ctrl+L, F5, etc.)
- **Error Handling**: Basic try-catch with QMessageBox warnings (181 occurrences)
- **History Tracking**: Postpone history and comparison history (analytics only)
- **Help System**: Menu status tips and placeholder text only
- **Accessibility**: Relies on PyQt5 defaults (no explicit ARIA-like labels)

### What's Being Added
- **Task History System**: TaskHistoryService, TaskHistoryDAO, history_events table
- **Undo/Redo Framework**: CommandPattern implementation with UndoStack
- **Accessibility Layer**: AccessibilityService with WCAG 2.1 AA compliance
- **Help System**: HelpDialog, TooltipManager, keyboard shortcut cheatsheet
- **Onboarding System**: WelcomeWizard, FirstRunDetector, interactive tutorial
- **Enhanced Error Handler**: ErrorService with context-aware recovery suggestions
- **6 Focus Mode Shortcuts**: Ctrl+Shift+C, Ctrl+D, Ctrl+Shift+D, Ctrl+M, Ctrl+Shift+T, Ctrl+Delete

---

## Implementation Plan

### STEP 1: Task History & Audit Log (5-6 days)

#### 1.1 Data Model & Database

**Create TaskHistoryEvent Model** - [src/models/task_history_event.py](src/models/task_history_event.py) (NEW ~80 lines)

```python
@dataclass
class TaskHistoryEvent:
    id: Optional[int] = None
    task_id: int
    event_type: TaskEventType  # Enum
    event_timestamp: datetime = field(default_factory=datetime.now)
    old_value: Optional[str] = None  # JSON serialized
    new_value: Optional[str] = None  # JSON serialized
    changed_by: str = "user"  # user, system, scheduler
    context_data: Optional[str] = None  # Additional metadata
```

**Create TaskEventType Enum** - [src/models/task_state.py](src/models/task_state.py) (MODIFY +25 lines)

```python
class TaskEventType(Enum):
    CREATED = "created"
    EDITED = "edited"
    COMPLETED = "completed"
    DEFERRED = "deferred"
    DELEGATED = "delegated"
    ACTIVATED = "activated"
    MOVED_TO_SOMEDAY = "moved_to_someday"
    MOVED_TO_TRASH = "moved_to_trash"
    RESTORED = "restored"
    PRIORITY_CHANGED = "priority_changed"
    DUE_DATE_CHANGED = "due_date_changed"
    DEPENDENCY_ADDED = "dependency_added"
    DEPENDENCY_REMOVED = "dependency_removed"
    TAG_ADDED = "tag_added"
    TAG_REMOVED = "tag_removed"
    CONTEXT_CHANGED = "context_changed"
    COMPARISON_WON = "comparison_won"
    COMPARISON_LOST = "comparison_lost"
```

**Add Database Table** - [src/database/schema.py](src/database/schema.py) (MODIFY +20 lines)

```sql
CREATE TABLE IF NOT EXISTS task_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    event_type TEXT NOT NULL CHECK(event_type IN (
        'created', 'edited', 'completed', 'deferred', 'delegated',
        'activated', 'moved_to_someday', 'moved_to_trash', 'restored',
        'priority_changed', 'due_date_changed', 'dependency_added',
        'dependency_removed', 'tag_added', 'tag_removed',
        'context_changed', 'comparison_won', 'comparison_lost'
    )),
    event_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    old_value TEXT,  -- JSON serialized
    new_value TEXT,  -- JSON serialized
    changed_by TEXT DEFAULT 'user',
    context_data TEXT,  -- Additional metadata
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_task_history_task_id
    ON task_history(task_id);
CREATE INDEX IF NOT EXISTS idx_task_history_timestamp
    ON task_history(event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_task_history_type
    ON task_history(event_type);
```

#### 1.2 Data Access Layer

**Create TaskHistoryDAO** - [src/database/task_history_dao.py](src/database/task_history_dao.py) (NEW ~200 lines)

**Key Methods**:
```python
class TaskHistoryDAO:
    def create_event(self, event: TaskHistoryEvent) -> TaskHistoryEvent
    def get_by_task_id(self, task_id: int, limit: int = 100) -> List[TaskHistoryEvent]
    def get_recent(self, limit: int = 50) -> List[TaskHistoryEvent]
    def get_by_type(self, event_type: TaskEventType) -> List[TaskHistoryEvent]
    def get_date_range(self, start: date, end: date) -> List[TaskHistoryEvent]
    def delete_by_task_id(self, task_id: int) -> bool
    def get_count_by_task(self, task_id: int) -> int
```

#### 1.3 Task History Service

**Create TaskHistoryService** - [src/services/task_history_service.py](src/services/task_history_service.py) (NEW ~300 lines)

**Core Methods**:
```python
class TaskHistoryService:
    def record_task_created(self, task: Task) -> None
    def record_task_edited(self, task: Task, old_task: Task) -> None
    def record_state_change(self, task: Task, old_state: TaskState, new_state: TaskState) -> None
    def record_priority_change(self, task: Task, old_priority: int, new_priority: int) -> None
    def record_due_date_change(self, task: Task, old_date: Optional[date], new_date: Optional[date]) -> None
    def record_dependency_added(self, task_id: int, dependency_id: int) -> None
    def record_tag_change(self, task_id: int, tag_name: str, added: bool) -> None
    def record_comparison_result(self, task_id: int, won: bool, opponent_id: int) -> None

    def get_timeline(self, task_id: int) -> List[TaskHistoryEvent]
    def get_formatted_summary(self, event: TaskHistoryEvent) -> str
```

**Helper Methods**:
```python
def _serialize_task_snapshot(self, task: Task) -> str:
    """Serialize task to JSON for old_value/new_value"""

def _format_event_message(self, event: TaskHistoryEvent) -> str:
    """Format event as human-readable message"""
    # Examples:
    # "Task created with priority High"
    # "State changed from Active to Deferred"
    # "Due date changed from 2025-01-15 to 2025-01-20"
```

#### 1.4 Integration Points

**Modify TaskDAO** - [src/database/task_dao.py](src/database/task_dao.py) (MODIFY +40 lines)

Add history recording to all mutation methods:
```python
def create(self, task: Task) -> Task:
    # ... existing code ...
    self.history_service.record_task_created(created_task)
    return created_task

def update(self, task: Task) -> bool:
    old_task = self.get_by_id(task.id)
    # ... existing code ...
    self.history_service.record_task_edited(task, old_task)
    return success
```

**Modify MainWindow Handlers** - [src/ui/main_window.py](src/ui/main_window.py) (MODIFY +20 lines)

Add history recording for all task actions:
- `_handle_complete_task()`: Record completion event
- `_handle_defer_task()`: Record deferral event
- `_handle_delegate_task()`: Record delegation event
- `_handle_someday_task()`: Record state change event

#### 1.5 Task History UI

**Create TaskHistoryDialog** - [src/ui/task_history_dialog.py](src/ui/task_history_dialog.py) (NEW ~350 lines)

**Design**:
- Dialog title: "Task History: [Task Title]"
- Timeline view (QTreeWidget or custom widget with vertical line)
- Group by date (Today, Yesterday, This Week, Older)
- Each event shows:
  - Icon (based on event type)
  - Timestamp (relative: "5 minutes ago", absolute on hover)
  - Event description (formatted message)
  - Changed by (user/system/scheduler)
  - Expand to see old/new values (diff view for edits)

**Layout**:
```
┌─────────────────────────────────────────┐
│ Task History: Implement authentication  │
├─────────────────────────────────────────┤
│ [Filter: All Events ▼]  [Export...]     │
├─────────────────────────────────────────┤
│ Today                                    │
│ ● 10:45 AM - Priority changed            │
│   │ From: Medium → To: High              │
│   │ Changed by: user                     │
│                                           │
│ ● 9:30 AM - Task edited                  │
│   │ Description updated                  │
│   │ [Show diff]                          │
│                                           │
│ Yesterday                                │
│ ● 3:15 PM - Postponed (Deferred)         │
│   │ Reason: Blocked by dependency        │
│   │ Start date: 2025-01-10               │
│                                           │
│ ● 11:00 AM - Task created                │
│   │ Priority: Medium, Due: 2025-01-15    │
└─────────────────────────────────────────┘
```

**Add Menu Item** - [src/ui/main_window.py](src/ui/main_window.py) (MODIFY +10 lines)

In context menu for tasks (right-click in Task List):
```python
history_action = QAction("View &History...", self)
history_action.setShortcut("Ctrl+H")
history_action.triggered.connect(self._show_task_history)
```

---

### STEP 2: Enhanced Error Handling (3-4 days)

#### 2.1 Error Handling Service

**Create ErrorService** - [src/services/error_service.py](src/services/error_service.py) (NEW ~400 lines)

**Core Classes**:
```python
@dataclass
class ErrorContext:
    error: Exception
    operation: str  # "export_data", "complete_task", etc.
    user_action: str  # "completing task", "exporting data"
    recovery_suggestions: List[str]
    severity: ErrorSeverity  # INFO, WARNING, ERROR, CRITICAL
    can_retry: bool = False
    tech_details: Optional[str] = None

class ErrorSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ErrorService(QObject):
    error_occurred = pyqtSignal(ErrorContext)

    def handle_error(self, error: Exception, operation: str,
                    user_action: str, parent_widget: QWidget = None) -> None:
        """Handle error with context-aware messaging"""
        context = self._build_error_context(error, operation, user_action)
        self._show_error_dialog(context, parent_widget)
        self._log_error(context)
        self.error_occurred.emit(context)

    def _build_error_context(self, error: Exception,
                            operation: str, user_action: str) -> ErrorContext:
        """Build error context with recovery suggestions"""

    def _get_recovery_suggestions(self, error: Exception,
                                  operation: str) -> List[str]:
        """Get context-specific recovery suggestions"""
        # Examples based on error type and operation:
        # FileNotFoundError + export: ["Check file path", "Ensure directory exists"]
        # PermissionError + import: ["Run as administrator", "Check file permissions"]
        # DatabaseError + complete_task: ["Restart application", "Check database integrity"]
```

**Recovery Suggestion Mapping**:
```python
ERROR_RECOVERY_MAP = {
    ("export_data", FileNotFoundError): [
        "Verify the export directory exists",
        "Try selecting a different location",
        "Check disk space availability"
    ],
    ("import_data", ValueError): [
        "Verify JSON file format is valid",
        "Check schema version compatibility",
        "Try exporting from the source again"
    ],
    ("complete_task", sqlite3.OperationalError): [
        "Restart the application",
        "Run database integrity check",
        "Restore from recent backup if issue persists"
    ],
    # ... 20+ operation-error pairs
}
```

#### 2.2 Enhanced Error Dialog

**Create EnhancedErrorDialog** - [src/ui/enhanced_error_dialog.py](src/ui/enhanced_error_dialog.py) (NEW ~300 lines)

**Design**:
- Severity-based icon (⚠️ WARNING, ❌ ERROR, 🔴 CRITICAL)
- User-friendly message (no stack traces visible by default)
- Recovery suggestions as actionable bullet points
- "Show Technical Details" expandable section
- Action buttons: Retry (if can_retry), Help, Copy Error, Close

**Layout**:
```
┌─────────────────────────────────────────┐
│ ❌ Error Completing Task                │
├─────────────────────────────────────────┤
│ We couldn't complete the task due to a  │
│ database error.                          │
│                                           │
│ What you can try:                        │
│ • Restart the application                │
│ • Check database integrity in Tools menu │
│ • Restore from recent backup             │
│                                           │
│ ▸ Show Technical Details                │
│                                           │
│        [Retry]  [Help]  [Copy Error]  [Close] │
└─────────────────────────────────────────┘
```

#### 2.3 Integration

**Modify All Services** - Wrap critical operations:
- [src/services/export_service.py](src/services/export_service.py) (MODIFY +30 lines)
- [src/services/import_service.py](src/services/import_service.py) (MODIFY +30 lines)
- [src/services/comparison_service.py](src/services/comparison_service.py) (MODIFY +20 lines)
- [src/services/resurfacing_scheduler.py](src/services/resurfacing_scheduler.py) (MODIFY +25 lines)

**Pattern**:
```python
try:
    # ... operation ...
except Exception as e:
    self.error_service.handle_error(
        e,
        operation="export_data",
        user_action="exporting your tasks to JSON",
        parent_widget=self
    )
    return {"success": False, "error": str(e)}
```

**Add Error Recovery Menu** - [src/ui/main_window.py](src/ui/main_window.py) (MODIFY +20 lines)

In Tools menu:
```python
check_db_action = QAction("Check Database Integrity", self)
check_db_action.triggered.connect(self._check_database_integrity)

view_logs_action = QAction("View Error Logs...", self)
view_logs_action.triggered.connect(self._view_error_logs)
```

---

### STEP 3: WCAG 2.1 AA Accessibility Compliance (6-7 days)

#### 3.1 Accessibility Service Foundation

**Create AccessibilityService** - [src/services/accessibility_service.py](src/services/accessibility_service.py) (NEW ~350 lines)

**Purpose**: Centralized accessibility management and WCAG compliance

**Key Methods**:
```python
class AccessibilityService:
    def apply_accessible_labels(self, widget: QWidget) -> None:
        """Apply accessible names and descriptions to widget tree"""

    def verify_contrast_ratios(self) -> List[ContrastIssue]:
        """Check all color combinations meet WCAG AA standards (4.5:1)"""

    def configure_keyboard_navigation(self, window: QMainWindow) -> None:
        """Set tab order and keyboard navigation paths"""

    def add_keyboard_hints(self, widget: QWidget) -> None:
        """Add keyboard shortcut hints to tooltips"""

    def announce_to_screen_reader(self, message: str, priority: str = "polite") -> None:
        """Announce message to screen readers (ARIA-like live regions)"""
```

#### 3.2 Widget Accessibility Enhancement

**Modify All UI Components** - Add accessible labels:

**FocusModeWidget** - [src/ui/focus_mode.py](src/ui/focus_mode.py) (MODIFY +60 lines)

```python
# Add accessible names
self.task_title_label.setAccessibleName("Current task title")
self.task_description.setAccessibleName("Task description")
self.complete_button.setAccessibleName("Mark task as complete")
self.complete_button.setAccessibleDescription(
    "Marks the current task as completed and moves to next task. Keyboard shortcut: Ctrl+Shift+C"
)

# Set accessible role
self.card_frame.setAccessibleName("Task card")
self.card_frame.setAccessibleDescription("Contains current task information and action buttons")

# Add ARIA-like live region announcements
def set_task(self, task: Optional[Task]):
    self._current_task = task
    if task:
        self.accessibility_service.announce_to_screen_reader(
            f"Now focusing on: {task.title}. Priority: {task.get_priority_enum().name}",
            priority="assertive"
        )
```

**TaskListView** - [src/ui/task_list_view.py](src/ui/task_list_view.py) (MODIFY +40 lines)

```python
# Table accessibility
self.task_table.setAccessibleName("Task list table")
self.task_table.setAccessibleDescription(
    "Sortable table of all tasks. Use arrow keys to navigate, Enter to edit, Space to select."
)

# Column headers
for col_idx, header in enumerate(self.headers):
    self.task_table.horizontalHeaderItem(col_idx).setAccessibleName(
        f"{header} column header. Click to sort."
    )
```

**All Dialogs** - Add to each dialog's `__init__`:
```python
self.accessibility_service.apply_accessible_labels(self)
self.accessibility_service.configure_keyboard_navigation(self)
```

#### 3.3 Keyboard Navigation

**Create KeyboardNavigationManager** - [src/services/keyboard_navigation_manager.py](src/services/keyboard_navigation_manager.py) (NEW ~200 lines)

**Features**:
- Define explicit tab order for all dialogs
- Skip disabled/hidden widgets
- Add focus indicators (visible outline)
- Handle Esc/Enter keys consistently
- Arrow key navigation for lists/tables

**Implementation**:
```python
class KeyboardNavigationManager:
    def configure_dialog(self, dialog: QDialog) -> None:
        """Set tab order and focus handling"""

    def add_focus_indicators(self, widget: QWidget) -> None:
        """Add visible focus outline for keyboard users"""
        # CSS: border: 2px solid #0078D4 when focused

    def enable_list_navigation(self, list_widget: QListWidget) -> None:
        """Enable full keyboard navigation for lists"""
        # Arrow keys, Home, End, Page Up/Down
```

#### 3.4 Color Contrast Compliance

**Create ContrastChecker** - [src/utils/contrast_checker.py](src/utils/contrast_checker.py) (NEW ~150 lines)

**Purpose**: Verify all color combinations meet WCAG AA 4.5:1 ratio

**Color Pairs to Check**:
```python
COLOR_PAIRS = [
    ("text", "background"),
    ("button_text", "button_background"),
    ("link_text", "background"),
    ("disabled_text", "background"),
    ("error_text", "background"),
    ("success_text", "background"),
]
```

**Fix Low-Contrast Issues**:
- Light theme: Ensure dark text (#222222) on light backgrounds (#FFFFFF)
- Dark theme: Ensure light text (#EEEEEE) on dark backgrounds (#2B2B2B)
- Links: Blue (#0066CC) on white passes, adjust if needed
- Disabled: Gray (#757575) minimum

**Update Stylesheets** - [resources/themes/light.qss](resources/themes/light.qss) (MODIFY +20 lines)
- [resources/themes/dark.qss](resources/themes/dark.qss) (MODIFY +20 lines)

```css
/* Light theme - WCAG AA compliant */
QLabel { color: #1A1A1A; }  /* 16:1 ratio on white */
QPushButton {
    color: #1A1A1A;
    background-color: #F5F5F5;
}
QPushButton:disabled {
    color: #757575;  /* 4.6:1 ratio - passes AA */
}

/* Dark theme - WCAG AA compliant */
QLabel { color: #F0F0F0; }  /* 15:1 ratio on #2B2B2B */
QPushButton {
    color: #F0F0F0;
    background-color: #3C3F41;
}
```

#### 3.5 Focus Indicators

**Add Focus Styles** - All stylesheets (MODIFY +30 lines each)

```css
/* Visible focus indicator (WCAG 2.4.7) */
*:focus {
    outline: 2px solid #0078D4;
    outline-offset: 2px;
}

QPushButton:focus {
    border: 2px solid #0078D4;
    background-color: #E5F3FF;  /* Light theme */
}

QLineEdit:focus, QTextEdit:focus {
    border: 2px solid #0078D4;
}
```

#### 3.6 Screen Reader Support

**Add ARIA-like Announcements** - Create live region system:

**Modify MainWindow** - [src/ui/main_window.py](src/ui/main_window.py) (MODIFY +40 lines)

```python
# Add status announcements
def _handle_complete_task(self, task_id: int):
    # ... existing code ...
    self.accessibility_service.announce_to_screen_reader(
        f"Task completed: {task.title}. Moving to next task.",
        priority="assertive"
    )

# Add navigation announcements
def _show_focus_mode(self):
    # ... existing code ...
    self.accessibility_service.announce_to_screen_reader(
        "Switched to Focus Mode",
        priority="polite"
    )
```

#### 3.7 Accessibility Testing & Documentation

**Create Accessibility Test Suite** - [tests/accessibility/test_wcag_compliance.py](tests/accessibility/test_wcag_compliance.py) (NEW ~300 lines)

**Tests**:
```python
def test_all_widgets_have_accessible_names():
    """WCAG 4.1.2 - All widgets have accessible names"""

def test_contrast_ratios_meet_aa():
    """WCAG 1.4.3 - Contrast ratio 4.5:1 minimum"""

def test_keyboard_navigation_complete():
    """WCAG 2.1.1 - All functionality available via keyboard"""

def test_focus_indicators_visible():
    """WCAG 2.4.7 - Focus indicators are visible"""

def test_labels_for_form_inputs():
    """WCAG 3.3.2 - All inputs have associated labels"""

def test_error_messages_accessible():
    """WCAG 3.3.1 - Errors are announced and linked to inputs"""
```

**Create Accessibility Documentation** - [docs/ACCESSIBILITY.md](docs/ACCESSIBILITY.md) (NEW ~200 lines)

Contents:
- WCAG 2.1 AA compliance statement
- Tested assistive technologies (NVDA, JAWS, Narrator)
- Keyboard shortcuts reference
- Known limitations
- Feedback contact

---

### STEP 4: Keyboard Shortcuts & Navigation (2 days)

#### 4.1 Focus Mode Action Shortcuts

**Modify FocusModeWidget** - [src/ui/focus_mode.py](src/ui/focus_mode.py) (MODIFY +80 lines)

**Add Shortcuts**:
```python
def _setup_shortcuts(self):
    """Configure keyboard shortcuts for Focus Mode actions"""

    # Complete: Ctrl+Shift+C
    complete_shortcut = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
    complete_shortcut.activated.connect(self._on_complete_clicked)

    # Defer: Ctrl+D
    defer_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
    defer_shortcut.activated.connect(self._on_defer_clicked)

    # Delegate: Ctrl+Shift+D
    delegate_shortcut = QShortcut(QKeySequence("Ctrl+Shift+D"), self)
    delegate_shortcut.activated.connect(self._on_delegate_clicked)

    # Someday: Ctrl+M (M for "Maybe")
    someday_shortcut = QShortcut(QKeySequence("Ctrl+M"), self)
    someday_shortcut.activated.connect(self._on_someday_clicked)

    # Trash: Ctrl+Delete
    trash_shortcut = QShortcut(QKeySequence("Ctrl+Delete"), self)
    trash_shortcut.activated.connect(self._on_trash_clicked)

    # Edit Task: Ctrl+E (when in Focus Mode)
    edit_shortcut = QShortcut(QKeySequence("Ctrl+Shift+E"), self)
    edit_shortcut.activated.connect(self._on_edit_task)
```

**Update Button Tooltips** - Add shortcut hints:
```python
self.complete_button.setToolTip("Mark as complete (Ctrl+Shift+C)")
self.defer_button.setToolTip("Defer task (Ctrl+D)")
self.delegate_button.setToolTip("Delegate task (Ctrl+Shift+D)")
self.someday_button.setToolTip("Move to Someday/Maybe (Ctrl+M)")
self.trash_button.setToolTip("Move to trash (Ctrl+Delete)")
```

#### 4.2 Global Application Shortcuts

**Add to MainWindow** - [src/ui/main_window.py](src/ui/main_window.py) (MODIFY +40 lines)

**New Shortcuts**:
```python
# Undo: Ctrl+Z (Step 5 prerequisite)
undo_action = QAction("&Undo", self)
undo_action.setShortcut(QKeySequence.Undo)  # Ctrl+Z
undo_action.triggered.connect(self._undo_last_action)
edit_menu.addAction(undo_action)

# Redo: Ctrl+Y
redo_action = QAction("&Redo", self)
redo_action.setShortcut(QKeySequence.Redo)  # Ctrl+Y or Ctrl+Shift+Z
redo_action.triggered.connect(self._redo_last_action)
edit_menu.addAction(redo_action)

# Help: F1
help_action = QAction("&Help", self)
help_action.setShortcut(QKeySequence.HelpContents)  # F1
help_action.triggered.connect(self._show_help)
help_menu.addAction(help_action)

# Keyboard Shortcuts Cheatsheet: Ctrl+?
shortcuts_action = QAction("&Keyboard Shortcuts", self)
shortcuts_action.setShortcut("Ctrl+?")
shortcuts_action.triggered.connect(self._show_shortcuts_cheatsheet)
help_menu.addAction(shortcuts_action)
```

#### 4.3 Keyboard Shortcuts Cheatsheet Dialog

**Create ShortcutsDialog** - [src/ui/shortcuts_dialog.py](src/ui/shortcuts_dialog.py) (NEW ~200 lines)

**Design**: Modal dialog with categorized shortcuts

**Layout**:
```
┌────────────────────────────────────────────┐
│ Keyboard Shortcuts                         │
├────────────────────────────────────────────┤
│ [General] [Focus Mode] [Task List] [Dialogs] │
├────────────────────────────────────────────┤
│ General                                     │
│ ────────────────────────────────────────   │
│ New Task           Ctrl+N                   │
│ Settings           Ctrl+,                   │
│ Help               F1                       │
│ Exit               Ctrl+Q                   │
│                                              │
│ Focus Mode                                  │
│ ────────────────────────────────────────   │
│ Complete Task      Ctrl+Shift+C             │
│ Defer Task         Ctrl+D                   │
│ Delegate Task      Ctrl+Shift+D             │
│ Someday/Maybe      Ctrl+M                   │
│ Move to Trash      Ctrl+Delete              │
│ Edit Task          Ctrl+Shift+E             │
│                                              │
│ Navigation                                  │
│ ────────────────────────────────────────   │
│ Focus Mode         Ctrl+F                   │
│ Task List          Ctrl+L                   │
│ Refresh            F5                       │
│                                              │
│            [Print]  [Close]                 │
└────────────────────────────────────────────┘
```

---

### STEP 5: Basic Undo/Redo System (3-4 days)

#### 5.1 Command Pattern Framework

**Create Command Base Class** - [src/commands/base_command.py](src/commands/base_command.py) (NEW ~80 lines)

```python
from abc import ABC, abstractmethod

class Command(ABC):
    """Base class for undoable commands"""

    @abstractmethod
    def execute(self) -> bool:
        """Execute the command. Returns True on success."""
        pass

    @abstractmethod
    def undo(self) -> bool:
        """Undo the command. Returns True on success."""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Return human-readable description (e.g., 'Complete task: Buy groceries')"""
        pass
```

#### 5.2 Concrete Commands

**Create Command Implementations** - [src/commands/](src/commands/) (NEW directory)

**CompleteTaskCommand** - [src/commands/complete_task_command.py](src/commands/complete_task_command.py) (~100 lines)

```python
class CompleteTaskCommand(Command):
    def __init__(self, task_dao: TaskDAO, task_id: int):
        self.task_dao = task_dao
        self.task_id = task_id
        self.original_state = None

    def execute(self) -> bool:
        task = self.task_dao.get_by_id(self.task_id)
        self.original_state = task.state
        task.state = TaskState.COMPLETED
        task.completed_at = datetime.now()
        return self.task_dao.update(task)

    def undo(self) -> bool:
        task = self.task_dao.get_by_id(self.task_id)
        task.state = self.original_state
        task.completed_at = None
        return self.task_dao.update(task)

    def get_description(self) -> str:
        task = self.task_dao.get_by_id(self.task_id)
        return f"Complete task: {task.title}"
```

**Other Commands** (similar pattern):
- [src/commands/defer_task_command.py](src/commands/defer_task_command.py) (~120 lines)
- [src/commands/delegate_task_command.py](src/commands/delegate_task_command.py) (~120 lines)
- [src/commands/delete_task_command.py](src/commands/delete_task_command.py) (~100 lines)
- [src/commands/edit_task_command.py](src/commands/edit_task_command.py) (~150 lines)
- [src/commands/change_priority_command.py](src/commands/change_priority_command.py) (~100 lines)

#### 5.3 Undo/Redo Manager

**Create UndoManager** - [src/services/undo_manager.py](src/services/undo_manager.py) (NEW ~200 lines)

```python
class UndoManager(QObject):
    """Manages undo/redo stack"""

    can_undo_changed = pyqtSignal(bool)
    can_redo_changed = pyqtSignal(bool)

    def __init__(self, max_stack_size: int = 50):
        super().__init__()
        self.undo_stack: List[Command] = []
        self.redo_stack: List[Command] = []
        self.max_stack_size = max_stack_size

    def execute_command(self, command: Command) -> bool:
        """Execute command and add to undo stack"""
        if command.execute():
            self.undo_stack.append(command)
            self.redo_stack.clear()  # Clear redo when new action

            # Limit stack size
            if len(self.undo_stack) > self.max_stack_size:
                self.undo_stack.pop(0)

            self.can_undo_changed.emit(True)
            self.can_redo_changed.emit(False)
            return True
        return False

    def undo(self) -> bool:
        """Undo last command"""
        if not self.can_undo():
            return False

        command = self.undo_stack.pop()
        if command.undo():
            self.redo_stack.append(command)
            self.can_undo_changed.emit(self.can_undo())
            self.can_redo_changed.emit(True)
            return True
        return False

    def redo(self) -> bool:
        """Redo last undone command"""
        if not self.can_redo():
            return False

        command = self.redo_stack.pop()
        if command.execute():
            self.undo_stack.append(command)
            self.can_undo_changed.emit(True)
            self.can_redo_changed.emit(self.can_redo())
            return True
        return False

    def can_undo(self) -> bool:
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self.redo_stack) > 0

    def get_undo_description(self) -> Optional[str]:
        if self.can_undo():
            return self.undo_stack[-1].get_description()
        return None

    def clear(self) -> None:
        """Clear all undo/redo history"""
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.can_undo_changed.emit(False)
        self.can_redo_changed.emit(False)
```

#### 5.4 Integration with MainWindow

**Modify MainWindow** - [src/ui/main_window.py](src/ui/main_window.py) (MODIFY +60 lines)

```python
def __init__(self):
    # ... existing code ...
    self.undo_manager = UndoManager(max_stack_size=50)

    # Connect signals to update menu state
    self.undo_manager.can_undo_changed.connect(self.undo_action.setEnabled)
    self.undo_manager.can_redo_changed.connect(self.redo_action.setEnabled)

    # Initially disabled
    self.undo_action.setEnabled(False)
    self.redo_action.setEnabled(False)

def _handle_complete_task(self, task_id: int):
    """Handle task completion with undo support"""
    command = CompleteTaskCommand(self.task_dao, task_id)
    if self.undo_manager.execute_command(command):
        self.statusBar().showMessage(
            f"Task completed. Press Ctrl+Z to undo.",
            5000
        )
        self._refresh_focus_task()

def _undo_last_action(self):
    """Undo last action"""
    desc = self.undo_manager.get_undo_description()
    if self.undo_manager.undo():
        self.statusBar().showMessage(f"Undone: {desc}", 3000)
        self._refresh_focus_task()
        self.task_list_view.refresh_tasks()

def _redo_last_action(self):
    """Redo last undone action"""
    if self.undo_manager.redo():
        self.statusBar().showMessage("Action redone", 3000)
        self._refresh_focus_task()
        self.task_list_view.refresh_tasks()
```

**Update Menu** - Add Edit menu with Undo/Redo:
```python
edit_menu = menubar.addMenu("&Edit")

undo_action = QAction("&Undo", self)
undo_action.setShortcut(QKeySequence.Undo)
undo_action.triggered.connect(self._undo_last_action)
edit_menu.addAction(undo_action)
self.undo_action = undo_action  # Store for enable/disable

redo_action = QAction("&Redo", self)
redo_action.setShortcut(QKeySequence.Redo)
redo_action.triggered.connect(self._redo_last_action)
edit_menu.addAction(redo_action)
self.redo_action = redo_action
```

---

### STEP 6: Onboarding & Help System (4-5 days)

#### 6.1 First-Run Detection

**Create FirstRunDetector** - [src/services/first_run_detector.py](src/services/first_run_detector.py) (NEW ~100 lines)

```python
class FirstRunDetector:
    def is_first_run(self) -> bool:
        """Check if this is first app launch"""
        return self.settings_dao.get_str('onboarding_completed', 'false') == 'false'

    def mark_onboarding_complete(self) -> None:
        """Mark onboarding as completed"""
        self.settings_dao.set('onboarding_completed', 'true')

    def should_show_tutorial(self) -> bool:
        """Check if tutorial should be shown"""
        return self.settings_dao.get_str('tutorial_shown', 'false') == 'false'
```

#### 6.2 Welcome Wizard

**Create WelcomeWizard** - [src/ui/welcome_wizard.py](src/ui/welcome_wizard.py) (NEW ~500 lines)

**Design**: Multi-page QWizard with 5 pages

**Page 1: Welcome**
```
┌─────────────────────────────────────────┐
│ Welcome to OneTaskAtATime! 🎯          │
├─────────────────────────────────────────┤
│                                          │
│   OneTaskAtATime helps you focus on     │
│   executing ONE task at a time.         │
│                                          │
│   Key principles:                        │
│   • Focus Mode shows only your          │
│     highest-priority task               │
│   • Smart ranking eliminates            │
│     "everything is urgent" problem      │
│   • Task resurfacing prevents           │
│     things from falling through cracks  │
│                                          │
│              [Next >]                    │
└─────────────────────────────────────────┘
```

**Page 2: Create First Task**
```
┌─────────────────────────────────────────┐
│ Create Your First Task                  │
├─────────────────────────────────────────┤
│ Task Title:                              │
│ [_________________________________]      │
│                                          │
│ Description (optional):                  │
│ [_________________________________]      │
│ [_________________________________]      │
│                                          │
│ Priority:                                │
│ ( ) Low  (•) Medium  ( ) High           │
│                                          │
│ Due Date (optional):                     │
│ [Select date...]                         │
│                                          │
│          [< Back]  [Next >]              │
└─────────────────────────────────────────┘
```

**Page 3: Understanding Focus Mode**
```
┌─────────────────────────────────────────┐
│ Focus Mode Overview                      │
├─────────────────────────────────────────┤
│                                          │
│ Focus Mode shows ONE task at a time:    │
│                                          │
│ [Screenshot or mockup of Focus Mode]    │
│                                          │
│ Actions you can take:                   │
│ • Complete (Ctrl+Shift+C)               │
│ • Defer (Ctrl+D) - Postpone to later    │
│ • Delegate (Ctrl+Shift+D)               │
│ • Someday/Maybe (Ctrl+M)                │
│ • Trash (Ctrl+Delete)                   │
│                                          │
│          [< Back]  [Next >]              │
└─────────────────────────────────────────┘
```

**Page 4: Priority & Ranking**
```
┌─────────────────────────────────────────┐
│ How Task Ranking Works                  │
├─────────────────────────────────────────┤
│ Tasks are ranked by Importance:         │
│                                          │
│ Importance = Priority × Urgency         │
│                                          │
│ Priority: Based on user setting (High/  │
│           Medium/Low) refined by Elo    │
│           comparisons                   │
│                                          │
│ Urgency: Based on due date (sooner =    │
│          more urgent)                   │
│                                          │
│ When tasks tie, you'll be asked to      │
│ compare them side-by-side!              │
│                                          │
│          [< Back]  [Next >]              │
└─────────────────────────────────────────┘
```

**Page 5: Finish**
```
┌─────────────────────────────────────────┐
│ You're All Set! 🚀                      │
├─────────────────────────────────────────┤
│ Quick tips:                              │
│                                          │
│ • Press F1 for help anytime             │
│ • Press Ctrl+? for keyboard shortcuts   │
│ • Manage contexts and tags in Manage    │
│   menu                                  │
│ • View settings with Ctrl+,             │
│                                          │
│ ☑ Show tutorial tips next time          │
│                                          │
│ Ready to focus?                         │
│                                          │
│          [< Back]  [Finish]              │
└─────────────────────────────────────────┘
```

**Integration** - [src/ui/main_window.py](src/ui/main_window.py) (MODIFY +20 lines)

```python
def __init__(self):
    # ... existing code ...

    # Show welcome wizard on first run
    if self.first_run_detector.is_first_run():
        QTimer.singleShot(500, self._show_welcome_wizard)

def _show_welcome_wizard(self):
    wizard = WelcomeWizard(self.db_connection, self)
    if wizard.exec_() == QWizard.Accepted:
        self.first_run_detector.mark_onboarding_complete()
        self._refresh_focus_task()
```

#### 6.3 Interactive Tutorial Tooltips

**Create TutorialTooltipManager** - [src/services/tutorial_tooltip_manager.py](src/services/tutorial_tooltip_manager.py) (NEW ~250 lines)

**Design**: Sequential tooltips that highlight UI elements

```python
class TutorialTooltip:
    widget: QWidget
    title: str
    message: str
    position: str  # "top", "bottom", "left", "right"
    highlight: bool = True  # Dim background, highlight widget

class TutorialTooltipManager(QObject):
    tutorial_completed = pyqtSignal()

    def start_tutorial(self, tutorial_name: str) -> None:
        """Start named tutorial sequence"""

    def show_next_tooltip(self) -> None:
        """Show next tooltip in sequence"""

    def skip_tutorial(self) -> None:
        """User skips tutorial"""
```

**Focus Mode Tutorial Steps**:
1. Highlight task card: "This is your current highest-priority task"
2. Highlight Complete button: "Click here or press Ctrl+Shift+C to complete"
3. Highlight Defer button: "Not ready? Defer it for later"
4. Highlight filter section: "Filter by context or project tags"

#### 6.4 Help System

**Create HelpDialog** - [src/ui/help_dialog.py](src/ui/help_dialog.py) (NEW ~400 lines)

**Design**: Tabbed dialog with searchable content

**Tabs**:
1. **Getting Started** - Quick intro, basic workflows
2. **Focus Mode** - How Focus Mode works, actions explained
3. **Task Management** - Creating/editing tasks, tags, contexts
4. **Priority System** - Elo ranking, comparisons, importance calculation
5. **Keyboard Shortcuts** - Full shortcut reference (embedded ShortcutsDialog content)
6. **FAQ** - Common questions

**Features**:
- Search box to filter help topics
- Rich text with images/screenshots
- Internal links (e.g., "See Priority System for details")
- "Was this helpful?" feedback buttons

**Content Example**:
```markdown
# Focus Mode

Focus Mode presents ONE task at a time - your highest-priority task.

## Actions

**Complete (Ctrl+Shift+C)**
Marks the task as done and moves to the next task.

**Defer (Ctrl+D)**
Postpone the task with a start date. The app tracks postponement
patterns and suggests interventions if needed.

**Delegate (Ctrl+Shift+D)**
Assign to someone else with a follow-up date. You'll be reminded
when follow-up is due.
```

**Add Help Menu** - [src/ui/main_window.py](src/ui/main_window.py) (MODIFY +15 lines)

```python
help_menu = menubar.addMenu("&Help")

help_action = QAction("&Help Contents", self)
help_action.setShortcut(QKeySequence.HelpContents)  # F1
help_action.triggered.connect(self._show_help)
help_menu.addAction(help_action)

shortcuts_action = QAction("&Keyboard Shortcuts", self)
shortcuts_action.setShortcut("Ctrl+?")
shortcuts_action.triggered.connect(self._show_shortcuts)
help_menu.addAction(shortcuts_action)

help_menu.addSeparator()

about_action = QAction("&About", self)
about_action.triggered.connect(self._show_about)
help_menu.addAction(about_action)
```

#### 6.5 Context-Sensitive Help

**Add WhatsThis Mode** - Use Qt's built-in WhatsThis:

```python
# Add to all dialogs
self.setWhatsThis("This dialog allows you to...")

# Add to specific widgets
self.priority_combo.setWhatsThis(
    "Select task priority: High, Medium, or Low. "
    "This sets the base priority before Elo adjustments."
)
```

**Enable WhatsThis button** in dialogs:
```python
self.setWindowFlags(
    self.windowFlags() | Qt.WindowContextHelpButtonHint
)
```

---

### STEP 7: Testing & Documentation (3-4 days)

#### 7.1 Unit Tests

**Test Task History** - [tests/services/test_task_history_service.py](tests/services/test_task_history_service.py) (~250 lines)
- `test_record_task_created()`
- `test_record_state_change()`
- `test_get_timeline()`
- `test_formatted_summary()`

**Test Error Handling** - [tests/services/test_error_service.py](tests/services/test_error_service.py) (~200 lines)
- `test_build_error_context()`
- `test_recovery_suggestions()`
- `test_error_severity_classification()`

**Test Undo/Redo** - [tests/services/test_undo_manager.py](tests/services/test_undo_manager.py) (~300 lines)
- `test_execute_command_adds_to_stack()`
- `test_undo_restores_state()`
- `test_redo_reapplies_command()`
- `test_new_command_clears_redo_stack()`
- `test_max_stack_size_enforced()`

**Test Accessibility** - [tests/accessibility/test_wcag_compliance.py](tests/accessibility/test_wcag_compliance.py) (~300 lines)
- Already outlined in Step 3.7

#### 7.2 UI Tests (pytest-qt)

**Test Keyboard Shortcuts** - [tests/ui/test_keyboard_shortcuts.py](tests/ui/test_keyboard_shortcuts.py) (~200 lines)
```python
def test_complete_task_shortcut(qtbot):
    focus_mode = FocusModeWidget(...)
    qtbot.addWidget(focus_mode)

    # Simulate Ctrl+Shift+C
    qtbot.keyClick(focus_mode, Qt.Key_C,
                   Qt.ControlModifier | Qt.ShiftModifier)

    # Verify task_completed signal emitted
```

**Test Help System** - [tests/ui/test_help_dialog.py](tests/ui/test_help_dialog.py) (~150 lines)
**Test Welcome Wizard** - [tests/ui/test_welcome_wizard.py](tests/ui/test_welcome_wizard.py) (~200 lines)
**Test Task History Dialog** - [tests/ui/test_task_history_dialog.py](tests/ui/test_task_history_dialog.py) (~150 lines)

#### 7.3 Integration Tests

**Test Complete Workflows** - [tests/integration/test_phase8_workflows.py](tests/integration/test_phase8_workflows.py) (~400 lines)

```python
def test_task_completion_with_undo():
    """Complete task, undo, verify restored"""

def test_task_history_records_all_changes():
    """Create, edit, defer, complete - verify all events recorded"""

def test_error_handling_with_recovery():
    """Trigger error, use recovery suggestion"""

def test_accessibility_keyboard_only_workflow():
    """Complete entire workflow using only keyboard"""

def test_onboarding_creates_first_task():
    """Run welcome wizard, verify task created"""
```

#### 7.4 Manual Testing Checklist

Create [docs/PHASE8_TESTING_CHECKLIST.md](docs/PHASE8_TESTING_CHECKLIST.md):

- [ ] Task history shows all event types correctly
- [ ] Undo/redo works for all major actions
- [ ] All keyboard shortcuts function correctly
- [ ] Screen reader announces all actions (test with NVDA)
- [ ] Tab navigation works in all dialogs
- [ ] Focus indicators are visible on all widgets
- [ ] Color contrast meets WCAG AA (use contrast checker tool)
- [ ] Error messages are helpful and suggest recovery
- [ ] Welcome wizard completes successfully
- [ ] Help dialog content is accurate and searchable
- [ ] Tutorial tooltips appear in correct sequence
- [ ] First-run detection works (delete settings, restart)

#### 7.5 Documentation

**Create Phase 8 Status Report** - [PHASE8_STATUS.md](PHASE8_STATUS.md) (~400 lines)

Follow format from Phase 5-7 status reports:
- Overview
- Completed Features
- Implementation Details
- Testing Coverage
- Known Issues
- Next Steps

**Update Main Documentation**:
- [README.md](README.md) - Add keyboard shortcuts section, accessibility statement
- [CLAUDE.md](CLAUDE.md) - Mark Phase 8 complete
- [implementation_plan.md](implementation_plan.md) - Update Phase 8 status to ✅

**Create User Guide** - [docs/USER_GUIDE.md](docs/USER_GUIDE.md) (NEW ~1000 lines)

Comprehensive guide covering:
- Getting started
- Focus Mode usage
- Task management
- Keyboard shortcuts reference
- Priority system explanation
- Accessibility features
- Troubleshooting

---

## Implementation Sequence

### Week 1: History & Error Handling
**Days 1-3**: Task history system (model, DAO, service, UI)
**Days 4-5**: Enhanced error handling (ErrorService, EnhancedErrorDialog, integration)

### Week 2: Accessibility Foundation
**Days 6-7**: Accessibility service, keyboard navigation manager
**Days 8-9**: Apply accessible labels to all widgets
**Day 10**: Color contrast fixes, focus indicators

### Week 3: Accessibility Completion & Shortcuts
**Days 11-12**: Screen reader support, ARIA announcements
**Day 13**: Keyboard shortcuts (Focus Mode + global)
**Day 14**: Accessibility testing and fixes

### Week 4: Undo/Redo & Help
**Days 15-16**: Command pattern, UndoManager, integration
**Days 17-18**: Help system (HelpDialog, ShortcutsDialog, WhatsThis)

### Week 5: Onboarding & Polish
**Days 19-20**: Welcome wizard, tutorial tooltips
**Days 21-22**: First-run detection, interactive tutorials
**Day 23**: Testing all features

### Week 6: Testing & Documentation
**Days 24-25**: Unit tests, UI tests, integration tests
**Days 26-27**: Manual testing, bug fixes
**Days 28-29**: Documentation (status report, user guide, README updates)
**Day 30**: Final QA and polish

---

## Critical Files

### NEW Files (27)

**Models & Data** (3):
1. [src/models/task_history_event.py](src/models/task_history_event.py) - ~80 lines
2. [src/database/task_history_dao.py](src/database/task_history_dao.py) - ~200 lines
3. [src/commands/base_command.py](src/commands/base_command.py) - ~80 lines

**Commands** (6):
4. [src/commands/complete_task_command.py](src/commands/complete_task_command.py) - ~100 lines
5. [src/commands/defer_task_command.py](src/commands/defer_task_command.py) - ~120 lines
6. [src/commands/delegate_task_command.py](src/commands/delegate_task_command.py) - ~120 lines
7. [src/commands/delete_task_command.py](src/commands/delete_task_command.py) - ~100 lines
8. [src/commands/edit_task_command.py](src/commands/edit_task_command.py) - ~150 lines
9. [src/commands/change_priority_command.py](src/commands/change_priority_command.py) - ~100 lines

**Services** (7):
10. [src/services/task_history_service.py](src/services/task_history_service.py) - ~300 lines
11. [src/services/error_service.py](src/services/error_service.py) - ~400 lines
12. [src/services/accessibility_service.py](src/services/accessibility_service.py) - ~350 lines
13. [src/services/keyboard_navigation_manager.py](src/services/keyboard_navigation_manager.py) - ~200 lines
14. [src/services/undo_manager.py](src/services/undo_manager.py) - ~200 lines
15. [src/services/first_run_detector.py](src/services/first_run_detector.py) - ~100 lines
16. [src/services/tutorial_tooltip_manager.py](src/services/tutorial_tooltip_manager.py) - ~250 lines

**UI Components** (5):
17. [src/ui/task_history_dialog.py](src/ui/task_history_dialog.py) - ~350 lines
18. [src/ui/enhanced_error_dialog.py](src/ui/enhanced_error_dialog.py) - ~300 lines
19. [src/ui/shortcuts_dialog.py](src/ui/shortcuts_dialog.py) - ~200 lines
20. [src/ui/help_dialog.py](src/ui/help_dialog.py) - ~400 lines
21. [src/ui/welcome_wizard.py](src/ui/welcome_wizard.py) - ~500 lines

**Utilities** (1):
22. [src/utils/contrast_checker.py](src/utils/contrast_checker.py) - ~150 lines

**Documentation** (5):
23. [docs/ACCESSIBILITY.md](docs/ACCESSIBILITY.md) - ~200 lines
24. [docs/PHASE8_TESTING_CHECKLIST.md](docs/PHASE8_TESTING_CHECKLIST.md) - ~100 lines
25. [docs/USER_GUIDE.md](docs/USER_GUIDE.md) - ~1000 lines
26. [PHASE8_STATUS.md](PHASE8_STATUS.md) - ~400 lines
27. [src/commands/](src/commands/) - NEW directory

### MODIFIED Files (9)

1. [src/database/schema.py](src/database/schema.py) - Add ~40 lines (task_history table, settings)
2. [src/models/task_state.py](src/models/task_state.py) - Add ~25 lines (TaskEventType enum)
3. [src/database/task_dao.py](src/database/task_dao.py) - Add ~40 lines (history integration)
4. [src/ui/main_window.py](src/ui/main_window.py) - Add ~250 lines (undo/redo, shortcuts, help menu, error handling)
5. [src/ui/focus_mode.py](src/ui/focus_mode.py) - Add ~140 lines (shortcuts, accessibility, history)
6. [src/ui/task_list_view.py](src/ui/task_list_view.py) - Add ~60 lines (accessibility, history menu)
7. [src/services/export_service.py](src/services/export_service.py) - Add ~30 lines (error handling)
8. [src/services/import_service.py](src/services/import_service.py) - Add ~30 lines (error handling)
9. [resources/themes/light.qss](resources/themes/light.qss) - Add ~50 lines (contrast, focus)
10. [resources/themes/dark.qss](resources/themes/dark.qss) - Add ~50 lines (contrast, focus)

### TEST Files (11)

1. [tests/services/test_task_history_service.py](tests/services/test_task_history_service.py) - ~250 lines
2. [tests/services/test_error_service.py](tests/services/test_error_service.py) - ~200 lines
3. [tests/services/test_undo_manager.py](tests/services/test_undo_manager.py) - ~300 lines
4. [tests/accessibility/test_wcag_compliance.py](tests/accessibility/test_wcag_compliance.py) - ~300 lines
5. [tests/ui/test_keyboard_shortcuts.py](tests/ui/test_keyboard_shortcuts.py) - ~200 lines
6. [tests/ui/test_help_dialog.py](tests/ui/test_help_dialog.py) - ~150 lines
7. [tests/ui/test_welcome_wizard.py](tests/ui/test_welcome_wizard.py) - ~200 lines
8. [tests/ui/test_task_history_dialog.py](tests/ui/test_task_history_dialog.py) - ~150 lines
9. [tests/integration/test_phase8_workflows.py](tests/integration/test_phase8_workflows.py) - ~400 lines
10. [tests/accessibility/](tests/accessibility/) - NEW directory
11. [tests/commands/](tests/commands/) - NEW directory with 6 test files (~100 lines each)

**Total New Lines**: ~9,000 lines (including tests and documentation)

---

## Success Criteria

### Functional Requirements

**Task History**:
- ✅ All task mutations recorded in task_history table
- ✅ History dialog shows complete timeline per task
- ✅ Events display with human-readable messages
- ✅ Old/new values preserved for auditing

**Error Handling**:
- ✅ All exceptions caught with context-aware messages
- ✅ Recovery suggestions provided for common errors
- ✅ Technical details available but hidden by default
- ✅ Errors logged for troubleshooting

**Accessibility (WCAG 2.1 AA)**:
- ✅ All widgets have accessible names and descriptions
- ✅ Keyboard navigation works for all functionality
- ✅ Focus indicators visible on all interactive elements
- ✅ Color contrast ratios meet 4.5:1 minimum
- ✅ Screen reader support (NVDA, JAWS, Narrator tested)
- ✅ Form inputs have associated labels
- ✅ Error messages announced to screen readers

**Keyboard Shortcuts**:
- ✅ Focus Mode actions have shortcuts (Complete, Defer, etc.)
- ✅ Global shortcuts work from any view
- ✅ Shortcuts displayed in tooltips
- ✅ Cheatsheet dialog accessible via Ctrl+?

**Undo/Redo**:
- ✅ Major actions are undoable (complete, defer, delegate, delete, edit)
- ✅ Ctrl+Z/Ctrl+Y work as expected
- ✅ Undo stack limited to 50 items
- ✅ Menu items enabled/disabled based on stack state

**Onboarding**:
- ✅ Welcome wizard shown on first run
- ✅ Wizard creates first task
- ✅ Tutorial explains Focus Mode and priority system
- ✅ Option to skip tutorial

**Help System**:
- ✅ F1 opens help dialog
- ✅ Help content covers all major features
- ✅ Keyboard shortcuts reference available
- ✅ Context-sensitive help (WhatsThis) on dialogs

### Non-Functional Requirements

- ✅ Task history queries perform well (< 100ms for 1000 events)
- ✅ Undo/redo operations feel instant (< 50ms)
- ✅ Keyboard shortcuts respond immediately
- ✅ Accessibility features don't impact performance
- ✅ Error handling doesn't expose sensitive data
- ✅ All dialogs maintain consistent UX patterns

### Testing Requirements

- ✅ Unit tests achieve >80% coverage for new services
- ✅ UI tests verify all keyboard shortcuts
- ✅ Accessibility tests pass WCAG 2.1 AA criteria
- ✅ Integration tests verify complete workflows
- ✅ Manual testing confirms screen reader compatibility
- ✅ Performance tests with large datasets (1000+ tasks, 5000+ history events)

### Documentation Requirements

- ✅ PHASE8_STATUS.md created with implementation summary
- ✅ USER_GUIDE.md provides comprehensive instructions
- ✅ ACCESSIBILITY.md documents compliance and testing
- ✅ README.md updated with keyboard shortcuts and accessibility statement
- ✅ Code comments explain complex algorithms (undo/redo, history tracking)

---

## Risk Mitigation

**Risk: Undo/redo breaks data integrity**
- Mitigation: Comprehensive command testing, transaction-based operations, limit to major actions only

**Risk: Task history table grows too large**
- Mitigation: Add archive/cleanup functionality, index by timestamp, test with 10,000+ events

**Risk: Accessibility features incomplete**
- Mitigation: Use automated tools (axe, WAVE), test with real screen readers, follow WCAG checklist

**Risk: Keyboard shortcuts conflict with system shortcuts**
- Mitigation: Follow platform conventions, avoid global hotkeys, make shortcuts configurable (future)

**Risk: Error handling over-simplifies technical issues**
- Mitigation: Always provide "Show Technical Details" option, log full errors, include error codes

**Risk: Onboarding wizard too lengthy**
- Mitigation: Keep to 5 pages max, allow skip, save progress, provide "replay tutorial" option

**Risk: Help content becomes outdated**
- Mitigation: Version help content with app version, review during each release, include screenshots

**Risk: WCAG compliance testing is time-consuming**
- Mitigation: Use automated tools first, focus manual testing on critical paths, document known limitations

---

## Notes

- Phase 7 already has theme system and settings infrastructure, so styling changes are straightforward
- PyQt5 provides some accessibility built-in (Qt Accessibility framework), we're enhancing it
- WCAG 2.1 AA is achievable; AAA would require significantly more effort (skip for v1.0)
- Undo/redo limited to major state changes (not for every edit field keystroke)
- Task history persists indefinitely; future phase could add archiving/cleanup
- Screen reader testing requires actual screen readers (NVDA free, JAWS trial, Windows Narrator built-in)
- Keyboard shortcuts follow Windows conventions (Ctrl+Z, Ctrl+Y, F1, etc.)
- Welcome wizard can be re-run via Help menu ("Show Tutorial Again")
- Error service integrates with existing logging infrastructure
- Focus indicators must be highly visible (2px solid border, high contrast color)

**End of Phase 8 Plan**
