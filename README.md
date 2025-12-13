# OneTaskAtATime
**A focused, no-frills to-do list desktop application for Windows**

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![PyQt5](https://img.shields.io/badge/GUI-PyQt5-green.svg)](https://pypi.org/project/PyQt5/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Many users spend too much time managing task *lists*, when they should just pick a single task and execute it. The overarching goal of this app is to aid the user in focusing on one task.

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

1. **Problem/Background:** Many do-to apps allow users to rank priority and urgency in an attempt to enforce a logical order of presentation, but in practice users often end up with a lot of high-priority / high-urgency tasks, defeating the purpose of ranking tasks in the first place.

   **Proposed Solution:** The app resolves ties by presenting pairs of tasks with equal top-rank importance for comparison. When the user selects the higher-priority task, the losing task's Priority Adjustment is incremented using exponential decay: **PA += 0.5^N** (where N = number of comparison losses). This approach leverages Zeno's Paradox to ensure Priority Adjustment never reaches 1, preventing Effective Priority from reaching zero while progressively deprioritizing tasks that consistently lose comparisons.

   **Importance Calculation:**
   - **Effective Priority** = Base Priority - Priority Adjustment
   - **Base Priority**: User-configurable 3-point scale (High = 3, Medium = 2, Low = 1)
   - **Urgency**: Based on remaining days until due date (tasks with lowest day counts including overdue = 3, latest due date = 1)
   - **Importance** = Effective Priority × Urgency (max = 9)

   When Base Priority is changed, both Priority Adjustment and comparison loss count reset to zero. See [CLAUDE.md](CLAUDE.md) for complete algorithmic details.

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
- Importance scoring: `(base_priority - priority_adjustment) × urgency_score`
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

The comparison-based ranking system is now fully functional with:
- Side-by-side task comparison dialog with clean UI
- Exponential decay priority adjustment algorithm (PA += 0.5^N)
- Comparison history tracking in database
- Manual priority adjustment reset with user warnings
- Automatic reset when base priority changes
- Full integration with Focus Mode workflow
- 18 comprehensive unit tests (100% pass rate)

See [PHASE3_STATUS.md](PHASE3_STATUS.md) for details.

**Phase 4: Task Management Interface** 🔄 IN PROGRESS

The comprehensive task management interface is functional with additional enhancements in progress:

**Completed:**
- Task list view with sorting, filtering, and search (7 columns, multi-filter)
- Enhanced task form with all fields (contexts, tags, dates, delegation)
- Context management dialog (CRUD with list/form layout)
- Project tag management dialog (CRUD with color picker integration)
- Dependency selection dialog (circular dependency prevention)
- View switching between Focus Mode and Task List (Ctrl+F/Ctrl+L)
- Management menu for contexts and tags
- 18 comprehensive UI tests (100% pass rate)

**In Progress:**
1. Add tag assignment UI to New Task and Edit Task forms (project tags and context tags)
2. Add dependency assignment UI to task forms (select/create predecessors)
3. Add Context Tag column to task list view
4. Enhance State filter to support multiple selections
5. Add context tag filtering UI element
6. Add Importance column for sorting by calculated score
7. Add Start Date column for sorting
8. Implement multi-column sorting capability

See [PHASE4_STATUS.md](PHASE4_STATUS.md) for details.

**Next Phase: Phase 5 - Dependency & Blocker System**

Enhancing dependency management features:
- Dependency graph visualization
- Blocker creation from postpone dialog
- Subtask breakdown workflow
- Circular dependency detection UI feedback
- Integration with Focus Mode (block dependent tasks)

See [implementation_plan.md](implementation_plan.md) for the full development roadmap.
