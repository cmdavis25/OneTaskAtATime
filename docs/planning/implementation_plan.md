# OneTaskAtATime - Implementation Plan

## Executive Summary

This document outlines the comprehensive implementation plan for **OneTaskAtATime**, a focused desktop to-do list application for Windows. The app will be built using **Python 3.10+ and PyQt5**, with **SQLite3** for local data storage.

**Current State**: Documentation-only repository
**Target**: Production-ready Windows desktop application (v1.0.0)

## Table of Contents

- [Executive Summary](#executive-summary)
- [Technology Stack](#technology-stack)
  - [Core Technologies](#core-technologies)
  - [Key Dependencies](#key-dependencies)
  - [Rationale](#rationale)
- [Application Architecture](#application-architecture)
  - [File Structure](#file-structure)
  - [Key Components](#key-components)
- [Core Algorithms](#core-algorithms)
  - [Priority Calculation](#priority-calculation)
  - [Comparison Resolution](#comparison-resolution)
  - [Task Resurfacing](#task-resurfacing)
- [Implementation Phases](#implementation-phases)
  - [Phase 0: Project Setup](#phase-0-project-setup)
  - [Phase 1: Data Layer](#phase-1-data-layer)
  - [Phase 2: MVP Focus Mode](#phase-2-mvp-focus-mode)
  - [Phase 3: Comparison UI](#phase-3-comparison-ui)
  - [Phase 4: Task Management Interface](#phase-4-task-management-interface)
  - [Phase 5: Dependency & Blocker System](#phase-5-dependency--blocker-system)
  - [Phase 6: Resurfacing System](#phase-6-resurfacing-system)
  - [Phase 7: Settings & Customization](#phase-7-settings--customization)
  - [Phase 8: Polish & UX](#phase-8-polish--ux)
  - [Phase 9: Testing & QA](#phase-9-testing--qa)
  - [Phase 10: Release](#phase-10-release)
- [Critical Files to Implement](#critical-files-to-implement)
- [Testing Strategy](#testing-strategy)
  - [Unit Tests](#unit-tests-pytest)
  - [UI Tests](#ui-tests-pytest-qt)
  - [Integration Tests](#integration-tests)
- [Key Design Decisions](#key-design-decisions)
- [Success Metrics](#success-metrics)

---

## Technology Stack

### Core Technologies
- **Language**: Python 3.10+
- **GUI Framework**: PyQt5 (native Windows desktop experience)
- **Database**: SQLite3 (Python standard library)

### Key Dependencies
```
PyQt5>=5.15.0
python-dateutil>=2.8.0
pytest>=7.0.0
pytest-qt>=4.2.0
APScheduler>=3.10.0
win10toast>=0.9
```

### Rationale
- **Python**: Rapid development, readable code, rich ecosystem
- **PyQt5**: Native Windows widgets, mature framework, Qt Designer support
- **SQLite3**: No external dependencies, ACID compliance, single-file portability
- **Local-first**: Privacy-preserving, offline capability, no server costs

---

## Application Architecture

### File Structure
```
OneTaskAtATime/
├── src/
│   ├── main.py                   # Application entry point
│   ├── models/                   # Data models (Task, Context, etc.)
│   ├── database/                 # SQLite DAOs and schema
│   ├── algorithms/               # Priority, ranking, resurfacing logic
│   ├── ui/                       # PyQt5 widgets and dialogs
│   ├── services/                 # Business logic services
│   └── utils/                    # Helper functions
├── tests/                        # pytest test suite
├── resources/                    # Icons, database files
└── requirements.txt
```

### Key Components

**Models** (`src/models/`)
- Task dataclass with all fields (priority, urgency, state, dependencies)
- Context, ProjectTag, TaskComparison dataclasses
- Enums for TaskState and PostponeReasonType

**Database Layer** (`src/database/`)
- SQLite schema with tables for tasks, contexts, tags, dependencies
- DAO pattern for CRUD operations
- Migration system for schema updates

**Algorithms** (`src/algorithms/`)
- `priority.py`: Calculate urgency (1-3) and effective priority (Elo-based)
- `ranking.py`: Rank tasks by importance score (effective_priority × urgency)
- `comparison_service.py`: Resolve tied tasks through Elo-based user comparison
- `resurfacing.py`: Surface deferred/delegated/someday tasks

**UI Components** (`src/ui/`)
- `main_window.py`: QMainWindow with menu and navigation
- `focus_mode.py`: Core single-task display (QWidget)
- `comparison_dialog.py`: Side-by-side task comparison (QDialog)
- `task_list_view.py`: Sortable/filterable task table (QTableView)
- `task_form_dialog.py`: Create/edit task form (QDialog)

---

## Core Algorithms

### Importance Calculation
- **Base Priority**: 1 (Low), 2 (Medium), 3 (High)
- **Elo Rating**: Standard Elo system (starts at 1500, typically ranges 1000-2000)
- **Effective Priority**: Elo rating mapped to band based on Base Priority
  - High (base=3): effective priority ∈ [2.0, 3.0]
  - Medium (base=2): effective priority ∈ [1.0, 2.0]
  - Low (base=1): effective priority ∈ [0.0, 1.0]
- **Urgency Score**: 1-3 based on days until due date (earliest = 3, latest = 1)
- **Importance Score**: effective_priority × urgency_score (max = 9)

### Comparison Resolution (Elo System)
1. Get all tasks with top importance score (within epsilon = 0.01)
2. If single task: display in Focus Mode
3. If multiple tied: present pair for user comparison
4. Update both tasks' Elo ratings using standard Elo formula:
   - New Rating = Old Rating + K × (Actual Score - Expected Score)
   - K-factor: 32 for new tasks (< 10 comparisons), 16 for established tasks
5. Effective priority recalculated from new Elo rating within appropriate band
6. Repeat until single winner emerges

### Task Resurfacing
- **Deferred Tasks**: Surface when start_date arrives (check hourly)
- **Delegated Tasks**: Remind N days before follow_up_date (check daily)
- **Someday Tasks**: Review every N days since last resurface (configurable)
- **Notifications**: Windows toast notifications + in-app panel

---

## Implementation Phases

### Phase 0: Project Setup
- Set up Python virtual environment
- Install PyQt5 and dependencies
- Create project structure
- Initialize SQLite connection module
- Configure pytest and pytest-qt
- Create basic QMainWindow that launches

**Deliverable**: Skeleton app with empty window

**Status**: ✅ Complete - See [PHASE0_STATUS.md](../phase_reports/PHASE0_STATUS.md) for details

### Phase 1: Data Layer
- Create SQLite schema (8 tables with indexes)
- Build Task, Context, ProjectTag DAOs
- Implement all CRUD operations
- Write unit tests (85%+ coverage)
- Create seed data for development

**Deliverable**: Fully functional database layer

**Status**: ✅ Complete - See [PHASE1_STATUS.md](../phase_reports/PHASE1_STATUS.md) for details

### Phase 2: MVP Focus Mode
- Implement priority/urgency algorithms
- Implement task ranking algorithm
- Build Focus Mode UI (QWidget with task card)
- Add action buttons (Complete, Defer, Delegate, Someday, Trash)
- Create postpone dialog (QDialog with reason selection)
- Basic task creation form
- Test with various scenarios

**Success Criteria**: User sees top-priority task, can complete it, see next task appear

**Deliverable**: Functional MVP Focus Mode

**Status**: ✅ Complete - See [PHASE2_STATUS.md](../phase_reports/PHASE2_STATUS.md) for details

### Phase 3: Comparison UI
- Implement tie detection
- Build side-by-side comparison dialog (QHBoxLayout)
- Implement Elo rating system with tiered base priority bands
- Store comparison history in database
- Add menu option to reset Elo ratings
- Configure K-factors (32 for new tasks, 16 for established)

**Deliverable**: Functional Elo-based priority conflict resolution

**Status**: ✅ Complete - See [PHASE3_STATUS.md](../phase_reports/PHASE3_STATUS.md) for details

### Phase 4: Task Management Interface
- Build task list view (QTableView with sorting/filtering)
- Build comprehensive task edit form (QFormLayout)
- Context management dialog
- Project tag management dialog
- Dependency selection dialog
- Search and bulk actions
- Project tag and context tag assignment UI in New Task and Edit Task forms
- Dependency assignment UI in task forms (select/create predecessors)
- Context Tag column in task list view
- Multi-select State filter supporting multiple state selections
- Context tag filtering UI element
- Importance column for sorting by calculated importance score
- Start Date column for sorting by start date
- Multi-column sorting capability (Shift+Click)
- User-adjustable column widths in task list view

**Deliverable**: Full task CRUD interface with enhanced filtering and tag management

**Status**: ✅ Complete - See [PHASE4_STATUS.md](../phase_reports/PHASE4_STATUS.md) for details

### Phase 5: Dependency & Blocker System
- Dependency graph visualization
- Blocker creation from postpone dialog
- Subtask breakdown workflow
- Circular dependency detection
- Postpone analytics dashboard
- Smart postpone suggestions

**Deliverable**: Complete dependency management

**Detailed Plan**: See [phase_5_plan.md](phase_5_plan.md)

**Status**: ✅ Complete - See [PHASE5_STATUS.md](../phase_reports/PHASE5_STATUS.md) for details

### Phase 6: Resurfacing System
- Implement APScheduler background jobs
- Build Windows notification system (win10toast)
- In-app notification panel
- Resurfacing settings dialog
- Review delegated tasks dialog
- Review someday tasks dialog
- Activated tasks display dialog
- Postponement pattern intervention
- 17 new user settings
- Notifications table and DAO
- Complete notification management system

**Deliverable**: Automated task resurfacing and notification system

**Detailed Plan**: See [phase_6_plan.md](phase_6_plan.md)

**Status**: ✅ Complete - See [PHASE6_STATUS.md](../phase_reports/PHASE6_STATUS.md) for details

### Phase 7: Settings & Customization
- Settings dialog (comparison decrement, intervals, theme)
- Import/export (JSON backup)
- Data reset functionality
- Theme system (light/dark/system modes)
- Advanced Elo tuning settings
- Multi-step nuclear reset with safety confirmations

**Deliverable**: User configuration system

**Detailed Plan**: See [phase_7_plan.md](phase_7_plan.md)

**Status**: ✅ Complete - See [PHASE7_STATUS.md](../phase_reports/PHASE7_STATUS.md) for details

### Phase 8: Polish & UX
- Keyboard shortcuts
- Undo/redo
- Task history
- Onboarding flow
- Help tooltips
- Error handling
- Accessibility audit
- WhatsThis contextual help system
- Robust dialog geometry management
- Enhanced workflow commands with proper undo/redo
- UI/UX improvements (checkboxes, keyboard navigation, compact layouts)
- Subtask breakdown redesign with full task data entry
- Focus Mode layout stability improvements
- Theme consistency and styling improvements

**Deliverable**: Production-ready UX with comprehensive polish

**Detailed Plan**: See [phase_8_plan.md](phase_8_plan.md)

**Status**: ✅ Complete - See [PHASE8_STATUS.md](../phase_reports/PHASE8_STATUS.md) for details
- Initial Phase 8: January 3, 2026
- Post-Phase 8 Enhancements: January 3-12, 2026
- 15 additional commits with significant improvements
- 47+ files modified, 2,000+ lines added

### Phase 9: Testing & QA
- E2E tests for critical flows
- Performance testing (10,000+ tasks)
- Bug fixing sprint

**Deliverable**: Stable, tested application

**Status**: ✅ Complete (2026-01-19)
- E2E test suite: 47/47 passing (100%)
- UI test pass rate: 92.1% (431/468)
- Overall test suite: ~95% pass rate
- Error elimination: 100% (0 errors)
- CI/CD ready: Full automation verified
- Bugs fixed: 26 bugs discovered and resolved (100% resolution)
- Production ready: All critical functionality tested and operational
- Latest improvement: PostponeDialog fixes (+13 tests, 89.3% → 92.1%)

### Phase 10: Release
- User documentation
  - Fix Help Contents dialog search bar to actually filter/narrow down results
- Create Windows installer
- Demo video/screenshots
- Beta testing
- v1.0.0 release

**Deliverable**: Production release

---

## Critical Files to Implement

1. **src/algorithms/priority.py** - Elo-based priority/urgency calculation (drives Focus Mode)
2. **src/services/comparison_service.py** - Elo-based comparison ranking
3. **src/database/schema.py** - SQLite schema definitions
4. **src/ui/focus_mode.py** - Main Focus Mode widget (core feature)
5. **src/algorithms/resurfacing.py** - Task resurfacing logic
6. **src/database/task_dao.py** - Task CRUD operations
7. **src/ui/main_window.py** - Main application window

---

## Testing Strategy

### Unit Tests (pytest)
- Algorithm correctness (priority, urgency, ranking)
- Database DAO operations
- Business logic services
- **Target**: 85%+ code coverage

### UI Tests (pytest-qt)
- Focus Mode workflows
- Comparison dialog interactions
- Task creation/editing
- Dependency management

### Integration Tests
- Database operations with SQLite
- Resurfacing service with scheduler
- End-to-end task lifecycle

---

## Key Design Decisions

1. **Python + PyQt5**: Native Windows experience, simpler than web tech
2. **SQLite3**: Local-first, no server required, single-file backup
3. **Computed scores**: Calculate priority/urgency on-demand (always accurate)
4. **Block dependencies**: Don't show blocked tasks in Focus Mode
5. **Model/View pattern**: Use for task list performance
6. **APScheduler**: Background jobs for resurfacing without blocking UI

---

## Success Metrics

✅ **Focus Mode**: Presents ONE task at a time
✅ **Priority resolution**: Elo-based comparison ranking eliminates "all high priority" problem
✅ **No purgatory**: Strategic resurfacing of deferred/delegated/someday tasks (Phase 6 complete)
✅ **Flat structure**: Tags instead of hierarchies
✅ **Blocker awareness**: Capture postpone reasons and create dependencies
✅ **Automated resurfacing**: Background scheduler prevents tasks from languishing
✅ **Dual notifications**: Windows toast + in-app panel for maximum visibility
✅ **Complete audit trail**: Full task history tracking with timeline view (Phase 8 complete)
✅ **Professional UX**: Undo/redo, keyboard shortcuts, contextual help, accessibility (Phase 8 complete)
✅ **Robust window management**: All dialogs persist size/position (Phase 8 complete)
✅ **Enhanced workflows**: Atomic undo/redo for complex operations (Phase 8 complete)

**Ultimate Goal**: Users spend more time executing tasks, less time managing lists.
