# Phase 6: Task Resurfacing System - Implementation Plan

## Executive Summary

This plan details the implementation of an automated task resurfacing and notification system for OneTaskAtATime. The system will:
1. **Automatically activate deferred tasks** when their start date arrives
2. **Remind users of delegated tasks** on or after follow-up dates
3. **Trigger periodic reviews** of Someday/Maybe tasks
4. **Analyze postponement patterns** and prompt intervention
5. **Provide dual notification channels**: Windows toast notifications (optional) + in-app notification panel (cross-platform)

## User Requirements Summary

Based on user feedback:
- ✅ **Deferred tasks**: Auto-activate when start_date arrives (no manual review)
- ✅ **Someday tasks**: Periodic review dialog every N days (configurable, default 7)
- ✅ **Notifications**: Windows toast (optional) + in-app panel (always available)
- ✅ **Analytics**: Track postponement patterns with intervention prompts
- ✅ **Delegated tasks**: Remind on or after follow-up date (not before)

## Implementation Architecture

### 1. Background Scheduler (APScheduler)

**Core Service**: `src/services/resurfacing_scheduler.py` (NEW)

**Library**: APScheduler 3.10+ (already in requirements.txt)

**Design Pattern**:
- `BackgroundScheduler` runs in separate thread (non-blocking for Qt event loop)
- Emits Qt signals to communicate with UI thread
- Started in MainWindow.__init__(), stopped in closeEvent()
- Uses SQLite job store for persistence across restarts

**Scheduled Jobs**:

| Job Name | Trigger Type | Default Interval | Function |
|----------|--------------|------------------|----------|
| `check_deferred_tasks` | IntervalTrigger | Every 1 hour | Auto-activate deferred tasks with start_date <= today |
| `check_delegated_tasks` | CronTrigger | Daily at 9:00 AM | Remind about delegated tasks needing follow-up |
| `trigger_someday_review` | IntervalTrigger | Every 7 days | Show Someday/Maybe review dialog |
| `analyze_postponements` | CronTrigger | Daily at 6:00 PM | Analyze patterns and create intervention notifications |

**Qt Signal Integration**:
```python
class ResurfacingScheduler(QObject):
    # Signals emitted to UI thread
    deferred_tasks_activated = pyqtSignal(list)  # List[Task]
    delegated_followup_needed = pyqtSignal(list)  # List[Task]
    someday_review_triggered = pyqtSignal()
    postpone_intervention_needed = pyqtSignal(list)  # List[PostponeSuggestion]
```

### 2. Resurfacing Business Logic

**Core Service**: `src/services/resurfacing_service.py` (NEW)

**Key Methods**:

**`activate_ready_deferred_tasks() -> List[Task]`**
- Query `task_dao.get_deferred_tasks_ready_to_activate(date.today())`
- For each task:
  - Set `state = TaskState.ACTIVE`
  - Clear `start_date` field
  - Update `last_resurfaced_at = now()`
  - Increment `resurface_count`
- Return list of activated tasks
- Called by scheduler job every hour (configurable)

**`check_delegated_followups() -> List[Task]`**
- Query `task_dao.get_delegated_tasks_for_followup(date.today(), days_before=0)`
- Returns tasks where `follow_up_date <= today` (on or after follow-up date)
- Update `last_resurfaced_at` for tracking
- Return list of tasks needing follow-up
- Called by scheduler job daily at 9 AM

**`should_trigger_someday_review() -> bool`**
- Check `last_someday_review_at` setting (global timestamp)
- Compare with `someday_review_days` interval (default 7)
- Return true if interval has elapsed or never reviewed

**`analyze_postponement_patterns() -> List[PostponeSuggestion]`**
- Use existing `PostponeSuggestionService.get_suggestions_for_all_tasks(limit=10)`
- Filter tasks with high postponement frequency
- Return suggestions for user intervention

### 3. Notification System

#### 3.1 Notification Data Model

**Model**: `src/models/notification.py` (NEW)

```python
@dataclass
class Notification:
    id: Optional[int] = None
    type: NotificationType  # INFO, WARNING, ERROR
    title: str
    message: str
    created_at: datetime = field(default_factory=datetime.now)
    is_read: bool = False
    action_type: Optional[str] = None  # 'open_focus', 'open_review_delegated', etc.
    action_data: Optional[str] = None  # JSON payload
    dismissed_at: Optional[datetime] = None
```

**Enum**: `NotificationType` (INFO, WARNING, ERROR)

#### 3.2 Database Storage

**Table**: `notifications` (add to `src/database/schema.py`)

```sql
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK(type IN ('info', 'warning', 'error')),
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_read INTEGER DEFAULT 0,
    action_type TEXT,
    action_data TEXT,
    dismissed_at TIMESTAMP
)
```

**DAO**: `src/database/notification_dao.py` (NEW)
- CRUD operations for notifications
- Methods: `create()`, `get_all()`, `get_unread()`, `mark_read()`, `dismiss()`

#### 3.3 Windows Toast Notifications

**Service**: `src/services/toast_notification_service.py` (NEW)

**Implementation**:
- Platform detection: `platform.system() == 'Windows'`
- Use `win10toast` library (already in requirements.txt)
- Run in background thread to avoid blocking UI
- Gracefully skip if not on Windows or if disabled in settings
- Default duration: 5 seconds

**Settings**:
- `enable_toast_notifications` (boolean, default: true)

#### 3.4 In-App Notification Panel

**Widget**: `src/ui/notification_panel.py` (NEW)

**Design**:
- Compact widget embedded in MainWindow layout (top-right area)
- Shows unread notification count badge
- Click to expand panel with notification list
- Each notification displays:
  - Icon (based on type: ℹ️ INFO, ⚠️ WARNING, ❌ ERROR)
  - Title (bold)
  - Message snippet (truncated if long)
  - Time ago (e.g., "5 minutes ago")
  - Action button (if action_type defined)
- Actions: Mark as Read, Dismiss
- "Mark All Read" button at bottom
- Auto-refresh on new notifications (via signal)

**Layout Integration**: Add to MainWindow above/beside Focus Mode widget

#### 3.5 Notification Manager

**Service**: `src/services/notification_manager.py` (NEW)

**Responsibilities**:
- Centralized notification creation and delivery
- Store notification in database
- Emit Qt signal `new_notification`
- Trigger toast notification (if enabled and on Windows)
- Provide query methods for UI

**API**:
```python
class NotificationManager(QObject):
    new_notification = pyqtSignal(Notification)

    def create_notification(
        self, type: NotificationType, title: str, message: str,
        action_type: str = None, action_data: dict = None
    ) -> Notification

    def get_unread_notifications(self) -> List[Notification]
    def mark_as_read(self, notification_id: int) -> bool
    def dismiss_notification(self, notification_id: int) -> bool
```

#### 3.6 Notification Types

| Type | Trigger | Title | Message | Action |
|------|---------|-------|---------|--------|
| DEFERRED_ACTIVATED | Auto-activation | "Tasks Ready to Work" | "N deferred task(s) are now active." | open_focus |
| DELEGATED_FOLLOWUP | Follow-up date reached | "Follow-up Required" | "N delegated task(s) have reached their follow-up date." | open_review_delegated |
| SOMEDAY_REVIEW | Review interval | "Someday/Maybe Review" | "Time to review your Someday tasks." | open_review_someday |
| POSTPONE_INTERVENTION | Pattern detected | "Task Needs Attention" | "Task 'X' postponed N times. Review?" | open_postpone_analytics |

### 4. Review Dialogs

#### 4.1 Review Delegated Dialog

**File**: `src/ui/review_delegated_dialog.py` (NEW)

**Design**: Similar to existing `ReviewDeferredDialog`

**Table Columns**:
- Checkbox (for selection)
- Title
- Delegated To
- Follow-up Date
- Days Overdue (how many days past follow-up date)
- Importance

**Actions**:
- **Activate Selected**: Move to ACTIVE state (user takes task back)
- **Mark Complete**: Complete selected tasks
- **Extend Follow-up**: Reschedule follow-up date
- **Re-delegate**: Change delegated_to and follow_up_date
- **Close**: Dismiss dialog

**Sorting**: By follow_up_date (earliest first)

#### 4.2 Review Someday Dialog

**File**: `src/ui/review_someday_dialog.py` (NEW)

**Design**: Similar to `ReviewDeferredDialog`

**Table Columns**:
- Checkbox
- Title
- Priority (Effective Priority)
- Tags
- Days Since Created
- Last Resurfaced

**Actions**:
- **Activate Selected**: Move to ACTIVE state
- **Keep in Someday**: Close dialog (updates last_someday_review_at)
- **Move to Trash**: Delete selected tasks

**Sorting**: By importance (Effective Priority × 1, no urgency for someday tasks)

**Settings Update**: On dialog close (any action), update `last_someday_review_at = now()`

### 5. Postponement Intervention

#### 5.1 Reflection Dialog

**File**: `src/ui/postpone_reflection_dialog.py` (NEW)

**When Shown**:
- **Immediate check**: When user postpones a task that already has >= 2 prior postponements
- **Flow**: Show BEFORE postpone dialog (intercept the postpone action)
- If user proceeds without intervention, continue to normal postpone dialog

**Content**:
- Display postponement history (dates, reasons, actions taken)
- Show suggestion from `PostponeSuggestionService`
- Explain why intervention is suggested

**Actions**:
1. **Break Down Task**: Launch subtask creation wizard, delete parent task
2. **Create Blocker**: Create new task and add as dependency
3. **Move to Someday**: Change state to SOMEDAY
4. **Move to Trash**: Delete task
5. **Proceed Anyway**: Continue to postpone dialog

**Integration Point**: Modify `FocusModeWidget` postpone button handlers to check:
```python
if self.postpone_workflow_service.should_show_reflection_dialog(task):
    dialog = PostponeReflectionDialog(task, self.db_connection)
    result = dialog.exec_()
    if result == PostponeReflectionDialog.ProceedToPostpone:
        # Continue to normal postpone flow
```

#### 5.2 Background Intervention Analysis

**Job**: `analyze_postponements` (daily at 6 PM)

**Logic**:
- Call `resurfacing_service.analyze_postponement_patterns()`
- For each suggestion returned:
  - Create notification with type=WARNING
  - Include task ID in action_data
  - Message includes postponement count and primary reason
- User can click notification to open Postpone Analytics Dashboard

**Threshold Settings**:
- `postpone_intervention_threshold` (default: 3) - Total postponements before alert
- `postpone_pattern_days` (default: 7) - Window for detecting patterns

### 6. Settings System

#### 6.1 New Settings

Add to `schema.py` `get_default_settings()`:

**Resurfacing Intervals**:
```python
('deferred_check_hours', '1', 'integer', 'Hours between deferred task checks'),
('delegated_check_time', '09:00', 'text', 'Time of day to check delegated tasks'),
('someday_review_days', '7', 'integer', 'Days between Someday/Maybe reviews'),
('someday_review_time', '18:00', 'text', 'Preferred time for someday review'),
('last_someday_review_at', 'null', 'datetime', 'Last someday review timestamp'),
```

**Notification Preferences**:
```python
('enable_toast_notifications', 'true', 'boolean', 'Enable Windows toast notifications'),
('enable_inapp_notifications', 'true', 'boolean', 'Enable in-app notification panel'),
('notification_retention_days', '30', 'integer', 'Days to keep old notifications'),
('notify_deferred_activation', 'true', 'boolean', 'Notify when deferred tasks activate'),
('notify_delegated_followup', 'true', 'boolean', 'Notify for delegated follow-ups'),
('notify_someday_review', 'true', 'boolean', 'Notify for someday reviews'),
('notify_postpone_intervention', 'true', 'boolean', 'Notify for postponement patterns'),
```

**Intervention Thresholds**:
```python
('postpone_intervention_threshold', '3', 'integer', 'Postponements before intervention'),
('postpone_pattern_days', '7', 'integer', 'Days window for pattern detection'),
```

#### 6.2 Settings Dialog

**File**: `src/ui/settings_dialog.py` (NEW)

**Design**: QDialog with QTabWidget for organized sections

**Tabs**:

**1. Resurfacing**
- Deferred Check Interval (hours): QSpinBox, range 1-24, default 1
- Delegated Check Time: QTimeEdit, default 09:00
- Someday Review Interval (days): QSpinBox, range 1-90, default 7
- Someday Review Time: QTimeEdit, default 18:00

**2. Notifications**
- Enable Windows Toast Notifications: QCheckBox
- Enable In-App Notifications: QCheckBox
- Notification Retention (days): QSpinBox, range 7-365, default 30

**3. Notification Triggers**
- Notify when deferred tasks activate: QCheckBox
- Notify for delegated follow-ups: QCheckBox
- Notify for someday reviews: QCheckBox
- Notify for postponement patterns: QCheckBox

**4. Intervention**
- Postponement Threshold: QSpinBox, range 2-10, default 3
- Pattern Detection Window (days): QSpinBox, range 3-14, default 7

**Save Behavior**:
- On Save: Update settings in database
- Emit signal to notify scheduler to reload settings
- Scheduler dynamically adjusts job intervals

**Access**: Add "Settings..." menu item to Tools menu in MainWindow

### 7. MainWindow Integration

**File**: `src/ui/main_window.py` (MODIFY)

**Changes**:

**1. Import new services** (lines 24-26):
```python
from ..services.resurfacing_scheduler import ResurfacingScheduler
from ..services.notification_manager import NotificationManager
from ..services.toast_notification_service import ToastNotificationService
```

**2. Initialize services in __init__()** (after line 45):
```python
# Initialize notification services
self.notification_manager = NotificationManager(self.db_connection)
self.toast_service = ToastNotificationService(self.db_connection)

# Initialize resurfacing scheduler
self.resurfacing_scheduler = ResurfacingScheduler(
    self.db_connection,
    self.notification_manager
)
```

**3. Add notification panel to UI** (in _init_ui(), after line 74):
```python
# Notification panel
self.notification_panel = NotificationPanel(
    self.db_connection,
    self.notification_manager
)
layout.insertWidget(0, self.notification_panel)  # Add at top
```

**4. Connect scheduler signals** (after line 83):
```python
# Connect scheduler signals
self.resurfacing_scheduler.deferred_tasks_activated.connect(
    self._on_deferred_tasks_activated
)
self.resurfacing_scheduler.delegated_followup_needed.connect(
    self._on_delegated_followup_needed
)
self.resurfacing_scheduler.someday_review_triggered.connect(
    self._on_someday_review_triggered
)
```

**5. Start scheduler** (after line 52):
```python
# Start background scheduler
self.resurfacing_scheduler.start()
```

**6. Add Settings menu item** (in _create_menu_bar()):
```python
# Tools Menu
tools_menu = menubar.addMenu("&Tools")

settings_action = QAction("&Settings...", self)
settings_action.setShortcut("Ctrl+,")
settings_action.triggered.connect(self._show_settings)
tools_menu.addAction(settings_action)
```

**7. Add signal handlers** (new methods):
```python
def _on_deferred_tasks_activated(self, tasks: List[Task]):
    """Handle deferred tasks auto-activation."""
    if tasks:
        self._refresh_focus_task()
        self.statusBar().showMessage(
            f"{len(tasks)} deferred task(s) activated", 5000
        )

def _on_delegated_followup_needed(self, tasks: List[Task]):
    """Show delegated follow-up dialog."""
    from .review_delegated_dialog import ReviewDelegatedDialog
    dialog = ReviewDelegatedDialog(self.db_connection, tasks, self)
    dialog.exec_()

def _on_someday_review_triggered(self):
    """Show someday review dialog."""
    from .review_someday_dialog import ReviewSomedayDialog
    dialog = ReviewSomedayDialog(self.db_connection, self)
    dialog.exec_()

def _show_settings(self):
    """Show settings dialog."""
    from .settings_dialog import SettingsDialog
    dialog = SettingsDialog(self.db_connection, self)
    if dialog.exec_() == QDialog.Accepted:
        # Reload scheduler settings
        self.resurfacing_scheduler.reload_settings()
```

**8. Shutdown scheduler on close** (override closeEvent):
```python
def closeEvent(self, event):
    """Handle application close event."""
    # Shutdown scheduler gracefully
    self.resurfacing_scheduler.shutdown(wait=True, timeout=5)
    event.accept()
```

### 8. Database Migrations

**File**: `src/database/schema.py` (MODIFY)

**Add migration method**:
```python
@staticmethod
def migrate_to_notification_system(db_connection: sqlite3.Connection) -> None:
    """
    Migrate database to support notification system.
    Adds notifications table and Phase 6 settings.
    """
    cursor = db_connection.cursor()

    # Create notifications table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL CHECK(type IN ('info', 'warning', 'error')),
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_read INTEGER DEFAULT 0,
            action_type TEXT,
            action_data TEXT,
            dismissed_at TIMESTAMP
        )
    """)

    # Add index for performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_notifications_is_read
        ON notifications(is_read)
    """)

    db_connection.commit()
```

**Call migration**: In `DatabaseConnection.__init__()` after schema creation

## Implementation Sequence

### Phase 6.1: Scheduler Foundation (2-3 days)
**Files**:
- `src/services/resurfacing_scheduler.py` (NEW)
- `src/services/resurfacing_service.py` (NEW)
- `src/ui/main_window.py` (MODIFY)

**Tasks**:
1. Create ResurfacingScheduler with APScheduler integration
2. Create ResurfacingService with business logic methods
3. Integrate scheduler into MainWindow lifecycle (start/stop)
4. Add settings for intervals
5. Test scheduler starts/stops without errors
6. Add console logging for job execution

### Phase 6.2: Notification System (3-4 days)
**Files**:
- `src/models/notification.py` (NEW)
- `src/database/notification_dao.py` (NEW)
- `src/services/notification_manager.py` (NEW)
- `src/services/toast_notification_service.py` (NEW)
- `src/ui/notification_panel.py` (NEW)
- `src/database/schema.py` (MODIFY - add notifications table)

**Tasks**:
1. Create notification model and enum
2. Add notifications table to schema with migration
3. Create NotificationDAO with CRUD operations
4. Create NotificationManager service with Qt signals
5. Create ToastNotificationService with Windows integration
6. Create NotificationPanel widget
7. Integrate panel into MainWindow layout
8. Test notification creation and display (both channels)

### Phase 6.3: Deferred Task Auto-Activation (1 day)
**Files**:
- `src/services/resurfacing_service.py` (MODIFY)
- `src/ui/main_window.py` (MODIFY)

**Tasks**:
1. Implement `activate_ready_deferred_tasks()` in ResurfacingService
2. Add scheduler job for hourly checks
3. Create notifications on activation
4. Connect signal in MainWindow to refresh Focus Mode
5. Test with various start dates (past, today, future)

### Phase 6.4: Delegated Task Reminders (2 days)
**Files**:
- `src/ui/review_delegated_dialog.py` (NEW)
- `src/services/resurfacing_service.py` (MODIFY)

**Tasks**:
1. Implement `check_delegated_followups()` in ResurfacingService
2. Create ReviewDelegatedDialog (model after ReviewDeferredDialog)
3. Add scheduler job for daily checks (cron)
4. Create notifications for follow-ups
5. Connect signal in MainWindow to show dialog
6. Test with various follow-up dates

### Phase 6.5: Someday/Maybe Review (2 days)
**Files**:
- `src/ui/review_someday_dialog.py` (NEW)
- `src/services/resurfacing_service.py` (MODIFY)
- `src/database/schema.py` (MODIFY - add last_someday_review_at setting)

**Tasks**:
1. Add `last_someday_review_at` setting to schema
2. Implement `should_trigger_someday_review()` in ResurfacingService
3. Create ReviewSomedayDialog
4. Add scheduler job for interval-based checks
5. Update `last_someday_review_at` on dialog close
6. Connect signal in MainWindow to show dialog
7. Test review trigger logic

### Phase 6.6: Postponement Intervention (2-3 days)
**Files**:
- `src/ui/postpone_reflection_dialog.py` (NEW)
- `src/ui/focus_mode.py` (MODIFY)
- `src/services/resurfacing_service.py` (MODIFY)

**Tasks**:
1. Create PostponeReflectionDialog with intervention options
2. Modify FocusModeWidget to check for intervention before postpone
3. Implement subtask breakdown workflow
4. Implement blocker creation workflow
5. Add daily batch analysis job for background notifications
6. Test intervention triggers (immediate and batch)

### Phase 6.7: Settings UI (2 days)
**Files**:
- `src/ui/settings_dialog.py` (NEW)
- `src/ui/main_window.py` (MODIFY - add menu item)
- `src/database/schema.py` (MODIFY - ensure all settings exist)

**Tasks**:
1. Create SettingsDialog with tabbed interface
2. Add all setting controls (spinboxes, checkboxes, time pickers)
3. Implement save/cancel logic
4. Add "Settings..." menu item to Tools menu
5. Implement scheduler.reload_settings() method
6. Test settings persistence and scheduler reload

### Phase 6.8: Testing and Polish (3-4 days)
**Files**:
- `tests/services/test_resurfacing_service.py` (NEW)
- `tests/services/test_notification_manager.py` (NEW)
- `tests/ui/test_review_someday_dialog.py` (NEW)
- `tests/ui/test_review_delegated_dialog.py` (NEW)
- `tests/integration/test_scheduler_integration.py` (NEW)

**Tasks**:
1. Write unit tests for ResurfacingService (use freezegun for time mocking)
2. Write unit tests for NotificationManager
3. Write UI tests for review dialogs (pytest-qt)
4. Write integration tests for scheduler jobs
5. Manual testing on Windows for toast notifications
6. Fix bugs and refine UX
7. Update documentation (PHASE6_STATUS.md)

**Total Estimated Time**: 17-24 days

## Critical Files Summary

### New Files (10)
1. `src/services/resurfacing_scheduler.py` - APScheduler setup and job management
2. `src/services/resurfacing_service.py` - Business logic for task resurfacing
3. `src/services/notification_manager.py` - Centralized notification handling
4. `src/services/toast_notification_service.py` - Windows toast integration
5. `src/models/notification.py` - Notification data model
6. `src/database/notification_dao.py` - Notification CRUD operations
7. `src/ui/notification_panel.py` - In-app notification widget
8. `src/ui/review_delegated_dialog.py` - Delegated task review dialog
9. `src/ui/review_someday_dialog.py` - Someday/Maybe review dialog
10. `src/ui/settings_dialog.py` - Application settings UI
11. `src/ui/postpone_reflection_dialog.py` - Postponement intervention dialog

### Modified Files (3)
1. `src/ui/main_window.py` - Scheduler integration, notification panel, signal connections
2. `src/database/schema.py` - Add notifications table, new settings
3. `src/ui/focus_mode.py` - Add intervention check before postpone

## Testing Strategy

### Unit Tests
- **ResurfacingService**: Mock database, use freezegun for date mocking
- **NotificationManager**: Mock DAO and toast service
- **ToastNotificationService**: Mock win10toast, test platform detection

### Integration Tests
- **Scheduler**: Test job execution with in-memory database
- **Resurfacing Workflow**: End-to-end test from deferred to active

### UI Tests (pytest-qt)
- **Review Dialogs**: Test table display, selection, activation
- **NotificationPanel**: Test notification display and interaction
- **SettingsDialog**: Test settings persistence

### Manual Testing
- Verify scheduler starts/stops cleanly
- Test all notification types (deferred, delegated, someday, intervention)
- Verify Windows toast appears on Windows
- Test settings changes affect scheduler behavior
- Verify no UI blocking during background jobs

## Success Criteria

✅ Deferred tasks with `start_date <= today` automatically activate (checked hourly)
✅ Delegated tasks generate reminders N days before `follow_up_date`
✅ Someday review dialog appears every N days (configurable)
✅ Postponement patterns trigger intervention after threshold
✅ Windows toast notifications work on Windows (optional)
✅ In-app notification panel displays all notifications (cross-platform)
✅ Settings dialog allows full customization
✅ Scheduler shuts down gracefully on app close
✅ No UI blocking - all background jobs run smoothly
✅ Tests achieve >80% code coverage for new code

## Risk Mitigation

**Risk**: Scheduler doesn't shutdown cleanly
**Mitigation**: Call `scheduler.shutdown(wait=True, timeout=5)` in closeEvent, add integration tests

**Risk**: Database contention from background jobs
**Mitigation**: Use separate connection per job, keep transactions short, enable SQLite WAL mode

**Risk**: UI blocking from notifications
**Mitigation**: Emit Qt signals from background threads, handle UI updates in main thread only

**Risk**: Toast notifications fail silently
**Mitigation**: Try/except wrapper, always create in-app notification as fallback, log errors

**Risk**: Users annoyed by frequent prompts
**Mitigation**: All notifications configurable, reasonable default intervals, allow dismiss/snooze
