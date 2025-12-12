# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**OneTaskAtATime** is a focused, no-frills to-do list GUI desktop application designed to help users concentrate on executing one task at a time rather than managing multiple task lists. The app is inspired by David Allen's "Getting Things Done" (GTD) methodology but simplifies it to reduce unnecessary complexity.

### Core Philosophy

- **Single-task focus**: The primary feature is Focus Mode, which presents users with one task at a time
- **Flat structure**: Avoid task hierarchies (no nested projects/phases); use tags for organization instead
- **Smart prioritization**: Use comparison-based ranking to resolve priority conflicts
- **Blocker awareness**: Capture reasons when users delay tasks to surface blockers and dependencies

## Architecture Principles

### Task Priority/Importance System

Tasks are scored using two dimensions:

1. **(Effective) Priority**: Effective Priority = Base Priority - Priority Adjustment
   - **Base Priority**: User-configurable 3-point scale (High = 3, Medium = 2, Low = 1)
   - **Priority Adjustment**: Accumulated penalty from comparison losses (starts at 0)
2. **Urgency**: Based on remaining days until due date
   - Tasks with lowest remaining day counts (including negatives for overdue) get urgency score of 3
   - Other tasks scored on normalized scale (latest due date = 1)

**Importance = Effective Priority × Urgency**

#### Comparison-Based Ranking

When multiple tasks have equal top-rank Importance, the app presents task pairs for comparison. The user decides which task is higher-priority, and the losing task's Priority Adjustment is incremented using exponential decay:

**Priority Adjustment += 0.5^N** (where N = number of comparison losses for this task)

This approach leverages Zeno's Paradox to prevent Priority Adjustment from ever reaching 1, ensuring:
- Tasks that consistently lose comparisons are progressively deprioritized
- Effective Priority never reaches zero (minimum Base Priority is 1)
- Each successive loss has diminishing impact, respecting the user's Base Priority choice

**Example progression** for a task with Base Priority = 3:
- Loss 1: PA = 0.5, Effective Priority = 2.5
- Loss 2: PA = 0.75, Effective Priority = 2.25
- Loss 3: PA = 0.875, Effective Priority = 2.125

#### Priority Adjustment Reset Rules

- **Automatic reset**: When user changes Base Priority, both Priority Adjustment and loss count reset to zero
- **Manual reset**: User may manually reset Priority Adjustment, but the app should warn that this will restore the task's ranking and may create new ties requiring re-comparison

#### Implementation Notes

Store two fields per task:
- `priority_adjustment` (current accumulated value)
- `comparison_losses` (count of losses, used to calculate N in 0.5^N formula)

### Task States

Beyond active tasks, the system manages:

- **Deferred Tasks**: Have a Start Date; not actionable until that date
- **Delegated Tasks**: Assigned to others with scheduled follow-ups
- **Someday/Maybe**: Not currently actionable but may become relevant
- **Trash**: Deemed unnecessary by user

These states must be strategically resurfaced to prevent tasks from languishing.

### Task Organization

- Use **flat structure** for the master task list
- Apply **tags** for Projects and Contexts (work environment filters)
- Each task may have only one Context, but Contexts apply to many tasks
- When a task involves multiple subtasks, prompt user to break it down and delete the parent

### Delay Handling

When users delay a task, prompt for reason:

- **Multiple subtasks**: Help user break down the task, select Next Action, delete original
- **Blocker encountered**: Create new task to address the blocker
- **Dependencies**: Link to upstream task(s) that must complete first

## Development Status

This is an early-stage project. The codebase currently contains only project documentation. When implementing:

- Focus on simplicity and minimalism in UI/UX
- Prioritize the single-task Focus Mode as the core user experience
- Implement the comparison-based priority resolution algorithm
- Build systems to resurface deferred/delegated/someday tasks
- Design interfaces that capture delay reasons and dependencies
