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

### Task Prioritization System

Tasks are scored using two dimensions:

1. **Priority**: 3-point scale (High = 3, Medium = 2, Low = 1)
2. **Urgency**: Based on days until due date
   - Tasks with lowest day counts (including negatives for overdue) get urgency score of 3
   - Other tasks scored on normalized scale (latest due date = 1)

When multiple tasks have equal top-rank importance, the app presents pairs for comparison and decrements the lower-priority task by 0.5 points (configurable).

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
