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
  - [Running Tests](#running-tests)
  - [Project Structure](#project-structure)
  - [Current Development Status](#current-development-status)

## About the Project

In David Allen's popular *"Getting Things Done"* (GTD) system, strong emphasis is placed on filtering a to-do list to determine the "Next Action" that is appropriate for your current working environment (referred to as "Context"). In theory, this makes perfect sense: it is well-known that "multitasking" is counter-productive, and therefore people should strive to focus on doing one thing at a time. Therefore, THE core feature of this app is a Focus Mode that presents the user with one task at a time, hence the app's name-sake.

Note: In a true dogmatic GTD system, a user would have an inbox for all of their informational inputs, which would then be sorted into Actionable Inputs and Non-Actionable Inputs. This is why many practitioners of GTD insist on incorporating their system into an email inbox or filing system. In my opinion, this sorting just adds an unnecessary step for most people. This app assumes that users are inputting actual tasks, not unsorted Inputs.

---

**Several usability problems need to be addressed in this app:**

1. **Problem/Background:** Many do-to apps allow users to rank priority and urgency in an attempt to enforce a logical order of presentation, but in practice users often end up with a lot of high-priority / high-urgency tasks, defeating the purpose of ranking tasks in the first place.

   **Proposed Solution:** The app will attempt to resolve this issue by presenting the user with a list of two tasks that have equal top-ranked importance (highest priority and highest urgency), asking them to choose the task that is higher priority. The app will then decrement the other task's priority (by half a point by default, or by a user-specified value > 0). The app will continue this process, comparing the top-ranked tasks until the user has only one option or completes a task.
    - Priority will be scored on a 3-point scale, where High = 3, Medium = 2, and Low = 1
    - Urgency will be scored based on a count of days until the task due date. The task(s) with the lowest counts (including negative values for overdue tasks) shall be assigned an urgency score of 3, with the other tasks scored on a normalized scale (latest due date = 1).

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
python src\main.py
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
python src\main.py
```

## Development

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

**Next Phase: Phase 2 - MVP Focus Mode**

Implementing the core Focus Mode feature with:
- Priority and urgency calculation algorithms
- Task ranking system
- Single-task display UI
- Action buttons (Complete, Defer, Delegate, etc.)
- Basic task creation

See [implementation_plan.md](implementation_plan.md) for the full development roadmap.
