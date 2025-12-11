# OneTaskAtATime - Implementation Plan

## Executive Summary

This document outlines the comprehensive implementation plan for **OneTaskAtATime**, a focused desktop to-do list application for Windows. The app will be built using **Python 3.10+ and PyQt5**, with **SQLite3** for local data storage.

**Current State**: Documentation-only repository
**Target**: Production-ready Windows desktop application (v1.0.0)
**Timeline**: 17 weeks to release

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
- `priority.py`: Calculate urgency (1-3) and effective priority
- `ranking.py`: Rank tasks by total score (priority + urgency)
- `comparison.py`: Resolve tied tasks through user comparison
- `resurfacing.py`: Surface deferred/delegated/someday tasks

**UI Components** (`src/ui/`)
- `main_window.py`: QMainWindow with menu and navigation
- `focus_mode.py`: Core single-task display (QWidget)
- `comparison_dialog.py`: Side-by-side task comparison (QDialog)
- `task_list_view.py`: Sortable/filterable task table (QTableView)
- `task_form_dialog.py`: Create/edit task form (QDialog)

---

## Core Algorithms

### Priority Calculation
- **Base Priority**: 1 (Low), 2 (Medium), 3 (High)
- **Priority Adjustment**: Decremented through comparison (default -0.5 per loss)
- **Effective Priority**: base_priority - priority_adjustment
- **Urgency Score**: 1-3 based on days until due date (earliest = 3, latest = 1)
- **Total Score**: effective_priority + urgency_score (max = 6)

### Comparison Resolution
1. Get all tasks with top score (within epsilon = 0.01)
2. If single task: display in Focus Mode
3. If multiple tied: present pair for user comparison
4. Winner unchanged, loser decremented by configurable amount
5. Repeat until single winner emerges

### Task Resurfacing
- **Deferred Tasks**: Surface when start_date arrives (check hourly)
- **Delegated Tasks**: Remind N days before follow_up_date (check daily)
- **Someday Tasks**: Review every N days since last resurface (configurable)
- **Notifications**: Windows toast notifications + in-app panel

---

## Implementation Phases

### Phase 0: Project Setup (Week 1)
- Set up Python virtual environment
- Install PyQt5 and dependencies
- Create project structure
- Initialize SQLite connection module
- Configure pytest and pytest-qt
- Create basic QMainWindow that launches

**Deliverable**: Skeleton app with empty window

### Phase 1: Data Layer (Week 2-3)
- Create SQLite schema (8 tables with indexes)
- Build Task, Context, ProjectTag DAOs
- Implement all CRUD operations
- Write unit tests (85%+ coverage)
- Create seed data for development

**Deliverable**: Fully functional database layer

### Phase 2: MVP Focus Mode (Week 4-6)
- Implement priority/urgency algorithms
- Implement task ranking algorithm
- Build Focus Mode UI (QWidget with task card)
- Add action buttons (Complete, Defer, Delegate, Someday, Trash)
- Create postpone dialog (QDialog with reason selection)
- Basic task creation form
- Test with various scenarios

**Success Criteria**: User sees top-priority task, can complete it, see next task appear

### Phase 3: Comparison UI (Week 7)
- Implement tie detection
- Build side-by-side comparison dialog (QHBoxLayout)
- Store comparison history in database
- Add menu option to reset adjustments

**Deliverable**: Functional priority conflict resolution

### Phase 4: Task Management Interface (Week 8-9)
- Build task list view (QTableView with sorting/filtering)
- Build comprehensive task edit form (QFormLayout)
- Context management dialog
- Project tag management dialog
- Dependency selection dialog
- Search and bulk actions

**Deliverable**: Full task CRUD interface

### Phase 5: Dependency & Blocker System (Week 10)
- Dependency graph visualization
- Blocker creation from postpone dialog
- Subtask breakdown workflow
- Circular dependency detection

**Deliverable**: Complete dependency management

### Phase 6: Resurfacing System (Week 11-12)
- Implement APScheduler background jobs
- Build Windows notification system (win10toast)
- In-app notification panel
- Resurfacing settings dialog
- "Review someday tasks" modal

**Deliverable**: Automated task resurfacing

### Phase 7: Settings & Customization (Week 13)
- Settings dialog (comparison decrement, intervals, theme)
- Import/export (JSON backup)
- Data reset functionality

**Deliverable**: User configuration system

### Phase 8: Polish & UX (Week 14-15)
- Keyboard shortcuts
- Undo/redo
- Task history
- Onboarding flow
- Help tooltips
- Error handling
- Accessibility audit

**Deliverable**: Production-ready UX

### Phase 9: Testing & QA (Week 16)
- E2E tests for critical flows
- Performance testing (10,000+ tasks)
- Bug fixing sprint

**Deliverable**: Stable, tested application

### Phase 10: Release (Week 17)
- User documentation
- Create Windows installer
- Demo video/screenshots
- Beta testing
- v1.0.0 release

**Deliverable**: Production release

---

## Critical Files to Implement

1. **src/algorithms/priority.py** - Priority/urgency calculation (drives Focus Mode)
2. **src/algorithms/comparison.py** - Comparison-based ranking
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
✅ **Priority resolution**: Comparison-based ranking eliminates "all high priority" problem
✅ **No purgatory**: Strategic resurfacing of deferred/delegated/someday tasks
✅ **Flat structure**: Tags instead of hierarchies
✅ **Blocker awareness**: Capture postpone reasons and create dependencies

**Ultimate Goal**: Users spend more time executing tasks, less time managing lists.

---

## Next Steps

1. Install Python 3.10+
2. Create virtual environment
3. Set up project structure
4. Install dependencies (requirements.txt)
5. Begin Phase 0 (Week 1)

This plan provides a clear path from documentation to production-ready Windows desktop application in 17 weeks.
