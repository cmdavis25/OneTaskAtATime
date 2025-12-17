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

1. **(Effective) Priority**: Elo-based calculation within base priority bands
   - **Base Priority**: User-configurable 3-point scale (High = 3, Medium = 2, Low = 1)
   - **Elo Rating**: Standard Elo rating system (starts at 1500, typically ranges 1000-2000)
   - **Band Mapping**: Elo rating is mapped to effective priority within strict bands:
     - High (base=3): effective priority ∈ [2.0, 3.0]
     - Medium (base=2): effective priority ∈ [1.0, 2.0]
     - Low (base=1): effective priority ∈ [0.0, 1.0]
2. **Urgency**: Based on remaining days until due date
   - Tasks with lowest remaining day counts (including negatives for overdue) get urgency score of 3
   - Other tasks scored on normalized scale (latest due date = 1)

**Importance = Effective Priority × Urgency**

#### Comparison-Based Ranking (Elo System)

When multiple tasks have equal top-rank Importance, the app presents task pairs for comparison. The user decides which task is higher-priority, and both tasks' Elo ratings are updated using the standard Elo formula:

**New Rating = Old Rating + K × (Actual Score - Expected Score)**

Where:
- **K-factor**: 32 for new tasks (< 10 comparisons), 16 for established tasks
- **Actual Score**: 1 for winner, 0 for loser
- **Expected Score**: 1 / (1 + 10^((Opponent Rating - Own Rating) / 400))

This system ensures:
- All High-priority tasks rank above all Medium-priority tasks
- All Medium-priority tasks rank above all Low-priority tasks
- Within each priority tier, Elo refines the ranking
- Tasks that consistently win comparisons get higher Elo ratings
- Tasks that consistently lose comparisons get lower Elo ratings
- Ratings stabilize over time as tasks accumulate comparison history

**Example**: Two High-priority tasks (base=3) with different Elo ratings:
- Task A: elo=1600 → effective priority = 2.60
- Task B: elo=1400 → effective priority = 2.40
- After A wins a comparison, A's elo increases slightly (e.g., to 1612), B's decreases (e.g., to 1388)

#### Priority Reset Rules

- **Automatic reset**: When user changes Base Priority, both Elo rating and comparison count reset to defaults (1500.0, 0)
- **Manual reset**: User may manually reset Elo rating, but the app should warn that this will restore the task's ranking and may create new ties requiring re-comparison

#### Implementation Notes

Store three fields per task:
- `base_priority` (user-selected tier: 1, 2, or 3)
- `elo_rating` (current Elo rating, defaults to 1500.0)
- `comparison_count` (total number of comparisons, used to determine K-factor)

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

## Development Environment

**CRITICAL: All development must be done inside the `onetask_env` virtual environment.**

### Virtual Environment Rules

1. **Always activate the virtual environment BEFORE installing dependencies or running code**
   ```bash
   # Windows
   onetask_env\Scripts\activate

   # Linux/Mac
   source onetask_env/bin/activate
   ```

2. **Never install packages globally** - All pip installations must happen inside the active virtual environment

3. **Verify environment is active** - The prompt should show `(onetask_env)` prefix

4. **Install dependencies within the virtual environment**
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

```bash
# Activate virtual environment first
onetask_env\Scripts\activate

# Seed database with sample data (first time)
python -m src.database.seed_data

# Launch application
python -m src.main

# Run tests
python -m pytest tests/ -v
```

## Development Guidelines

When implementing features:

- Focus on simplicity and minimalism in UI/UX
- Prioritize the single-task Focus Mode as the core user experience
- Implement the comparison-based priority resolution algorithm
- Build systems to resurface deferred/delegated/someday tasks
- Design interfaces that capture delay reasons and dependencies

## Phase Progress Reporting

When completing a development phase, create a status report following the standardized format documented in [phase_progress_report_instructions.md](phase_progress_report_instructions.md). This ensures consistent documentation across all phases and provides clear reference material for project state and progress.

See [PHASE0_STATUS.md](PHASE0_STATUS.md) for an example of a properly formatted phase report.
