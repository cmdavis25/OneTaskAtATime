# Phase Progress Report Format

This document defines the standard format for all phase progress reports in the OneTaskAtATime project. Each phase completion should generate a status document following this structure.

## File Naming Convention

`PHASE{N}_STATUS.md` where N is the phase number (0, 1, 2, 3, etc.)

## Required Document Structure

### 1. Header
```markdown
# Phase {N}: {Phase Name} - {STATUS} {emoji}
```
- **STATUS** should be one of: `COMPLETE`, `IN PROGRESS`, `PLANNED`
- **emoji** should be: ✅ for COMPLETE, 🚧 for IN PROGRESS, 📋 for PLANNED

### 2. Table of Contents
Include a comprehensive TOC linking to all major sections:
```markdown
## Table of Contents

- [Overview](#overview)
- [Deliverables Completed](#deliverables-completed)
  - [1. First Deliverable](#1-first-deliverable-)
  - [2. Second Deliverable](#2-second-deliverable-)
- [How to Use](#how-to-use)
- [Verification Checklist](#verification-checklist)
- [What's Next: Phase {N+1}](#whats-next-phase-n1)
- [Key Files Created](#key-files-created)
- [Success Criteria Met](#success-criteria-met-)
- [Notes](#notes)
```

### 3. Overview Section
Brief 1-3 paragraph summary of:
- What was accomplished in this phase
- Current status of the project
- Any significant milestones reached

### 4. Deliverables Completed
Break down each deliverable with:
- **Subsection header** with ✅ emoji: `### {N}. {Deliverable Name} ✅`
- **Detailed description** of what was built/implemented
- **Code examples** or directory structures where relevant
- **Key features** or functionality added

Example:
```markdown
### 1. Project Structure ✅
Created complete directory hierarchy:
```
OneTaskAtATime/
├── src/
│   ├── main.py
│   └── models/
```
```

### 5. How to Use
Provide practical instructions for:
- **First Time Setup**: Initial installation/configuration steps
- **Running the Application**: How to launch and use new features
- **Running Tests**: How to verify the implementation

Use code blocks with bash syntax highlighting:
```markdown
### First Time Setup
```bash
# Run the automated setup
setup.bat
```
```

### 6. Verification Checklist
Provide a task list format checklist of all testable criteria:
```markdown
## Verification Checklist

- [x] Feature A works correctly
- [x] Feature B launches without errors
- [x] Tests pass with required coverage
```

### 7. What's Next Section
```markdown
## What's Next: Phase {N+1} - {Next Phase Name}

The next phase will implement:
1. Feature X
2. Feature Y
3. Feature Z

See [implementation_plan.md](implementation_plan.md) for complete Phase {N+1} requirements.
```

### 8. Key Files Created/Modified
Table format listing significant files:
```markdown
## Key Files Created

| File | Purpose | Lines |
|------|---------|-------|
| [src/main.py](src/main.py) | Application entry point | 28 |
| [src/models/task.py](src/models/task.py) | Task data model | 150 |
```

Include markdown links to files for easy navigation.

### 9. Success Criteria Met
Quote the original success criteria from the implementation plan and show how it was met or exceeded:
```markdown
## Success Criteria Met ✅

**From Implementation Plan:**
> **Deliverable**: {Original requirement}

**Actual Achievement:**
- ✅ {Requirement met}
- ✅ {Requirement met}
- ✅ **BONUS**: {Extra work completed}
```

### 10. Notes Section
Include any:
- Deviations from original plan
- Technical decisions made
- Known issues or limitations
- Recommendations for future phases

### 11. Footer
```markdown
---

**Phase {N} Status: {STATUS}** {emoji}

{Next action statement}
```

## Formatting Standards

1. **Emojis**: Use consistently (✅ for complete items, 🚧 for in-progress, ❌ for blocked)
2. **Code blocks**: Always specify language for syntax highlighting
3. **File links**: Use markdown link format `[filename](path/to/file)` for all file references
4. **Headings**: Use proper hierarchy (## for main sections, ### for subsections)
5. **Lists**: Use `-` for unordered lists, numbers for ordered lists
6. **Tables**: Use markdown table format with aligned columns
7. **Line length**: Aim for 80-100 character line length in documentation text
8. **Blank lines**: Use blank lines to separate sections for readability

## Example Reference

See [PHASE0_STATUS.md](PHASE0_STATUS.md) for a complete example following this format.

## Purpose

These reports serve multiple purposes:
1. **Documentation**: Track what was accomplished and how
2. **Onboarding**: Help new developers understand project evolution
3. **Verification**: Provide checklists to confirm phase completion
4. **Planning**: Bridge between completed and upcoming work
5. **AI Context**: Give Claude Code clear reference for project state

---

When creating new phase reports, copy the structure from PHASE0_STATUS.md and adapt it to your specific phase deliverables.
