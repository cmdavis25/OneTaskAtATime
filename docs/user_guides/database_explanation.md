# Database Schema Explanation

This document explains the database schema for OneTaskAtATime, showing how all 8 tables work together to support the GTD-inspired task management system.

## Database Schema Overview

### Core Entity Tables (3)

#### 1. **`tasks`** - The heart of the system
Stores all task data regardless of state (active, deferred, completed, etc.)

**Key Fields:**
- `id` - Primary key
- `title` - Task description
- `description` - Optional detailed notes
- **Priority System:**
  - `base_priority` - 1 (Low), 2 (Medium), 3 (High)
  - `priority_adjustment` - Cumulative increments from losing comparisons (default 0.0)
  - Effective Priority = base_priority - priority_adjustment
- **Urgency System:**
  - `due_date` - Optional deadline for urgency calculation
- **State Management:**
  - `state` - active, deferred, delegated, someday, completed, trash
  - `start_date` - When deferred tasks become actionable
  - `delegated_to` - Person/system responsible
  - `follow_up_date` - When to check on delegated tasks
  - `completed_at` - Completion timestamp
- **Organization:**
  - `context_id` - Foreign key to contexts (nullable)
- **Resurfacing:**
  - `last_resurfaced_at` - When task was last shown to user
  - `resurface_count` - How many times resurfaced

**Indexes:** state, due_date, start_date, follow_up_date, context_id, base_priority

---

#### 2. **`contexts`** - Work environment filters
GTD concept: filter tasks by where/how you can do them (@computer, @phone, @errands)

**Key Fields:**
- `id` - Primary key
- `name` - Unique context name (e.g., "@computer", "@phone")
- `description` - Optional explanation

**Relationship:**
- One-to-Many with tasks (one context → many tasks)
- Each task has **at most one** context
- When context is deleted → tasks.context_id set to NULL (ON DELETE SET NULL)

---

#### 3. **`project_tags`** - Flat project organization
Unlike hierarchical folders, these are simple tags for grouping

**Key Fields:**
- `id` - Primary key
- `name` - Unique tag name (e.g., "Work", "Personal", "Home")
- `description` - Optional project description
- `color` - Hex color code for UI (#FF5733)

**Relationship:**
- Many-to-Many with tasks (via task_project_tags junction table)
- Each task can have **multiple** project tags

---

### Junction Table (1)

#### 4. **`task_project_tags`** - Links tasks to projects
Implements many-to-many relationship between tasks and project_tags

**Key Fields:**
- `task_id` - Foreign key to tasks
- `project_tag_id` - Foreign key to project_tags
- Primary key is (task_id, project_tag_id) composite

**Relationship:**
- When task is deleted → associations removed (ON DELETE CASCADE)
- When project_tag is deleted → associations removed (ON DELETE CASCADE)

**Example:**
```
Task "Review PR" can have tags: [Work, Learning]
Tag "Work" can apply to: [Review PR, Write docs, Fix bug]
```

---

### Relationship Tables (1)

#### 5. **`dependencies`** - Task blockers
Tracks which tasks must complete before others can start

**Key Fields:**
- `id` - Primary key
- `blocked_task_id` - Task that is waiting (Foreign key to tasks)
- `blocking_task_id` - Task that must complete first (Foreign key to tasks)
- `created_at` - When dependency was created

**Constraints:**
- CHECK: blocked_task_id ≠ blocking_task_id (no self-dependencies)
- Circular dependency detection in application layer (DFS algorithm)

**Relationship:**
- When either task is deleted → dependency removed (ON DELETE CASCADE)

**Example:**
```
Task A: "Write documentation" (blocked_task_id)
Task B: "Review PR #142" (blocking_task_id)
→ Can't write docs until PR is reviewed
```

**Indexes:** blocked_task_id, blocking_task_id (for fast lookups both ways)

---

### History/Tracking Tables (2)

#### 6. **`task_comparisons`** - Priority adjustment history
Records when users choose between tied tasks

**Key Fields:**
- `id` - Primary key
- `winner_task_id` - Task chosen as higher priority
- `loser_task_id` - Task chosen as lower priority
- `adjustment_amount` - Amount subtracted from loser (default 0.5)
- `compared_at` - Timestamp

**Purpose:**
- Tracks comparison history for analysis
- Can be used to reset adjustments or understand user preferences
- Winner's priority unchanged, loser gets priority_adjustment incremented

**Example:**
```
User sees two high-priority tasks:
- Task A: "Fix critical bug" (priority 3.0)
- Task B: "Update docs" (priority 3.0)

User chooses A → Comparison recorded:
- winner_task_id: A
- loser_task_id: B
- adjustment_amount: 0.5

Result: Task B's priority_adjustment increased to 0.5
→ Effective priority: 3.0 - 0.5 = 2.5
```

**Indexes:** winner_task_id, loser_task_id

---

#### 7. **`postpone_history`** - Delay tracking
Captures when/why users postpone tasks to surface blockers

**Key Fields:**
- `id` - Primary key
- `task_id` - Foreign key to tasks
- `reason_type` - multiple_subtasks, blocker, dependency, not_ready, other
- `reason_notes` - User's explanation
- `action_taken` - broke_down, created_blocker, added_dependency, deferred, none
- `postponed_at` - Timestamp

**Purpose:**
- Identify patterns in task avoidance
- Ensure appropriate follow-up actions
- Surface blockers that need addressing

**Example:**
```
User postpones "Launch website":
- reason_type: multiple_subtasks
- reason_notes: "Need to design, develop, and deploy"
- action_taken: broke_down
→ System helps break into 3 separate tasks
```

**Relationship:**
- When task is deleted → history preserved (no CASCADE, for analytics)

**Index:** task_id

---

### Configuration Table (1)

#### 8. **`settings`** - Application configuration
Type-safe key-value storage for app settings

**Key Fields:**
- `key` - Primary key (unique setting name)
- `value` - Stored as text (converted based on value_type)
- `value_type` - string, integer, float, boolean, json
- `description` - What this setting controls
- `updated_at` - Last modification

**Default Settings:**
```
comparison_decrement: 0.5 (float) - Amount to subtract in comparisons
someday_review_days: 7 (integer) - Days between someday task reviews
delegated_remind_days: 1 (integer) - Days before follow-up to remind
deferred_check_hours: 1 (integer) - Hours between deferred task checks
theme: 'light' (string) - UI theme
enable_notifications: true (boolean) - Windows toast notifications
score_epsilon: 0.01 (float) - Threshold for tie detection
```

---

## Key Relationships Diagram

```
                    ┌─────────────┐
                    │  contexts   │
                    └──────┬──────┘
                           │ 1
                           │
                           │ N
                    ┌──────▼──────┐
            ┌───────┤    tasks    ├───────┐
            │       └──────┬──────┘       │
            │              │              │
            │ N            │ N            │ N
            │              │              │
    ┌───────▼────────┐  ┌─▼──────────┐  ┌─▼───────────┐
    │ dependencies   │  │task_project│  │postpone_    │
    │                │  │   _tags    │  │  history    │
    │ blocked_task  ─┼──┤            │  └─────────────┘
    │ blocking_task ─┼──┤            │
    └────────────────┘  └────┬───────┘
                             │ N
                             │
                             │ 1
                      ┌──────▼──────┐
                      │project_tags │
                      └─────────────┘

    ┌─────────────────┐
    │task_comparisons │ ─┐
    │ winner_task ────┼──┼─→ tasks
    │ loser_task  ────┼──┘
    └─────────────────┘

    ┌──────────┐
    │ settings │ (standalone)
    └──────────┘
```

## Data Flow Examples

### Example 1: Creating a Task with Full Context
```sql
-- 1. Create context
INSERT INTO contexts (name) VALUES ('@computer');  -- id=1

-- 2. Create project tag
INSERT INTO project_tags (name, color) VALUES ('Work', '#3498db');  -- id=1

-- 3. Create task
INSERT INTO tasks (
    title, base_priority, due_date, state, context_id
) VALUES (
    'Review PR #142', 3, '2025-12-15', 'active', 1
);  -- id=1

-- 4. Associate with project
INSERT INTO task_project_tags (task_id, project_tag_id)
VALUES (1, 1);
```

### Example 2: Task with Dependency
```sql
-- Task A must complete before Task B can start
INSERT INTO dependencies (blocked_task_id, blocking_task_id)
VALUES (task_b_id, task_a_id);

-- When querying Task B:
SELECT t.*,
       GROUP_CONCAT(d.blocking_task_id) as blocking_tasks
FROM tasks t
LEFT JOIN dependencies d ON t.id = d.blocked_task_id
WHERE t.id = task_b_id;
```

### Example 3: Priority Comparison Flow
```sql
-- 1. Find top-ranked tasks
SELECT * FROM tasks
WHERE state = 'active'
ORDER BY (base_priority - priority_adjustment) * urgency_score DESC
LIMIT 2;

-- 2. User chooses Task A over Task B
INSERT INTO task_comparisons (winner_task_id, loser_task_id, adjustment_amount)
VALUES (task_a_id, task_b_id, 0.5);

-- 3. Update loser's priority
UPDATE tasks
SET priority_adjustment = priority_adjustment + 0.5
WHERE id = task_b_id;
```

### Example 4: Deferred Task Activation
```sql
-- Check for deferred tasks ready to activate
SELECT * FROM tasks
WHERE state = 'deferred'
  AND start_date <= CURRENT_DATE
ORDER BY start_date ASC;

-- Activate task
UPDATE tasks
SET state = 'active', start_date = NULL
WHERE id = task_id;
```

### Example 5: Delegated Task Follow-up
```sql
-- Find delegated tasks needing follow-up (1 day before)
SELECT * FROM tasks
WHERE state = 'delegated'
  AND follow_up_date <= DATE('now', '+1 day')
ORDER BY follow_up_date ASC;
```

## Database Integrity Features

1. **Foreign Key Constraints** - Maintain referential integrity
2. **CHECK Constraints** - Prevent invalid states/priorities at DB level
3. **UNIQUE Constraints** - Ensure context/tag names are unique
4. **Indexes** - Optimize common queries (by state, due date, etc.)
5. **Cascade Rules** - Automatic cleanup of associations when entities deleted
6. **Self-reference Prevention** - Tasks can't depend on themselves

## Circular Dependency Detection

The most complex feature is detecting circular dependencies in the dependency graph.

**Algorithm:** Depth-First Search (DFS)

**How it works:**
1. Before adding dependency "Task A blocked by Task B"
2. Start from Task B and traverse all blocking tasks
3. If we can reach Task A → circular dependency exists!
4. Reject the new dependency with error

**Example:**
```python
# Existing: A → B → C (A blocked by B, B blocked by C)
# Trying to add: C → A (would create cycle)

def _has_path(from_task, to_task, visited):
    if from_task == to_task:
        return True  # Found cycle!

    if from_task in visited:
        return False  # Already checked

    visited.add(from_task)

    # Check all tasks that from_task is blocked by
    for blocking_task in get_blocking_tasks(from_task):
        if _has_path(blocking_task, to_task, visited):
            return True

    return False

# Before adding C → A:
# Check: _has_path(C, A, {})
# → C blocked by B
# → _has_path(B, A, {C})
# → B blocked by A
# → _has_path(A, A, {C, B})
# → Returns True! Cycle detected!
```

## Performance Considerations

**Indexed Queries (Fast):**
- Get all active tasks: `SELECT * FROM tasks WHERE state = 'active'`
- Get tasks by context: `SELECT * FROM tasks WHERE context_id = ?`
- Get tasks by due date: `SELECT * FROM tasks WHERE due_date <= ?`
- Get dependencies: `SELECT * FROM dependencies WHERE blocked_task_id = ?`

**Requires Careful Optimization:**
- Complex priority ranking with urgency calculation
- Finding all transitive dependencies (for cycle detection)
- Resurfacing queries across multiple states

## Table Sizes (Expected)

For a typical user:
- **tasks:** 100-1000 rows (active workflow)
- **contexts:** 5-15 rows (small, stable)
- **project_tags:** 10-50 rows (moderate, stable)
- **task_project_tags:** 200-2000 rows (grows with tasks)
- **dependencies:** 50-200 rows (subset of tasks)
- **task_comparisons:** 500-5000 rows (grows over time, could be pruned)
- **postpone_history:** 200-1000 rows (analytics data)
- **settings:** 10-20 rows (very small)

## Schema Design Philosophy

This schema supports the entire GTD workflow while maintaining:

1. **Flat Task Structure** - No nested projects/phases
2. **Flexible Organization** - Tags instead of hierarchies
3. **Single Context Rule** - One work environment per task
4. **Multiple Projects** - Tasks can belong to many projects via tags
5. **Dependency Tracking** - Without allowing circular dependencies
6. **Historical Data** - Track comparisons and postponements
7. **Type Safety** - Settings validated by type
8. **Data Integrity** - Constraints enforced at database level

This design enables powerful filtering, prevents invalid states, and supports the core Focus Mode feature of presenting one task at a time!