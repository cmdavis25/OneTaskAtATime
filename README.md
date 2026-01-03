# OneTaskAtATime
**A focused, no-frills to-do list desktop application for Windows**

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![PyQt5](https://img.shields.io/badge/GUI-PyQt5-green.svg)](https://pypi.org/project/PyQt5/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Many users spend too much time managing task *lists*, when they should just pick a single task and execute it. The overarching goal of this app is to aid the user in focusing on one task.

⚠ **Warning (!!!)** ⚠ : **This project was vibe-coded (with love and care) using Claude Code. Do NOT assume that this code is bug-free... it very likely isn't. Use at your own risk!**

## Table of Contents

- [About the Project](#about-the-project)
- [Quick Start](#quick-start)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Manual Setup](#manual-setup)
- [Development](#development)
  - [Database Architecture](#database-architecture)
  - [Running Tests](#running-tests)
  - [Project Structure](#project-structure)
  - [Current Development Status](#current-development-status)

## About the Project

In David Allen's popular *"Getting Things Done"* (GTD) system, strong emphasis is placed on filtering a to-do list to determine the "Next Action" that is appropriate for your current working environment (referred to as "Context"). In theory, this makes perfect sense: it is well-known that "multitasking" is counter-productive, and therefore people should strive to focus on doing one thing at a time. Therefore, THE core feature of this app is a Focus Mode that presents the user with one task at a time, hence the app's name-sake.

Note: In a true dogmatic GTD system, a user would have an inbox for all of their informational inputs, which would then be sorted into Actionable Inputs and Non-Actionable Inputs. This is why many practitioners of GTD insist on incorporating their system into an email inbox or filing system. In my opinion, this sorting just adds an unnecessary step for most people. This app assumes that users are inputting actual tasks, not unsorted Inputs.

---

**Several usability problems need to be addressed in this app:**

1. **Problem/Background:** Many to-do apps allow users to rank priority and urgency in an attempt to enforce a logical order of presentation, but in practice users often end up with a lot of high-priority / high-urgency tasks, defeating the purpose of ranking tasks in the first place.

   **Proposed Solution:** The app resolves ties by presenting pairs of tasks with equal top-rank importance for comparison using an **Elo rating system**. When users compare two tasks, both tasks' Elo ratings are updated using the standard Elo formula. This rating is then mapped to an effective priority within strict bands based on the task's base priority tier.

   **Importance Calculation:**
   - **Effective Priority** = Elo rating mapped to band based on Base Priority
     - High (base=3): effective priority ∈ [2.0, 3.0]
     - Medium (base=2): effective priority ∈ [1.0, 2.0]
     - Low (base=1): effective priority ∈ [0.0, 1.0]
   - **Base Priority**: User-configurable 3-point scale (High = 3, Medium = 2, Low = 1)
   - **Elo Rating**: Standard Elo system (starts at 1500, typically ranges 1000-2000)
   - **Urgency**: Based on remaining days until due date (tasks with lowest day counts including overdue = 3, latest due date = 1)
   - **Importance** = Effective Priority × Urgency (max = 9)

   This system ensures that all High tasks rank above all Medium tasks, and all Medium tasks rank above all Low tasks, while Elo refines ranking within each tier. When Base Priority is changed, both Elo rating and comparison count reset to defaults. See [CLAUDE.md](CLAUDE.md) for complete algorithmic details.

2. **Problem/Background:** Tasks that are not immediately actionable or low-priority/low-urgency tend to end up in a purgatory state, left to rot and fester. GTD argues that these tasks should be sorted into the following states:
    - Deferred Tasks, which can only be completed after a specified Start Date
    - Delegated Tasks, which are assigned to another person and require a scheduled follow-up conversation (which in and of itself is a separate Deferred Task)
    - Someday/Maybe, for tasks that are not currently actionable, but *might* become actionable at an unknown date in the future
    - Trash, for tasks that the user deems unnecessary and which therefore should be removed from consideration

    The problem with this bucketing approach is that most apps fail to routinely resurface tasks in those buckets to the user.

    **Proposed Solution:** This app will attempt to fix that problem by resurfacing tasks in those buckets strategically.

3. **Problem/Background:** In attempting to execute the Next Action, GTD practitioners often find that their next task is comprised of multiple complex steps -- and therefore must be considered as a collection of tasks within a "Project". The heirarchy imposed can lead to difficulties with both prioritization and navigation, as tasks become buried within Projects, Phases, and ever-deeper levels of "organization". Task heirarchies add needless complexity and are detrimental to productivity.

   **Proposed Solution:** While there may be some value in tracking Projects as a form of tag meta-data (for filtering purposes), the structure of the master task list should be kept flat.Similarly, organizing tasks by work environment "Context" should also be done with tagging, rather than a hierarchy. A task may have only one Context, while a given Context may apply to as many tasks as the user desires.

4. **Problem/Background:** Tasks can also be difficult to complete due to various blockers and/or dependencies on other tasks. In failing to confront users when they delay a task, most to-do list apps fail to capture the user's reason for doing so.

   **Proposed Solution:** This app proposes to fix this problem by presenting users with prompts to explain their decision when they delay a task.
    - If a user responds (with a button) that a delayed task involves multiple subtasks, the interface should prompt them to enter those tasks, pick the Next Action and then delete the original task. Again, the goal here is to reduce task heirarchy.
    - If a user responds (with a button) that they encountered a blocker, the interface should prompt the user to create a new task to log and address that blocker.
    - If a user responds (with a button) that the task depends on completion of one or more tasks, the interface should prompt the user to choose or create the upstream task(s).

## Quick Start

### Prerequisites
- Python 3.10 or higher
- Windows 10/11 (primary target platform)

### Installation

1. Clone this repository:
```bash
git clone https://github.com/cmdavis25/OneTaskAtATime.git
```
```bash
cd OneTaskAtATime
```

2. Run the setup script:
```bash
setup.bat
```

This will:
- Create a Python virtual environment
- Install all required dependencies
- Set up the project structure

3. Activate the virtual environment:
```bash
onetask_env\Scripts\activate
```

4. Run the application:
```bash
python -m src.main
```

### Manual Setup

If you prefer manual setup:

```bash
# Create virtual environment
python -m venv onetask_env
```
```bash
# Activate virtual environment
onetask_env\Scripts\activate
```
```bash
# Install dependencies
pip install -r requirements.txt
```
```bash
# Run application
python -m src.main
```

## Development

### Database Architecture

The application uses an **SQLite database** with **8 tables** that work together to support the GTD-inspired workflow:

**Core Entities:**
- **tasks** - Main task storage with priority system, urgency tracking, and state management
- **contexts** - Work environment filters (@computer, @phone, @errands, etc.)
- **project_tags** - Flat project organization using tags (no hierarchies)

**Relationships & History:**
- **task_project_tags** - Many-to-many junction for tasks and projects
- **dependencies** - Task blocker tracking with circular dependency prevention
- **task_comparisons** - History of priority adjustments from user comparisons
- **postpone_history** - Tracks when/why tasks were delayed to surface blockers
- **settings** - Type-safe application configuration storage

**Key Features:**
- Importance scoring: `effective_priority × urgency_score` (effective priority calculated from Elo rating)
- Elo-based comparison system within base priority bands
- Automatic resurfacing of deferred, delegated, and someday tasks
- Circular dependency detection using depth-first search
- 12 strategic indexes for query performance

See [database_explanation.md](database_explanation.md) for complete schema details, relationship diagrams, and data flow examples.

### Running Tests

```bash
# Activate virtual environment
onetask_env\Scripts\activate
```
```bash
# Run all tests with coverage
pytest
```
```bash
# Run specific test categories
pytest -m unit          # Unit tests only
```
```bash
pytest -m integration   # Integration tests only
```
```bash
pytest -m ui            # UI tests only
```

### Project Structure

```
OneTaskAtATime/
├── src/                    # Application source code
│   ├── main.py            # Entry point
│   ├── models/            # Data models
│   ├── database/          # SQLite DAOs and schema
│   ├── algorithms/        # Priority, ranking, resurfacing
│   ├── ui/                # PyQt5 widgets and dialogs
│   ├── services/          # Business logic services
│   └── utils/             # Helper functions
├── tests/                 # Test suite
├── resources/             # Database and assets
└── requirements.txt       # Python dependencies
```

### Current Development Status

**Phase 0: Project Setup** ✅ COMPLETE

The project skeleton is now in place with:
- Project directory structure
- PyQt5 application framework
- SQLite database connection module
- Basic main window with menu bar
- pytest configuration and test framework

See [PHASE0_STATUS.md](PHASE0_STATUS.md) for details.

**Phase 1: Data Layer** ✅ COMPLETE

The database layer is fully functional with:
- Complete SQLite schema (8 tables, 12 indexes)
- Data models (Task, Context, ProjectTag, Dependency, etc.)
- Full DAO layer with CRUD operations
- Circular dependency detection
- Type-safe settings storage
- 59 comprehensive unit tests
- Seed data script for development

See [PHASE1_STATUS.md](PHASE1_STATUS.md) for details.

**Phase 2: MVP Focus Mode** ✅ COMPLETE

The core Focus Mode feature is now functional with:
- Priority and urgency calculation algorithms (Importance = Priority × Urgency)
- Task ranking system with tie detection
- Single-task display UI with clean, distraction-free design
- Action buttons (Complete, Defer, Delegate, Someday, Trash)
- Postpone dialogs with reason capture
- Basic task creation form
- Service layer coordinating business logic
- 43 comprehensive unit tests (100% pass rate)

See [PHASE2_STATUS.md](PHASE2_STATUS.md) for details.

**Phase 3: Comparison-Based Priority Resolution** ✅ COMPLETE

The Elo-based comparison ranking system is now fully functional with:
- Side-by-side task comparison dialog with clean UI
- Elo rating system with tiered base priority bands
- Standard Elo formula with configurable K-factors (32 for new tasks, 16 for established)
- Comparison history tracking in database
- Manual Elo rating reset with user warnings
- Automatic reset when base priority changes
- Full integration with Focus Mode workflow
- 20+ comprehensive unit tests (100% pass rate)

See [PHASE3_STATUS.md](PHASE3_STATUS.md) for details.

**Phase 4: Task Management Interface** ✅ COMPLETE

The comprehensive task management interface is fully functional with:
- Task list view with sorting, filtering, and search (9 columns with user-adjustable widths)
- Enhanced task form with all fields (contexts, tags, dates, delegation)
- Context management dialog (CRUD with list/form layout)
- Project tag management dialog (CRUD with color picker integration)
- Dependency selection dialog (circular dependency prevention)
- Tag assignment UI in New Task and Edit Task forms (project tags and context tags)
- Dependency assignment UI in task forms (select/create predecessors)
- Multi-select State filter supporting multiple state selections
- Context tag filtering UI element with dropdown selection
- Importance column displaying calculated priority scores
- Start Date column for deferred task visibility
- Multi-column sorting capability
- View switching between Focus Mode and Task List (Ctrl+F/Ctrl+L)
- Management menu for contexts and tags
- 18 comprehensive UI tests (100% pass rate)

See [PHASE4_STATUS.md](PHASE4_STATUS.md) for details.

**Phase 5: Dependency & Blocker System** ✅ COMPLETE

The postpone workflow system is now fully functional with core workflows AND enhanced features:

**Core Workflows:**
- Postpone history tracking in database (PostponeHistoryDAO)
- Three integrated workflows triggered from postpone dialog:
  - Blocker creation (new or existing task with field inheritance)
  - Dependency management (link to existing upstream tasks)
  - Subtask breakdown (split complex tasks with optional deletion)
- Field inheritance patterns (priority, urgency, organization preserved)
- Visual dependency indicators in task list (⛔ icon with tooltips)
- Inline workflow execution (blocker/dependency/subtask dialogs appear within defer flow)
- Postpone recording integrated into defer and delegate operations

**Enhanced Features:**
- **Pattern Detection & Reflection System**: Mandatory reflection dialogs when postpone patterns detected (2nd+ same reason or 3rd+ total postpones)
- **Dependency Graph Visualization**: Text-based tree view of task dependency chains with circular detection (right-click → "View Dependency Graph")
- **Analytics Dashboard**: 4-panel postpone analytics (reason breakdown, most postponed tasks, recent activity, action summary)
- **Disposition Actions**: Direct state changes from reflection (Someday/Maybe, Trash) to resolve chronic patterns
- **Smart Time Formatting**: Relative time display ("2 hr ago", "Yesterday at 3:00 PM")
- **Export Functionality**: Save dependency graphs to text files

See [PHASE5_STATUS.md](PHASE5_STATUS.md) for complete details.

**Phase 6: Task Resurfacing and Notification System** ✅ COMPLETE

The automated resurfacing and notification system is now fully functional:

**Background Automation:**
- **APScheduler Integration**: 4 automated background jobs (deferred checks, delegated follow-ups, someday reviews, postponement analysis)
- **Immediate Startup Checks**: Runs deferred/delegated checks on app launch
- **Dynamic Settings Reload**: Intervals adjustable without restart
- **Graceful Shutdown**: Clean scheduler shutdown on app close

**Dual Notification Channels:**
- **Windows Toast Notifications**: Native OS notifications (Windows 10/11)
- **In-App Notification Panel**: Cross-platform panel with unread badge, expandable list, per-notification actions
- **User-Configurable**: Enable/disable each channel independently

**Resurfacing Features:**
- **Deferred Task Auto-Activation**: Tasks with start_date ≤ today automatically activate (hourly check, configurable)
- **Delegated Task Reminders**: Follow-up prompts on/after follow_up_date (daily at 9 AM, configurable)
- **Someday/Maybe Reviews**: Periodic review dialog every N days (default: 7 days, configurable)
- **Postponement Intervention**: Pattern detection with notifications when threshold exceeded (default: 3 postponements)

**Review Dialogs:**
- **ReviewDelegatedDialog**: Review delegated tasks with Activate/Complete/Extend actions
- **ReviewSomedayDialog**: Review Someday tasks with Activate/Keep/Trash actions
- **ActivatedTasksDialog**: Display auto-activated deferred tasks with details
- **SettingsDialog**: 4-tab comprehensive settings (Resurfacing, Notifications, Triggers, Intervention)

**Database & Services:**
- **Notifications Table**: Persistent notification storage with read/unread tracking
- **17 New Settings**: Complete configuration for intervals, channels, and thresholds
- **NotificationManager**: Centralized notification creation and delivery
- **ResurfacingService**: Business logic for all resurfacing scenarios

**Integration:**
- Settings menu item (Ctrl+,) for runtime configuration
- Focus Mode and Task List auto-refresh on state changes
- No UI blocking during background jobs
- Thread-safe Qt signal communication

See [PHASE6_STATUS.md](PHASE6_STATUS.md) for complete details.

**Phase 7: Settings & Customization** ✅ COMPLETE

The final phase delivers comprehensive data management and customization features:

**Theme System:**
- **Light/Dark Themes**: Professional Qt stylesheets with complete widget coverage
- **System Detection**: Automatic Windows theme detection via registry
- **Font Customization**: Adjustable base font size (8-16pt)
- **Instant Application**: Theme changes apply immediately on settings save

**Data Export:**
- **JSON Export**: Full database export with structured schema (tasks, contexts, tags, dependencies, comparisons, history, notifications, settings)
- **Database Backup**: Direct SQLite file backup for disaster recovery
- **Progress Tracking**: Threaded export with real-time progress bar
- **Metadata Preservation**: Export date, app version, schema version tracking
- **File Menu Integration**: Quick access via Ctrl+E

**Data Import:**
- **Replace Mode**: Nuclear replacement of all data with validation
- **Merge Mode**: Smart ID conflict resolution with automatic remapping
- **Schema Validation**: Version compatibility checking (reject newer schemas)
- **File Preview**: Summary display before import (date, version, counts)
- **Transaction Safety**: Automatic rollback on error
- **Relationship Preservation**: Maintains all foreign key references during merge
- **File Menu Integration**: Quick access via Ctrl+I

**Nuclear Reset:**
- **Multi-Step Verification**: Triple confirmation process
  1. Real-time deletion summary
  2. Type "RESET" exactly
  3. Acknowledge permanence checkbox
  4. Final system warning dialog
- **Selective Deletion**: Choose to preserve contexts, tags, and/or settings
- **Detailed Reporting**: Shows counts of deleted items
- **Transaction-Based**: Safe atomic operation with rollback protection
- **Tools Menu Integration**: No keyboard shortcut (prevents accidents)

**Advanced Settings:**
- **Elo K-Factors**: Tune comparison sensitivity for new (16-64) and established (8-32) tasks
- **Threshold Configuration**: Set comparison count before K-factor transition (5-20)
- **Epsilon Tuning**: Adjust tie detection threshold (0.001-0.1)
- **Visual Reference**: Read-only Elo band ranges display
- **Reset to Defaults**: One-click restoration of recommended values

**Settings Dialog Expansion:**
- **6 Total Tabs**: Resurfacing, Notifications, Triggers, Intervention, Theme, Advanced
- **30+ Settings**: Complete application configuration
- **Tooltips**: Helpful guidance for advanced features
- **Persistent Storage**: All settings saved to database

**Testing:**
- **50+ Unit Tests**: Comprehensive coverage of ExportService, ImportService, DataResetService
- **Export/Import Roundtrip**: Verified data integrity
- **Edge Case Handling**: Empty databases, missing files, schema mismatches
- **Transaction Testing**: Rollback safety verification

See [PHASE7_STATUS.md](PHASE7_STATUS.md) for complete details.

---

## Application Complete

**OneTaskAtATime** is now feature-complete with all 7 planned phases implemented:

✅ Phase 0: Project Setup
✅ Phase 1: Data Layer
✅ Phase 2: MVP Focus Mode
✅ Phase 3: Comparison-Based Priority Resolution
✅ Phase 4: Task Management Interface
✅ Phase 5: Dependency & Blocker System
✅ Phase 6: Task Resurfacing and Notification System
✅ **Phase 7: Settings & Customization**

**Total Project Stats:**
- **~15,000+ lines of code**
- **150+ comprehensive unit tests**
- **Complete GTD-inspired task management system**
- **Professional UI with light/dark themes**
- **Full data portability and backup capabilities**

**Future Enhancements (Potential):**
- Advanced analytics dashboard (completion trends, time-to-completion metrics)
- Search and filter enhancements (full-text search, saved filter presets)
- Scheduled automatic backups
- Cloud backup integration
- Theme editor and custom theme creation
- Export filtering (date ranges, specific states)
- Keyboard shortcut customization

See [implementation_plan.md](implementation_plan.md) for the full development roadmap.
