# Phase 7: Settings & Customization - Implementation Plan

## Executive Summary

Phase 7 completes the OneTaskAtATime application with comprehensive data management, customization, and backup capabilities. This phase adds:

1. **Enhanced Settings Dialog** - Theme and Advanced tabs (6 total tabs)
2. **Import/Export System** - Full data portability via JSON and SQLite backup
3. **Data Reset Functionality** - Nuclear reset with strong multi-step confirmation
4. **Theme System** - Light/Dark mode with Qt stylesheets
5. **Comparison/Elo Tuning** - Advanced settings for power users

**User-Confirmed Requirements:**
- ✅ Export: ALL data (tasks, contexts, tags, history) in JSON + SQLite backup
- ✅ Import: Replace or merge modes with ID conflict resolution
- ✅ Reset: Full nuclear reset (single operation, strong confirmation)
- ✅ Theme: Light/Dark mode selection
- ✅ Advanced: K-factors, epsilon tuning for Elo system

**Total Estimated Effort**: 15-20 days

---

## Architecture Overview

### Current State
- **Settings Infrastructure**: SettingsDAO with type-safe key-value storage (30+ settings exist from Phase 6)
- **SettingsDialog**: 4 tabs implemented (../../resurfacing, Notifications, Triggers, Intervention)
- **Database Schema**: 9 tables with comprehensive indexes
- **Menu Structure**: File, View, Manage, Tools, Help menus

### What's Being Added
- **2 New Tabs**: Theme + Advanced (total 6 tabs)
- **4 Services**: ExportService, ImportService, DataResetService, ThemeService
- **3 UI Dialogs**: ExportDialog, ImportDialog, ResetConfirmationDialog
- **Theme Resources**: light.qss, dark.qss stylesheets
- **Menu Items**: File > Import/Export submenu, Tools > Reset All Data

---

## Implementation Plan

### STEP 1: Theme System Foundation (2-3 days)

**Create ThemeService** - [src/services/theme_service.py](../../src/services/theme_service.py) (NEW ~150 lines)

**Purpose**: Manage Qt stylesheet loading and application

**Key Methods**:
```python
class ThemeService:
    def get_current_theme() -> str
    def apply_theme(theme_name: str) -> None
    def _load_stylesheet(theme_name: str) -> str
    def _detect_system_theme() -> str  # Windows registry check
```

**Create Stylesheets**:
- [resources/themes/light.qss](../../resources/themes/light.qss) (NEW ~100 lines)
- [resources/themes/dark.qss](../../resources/themes/dark.qss) (NEW ~150 lines)

**Dark Theme Example**:
```css
QMainWindow { background-color: #2b2b2b; color: #ffffff; }
QPushButton { background-color: #3c3f41; border: 1px solid #555555; }
QTableWidget { background-color: #313335; gridline-color: #555555; }
```

**Add Theme Tab to SettingsDialog** - [src/ui/settings_dialog.py](../../src/ui/settings_dialog.py) (MODIFY +80 lines)

**Layout**:
- Theme dropdown: Light/Dark/System Default (QComboBox)
- Font size: 8-16pt, default 10pt (QSpinBox)
- Preview area showing sample task card
- Live preview updates when theme changes

**Integration in MainWindow** - [src/ui/main_window.py](../../src/ui/main_window.py) (MODIFY +15 lines)

```python
# In __init__()
self.theme_service = ThemeService(self.db_connection, self.app)
self.theme_service.apply_theme(self.settings_dao.get_str('theme', 'light'))
```

**New Settings**:
```python
('theme', 'light', 'string', 'UI theme (light/dark/system)'),
('font_size', '10', 'integer', 'Base font size in points'),
```

---

### STEP 2: Export System (3-4 days)

**Create ExportService** - [src/services/export_service.py](../../src/services/export_service.py) (NEW ~300 lines)

**Core Methods**:
```python
def export_to_json(filepath: str, progress_callback=None) -> Dict[str, Any]:
    """Export all data to structured JSON"""
    # Returns: {success: bool, filepath: str, task_count: int, ...}

def export_database_backup(dest_filepath: str) -> Dict[str, Any]:
    """Create SQLite database file backup"""
    # Uses shutil.copy2() for file-level copy

def _export_tasks(progress_callback=None) -> List[Dict]:
    """Export all tasks with relationships preserved"""

# Similar methods for contexts, tags, dependencies, comparisons, history, notifications, settings
```

**JSON Export Structure**:
```json
{
  "metadata": {
    "export_date": "2025-01-15T10:30:00",
    "app_version": "1.0.0",
    "schema_version": 1,
    "export_type": "full"
  },
  "contexts": [...],
  "project_tags": [...],
  "tasks": [...],
  "dependencies": [...],
  "task_comparisons": [...],
  "postpone_history": [...],
  "notifications": [...],
  "settings": {...}
}
```

**Create ExportDialog** - [src/ui/export_dialog.py](../../src/ui/export_dialog.py) (NEW ~200 lines)

**UI Features**:
- Radio buttons: JSON vs SQLite Database Backup
- Checkboxes: What to include (tasks required, others optional)
- File path selection with default: `onetask_backup_YYYYMMDD_HHMMSS.json`
- Progress bar with status label
- Callback integration: `self.export_service.export_to_json(filepath, self._update_progress)`

**Add Menu Items** - [src/ui/main_window.py](../../src/ui/main_window.py) (MODIFY +25 lines)

```python
# File Menu > Import/Export submenu
export_json_action = QAction("Export Data...", self)
export_json_action.setShortcut("Ctrl+Shift+E")
export_json_action.triggered.connect(self._export_data)

backup_db_action = QAction("Backup Database...", self)
backup_db_action.setShortcut("Ctrl+B")
backup_db_action.triggered.connect(self._backup_database)
```

---

### STEP 3: Import System (4-5 days)

**Create ImportService** - [src/services/import_service.py](../../src/services/import_service.py) (NEW ~400 lines)

**Core Methods**:
```python
def import_from_json(filepath: str, merge_mode: str, progress_callback=None) -> Dict:
    """Import from JSON with validation"""
    # Steps:
    # 1. Validate JSON structure and schema version
    # 2. Begin transaction
    # 3. Clear data if replace mode
    # 4. Import in dependency order: contexts → tags → tasks → dependencies → ...
    # 5. Commit or rollback on error

def restore_database_backup(source_filepath: str) -> Dict:
    """Restore from .db file"""
    # Close connection, backup current DB, copy source, return restart required

def _validate_import_data(data: Dict) -> Dict[str, Any]:
    """Validate JSON structure and check schema version compatibility"""

def _import_tasks(tasks_data: List[Dict], merge_mode: str, progress_callback) -> int:
    """Import tasks with ID conflict resolution"""
    # Replace mode: preserve IDs
    # Merge mode: remap IDs, track in _task_id_mapping dict
```

**ID Conflict Resolution (Merge Mode)**:
```python
id_mapping = {}  # old_id -> new_id
for task_data in tasks_data:
    task = self._dict_to_task(task_data)
    existing = self.task_dao.get_by_id(task.id)
    if existing:
        task.id = None  # Force new ID generation
    created_task = self.task_dao.create(task)
    id_mapping[task_data['id']] = created_task.id
```

**Create ImportDialog** - [src/ui/import_dialog.py](../../src/ui/import_dialog.py) (NEW ~250 lines)

**UI Features**:
- File selection with QFileDialog
- Radio buttons: Replace All Data vs Merge
- Warning banner for replace mode (../../red background)
- File summary display: export date, schema version, counts per table
- Progress bar with status updates
- Schema version compatibility check (../../reject if newer)

**Add Menu Items** - [src/ui/main_window.py](../../src/ui/main_window.py) (MODIFY +25 lines)

```python
import_json_action = QAction("Import Data...", self)
import_json_action.setShortcut("Ctrl+Shift+I")
import_json_action.triggered.connect(self._import_data)

restore_db_action = QAction("Restore Database...", self)
restore_db_action.setShortcut("Ctrl+R")
restore_db_action.triggered.connect(self._restore_database)
```

**Handler Pattern**:
```python
def _import_data(self):
    dialog = ImportDialog(self.db_connection, self)
    if dialog.exec_() == QDialog.Accepted:
        self._refresh_focus_task()
        self.task_list_view.refresh_tasks()
        self.statusBar().showMessage("Data imported successfully", 5000)
```

---

### STEP 4: Data Reset System (2 days)

**Create DataResetService** - [src/services/data_reset_service.py](../../src/services/data_reset_service.py) (NEW ~150 lines)

**Core Methods**:
```python
def get_reset_summary() -> Dict[str, int]:
    """Return counts for each table to be deleted"""
    # Query: SELECT COUNT(*) FROM tasks, contexts, tags, etc.

def reset_all_data(include_contexts: bool, include_tags: bool, reset_settings: bool) -> Dict:
    """Nuclear reset with options"""
    # Delete in dependency order:
    # task_comparisons → postpone_history → notifications → task_project_tags
    # → dependencies → tasks → [project_tags] → [contexts]
    # Transaction-based with rollback on error
```

**Create ResetConfirmationDialog** - [src/ui/reset_confirmation_dialog.py](../../src/ui/reset_confirmation_dialog.py) (NEW ~200 lines)

**Multi-Step Confirmation**:
1. Show red warning with consequences
2. Display summary from `get_reset_summary()`
3. Options: delete contexts (☑), delete tags (☑), reset settings (☐)
4. Type "RESET" exactly in text field
5. Checkbox: "I understand this is permanent"
6. Button enabled only when both confirmations complete
7. Final QMessageBox.warning() before execution

**UI Layout**:
```
⚠️ DANGER: Reset All Data
You are about to PERMANENTLY DELETE all data.
This action CANNOT BE UNDONE!

What will be deleted:
✓ 150 tasks
✓ 12 dependencies
✓ 45 comparisons
✓ 67 postpone records
✓ 23 notifications

Options:
☑ Also delete contexts (5)
☑ Also delete project tags (8)
☐ Reset settings to defaults

Type exactly: RESET
[_________________]

☐ I understand this is permanent

[Cancel]  [Reset All Data]
```

**Add Menu Item** - [src/ui/main_window.py](../../src/ui/main_window.py) (MODIFY +10 lines)

```python
# Tools Menu
reset_all_action = QAction("Reset All Data...", self)
# NO SHORTCUT - prevent accidents
reset_all_action.triggered.connect(self._reset_all_data)
tools_menu.addAction(../../reset_all_action)
```

---

### STEP 5: Advanced Settings Tab (1-2 days)

**Add Advanced Tab to SettingsDialog** - [src/ui/settings_dialog.py](../../src/ui/settings_dialog.py) (MODIFY +100 lines)

**Tab Content**:

**Warning Label** (top):
```
⚠️ Only change these settings if you understand the Elo comparison system.
```

**Elo System Parameters Group** (QGroupBox with QFormLayout):
- K-factor (new tasks): QSpinBox, range 16-64, default 32
  - Tooltip: "Sensitivity for first 10 comparisons (higher = larger rating changes)"
- K-factor (established): QSpinBox, range 8-32, default 16
  - Tooltip: "Sensitivity after 10 comparisons (lower = more stable ratings)"
- New task threshold: QSpinBox, range 5-20, default 10
  - Tooltip: "Number of comparisons before switching to base K-factor"
- Score epsilon: QDoubleSpinBox, range 0.001-0.1, default 0.01, step 0.001
  - Tooltip: "Threshold for tie detection (smaller = stricter equality)"

**Elo Band Ranges Group** (QGroupBox, read-only):
```
High Priority   (base=3): [2.0, 3.0]
Medium Priority (base=2): [1.0, 2.0]
Low Priority    (base=1): [0.0, 1.0]
```

**Reset to Defaults Button**:
```python
def _reset_advanced_defaults(self):
    self.k_factor_new_spin.setValue(32)
    self.k_factor_spin.setValue(16)
    self.threshold_spin.setValue(10)
    self.epsilon_spin.setValue(0.01)
```

**Settings Keys** (verify in [src/database/schema.py](../../src/database/schema.py)):
```python
('elo_k_factor_new', '32', 'integer', 'K-factor for new tasks'),
('elo_k_factor', '16', 'integer', 'K-factor for established tasks'),
('elo_new_task_threshold', '10', 'integer', 'Comparisons before base K-factor'),
('score_epsilon', '0.01', 'float', 'Threshold for tie detection'),
```

---

### STEP 6: Testing and Documentation (3-4 days)

**Unit Tests**:

**test_export_service.py** (~200 lines):
- `test_export_json_all_tables()` - Verify complete export
- `test_export_json_structure()` - Validate JSON schema
- `test_export_progress_callback()` - Verify callback invoked
- `test_export_database_backup()` - Verify .db copy
- `test_export_empty_database()` - Handle no data
- `test_export_file_permission_error()` - Mock filesystem error

**test_import_service.py** (~250 lines):
- `test_import_json_replace_mode()` - Clear then import
- `test_import_json_merge_mode()` - ID remapping
- `test_import_validation_fails()` - Invalid JSON structure
- `test_import_schema_version_newer()` - Reject import
- `test_import_transaction_rollback()` - Error recovery
- `test_restore_database_backup()` - .db file restore

**test_data_reset_service.py** (~150 lines):
- `test_get_reset_summary()` - Verify counts
- `test_reset_all_data()` - Full nuclear reset
- `test_reset_with_options()` - Selective deletion
- `test_reset_preserves_settings()` - Settings not deleted by default

**test_theme_service.py** (~100 lines):
- `test_apply_theme_light()` - Stylesheet loading
- `test_apply_theme_dark()` - Stylesheet loading
- `test_missing_stylesheet_fallback()` - Graceful degradation

**UI Tests (pytest-qt)**:
- `test_export_dialog_file_selection()`
- `test_import_dialog_validation_display()`
- `test_reset_confirmation_enable_logic()`
- `test_settings_theme_tab_save()`
- `test_settings_advanced_tab_save()`

**Integration Tests**:
- `test_export_import_roundtrip()` - Export → clear → import → verify match
- `test_theme_switching_live()` - Apply theme without restart
- `test_export_while_scheduler_running()` - No conflicts

**Documentation**:
- Create [PHASE7_STATUS.md](../phase_reports/PHASE7_STATUS.md) following Phase 5/6 format
- Update [README.md](../../README.md) with import/export instructions
- Update [CLAUDE.md](../../CLAUDE.md) with Phase 7 completion

---

## Implementation Sequence

### Week 1: Foundation
**Days 1-2**: Theme system (service + stylesheets + settings tab + main window integration)
**Day 3**: Export service core logic (JSON structure, table export methods)

### Week 2: Export/Import
**Days 4-5**: Export dialog + menu integration + testing
**Days 6-7**: Import service core logic (validation, transaction handling, ID remapping)
**Days 8-9**: Import dialog + menu integration + testing

### Week 3: Reset & Advanced
**Day 10**: Data reset service + dialog
**Day 11**: Advanced settings tab + validation
**Day 12**: Testing all new features

### Week 4: Polish & Documentation
**Days 13-14**: Unit tests for all services
**Days 15-16**: Integration tests + UI tests
**Days 17-18**: Manual testing, bug fixes, documentation

---

## Critical Files

### NEW Files (10)
1. [src/services/export_service.py](../../src/services/export_service.py) - ~300 lines
2. [src/services/import_service.py](../../src/services/import_service.py) - ~400 lines
3. [src/services/data_reset_service.py](../../src/services/data_reset_service.py) - ~150 lines
4. [src/services/theme_service.py](../../src/services/theme_service.py) - ~150 lines
5. [src/ui/export_dialog.py](../../src/ui/export_dialog.py) - ~200 lines
6. [src/ui/import_dialog.py](../../src/ui/import_dialog.py) - ~250 lines
7. [src/ui/reset_confirmation_dialog.py](../../src/ui/reset_confirmation_dialog.py) - ~200 lines
8. [resources/themes/light.qss](../../resources/themes/light.qss) - ~100 lines
9. [resources/themes/dark.qss](../../resources/themes/dark.qss) - ~150 lines
10. [resources/themes/](../../resources/themes/) - NEW directory

### MODIFIED Files (3)
1. [src/ui/settings_dialog.py](../../src/ui/settings_dialog.py) - Add ~180 lines (Theme + Advanced tabs)
2. [src/ui/main_window.py](../../src/ui/main_window.py) - Add ~130 lines (menu items + handlers + theme init)
3. [src/database/schema.py](../../src/database/schema.py) - Add ~20 lines (verify theme/advanced settings)

### TEST Files (7)
1. [tests/services/test_export_service.py](tests/services/test_export_service.py) - ~200 lines
2. [tests/services/test_import_service.py](tests/services/test_import_service.py) - ~250 lines
3. [tests/services/test_data_reset_service.py](tests/services/test_data_reset_service.py) - ~150 lines
4. [tests/services/test_theme_service.py](tests/services/test_theme_service.py) - ~100 lines
5. [tests/ui/test_export_dialog.py](tests/ui/test_export_dialog.py) - ~100 lines
6. [tests/ui/test_import_dialog.py](tests/ui/test_import_dialog.py) - ~100 lines
7. [tests/ui/test_reset_confirmation_dialog.py](tests/ui/test_reset_confirmation_dialog.py) - ~100 lines

**Total New Lines**: ~3,200 lines

---

## Success Criteria

### Functional Requirements
- ✅ Export all data to JSON with complete relationships preserved
- ✅ Export SQLite database as .db file backup
- ✅ Import from JSON with validation and error handling
- ✅ Import with replace mode (clear existing data)
- ✅ Import with merge mode (ID conflict resolution via remapping)
- ✅ Restore from database backup with automatic current DB backup
- ✅ Reset all data with multi-step confirmation (type "RESET" + checkbox)
- ✅ Theme switching (light/dark/system) applies without restart
- ✅ Advanced Elo settings (K-factors, epsilon) with tooltips
- ✅ Settings persist across app restarts

### Non-Functional Requirements
- ✅ Export/import show progress for large datasets (500+ tasks)
- ✅ Transaction-based import ensures all-or-nothing atomicity
- ✅ Graceful error handling with user-friendly messages
- ✅ Data integrity validation before import (schema version check)
- ✅ No data loss during operations
- ✅ Theme applies to all dialogs (MainWindow, FocusMode, TaskList, etc.)
- ✅ UI remains responsive during long operations (progress callbacks)

### Testing Requirements
- ✅ Unit tests achieve >80% coverage for new services
- ✅ Integration tests verify export → import round-trip
- ✅ UI tests verify all dialogs work correctly
- ✅ Manual testing confirms no regressions
- ✅ Performance tests for large datasets (500+ tasks)

### Documentation Requirements
- ✅ PHASE7_STATUS.md created with implementation summary
- ✅ README.md updated with import/export usage instructions
- ✅ Code comments explain complex operations (ID remapping, transaction handling)
- ✅ Settings tooltips guide users on advanced features

---

## Risk Mitigation

**Risk: Data loss during import/export**
- Mitigation: Transaction-based import with rollback, backup before DB restore, extensive validation

**Risk: Schema version incompatibility**
- Mitigation: Include version in metadata, reject newer versions, provide clear error messages

**Risk: Large file performance issues**
- Mitigation: Progress callbacks for UI responsiveness, test with 1000+ task datasets

**Risk: Theme stylesheet conflicts**
- Mitigation: Specific CSS selectors, test with all dialogs, fallback to default Qt theme

**Risk: ID conflicts in merge mode**
- Mitigation: Build ID mapping dictionary, remap foreign keys, extensive testing

**Risk: User accidentally resets data**
- Mitigation: Multi-step confirmation (type "RESET" + checkbox + final warning), no shortcut key, preview counts

---

## Notes

- Phase 6 already implemented 30+ settings, so infrastructure is mature
- Existing SettingsDialog provides proven pattern to follow
- JSON format chosen over CSV for relationship preservation
- SQLite backup provides simple file-level backup option
- Merge mode ID remapping is complex - allocate extra testing time
- Theme system uses Qt stylesheets (QSS) for flexibility
- Advanced settings target power users - include warnings

**End of Phase 7 Plan**
