# OneTaskAtATime User Guide

**Version:** 1.0.0
**Last Updated:** 2026-01-25

Welcome to OneTaskAtATime, a focused task management application designed to help you execute one task at a time instead of endlessly organizing lists. This guide will help you master the application and boost your productivity.

---

## Table of Contents

1. [Introduction and Getting Started](#1-introduction-and-getting-started)
2. [Creating and Managing Tasks](#2-creating-and-managing-tasks)
3. [Understanding the Priority System](#3-understanding-the-priority-system)
4. [Task States Explained](#4-task-states-explained)
5. [Using Focus Mode](#5-using-focus-mode)
6. [Postpone Handling and Dependencies](#6-postpone-handling-and-dependencies)
7. [Task Resurfacing System](#7-task-resurfacing-system)
8. [Task List View](#8-task-list-view)
9. [Comparison Dialog](#9-comparison-dialog)
10. [Data Management](#10-data-management)
11. [Customization and Settings](#11-customization-and-settings)
12. [Keyboard Shortcuts Reference](#12-keyboard-shortcuts-reference)
13. [Tips and Best Practices](#13-tips-and-best-practices)
14. [Troubleshooting Quick Reference](#14-troubleshooting-quick-reference)
15. [Getting Help](#15-getting-help)

---

## 1. Introduction and Getting Started

### What is OneTaskAtATime?

OneTaskAtATime is a desktop task management application built on a simple philosophy: **stop managing lists, start executing tasks**. Many productivity apps overwhelm users with complex hierarchies, endless categorization, and feature bloat. OneTaskAtATime takes a different approach.

The core feature is **Focus Mode**, which presents you with exactly one task at a time—the most important thing you should be working on right now. No distractions, no decision fatigue, just focused execution.

### Core Philosophy

OneTaskAtATime is inspired by David Allen's "Getting Things Done" (GTD) methodology but simplifies it:

- **Single-task focus**: Stop juggling multiple tasks mentally. Focus Mode shows you one task.
- **Flat structure**: No nested projects or complex hierarchies. Use tags to organize.
- **Smart prioritization**: An Elo rating system (like chess rankings) ensures the right task bubbles to the top.
- **Blocker awareness**: The app asks why you're delaying tasks, helping surface dependencies and blockers.
- **Task resurfacing**: Deferred and delegated tasks automatically resurface when needed, preventing tasks from being forgotten.

### System Requirements

**Minimum:**
- Windows 11 (Windows 10 may work but is untested)
- 2 GB RAM (4 GB recommended)
- 150 MB disk space
- 1280x720 display resolution (1920x1080 recommended)

**Supported Platforms:**
- Windows 11 Home/Pro/Enterprise 64-bit
- Windows 10 version 1909+ (expected to work, not formally tested)

**Not Supported:**
- Windows 8.1 or earlier
- Linux (planned for v1.2)
- macOS (planned for v1.3)

### Installation Quick Reference

**Method 1: Windows Installer (Recommended)**
1. Download `OneTaskAtATime-1.0.0-Setup.exe` from GitHub Releases
2. Run the installer
3. Follow the installation wizard
4. Launch from Start Menu or desktop shortcut

**Method 2: From Source (Developers)**
1. Clone the repository: `git clone https://github.com/cmdavis25/OneTaskAtATime.git`
2. Run setup script: `setup.bat`
3. Activate virtual environment: `onetask_env\Scripts\activate`
4. Launch: `python -m src.main`

See [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) for detailed installation instructions.

### First Launch

When you first launch OneTaskAtATime:

1. **Database Creation**: The app creates a local database at `%APPDATA%\OneTaskAtATime\onetaskattime.db`
2. **Default Settings**: Sensible defaults are applied (Light theme, medium font, hourly resurfacing checks)
3. **Empty State**: You'll see an empty task list with a prompt to create your first task

**What to do first:**
1. Press `Ctrl+N` to create your first task
2. Add 3-5 tasks to get started
3. Press `Ctrl+2` to switch to Task List, `Ctrl+1` to switch back to Focus Mode
4. Start working on your highest-priority task

---

## 2. Creating and Managing Tasks

### Creating a New Task

**Keyboard Shortcut:** `Ctrl+N`

**Steps:**
1. Press `Ctrl+N` or click **File → New Task**
2. Fill in the task details (see fields below)
3. Click **OK** to save

**Task Fields:**

- **Title** (required): Brief description of the task (e.g., "Write quarterly report")
- **Description** (optional): Detailed notes, context, or instructions
- **Base Priority** (required): High, Medium, or Low
  - High: Critical, urgent, or high-impact tasks
  - Medium: Important but not urgent
  - Low: Nice-to-have, low-impact tasks
- **Due Date** (optional): When the task must be completed
  - Click calendar icon to select date
  - Affects urgency calculation (tasks due sooner are more urgent)
- **Start Date** (optional): When the task becomes actionable
  - Tasks with future start dates are automatically **Deferred**
  - They resurface and become **Active** when start date arrives
- **Context** (optional): Work environment or mode required
  - Examples: `@computer`, `@phone`, `@office`, `@home`, `@errands`
  - Each task can have only one context
  - Click **Manage Contexts** button to create new contexts
- **Project Tags** (optional): Organize tasks by project
  - Examples: `Website Redesign`, `Q1 Marketing`, `Personal Development`
  - Tasks can have multiple project tags
  - Click **Manage Tags** button to create new tags with colors
- **Delegated To** (optional): Person responsible if task is delegated
  - Only relevant if you plan to delegate the task
  - Used with **Follow-Up Date** for reminders
- **Follow-Up Date** (optional): When to check on delegated task progress
  - Automatically sets task state to **Delegated**
  - App will remind you on this date

![New Task Dialog](../../screenshots/task-form.png)

### Editing an Existing Task

**Keyboard Shortcut:** Double-click or right-click → Edit Task

**Steps:**
1. Select a task in Task List View (`Ctrl+2`)
2. Double-click the task or right-click → **Edit Task**
3. Modify any fields
4. Click **OK** to save changes

**Important Notes:**
- Changing Base Priority resets Elo rating to 1500 and comparison count to 0
- Adding a Start Date in the future moves task to **Deferred** state
- Adding Delegated To and Follow-Up Date moves task to **Delegated** state

### Deleting Tasks (Moving to Trash)

**Keyboard Shortcut:** `Alt+T` (in Focus Mode) or `Delete` key (in Task List)

**Steps:**
1. Select task (in Task List) or view task (in Focus Mode)
2. Press `Alt+T` or `Delete` key, or click **Trash** button
3. Task moves to **Trash** state (not permanently deleted)

**Recovering from Trash:**
1. Open Task List (`Ctrl+2`)
2. Filter by State: **Trash**
3. Right-click task → **Set State → Active**

**Permanent Deletion:**
Tasks in trash are kept indefinitely. Use **Tools → Nuclear Reset** to permanently delete all trash items (requires confirmation).

### Task Fields Reference Table

| Field | Required | Purpose | Examples |
|-------|----------|---------|----------|
| Title | Yes | Brief task description | "Write report", "Call client" |
| Description | No | Detailed notes | Meeting notes, instructions |
| Base Priority | Yes | High/Medium/Low tier | High for urgent tasks |
| Due Date | No | Deadline for completion | 2026-02-15 |
| Start Date | No | When task becomes actionable | 2026-01-30 |
| Context | No | Work environment filter | @computer, @phone |
| Project Tags | No | Project categorization | Website Redesign, Marketing |
| Delegated To | No | Person assigned | John Smith, Team Lead |
| Follow-Up Date | No | When to check progress | 2026-02-01 |

---

## 3. Understanding the Priority System

OneTaskAtATime uses a sophisticated two-dimensional priority system to ensure the most important task always rises to the top.

### Base Priority (User-Controlled)

You select one of three priority tiers when creating a task:

- **High (3)**: Critical, urgent, or high-impact tasks
- **Medium (2)**: Important but not time-sensitive
- **Low (1)**: Nice-to-have, low-priority tasks

**Key Rule:** All High tasks rank above all Medium tasks. All Medium tasks rank above all Low tasks. This ensures critical work is never buried under low-priority items.

### Elo Rating System (Automatic)

Within each priority tier, tasks are refined using an **Elo rating system** (the same algorithm used in chess rankings).

**How it works:**
1. Every task starts with an Elo rating of **1500**
2. When two tasks have equal importance, you compare them using the Comparison Dialog
3. You choose which task is more important
4. Both tasks' Elo ratings update:
   - Winner's rating increases slightly
   - Loser's rating decreases slightly
5. Over time, consistently high-priority tasks within a tier get higher ratings

**Elo Rating Formula:**
```
New Rating = Old Rating + K × (Actual Score - Expected Score)
```

Where:
- **K-factor**: 32 for new tasks (< 10 comparisons), 16 for established tasks
- **Actual Score**: 1 for winner, 0 for loser
- **Expected Score**: 1 / (1 + 10^((Opponent Rating - Own Rating) / 400))

**Why this matters:**
- Tasks that consistently win comparisons rank higher
- Tasks that lose comparisons rank lower
- Ratings stabilize over time as tasks accumulate comparison history
- More accurate ranking than manual priority adjustment

### Effective Priority (Calculated from Elo)

Your task's Elo rating is mapped to an **effective priority** within strict bands based on base priority:

| Base Priority | Elo Range | Effective Priority Range |
|---------------|-----------|--------------------------|
| High (3) | 1000-2000 | 2.0 - 3.0 |
| Medium (2) | 1000-2000 | 1.0 - 2.0 |
| Low (1) | 1000-2000 | 0.0 - 1.0 |

**Example:**
- Task A: High priority, Elo 1600 → Effective Priority = 2.60
- Task B: High priority, Elo 1400 → Effective Priority = 2.40
- Task C: Medium priority, Elo 1800 → Effective Priority = 1.90

Task A ranks highest, then B, then C, even though C has the highest Elo rating (because it's in a lower base tier).

### Urgency (Based on Due Dates)

Urgency is calculated from remaining days until due date:

- **No due date**: Urgency = 1.0 (lowest)
- **Tasks with due dates**: Scaled based on proximity
  - Task due soonest (or overdue) = Urgency 3.0
  - Task due latest = Urgency 1.0
  - Tasks in between scaled proportionally

**Example:**
- Task A: Due tomorrow → Urgency 3.0
- Task B: Due in 7 days → Urgency 2.0
- Task C: Due in 30 days → Urgency 1.0

### Importance = Effective Priority × Urgency

The final **Importance Score** is the product of effective priority and urgency:

```
Importance = Effective Priority × Urgency
```

**Maximum Importance:** 3.0 × 3.0 = 9.0 (High priority task due immediately)

**Example Calculation:**
- Task A: Effective Priority 2.6 (High, Elo 1600) × Urgency 3.0 (due tomorrow) = **Importance 7.8**
- Task B: Effective Priority 2.4 (High, Elo 1400) × Urgency 2.0 (due in 7 days) = **Importance 4.8**
- Task C: Effective Priority 1.9 (Medium, Elo 1800) × Urgency 1.0 (due in 30 days) = **Importance 1.9**

Task A is shown first in Focus Mode because it has the highest importance score.

### When Comparisons Happen

The Comparison Dialog appears when:

1. **Multiple tasks have equal top-rank importance** (ties for #1 position)
2. You haven't compared those specific tasks before
3. You're in Focus Mode and the app needs to determine which task to show

The dialog shows two tasks side-by-side and asks you to choose which is more important. Your choice updates both Elo ratings.

### Priority Reset Rules

**Automatic Reset (when you change Base Priority):**
- Elo rating resets to 1500
- Comparison count resets to 0
- Effective priority recalculated based on new tier

**Manual Reset:**
- Right-click task in Task List → **Reset Elo Rating**
- App warns this may create ties requiring new comparisons
- Use sparingly—usually automatic comparisons are better

---

## 4. Task States Explained

Tasks move through different states based on your actions and the current date. Understanding states helps you manage your workflow effectively.

### Active

**Definition:** Tasks you can work on right now.

**Characteristics:**
- No start date, or start date has passed
- Not delegated to anyone else
- Not moved to Someday/Maybe or Trash
- Appear in Focus Mode
- Default state for new tasks without start dates

**When to use:** This is your primary working state—tasks you should be executing.

### Deferred

**Definition:** Tasks that aren't actionable until a future date.

**Characteristics:**
- Has a **Start Date** in the future
- Automatically becomes **Active** when start date arrives
- Not shown in Focus Mode until activated
- App sends notification when task activates (if notifications enabled)

**When to use:**
- Tasks that can't be started yet (e.g., "Review Q2 budget" when Q2 hasn't started)
- Scheduled work for specific dates
- Tasks waiting for external events

**How to defer a task:**
1. Edit task (double-click or right-click → Edit)
2. Set **Start Date** to future date
3. Click OK—state automatically changes to Deferred

**Resurfacing:** Hourly background check activates deferred tasks when start date ≤ today. See [Task Resurfacing System](#7-task-resurfacing-system).

### Delegated

**Definition:** Tasks assigned to someone else that require follow-up.

**Characteristics:**
- Has **Delegated To** (person name) and **Follow-Up Date**
- Not shown in Focus Mode (someone else is responsible)
- App reminds you on follow-up date to check progress
- Tracks accountability for delegated work

**When to use:**
- Tasks you've assigned to colleagues, team members, or vendors
- Work you're waiting on from others
- Tasks requiring follow-up conversations

**How to delegate a task:**
1. Edit task or use Defer → Delegate workflow
2. Enter **Delegated To** (person name)
3. Set **Follow-Up Date** (when to check progress)
4. Click OK—state automatically changes to Delegated

**Resurfacing:** Daily check at 9 AM resurfaces delegated tasks on/after follow-up date. See [Task Resurfacing System](#7-task-resurfacing-system).

### Someday/Maybe

**Definition:** Tasks that might become relevant later but aren't actionable now.

**Characteristics:**
- Ideas, possibilities, or aspirational tasks
- Not shown in Focus Mode
- Periodically reviewed (default: every 7 days)
- Can be activated or trashed during review

**When to use:**
- "Might be nice to..." ideas
- Low-priority tasks you're not committed to
- Tasks blocked indefinitely with no clear path forward
- Ideas you want to remember but not act on now

**How to move to Someday/Maybe:**
- In Focus Mode: Click **Someday** button (`Alt+S`)
- In Task List: Right-click → **Set State → Someday/Maybe**

**Resurfacing:** Periodic review dialog prompts you to activate, keep, or trash Someday tasks. See [Task Resurfacing System](#7-task-resurfacing-system).

### Completed

**Definition:** Tasks you've finished.

**Characteristics:**
- Marked done with completion timestamp
- No longer appear in Focus Mode or active task lists
- Preserved for historical record and analytics
- Cannot be edited (must reactivate first)

**How to complete a task:**
- In Focus Mode: Click **Complete** button (`Alt+C`)
- In Task List: Right-click → **Mark Complete**

**Viewing completed tasks:**
1. Open Task List (`Ctrl+2`)
2. Filter by State: **Completed**
3. Sort by Completion Date to see recent completions

### Trash

**Definition:** Tasks you've decided are unnecessary.

**Characteristics:**
- Soft delete (not permanently removed)
- Can be recovered by changing state back to Active
- Not shown in Focus Mode or normal task lists
- Kept indefinitely unless manually purged

**When to use:**
- Tasks that are no longer relevant
- Duplicate tasks
- Ideas that won't be pursued
- Tasks superseded by other work

**How to trash a task:**
- In Focus Mode: Click **Trash** button (`Alt+T`)
- In Task List: Press `Delete` key or right-click → **Move to Trash**

**Recovering from trash:**
1. Task List → Filter by State: **Trash**
2. Right-click task → **Set State → Active**

### State Transition Summary

| From State | To State | How | When |
|------------|----------|-----|------|
| Active | Completed | Complete button | Task finished |
| Active | Deferred | Set start date | Task not actionable yet |
| Active | Delegated | Set delegate + follow-up | Assign to someone else |
| Active | Someday/Maybe | Someday button | Not committed to task |
| Active | Trash | Trash button | Task no longer needed |
| Deferred | Active | Automatic | Start date arrives |
| Delegated | Active | Review dialog | Follow-up date arrives |
| Someday/Maybe | Active | Review dialog | Decide to pursue task |
| Someday/Maybe | Trash | Review dialog | Decide not to pursue |
| Trash | Active | Manual state change | Recover deleted task |

---

## 5. Using Focus Mode

Focus Mode is the heart of OneTaskAtATime. It presents you with exactly one task—the most important thing you should be working on right now.

### What is Focus Mode?

Focus Mode is a distraction-free view showing:
- **One task** with full details (title, description, context, tags, due date)
- **Action buttons** to act on the task (Complete, Defer, Delegate, Someday, Trash)
- **No other tasks visible**—eliminates decision fatigue

### Entering Focus Mode

**Keyboard Shortcut:** `Ctrl+1`

**Steps:**
1. Press `Ctrl+1` from any view
2. OR click **View → Focus Mode**
3. The highest-importance task appears

![Focus Mode](../../screenshots/focus-mode.png)

### How Focus Mode Works

1. **Task Selection:** App calculates importance score (Effective Priority × Urgency) for all Active tasks
2. **Tie Resolution:** If multiple tasks have equal top importance, Comparison Dialog appears
3. **Display:** Highest-importance task is shown with all details
4. **Automatic Advancement:** When you act on the task (complete, defer, etc.), the next highest-importance task appears immediately

**No tasks available?**
- If no Active tasks exist, Focus Mode shows "No tasks available" message
- Deferred, Delegated, and Someday tasks are not shown in Focus Mode
- Create a new task (`Ctrl+N`) or activate a deferred task to see something in Focus Mode

### Action Buttons Explained

Focus Mode provides five action buttons:

#### Complete (Alt+C)

**When to use:** Task is finished

**What happens:**
1. Task state changes to **Completed**
2. Completion timestamp recorded
3. Next task appears in Focus Mode
4. Completed task moves to history (view in Task List → State: Completed)

**Use for:**
- Finished work
- Tasks no longer needed (alternatively use Trash)
- Successful outcomes

#### Defer (Alt+D)

**When to use:** Task isn't actionable right now, but will be later

**What happens:**
1. Postpone Dialog appears asking why you're deferring
2. You select a reason:
   - **Multiple subtasks**: Break task into smaller tasks
   - **Blocker encountered**: Create blocker task
   - **Dependencies**: Link to upstream tasks
   - **Other reason**: Free-text explanation
3. Based on your reason, additional dialogs may appear (subtask breakdown, blocker creation, dependency selection)
4. Task state changes to **Deferred** with start date you specify
5. Next task appears in Focus Mode

**Use for:**
- Tasks waiting on external events
- Tasks scheduled for specific future dates
- Tasks blocked by other work

See [Postpone Handling and Dependencies](#6-postpone-handling-and-dependencies) for detailed workflow.

#### Delegate (Alt+G)

**When to use:** Someone else should do this task

**What happens:**
1. Delegation Dialog appears
2. You enter:
   - **Delegated To** (person name)
   - **Follow-Up Date** (when to check progress)
3. Task state changes to **Delegated**
4. Postpone reason recorded as "Delegated to [person]"
5. App will remind you on follow-up date
6. Next task appears in Focus Mode

**Use for:**
- Tasks assigned to team members
- Work you're waiting on from others
- Tasks requiring expertise you don't have

#### Someday/Maybe (Alt+S)

**When to use:** Task might be relevant later, but not now

**What happens:**
1. Task state changes to **Someday/Maybe**
2. Postpone reason recorded as "Moved to Someday/Maybe"
3. Task removed from Focus Mode rotation
4. App will periodically prompt you to review Someday tasks (default: every 7 days)
5. Next task appears in Focus Mode

**Use for:**
- Ideas or aspirations not committed to
- Low-priority tasks indefinitely postponed
- Tasks blocked with no clear resolution path
- "Nice to have" items

#### Trash (Alt+T)

**When to use:** Task is no longer needed

**What happens:**
1. Task state changes to **Trash**
2. Postpone reason recorded as "Moved to Trash"
3. Task removed from Focus Mode
4. Task can be recovered from Trash if needed
5. Next task appears in Focus Mode

**Use for:**
- Tasks that are no longer relevant
- Duplicate tasks
- Ideas you won't pursue
- Tasks superseded by other work

### Why Focus Mode Reduces Decision Fatigue

**Traditional to-do lists:**
- Show 20-100 tasks at once
- Force you to constantly re-evaluate priorities
- Create anxiety about choosing the "right" task
- Lead to procrastination through analysis paralysis

**Focus Mode approach:**
- Shows exactly one task
- App makes the priority decision for you (based on your importance formula)
- You only decide: "Work on this now, or not?"
- Eliminates choice overload

**Research shows:** Limiting choices increases action and reduces mental fatigue. Focus Mode applies this principle to task management.

### Focus Mode Workflow Example

**Morning routine:**
1. Open app (`Ctrl+1` if not already in Focus Mode)
2. See top task: "Prepare Q1 presentation"
3. Work on presentation
4. Click **Complete** (`Alt+C`) when done
5. Next task appears: "Review budget proposal"
6. Not ready to work on this yet → Click **Defer** (`Alt+D`)
7. Set start date to tomorrow
8. Next task appears: "Call vendor about invoice"
9. Complete the call → Click **Complete** (`Alt+C`)
10. Continue cycle until no more active tasks

---

## 6. Postpone Handling and Dependencies

OneTaskAtATime helps you understand why tasks get delayed and creates structure around blockers and dependencies.

### What Happens When You Defer a Task

When you click **Defer** (`Alt+D`) in Focus Mode or defer a task from Task List:

1. **Postpone Dialog appears** asking "Why are you postponing this task?"
2. You select one of four reasons (see below)
3. Based on your reason, the app may trigger additional workflows
4. Postponement is recorded in history with timestamp and reason
5. Task moves to appropriate state (usually Deferred)

### Postpone Dialog Options

![Postpone Dialog](../../screenshots/postpone-dialog.png)

#### Option 1: Multiple Subtasks

**Select when:** The task is too complex and needs to be broken down

**Workflow:**
1. Select "This task has multiple subtasks"
2. Click OK
3. **Subtask Breakdown Dialog** appears
4. You create 2+ smaller tasks from the parent task
5. App links subtasks with dependencies (if desired)
6. You select which subtask is the "Next Action"
7. Parent task is marked as Completed or deleted (your choice)

**Result:**
- Complex task broken into manageable pieces
- Focus Mode shows the next actionable subtask
- Progress tracked through smaller increments

**Example:**
- Parent: "Launch new website"
- Subtasks:
  1. Design homepage mockup
  2. Write copy for About page
  3. Set up hosting account
  4. Deploy site to production
- Next Action: "Design homepage mockup"

#### Option 2: Blocker Encountered

**Select when:** Something is preventing you from completing the task

**Workflow:**
1. Select "I encountered a blocker"
2. Click OK
3. **Create Blocker Dialog** appears (same as New Task dialog)
4. You create a task representing the blocker
5. Blocker task is linked as a dependency to the original task
6. Original task deferred until blocker is resolved
7. Blocker task appears in Focus Mode as highest priority

**Result:**
- Blocker explicitly tracked as a task
- Original task won't resurface until blocker is complete
- Clear path forward to unblock work

**Example:**
- Original task: "Deploy new feature to production"
- Blocker: "Get approval from security team"
- Blocker task created with High priority
- Focus Mode shows blocker task next
- After security approval received and blocker completed, original task resurfaces

#### Option 3: Dependencies

**Select when:** This task can't be started until other tasks are complete

**Workflow:**
1. Select "This task depends on other tasks"
2. Click OK
3. **Dependency Selection Dialog** appears
4. You select one or more existing tasks as dependencies (or create new ones)
5. Dependencies linked to original task
6. Original task deferred until all dependencies complete
7. Dependency indicator (⛔) appears in Task List

**Result:**
- Task dependency structure explicitly captured
- Original task blocked until upstream work finishes
- Clear visibility into what's preventing progress

**Example:**
- Original task: "Write final report"
- Dependencies:
  - "Collect data from team members" (upstream task)
  - "Review previous quarter's report" (upstream task)
- Original task won't resurface until both dependencies are completed

**Viewing dependency graph:**
- Right-click task in Task List → **View Dependency Graph**
- Shows tree structure of all upstream and downstream tasks
- Detects circular dependencies (warns you if detected)

#### Option 4: Other Reason

**Select when:** None of the above apply

**Workflow:**
1. Select "Other reason" and enter free-text explanation
2. Click OK
3. Set start date for when task should resurface
4. Task moves to Deferred state

**Result:**
- Postpone reason recorded for future reference
- Task resurfaces on specified date
- No additional workflows triggered

**Use for:**
- Waiting on external factors (e.g., "Waiting for budget approval")
- Seasonal work (e.g., "Prepare tax documents" → defer to March)
- Personal reasons (e.g., "Not in the right headspace for this")

### Postponement Pattern Detection

If you repeatedly postpone the same task, the app notices:

**Thresholds:**
- **2+ postponements** with the same reason → Reflection prompt
- **3+ total postponements** (any reason) → Intervention suggestion

**Reflection Dialog:**
When threshold exceeded, app asks:
1. "You've postponed this task 3 times. Is this task still relevant?"
2. Options:
   - Continue postponing (set new start date)
   - Move to Someday/Maybe
   - Move to Trash
   - Break down into subtasks

**Purpose:** Prevent tasks from becoming "zombie tasks" that never get done and create psychological burden.

### Dependency Management

**Creating dependencies:**
1. Edit task (double-click or right-click → Edit)
2. Click **Add Dependency** button
3. Select existing task(s) or create new task
4. Click OK

**Viewing dependencies:**
- **Task List:** ⛔ icon appears in task row if dependencies exist
- **Tooltip:** Hover over ⛔ to see list of upstream tasks
- **Dependency Graph:** Right-click → **View Dependency Graph**

**Circular dependency prevention:**
The app prevents you from creating circular dependencies (A depends on B, B depends on A). If you try, you'll see a warning.

**Deleting tasks with dependencies:**
If you delete a task that other tasks depend on, the app warns you and offers to remove the dependencies or cancel the deletion.

---

## 7. Task Resurfacing System

OneTaskAtATime automatically resurfaces deferred, delegated, and Someday tasks so they don't get forgotten.

### How Resurfacing Works

The app runs background checks at configurable intervals:

1. **Deferred Task Check** (default: hourly)
   - Scans all Deferred tasks
   - If `start_date ≤ today`, task becomes Active
   - Notification sent (if enabled)
   - Task appears in Focus Mode

2. **Delegated Task Check** (default: daily at 9 AM)
   - Scans all Delegated tasks
   - If `follow_up_date ≤ today`, reminder sent
   - Review Delegated Dialog appears (optional, configurable)
   - You decide: Activate, Complete, or Extend follow-up

3. **Someday/Maybe Review** (default: every 7 days)
   - Review Someday Dialog appears
   - Shows all Someday/Maybe tasks
   - You decide for each: Activate, Keep, or Trash

4. **Postponement Intervention** (default: 3 postponements)
   - Tracks postponement count per task
   - When threshold exceeded, Reflection Dialog appears
   - Helps you decide if task should continue, be modified, or removed

### Deferred Task Activation

**Automatic process:**
1. Background job runs hourly (configurable)
2. All tasks with `start_date ≤ today` change state from Deferred → Active
3. Notification appears: "3 deferred tasks activated"
4. Click notification to see **Activated Tasks Dialog** with details

**Activated Tasks Dialog:**
- Lists all newly activated tasks
- Shows title, priority, due date
- Click task to jump to it in Task List
- Click OK to dismiss

**Manual activation:**
- Task List → Filter: Deferred
- Right-click task → **Set State → Active**

### Delegated Task Reminders

**Automatic process:**
1. Background job runs daily at 9 AM (configurable)
2. All tasks with `follow_up_date ≤ today` trigger reminder
3. Notification appears: "2 delegated tasks need follow-up"
4. Click notification to open **Review Delegated Dialog**

**Review Delegated Dialog:**
- Lists all delegated tasks ready for follow-up
- Shows delegated to, follow-up date, task details
- Actions per task:
  - **Activate**: Task complete by delegate, bring back to your plate
  - **Complete**: Delegate finished the task, mark it done
  - **Extend**: Still waiting, set new follow-up date (pushes task out)

**Example workflow:**
1. You delegated "Update client database" to Sarah, follow-up 2026-02-01
2. On 2026-02-01 at 9 AM, reminder appears
3. You open Review Delegated Dialog
4. You call Sarah → she's finished the work
5. You click **Complete** → task marked done
6. Task moves to Completed state

### Someday/Maybe Reviews

**Automatic process:**
1. Background job runs every N days (default: 7, configurable)
2. **Review Someday Dialog** appears
3. Lists all Someday/Maybe tasks
4. You review each and choose action

**Review Someday Dialog:**
- Shows all Someday/Maybe tasks with details
- Actions per task:
  - **Activate**: Decide to pursue this task now
  - **Keep**: Still want to consider later
  - **Trash**: No longer interested
- Batch actions: Select multiple → Apply action to all

**Purpose:** Prevents Someday/Maybe from becoming a graveyard of forgotten ideas.

**Best practice:** Schedule dedicated time for Someday reviews (e.g., Friday afternoon, Sunday evening).

### Notification Panel

**Accessing:** Click notification icon in status bar

**Features:**
- View all resurfacing notifications
- Unread badge counter (red number)
- Click notification to jump to related dialog or task
- Mark notifications as read
- Clear old notifications

**Notification types:**
- Deferred tasks activated
- Delegated tasks need follow-up
- Someday/Maybe review scheduled
- Postponement pattern detected

**Disabling notifications:**
1. **Settings** (`Ctrl+,`)
2. **Notifications** tab
3. Uncheck "Enable Windows toast notifications" or "Enable in-app notifications"

### Configuring Resurfacing Intervals

**Settings → Resurfacing tab:**

- **Deferred Task Check Interval**: 30 min, 1 hr, 2 hr, 4 hr, 12 hr, 24 hr
- **Delegated Task Check Time**: Daily at specified hour (default: 9 AM)
- **Someday/Maybe Review Interval**: 3, 7, 14, 30, 60 days
- **Postponement Threshold**: 2, 3, 5, 10 postponements before intervention

**Applying changes:**
- Click **Save** in Settings Dialog
- Changes take effect immediately (no restart required)

---

## 8. Task List View

The Task List View provides a comprehensive table of all your tasks with powerful filtering, sorting, and search capabilities.

### Accessing Task List

**Keyboard Shortcut:** `Ctrl+2`

**Steps:**
1. Press `Ctrl+2`
2. OR click **View → Task List**

![Task List View](../../screenshots/task-list.png)

### Task List Columns

| Column | Description | Sortable | Filterable |
|--------|-------------|----------|------------|
| **Title** | Task name | Yes | Search box |
| **Priority** | Base priority (High/Medium/Low) | Yes | Dropdown |
| **Elo Rating** | Current Elo score | Yes | No |
| **Importance** | Calculated importance score | Yes | No |
| **State** | Active/Deferred/Delegated/etc. | Yes | Multi-select |
| **Due Date** | Deadline | Yes | Date range |
| **Start Date** | When task becomes actionable | Yes | Date range |
| **Context** | Work environment tag | Yes | Dropdown |
| **Tags** | Project tags | No | Tag filter |
| **Dependencies** | ⛔ icon if dependencies exist | No | No |

### Filtering Tasks

**State Filter:**
1. Click **State** dropdown in toolbar
2. Select one or more states (Active, Deferred, Delegated, Someday/Maybe, Completed, Trash)
3. Task list updates instantly

**Multi-select example:** Select both "Active" and "Deferred" to see all actionable tasks.

**Context Filter:**
1. Click **Context** dropdown in toolbar
2. Select a context (e.g., `@computer`)
3. Only tasks with that context appear

**Use case:** Filter by `@phone` context when making calls, `@errands` when running errands.

**Project Tag Filter:**
1. Click **Tags** dropdown in toolbar
2. Select one or more project tags
3. Only tasks with those tags appear

**Clearing filters:** Click **Clear Filters** button in toolbar.

### Searching Tasks

**Search box** in toolbar searches:
- Task titles
- Task descriptions
- Context names
- Project tag names

**Real-time results:** Task list updates as you type.

**Search is case-insensitive.**

**Example:** Type "report" to find all tasks containing "report" in title or description.

### Sorting Tasks

**Single-column sort:**
1. Click any column header
2. Click again to reverse sort direction
3. Arrow icon indicates sort direction

**Multi-column sort:**
1. Hold `Shift` while clicking column headers
2. First click = primary sort
3. Second click (with Shift) = secondary sort
4. Continue for tertiary sort, etc.

**Example:** Sort by State (primary) → Due Date (secondary) to see all Active tasks ordered by deadline.

### Context Menu Actions

Right-click any task to access:

- **Edit Task**: Open edit dialog
- **Mark Complete**: Change state to Completed
- **Set State →** Submenu with all states
- **Add Dependency**: Link to upstream task
- **View Dependency Graph**: Visualize task dependencies
- **Reset Elo Rating**: Reset to 1500 (warns about creating ties)
- **Move to Trash** (`Delete`): Soft delete

### Bulk Actions

**Selecting multiple tasks:**
1. Click first task
2. Hold `Shift` and click last task (range select)
3. OR hold `Ctrl` and click individual tasks (multi-select)

**Available bulk actions:**
- **Mark Complete**: All selected tasks → Completed
- **Move to Trash**: All selected tasks → Trash
- **Set State**: Change all selected tasks to same state

**Use case:** Select all completed tasks and move to Trash for cleanup.

### Column Customization

**Show/Hide Columns:**
1. Right-click any column header
2. Uncheck columns you want to hide
3. Check columns you want to show

**Reorder Columns:**
1. Click and drag column header
2. Drop in new position

**Resize Columns:**
1. Hover over column border in header
2. Cursor changes to resize icon
3. Click and drag to resize

**Settings are saved** automatically and persist across sessions.

---

## 9. Comparison Dialog

The Comparison Dialog appears when multiple tasks have equal importance and the app needs your input to determine which is more important.

### When It Appears

**Trigger conditions:**
1. You're in Focus Mode
2. Two or more tasks have identical importance scores (Effective Priority × Urgency)
3. These tasks haven't been compared before

**Example:**
- Task A: Effective Priority 2.5, Urgency 2.0 → Importance 5.0
- Task B: Effective Priority 2.5, Urgency 2.0 → Importance 5.0
- Tasks tied at 5.0 → Comparison Dialog appears

![Comparison Dialog](../../screenshots/priority-comparison.png)

### How to Make a Comparison

**Dialog layout:**
- **Left panel:** Task A details (title, description, context, due date, current Elo)
- **Right panel:** Task B details
- **Choose button** below each task
- **Skip button** at bottom
- **Progress indicator:** "Comparison 1 of 3"

**Steps:**
1. Read both task descriptions
2. Consider:
   - Which has greater impact if completed?
   - Which aligns more with your goals?
   - Which feels more important right now?
3. Click **Choose Task A** or **Choose Task B**
4. Elo ratings update immediately
5. Next comparison appears (if more ties exist)

**No wrong answer:** Comparisons are subjective. Your gut feeling is usually correct.

### How Elo Updates Work

When you choose Task A over Task B:

**Task A (winner):**
- Elo rating increases by 8-16 points (depends on current ratings and K-factor)
- Effective priority slightly increases
- More likely to appear first in future ties

**Task B (loser):**
- Elo rating decreases by 8-16 points
- Effective priority slightly decreases
- Less likely to appear first in future ties

**K-factor effect:**
- New tasks (< 10 comparisons): K=32 → larger rating swings
- Established tasks (10+ comparisons): K=16 → smaller rating swings
- Ratings stabilize over time as tasks accumulate comparisons

**Example calculation:**
- Task A: Elo 1500, 5 comparisons (K=32)
- Task B: Elo 1500, 5 comparisons (K=32)
- Expected scores (equal Elo): 0.5 each
- You choose Task A → Actual score: A=1, B=0
- New Elo: A = 1500 + 32 × (1 - 0.5) = 1516
- New Elo: B = 1500 + 32 × (0 - 0.5) = 1484

After this comparison, Task A (1516) ranks slightly higher than Task B (1484) within the same priority tier.

### Skip Option

**When to skip:**
- You can't decide between tasks
- Need more information to make a comparison
- Tasks seem truly equal

**What happens when you skip:**
- No Elo updates occur
- Comparison is recorded as "skipped"
- App selects one task randomly to show in Focus Mode
- You may be asked to compare again later

**Note:** Skipping occasionally is fine, but if you skip frequently, consider whether your task descriptions are detailed enough to make informed decisions.

### Progress Tracking

**Progress indicator** shows "Comparison X of Y" where:
- X = current comparison number
- Y = total comparisons needed to resolve all ties

**Multiple comparisons:**
If 5 tasks are tied, you may need to compare several pairs to determine the top task. The app minimizes comparisons using an efficient algorithm (usually log2(N) comparisons for N tied tasks).

**Canceling comparisons:**
You can close the Comparison Dialog without completing all comparisons. The app will ask again next time you enter Focus Mode.

### Viewing Comparison History

**Not currently available in UI**, but comparison history is stored in the database (`task_comparisons` table) for future analytics features.

---

## 10. Data Management

OneTaskAtATime provides robust data export, import, and backup capabilities to protect your task data.

### Database Location

**Default location:** `%APPDATA%\OneTaskAtATime\onetaskattime.db`

**Full path example:** `C:\Users\YourName\AppData\Roaming\OneTaskAtATime\onetaskattime.db`

**Database format:** SQLite 3

**Accessing database:**
1. Press `Win+R`
2. Type `%APPDATA%\OneTaskAtATime`
3. Press Enter
4. Find `onetaskattime.db` file

**Warning:** Do not manually edit the database file. Use the app's import/export features.

### Export to JSON

**Purpose:** Create human-readable backup of all your data

**Keyboard Shortcut:** `Ctrl+Shift+E`

**Steps:**
1. Click **File → Export Data** or press `Ctrl+Shift+E`
2. Choose save location
3. Enter filename (default: `onetaskattime_export_YYYY-MM-DD.json`)
4. Click **Save**
5. Progress bar shows export status
6. Success message appears

**What gets exported:**
- All tasks (all states, including trash)
- All contexts
- All project tags
- All task dependencies
- All comparison history
- All postpone history
- All notifications
- All settings

**Export format:**
```json
{
  "export_date": "2026-01-25T10:30:00",
  "app_version": "1.0.0",
  "schema_version": 1,
  "tasks": [...],
  "contexts": [...],
  "project_tags": [...],
  "dependencies": [...],
  "comparisons": [...],
  "postpone_history": [...],
  "notifications": [...],
  "settings": [...]
}
```

**File size:** Typically 100-500 KB for 100-1000 tasks (JSON is text-based and compresses well).

### Import from JSON

**Purpose:** Restore data from export or merge data from another installation

**Keyboard Shortcut:** `Ctrl+Shift+I`

**Steps:**
1. Click **File → Import Data** or press `Ctrl+Shift+I`
2. Select JSON export file
3. **Import Preview Dialog** appears showing:
   - Export date and version
   - Number of tasks, contexts, tags, etc.
   - Schema compatibility check
4. Choose import mode:
   - **Replace**: Delete all existing data, import file data (DESTRUCTIVE)
   - **Merge**: Keep existing data, add file data, resolve ID conflicts
5. Click **Import**
6. Progress bar shows import status
7. Success message with import summary

**Replace mode:**
- **Use when:** Starting fresh or restoring complete backup
- **Warning:** All current data is permanently deleted
- **Confirmation:** Requires typing "REPLACE" to confirm

**Merge mode:**
- **Use when:** Combining data from multiple sources
- **ID conflict resolution:** New IDs assigned to imported items to avoid conflicts
- **Relationship preservation:** Dependencies and links automatically remapped to new IDs

**Schema validation:**
- App checks export file version compatibility
- If export is from newer version, import is blocked (prevent data corruption)
- If export is from older version, app attempts migration

### Backup Best Practices

**Recommendation:** Export data weekly or after significant changes

**Backup strategy:**
1. **Weekly automated backup:**
   - Create calendar reminder to export data every Sunday
   - Save export to cloud storage folder (Dropbox, OneDrive, Google Drive)
   - Keep last 4 weeks of backups

2. **Pre-import backup:**
   - Always export current data before importing
   - Allows rollback if import causes issues

3. **Version-named files:**
   - Use date-stamped filenames: `onetaskattime_2026-01-25.json`
   - Easy to identify and restore specific points in time

4. **Database file backup (advanced):**
   - Copy `%APPDATA%\OneTaskAtATime\onetaskattime.db` file
   - Faster to restore than JSON import
   - Less human-readable than JSON

**Restoration process:**
1. Install fresh copy of OneTaskAtATime (or use existing)
2. File → Import Data
3. Select backup JSON file
4. Choose **Replace** mode
5. Type "REPLACE" to confirm
6. All data restored from backup

### Nuclear Reset (Complete Data Wipe)

**Purpose:** Delete all data and start completely fresh

**Access:** **Tools → Nuclear Reset** (no keyboard shortcut to prevent accidents)

**Warning:** This is PERMANENT and IRREVERSIBLE. All data is deleted.

**Multi-step confirmation process:**
1. **Real-time deletion summary** showing counts (e.g., "47 tasks will be deleted")
2. **Type "RESET" exactly** in text box to confirm
3. **Acknowledge permanence checkbox** ("I understand this cannot be undone")
4. **Final system warning dialog** as last safety check

**Selective preservation:**
- Option to preserve contexts (keep your `@computer`, `@phone` tags)
- Option to preserve project tags (keep your project organization)
- Option to preserve settings (keep theme, font size, intervals)

**Use cases:**
- Testing/demo environments
- Starting completely fresh after major project change
- Clearing old data before giving app to someone else

**Pre-reset recommendation:**
1. Export data first (File → Export Data)
2. Save export somewhere safe
3. Perform nuclear reset
4. Can restore from export if needed

---

## 11. Customization and Settings

OneTaskAtATime offers extensive customization to match your preferences and workflow.

### Accessing Settings

**Keyboard Shortcut:** `Ctrl+,`

**Steps:**
1. Press `Ctrl+,` or click **Tools → Settings**
2. Settings Dialog opens with 6 tabs

![Settings Dialog](../../screenshots/settings-dialog.png)

### Theme Selection (Theme Tab)

**Available themes:**
- **Light**: High contrast, bright background, dark text (default)
- **Dark**: Low contrast, dark background, light text (easier on eyes)
- **System**: Automatically matches Windows theme (Light/Dark)

**Changing theme:**
1. Settings → **Theme** tab
2. Select theme from dropdown
3. Click **Save**
4. Theme applies immediately (no restart required)

**System theme detection:**
- Reads Windows registry for system theme preference
- Updates automatically when Windows theme changes (requires restart)

### Font Size Adjustment (Theme Tab)

**Available sizes:**
- Small (8pt)
- Medium (10pt) - default
- Large (12pt)
- Extra Large (14pt)

**Changing font size:**
1. Settings → **Theme** tab
2. Move **Font Size** slider
3. Click **Save**
4. Font size applies immediately to all text in app

**Use case:** Increase font size for better readability on high-resolution displays or for accessibility.

### Resurfacing Intervals (Resurfacing Tab)

**Configurable intervals:**

**Deferred Task Check:**
- Options: 30 min, 1 hr, 2 hr, 4 hr, 12 hr, 24 hr
- Default: 1 hour
- Purpose: How often to check if deferred tasks should activate

**Delegated Task Check Time:**
- Options: Any hour 0-23 (e.g., 9 = 9 AM)
- Default: 9 (9 AM)
- Purpose: What time each day to check delegated follow-ups

**Someday/Maybe Review Interval:**
- Options: 3, 7, 14, 30, 60 days
- Default: 7 days
- Purpose: How often to prompt Someday/Maybe review

**Postponement Intervention Threshold:**
- Options: 2, 3, 5, 10 postponements
- Default: 3 postponements
- Purpose: After how many postponements to trigger reflection dialog

**Applying changes:**
- Click **Save** in Settings Dialog
- Scheduler reloads with new intervals immediately

### Notification Preferences (Notifications Tab)

**Windows Toast Notifications:**
- Toggle: Enable/Disable
- Default: Enabled
- Description: Native Windows 10/11 toast notifications appear in notification center

**In-App Notification Panel:**
- Toggle: Enable/Disable
- Default: Enabled
- Description: Notification icon in status bar shows unread count

**Sound Notifications:**
- Toggle: Enable/Disable (not implemented in v1.0)
- Default: Disabled
- Description: Play sound when notifications appear

**Do Not Disturb Mode:**
- Toggle: Enable/Disable (not implemented in v1.0)
- Default: Disabled
- Description: Suppress all notifications during specified hours

### Advanced Settings (Advanced Tab)

**Elo K-Factors:**

**New Task K-Factor:**
- Range: 16-64
- Default: 32
- Description: How much Elo ratings change for tasks with < 10 comparisons
- Higher values = more volatile ratings (faster learning)

**Established Task K-Factor:**
- Range: 8-32
- Default: 16
- Description: How much Elo ratings change for tasks with 10+ comparisons
- Lower values = more stable ratings

**K-Factor Transition Threshold:**
- Range: 5-20 comparisons
- Default: 10 comparisons
- Description: After how many comparisons tasks are considered "established"

**Epsilon (Tie Detection Threshold):**
- Range: 0.001-0.1
- Default: 0.01
- Description: How close importance scores must be to trigger comparison
- Lower values = more comparisons (stricter tie detection)

**Elo Band Ranges (read-only reference):**
- High Priority: 2.0 - 3.0
- Medium Priority: 1.0 - 2.0
- Low Priority: 0.0 - 1.0

**Reset to Defaults:**
- Click **Reset to Defaults** button
- Restores all advanced settings to recommended values

**Use case:** Adjust K-factors if you want faster or slower Elo rating changes based on comparison outcomes.

### Window Geometry Reset

**Purpose:** Reset window size and position to defaults

**Location:** Settings → Theme tab → **Reset Window Geometry** button

**When to use:**
- Window is off-screen (multi-monitor setup changed)
- Window is too small/large
- Want to restore default layout

**What resets:**
- Main window position (centered on screen)
- Main window size (1200×800 default)
- All dialog sizes and positions

### Database Statistics

**Location:** Settings → Advanced tab → **Database Statistics** section (view-only)

**Information shown:**
- Total tasks count
- Active tasks count
- Completed tasks count
- Deferred tasks count
- Delegated tasks count
- Someday/Maybe tasks count
- Trash count
- Total contexts count
- Total project tags count
- Total dependencies count
- Total comparisons count
- Database file size

**Use case:** Monitor data growth, verify export completeness, troubleshoot performance.

---

## 12. Keyboard Shortcuts Reference

OneTaskAtATime is designed for keyboard-driven productivity. Master these shortcuts to work faster.

### General Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | New Task |
| `Ctrl+1` | Switch to Focus Mode |
| `Ctrl+2` | Switch to Task List |
| `Ctrl+F` | Search Tasks |
| `Ctrl+Shift+E` | Export Data |
| `Ctrl+Shift+I` | Import Data |
| `Ctrl+Shift+A` | Postpone Analytics |
| `Ctrl+,` | Open Settings |
| `Ctrl+?` | Keyboard Shortcuts Help |
| `F1` | Open Help Dialog |
| `F5` | Refresh View |
| `Ctrl+Q` | Quit Application |

### Navigation Shortcuts

| Shortcut | Action |
|----------|--------|
| `Tab` | Move to next field/control |
| `Shift+Tab` | Move to previous field/control |
| `Enter` | Confirm/OK in dialogs |
| `Esc` | Cancel/Close dialog |
| `Ctrl+1` / `Ctrl+2` | Switch between Focus Mode and Task List |

### Focus Mode Shortcuts

| Shortcut | Action |
|----------|--------|
| `Alt+C` | Complete current task |
| `Alt+D` | Defer current task |
| `Alt+G` | Delegate current task |
| `Alt+S` | Move to Someday/Maybe |
| `Alt+T` | Move to Trash |
| `Ctrl+N` | Create new task (from Focus Mode) |

### Task List Shortcuts

| Shortcut | Action |
|----------|--------|
| `Delete` | Move selected task to Trash |
| `Ctrl+A` | Select all tasks |
| `Ctrl+C` | Copy selected task details |
| `Ctrl+F` | Focus search box |
| `Ctrl+H` | View task history (right-click menu) |
| `↑` / `↓` | Navigate task list |
| `Enter` | Open selected task in edit dialog |
| `Shift+Click` | Range select tasks |
| `Ctrl+Click` | Multi-select tasks |

### Dialog Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Confirm/OK |
| `Esc` | Cancel/Close |
| `Tab` | Next field |
| `Shift+Tab` | Previous field |
| `Alt+[Letter]` | Activate control with underlined letter |
| `Shift+F1` | WhatsThis help mode (then click field) |

### Comparison Dialog Shortcuts

| Shortcut | Action |
|----------|--------|
| `←` or `1` | Choose left task |
| `→` or `2` | Choose right task |
| `S` or `Esc` | Skip comparison |

### Context Menu Shortcuts

| Shortcut | Action |
|----------|--------|
| Right-click | Open context menu |
| `↑` / `↓` | Navigate menu |
| `Enter` | Select menu item |
| `Esc` | Close menu |

---

## 13. Tips and Best Practices

Get the most out of OneTaskAtATime with these proven strategies.

### Start with Focus Mode

**Tip:** Make Focus Mode your default view

**Why:** Focus Mode eliminates decision fatigue. You're presented with one task—no distractions, no second-guessing.

**How:**
1. Launch app
2. Press `Ctrl+1` to enter Focus Mode
3. Work on the task shown
4. Use action buttons to advance
5. Only switch to Task List (`Ctrl+2`) when you need to review, search, or bulk-edit

**Avoid:** Opening Task List and scrolling endlessly trying to decide what to work on.

### Use Contexts Effectively

**Tip:** Create contexts for different work environments

**Examples:**
- `@computer` - Tasks requiring a computer
- `@phone` - Phone calls to make
- `@office` - Must be at office location
- `@home` - Can only do at home
- `@errands` - Out-and-about tasks
- `@deep_work` - Tasks requiring uninterrupted focus
- `@low_energy` - Tasks for when you're tired

**Workflow:**
1. Assign context to every task
2. Filter Task List by current context
3. Focus Mode shows tasks matching your current environment

**Example:** When you're at the office, filter by `@office` and `@computer` to see only relevant tasks.

### Tag Projects for Organization

**Tip:** Use project tags instead of hierarchical folders

**Why:** Flat structure prevents tasks from getting buried in nested folders. Tags allow multi-dimensional organization (one task can belong to multiple projects).

**Examples:**
- `Website Redesign`
- `Q1 Marketing Campaign`
- `Product Launch`
- `Personal Development`
- `Client: Acme Corp`

**Workflow:**
1. Create project tag with distinct color
2. Assign tag to all related tasks
3. Filter by tag to see all project tasks
4. Sort by Due Date to see project timeline

**Avoid:** Creating nested project hierarchies (e.g., Marketing > Q1 > Social Media > Campaign A).

### Break Down Complex Tasks

**Tip:** If a task feels overwhelming, it's too complex—break it down

**When to break down:**
- Task takes more than 2 hours to complete
- You find yourself postponing the same task repeatedly
- Task description contains multiple steps or "and"

**How:**
1. Click **Defer** (`Alt+D`) in Focus Mode
2. Select "Multiple subtasks"
3. Create 2-5 smaller tasks
4. Link subtasks with dependencies if needed
5. Select the "Next Action"
6. Complete original task

**Example:**
- Original: "Launch new product"
- Subtasks:
  1. Finalize product specifications
  2. Create marketing materials
  3. Set up e-commerce listing
  4. Send launch email to customers
- Next Action: "Finalize product specifications"

### Review Someday/Maybe Regularly

**Tip:** Don't let Someday/Maybe become a graveyard

**Best practice:**
- Set Someday Review Interval to 7 days (Settings → Resurfacing)
- Block 15 minutes every Sunday for review
- Use Review Someday Dialog to Activate or Trash items
- Be ruthless—if you haven't acted in 30+ days, trash it

**Mindset:** Someday/Maybe should be for ideas you're genuinely considering, not a guilt-free dumping ground.

### Export Data Weekly

**Tip:** Create weekly backups to protect your task data

**Automation:**
1. Set calendar reminder every Sunday at 6 PM
2. Press `Ctrl+Shift+E` to export
3. Save to cloud storage folder (auto-synced to Dropbox/OneDrive)
4. Keep last 4 weeks of exports

**Why:** Protects against data corruption, accidental deletion, or database errors.

**Filename format:** `onetaskattime_2026-01-25.json` (includes date for easy identification)

### Leverage Elo Comparisons

**Tip:** Trust the comparison system to refine priorities

**When comparisons appear:**
- Don't overthink it—choose based on gut feeling
- Consider: Which has greater impact? Which aligns with goals?
- Remember: No wrong answer, ratings adjust over time

**Avoid skipping:** Skipping too often prevents Elo system from learning your priorities.

**Over time:** Tasks that consistently win comparisons rise to the top. Your true priorities emerge naturally.

### Set Realistic Due Dates

**Tip:** Only set due dates for tasks with real deadlines

**Why:** Every task with a due date affects urgency calculation. Too many due dates dilute the urgency signal.

**Best practice:**
- Set due dates for: Client deliverables, bill payments, event-driven tasks
- Skip due dates for: Ongoing work, personal projects, aspirational tasks

**Result:** Urgency calculation accurately reflects what's truly time-sensitive.

### Use Delegated Tasks for Accountability

**Tip:** Track work you're waiting on using Delegated state

**Workflow:**
1. Assign task to colleague/vendor
2. Set Delegated To: [Person name]
3. Set Follow-Up Date: When to check progress
4. Task moves to Delegated state (out of your Focus Mode)
5. On follow-up date, Review Delegated Dialog appears
6. Complete, extend, or reactivate based on progress

**Why:** Prevents delegated work from disappearing into the void. Maintains accountability.

### Capture Postpone Reasons Honestly

**Tip:** When postponing, be honest about why

**Why:** Postpone pattern detection helps surface chronic blockers and dependencies.

**Examples:**
- "Waiting for budget approval" → Track external blocker
- "Task too vague" → Subtask breakdown needed
- "Not in right headspace" → Consider Someday/Maybe
- "Blocked by legal review" → Create blocker task

**Result:** App helps you identify and resolve systemic issues preventing task completion.

---

## 14. Troubleshooting Quick Reference

Quick solutions to common issues. For detailed troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

### App Won't Start

**Symptom:** Double-clicking icon does nothing

**Quick fixes:**
1. Check Task Manager for existing OneTaskAtATime.exe process → End Task
2. Run as Administrator (right-click → Run as administrator)
3. Check database folder permissions (`%APPDATA%\OneTaskAtATime`)

### Database Errors

**Symptom:** "Database is locked" or "Unable to access database"

**Quick fixes:**
1. Close all instances of the app
2. Restart computer
3. Check antivirus isn't blocking database access
4. Restore from backup (File → Import Data)

### Slow Performance

**Symptom:** Task List takes 3+ seconds to load, UI feels laggy

**Quick fixes:**
1. Check task count (Settings → Advanced → Database Statistics)
   - 10,000+ tasks may cause slowdowns
2. Archive completed tasks (export, then delete old completed tasks)
3. Close other high-memory applications
4. Increase RAM allocation (if running many apps)

### Theme Not Applying

**Symptom:** Theme change doesn't take effect

**Quick fixes:**
1. Settings → Theme → Select theme → **Save** (don't just click OK)
2. Restart application
3. Reset to defaults: Settings → Advanced → Reset to Defaults

### Notifications Not Appearing

**Symptom:** No Windows toast notifications

**Quick fixes:**
1. Settings → Notifications → Verify "Enable Windows toast notifications" is checked
2. Windows Settings → System → Notifications → Ensure OneTaskAtATime is allowed
3. Check Do Not Disturb mode in Windows is disabled
4. Restart app

### Keyboard Shortcuts Not Working

**Symptom:** Pressing `Ctrl+N` doesn't create new task

**Quick fixes:**
1. Ensure dialog isn't open (close all dialogs first)
2. Check if focus is in text field (Tab to navigate out)
3. Try clicking window to ensure it's focused
4. Restart application
5. Check for conflicting hotkey software

### Data Export Fails

**Symptom:** "Export failed" error message

**Quick fixes:**
1. Verify write permissions to save location
2. Choose different save location (e.g., Desktop instead of C:\)
3. Close app, restart, try again
4. Check disk space (need ~1 MB free minimum)

### Task Won't Delete

**Symptom:** Clicking Trash doesn't remove task

**Quick fixes:**
1. Check if task has dependencies → Remove dependencies first
2. Right-click → Set State → Trash (alternative method)
3. Restart app and try again

### Can't Find Deferred Task

**Symptom:** Task with start date isn't appearing

**Quick fixes:**
1. Task List → Filter by State: **Deferred**
2. Check start date hasn't passed (task may have auto-activated to Active state)
3. Task List → Clear all filters → Search for task title

### For more detailed solutions, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## 15. Getting Help

### Built-In Help (F1)

**Keyboard Shortcut:** `F1`

**Features:**
- Searchable help content
- Six help categories:
  1. Getting Started
  2. Focus Mode
  3. Task Management
  4. Priority System
  5. Keyboard Shortcuts
  6. FAQ
- Real-time search with match highlighting
- Tab hiding for zero-match searches

**How to use:**
1. Press `F1` to open Help Dialog
2. Type search term in search box
3. Click category tabs to browse topics
4. Click hyperlinks to jump to related topics

### WhatsThis Help (Shift+F1)

**Keyboard Shortcut:** `Shift+F1`

**How it works:**
1. Press `Shift+F1`
2. Cursor changes to question mark
3. Click any field/button to see context-sensitive help
4. Help tooltip appears explaining that element

**Use case:** "What does this field do?" → `Shift+F1` → Click field → Read explanation

### Documentation Files

**Comprehensive guides included with installation:**

- **USER_GUIDE.md** (this file): Complete feature documentation
- **INSTALLATION_GUIDE.md**: Installation instructions for all methods
- **TROUBLESHOOTING.md**: Detailed solutions to common problems
- **KNOWN_ISSUES.md**: Known limitations and workarounds
- **CHANGELOG.md**: Version history and release notes

**Location:** `C:\Program Files\OneTaskAtATime\docs\` (installer) or project root (source install)

### GitHub Issues

**Report bugs or request features:**

**URL:** https://github.com/cmdavis25/OneTaskAtATime/issues

**Before posting:**
1. Search existing issues to avoid duplicates
2. Check KNOWN_ISSUES.md to see if it's a known limitation
3. Try solutions in TROUBLESHOOTING.md

**Bug report template:**
- **Summary:** Brief description
- **Steps to reproduce:** Numbered list
- **Expected behavior:** What should happen
- **Actual behavior:** What actually happened
- **Version:** OneTaskAtATime version (Help → About)
- **OS:** Windows version
- **Screenshots:** If applicable

**Feature request template:**
- **Summary:** Feature name/description
- **Use case:** Why you need this feature
- **Proposed solution:** How it might work
- **Alternatives considered:** Other approaches you've tried

### GitHub Discussions

**Ask questions and share tips:**

**URL:** https://github.com/cmdavis25/OneTaskAtATime/discussions

**Categories:**
- **Q&A**: Ask usage questions
- **Show and Tell**: Share workflows and customizations
- **Ideas**: Discuss potential features
- **General**: Other topics

### Community Support

**Not currently available** (no Discord/Slack/forum as of v1.0)

**Planned:** Community forum in v1.1 for user-to-user support and knowledge sharing

### Email Support

**Not currently available** (no dedicated support email as of v1.0)

**Workaround:** Post question in GitHub Discussions

---

## Appendix: Quick Start Checklist

New to OneTaskAtATime? Follow this checklist to get up and running quickly.

### Day 1: Setup

- [ ] Install OneTaskAtATime (see [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md))
- [ ] Launch app for first time
- [ ] Create 3-5 initial tasks (`Ctrl+N`)
- [ ] Assign Base Priority (High/Medium/Low) to each task
- [ ] Add due dates to time-sensitive tasks
- [ ] Create 2-3 contexts (`@computer`, `@phone`, `@office`)
- [ ] Assign contexts to tasks
- [ ] Enter Focus Mode (`Ctrl+1`)
- [ ] Complete or defer your first task

### Week 1: Build Habits

- [ ] Start each work session in Focus Mode (`Ctrl+1`)
- [ ] Create tasks as they arise (`Ctrl+N`)
- [ ] Use action buttons to process tasks (Complete, Defer, Delegate, Someday, Trash)
- [ ] When postponing, select honest reasons (blocker, dependencies, subtasks)
- [ ] Break down at least one complex task into subtasks
- [ ] Make your first Elo comparison (when prompted)
- [ ] Export data for first backup (`Ctrl+Shift+E`)

### Week 2: Optimize

- [ ] Review contexts—add or remove based on actual usage
- [ ] Create project tags for ongoing work
- [ ] Assign project tags to tasks
- [ ] Filter Task List by context to focus work
- [ ] Experiment with theme (Light vs Dark) in Settings (`Ctrl+,`)
- [ ] Adjust font size for comfort
- [ ] Review Someday/Maybe tasks (if any)
- [ ] Customize resurfacing intervals in Settings

### Week 3: Master

- [ ] Use keyboard shortcuts exclusively for one day
- [ ] Review postpone history (Task List → Right-click task → View History)
- [ ] Create dependencies between related tasks
- [ ] View dependency graph (Right-click task → View Dependency Graph)
- [ ] Delegate a task with follow-up date
- [ ] Review delegated tasks when reminder appears
- [ ] Make 5+ Elo comparisons to train the system
- [ ] Export weekly backup

### Ongoing: Maintain

- [ ] Weekly: Export data backup
- [ ] Weekly: Review Someday/Maybe tasks
- [ ] Monthly: Archive old completed tasks (export → delete)
- [ ] Monthly: Review and adjust contexts/tags
- [ ] Quarterly: Review Settings and optimize intervals

---

**Congratulations!** You've completed the OneTaskAtATime User Guide. You now have all the knowledge to manage tasks effectively and boost your productivity.

**Remember:** The goal isn't to manage perfect lists—it's to execute tasks. Start with Focus Mode, trust the priority system, and keep moving forward.

**Questions?** Press `F1` for built-in help or visit https://github.com/cmdavis25/OneTaskAtATime/discussions

**Happy tasking!**
