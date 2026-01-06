# Implementation Plan: Merge Blocker and Dependency Radio Options

## Summary

Merge the "Encountered a blocker" and "Waiting on another task" radio button options in the Deferred Task dialog into a single option that provides a unified multi-select dependency workflow. This eliminates functional redundancy while preserving the best features of both workflows.

## User Decisions

- **Dialog Experience**: Use multi-select dependency dialog (current 'Waiting on another task' workflow)
- **Radio Button Label**: "Has blocking tasks / dependencies"
- **Analytics**: Consolidate under `PostponeReasonType.BLOCKER` (deprecate `DEPENDENCY`)
- **Undo Behavior**: Move newly created blocking tasks to TRASH when undoing defer action

## Critical Files

### UI Components
- [src/ui/postpone_dialog.py](src/ui/postpone_dialog.py) - Main defer dialog with radio buttons
- [src/ui/dependency_selection_dialog.py](src/ui/dependency_selection_dialog.py) - Multi-select blocking tasks dialog
- [src/ui/blocker_selection_dialog.py](src/ui/blocker_selection_dialog.py) - To be deprecated/removed

### Commands
- [src/commands/defer_with_blocker_command.py](src/commands/defer_with_blocker_command.py) - To be deprecated
- [src/commands/defer_with_dependencies_command.py](src/commands/defer_with_dependencies_command.py) - Enhance to track created tasks

### Services
- [src/services/postpone_workflow_service.py](src/services/postpone_workflow_service.py) - Workflow coordination and analytics

### Models
- [src/models/enums.py](src/models/enums.py) - PostponeReasonType enum (deprecate DEPENDENCY)

### Main Window
- [src/ui/main_window.py](src/ui/main_window.py) - Command execution and menu integration

## Implementation Steps

### 1. Enhance DependencySelectionDialog to Support New Task Creation with Inheritance

**File**: [src/ui/dependency_selection_dialog.py](src/ui/dependency_selection_dialog.py)

**Changes**:
- Modify "New Task" button handler to use `EnhancedTaskFormDialog` (like blocker workflow)
- Pre-fill new task form with inherited attributes from blocked task:
  - Priority (base_priority, elo_rating, comparison_count)
  - Due date
  - Context
  - Project tags
- Track which blocking tasks were created during this dialog session (new instance variable `created_blocking_task_ids`)
- Add method `get_created_blocking_task_ids()` to return list of task IDs created during session
- Keep existing multi-select functionality and immediate dependency saving

**Why**: This gives users the best of both workflows—multi-select capability with intelligent defaults for new tasks.

### 2. Update DeferWithDependenciesCommand to Track Created Tasks

**File**: [src/commands/defer_with_dependencies_command.py](src/commands/defer_with_dependencies_command.py)

**Changes**:
- Add constructor parameter `created_blocking_task_ids: List[int]` (defaults to empty list)
- Store created task IDs as instance variable
- Update `undo()` method to move created blocking tasks to TRASH state when undoing
- Use `task_dao.update_state()` to transition created tasks to `TaskState.TRASH`

**Why**: Implements the desired undo behavior where blocking tasks created during the workflow are cleaned up on undo.

### 3. Consolidate Radio Button Options in PostponeDialog

**File**: [src/ui/postpone_dialog.py](src/ui/postpone_dialog.py)

**Changes**:
- Remove "Encountered a blocker" radio button (lines 205-206)
- Change "Waiting on another task" radio button text to "Has blocking tasks / dependencies" (line 209)
- Update `PostponeReasonType.DEPENDENCY` mapping to `PostponeReasonType.BLOCKER` (line 209)
- Remove blocker workflow branch in `on_accept()` method (lines 250-256)
- Update dependency workflow branch to:
  - Open `DependencySelectionDialog` (existing)
  - Retrieve created blocking task IDs from dialog
  - Pass created task IDs to `DeferWithDependenciesCommand`
- Keep reflection dialog integration unchanged

**Why**: Simplifies the UI and unifies the workflows under one option.

### 4. Update PostponeWorkflowService

**File**: [src/services/postpone_workflow_service.py](src/services/postpone_workflow_service.py)

**Changes**:
- Rename `handle_dependency_workflow()` to `handle_blocker_workflow()` (replace existing version)
- Update method to:
  - Accept both `blocking_task_ids` list and `created_blocking_task_ids` list
  - Use `PostponeReasonType.BLOCKER` for analytics
  - Use `ActionTaken.CREATED_BLOCKER` when `created_blocking_task_ids` is non-empty
  - Use `ActionTaken.ADDED_DEPENDENCY` when only existing tasks selected (for backward compatibility in analytics)
- Remove old `handle_blocker_workflow()` method (single blocker version)

**Why**: Consolidates workflow handling while preserving useful analytics distinctions.

### 5. Update Main Window Command Usage

**File**: [src/ui/main_window.py](src/ui/main_window.py)

**Changes**:
- Remove blocker command workflow (lines 462-471)
- Update dependency command instantiation to pass `created_blocking_task_ids` from dialog
- Remove import for `DeferWithBlockerCommand`

**Why**: Removes deprecated blocker-specific command path.

### 6. Deprecate PostponeReasonType.DEPENDENCY Enum Value

**File**: [src/models/enums.py](src/models/enums.py)

**Changes**:
- Add deprecation comment to `DEPENDENCY` enum value
- Keep enum value for backward compatibility with existing postpone history records
- Document that new deferrals should use `BLOCKER` instead

**Why**: Maintains backward compatibility while consolidating new usage under BLOCKER.

### 7. Remove Deprecated Files (Optional Cleanup)

**Files to Remove**:
- [src/ui/blocker_selection_dialog.py](src/ui/blocker_selection_dialog.py)
- [src/commands/defer_with_blocker_command.py](src/commands/defer_with_blocker_command.py)

**Why**: Clean up unused code after migration is complete.

### 8. Update Tests

**Test Files to Update**:
- Tests for `DependencySelectionDialog` - verify new task creation with inheritance
- Tests for `DeferWithDependenciesCommand` - verify undo moves created tasks to trash
- Tests for `PostponeDialog` - verify merged radio button option
- Tests for `PostponeWorkflowService` - verify consolidated blocker workflow

**New Tests Needed**:
- Test that created blocking tasks inherit attributes correctly
- Test that undo removes dependencies AND trashes created tasks
- Test that analytics use BLOCKER reason type
- Test backward compatibility with existing DEPENDENCY records

## Migration Considerations

### Analytics Impact
- Historical `PostponeRecord` entries with `PostponeReasonType.DEPENDENCY` will remain unchanged
- New deferrals will use `PostponeReasonType.BLOCKER`
- Analytics queries should handle both reason types during transition period
- `ActionTaken` still distinguishes between `CREATED_BLOCKER` and `ADDED_DEPENDENCY` for granular insights

### Undo/Redo History
- Existing undo stack entries with `DeferWithBlockerCommand` or `DeferWithDependenciesCommand` will continue to work
- New deferrals use enhanced `DeferWithDependenciesCommand` with created task tracking

### User Experience
- Users will see 4 radio options instead of 5 (simpler, less confusing)
- Single workflow handles both creating new blocking tasks and selecting existing ones
- Multi-select capability is now available for all blocking task scenarios
- More powerful "New Task" button with intelligent defaults

## Risks and Mitigations

**Risk**: Existing tests may fail due to enum value changes
**Mitigation**: Update tests to use `PostponeReasonType.BLOCKER`, keep `DEPENDENCY` for backward compatibility tests

**Risk**: Undo stack corruption if old commands are in history
**Mitigation**: Keep both command classes temporarily, only remove after confirming no active undo stacks

**Risk**: Analytics dashboards break due to missing DEPENDENCY reason type
**Mitigation**: Deprecate rather than remove enum value, update analytics queries to treat both as equivalent

## Success Criteria

- ✅ Deferred Task dialog shows 4 radio options (down from 5)
- ✅ "Has blocking tasks / dependencies" option opens multi-select dialog
- ✅ Creating new blocking tasks inherits priority, due date, context, and project tags
- ✅ Users can add multiple blocking tasks (new or existing) in one workflow
- ✅ Undo defer action removes dependencies AND moves created blocking tasks to TRASH
- ✅ Postpone analytics record `PostponeReasonType.BLOCKER` for merged workflow
- ✅ Existing tests pass with updated assertions
- ✅ No regression in other defer workflows (subtasks, not ready, other)
