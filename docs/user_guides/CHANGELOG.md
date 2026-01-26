# Changelog

All notable changes to OneTaskAtATime will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-24

### Added

#### Core Features
- **Focus Mode**: Present one task at a time to eliminate decision fatigue
  - Single-task view with action buttons (Complete, Defer, Delegate, Someday, Trash)
  - Automatic advancement to next highest-priority task
  - Keyboard shortcuts for all actions
- **Elo-Based Priority System**: Intelligent task ranking using chess-like algorithm
  - Three-tier base priority system (High, Medium, Low)
  - Within-tier refinement using Elo ratings (1000-2000 range)
  - Band mapping ensures High > Medium > Low priority separation
  - Comparison dialog for resolving equal-importance tasks
  - K-factor adjustment based on task comparison history (32 for new, 16 for established)
- **Importance Calculation**: Priority × Urgency formula
  - Effective priority derived from Elo rating within band constraints
  - Urgency based on due date proximity
  - Combined score determines task ranking
- **Task States Management**:
  - **Active**: Currently actionable tasks
  - **Deferred**: Tasks with future start dates
  - **Delegated**: Tasks assigned to others with follow-up dates
  - **Someday/Maybe**: Tasks not currently actionable
  - **Completed**: Finished tasks with completion timestamps
  - **Trash**: Deleted tasks (recoverable)
- **Postpone Workflow**: Intelligent handling of deferred tasks
  - Blocker detection and creation
  - Dependency linking for blocked tasks
  - Postponement pattern tracking
  - Intervention suggestions for repeatedly delayed tasks
- **Dependency Management**:
  - Link tasks that must be completed in order
  - Visual dependency graph with interactive navigation
  - Circular dependency prevention
  - Automatic dependency indicators in task list
  - Cascade handling when dependencies are deleted
- **Task Resurfacing**: Automated reminders to prevent task neglect
  - Deferred tasks activate on start date
  - Delegated tasks resurface on follow-up date
  - Someday/Maybe review prompts (configurable interval)
  - Notification system with Windows toast notifications
  - Resurfacing scheduler with background monitoring

#### UI/UX
- **Main Window**: Tabbed interface with Focus Mode and Task List views
  - Responsive layout with geometry persistence
  - Window position and size remembered across sessions
  - Status bar with task counts and statistics
- **Task List View**: Comprehensive task management interface
  - Sortable columns (Priority, Title, Due Date, State, Context, Tags)
  - Multi-column filtering
  - Quick search with real-time results
  - Context menu with all task actions
  - Bulk operations support
  - Column visibility customization
  - Dependency indicators and navigation
- **Task Form Dialog**: Feature-rich task creation and editing
  - All task properties in one dialog
  - Context and project tag selection with management buttons
  - Due date picker with calendar widget
  - Base priority selection (High/Medium/Low)
  - Inline context and tag creation
  - Form validation with helpful error messages
  - WhatsThis help for all fields (Shift+F1)
- **Comparison Dialog**: Side-by-side task comparison for ranking
  - Displays both tasks' full details
  - Shows current Elo ratings
  - One-click selection
  - Progress tracking (X of Y comparisons)
  - Skip option for uncertain choices
- **Sequential Ranking Dialog**: Drag-and-drop task ordering
  - Visual reordering interface
  - Batch Elo updates based on final order
  - Used for initial task setup or manual reordering
- **Analytics Dashboard**: Comprehensive productivity insights
  - Task completion trends over time
  - Priority distribution charts
  - Context and project tag statistics
  - Completion rate by priority level
  - Interactive charts with filtering
  - Export analytics data to CSV
- **Notification Panel**: Centralized notification management
  - View all resurfacing notifications
  - Dismiss or act on notifications directly
  - Notification history log
  - Badge counter on notification icon
- **Settings Dialog**: Extensive customization options
  - Theme selection (Light, Dark, System)
  - Font size adjustment
  - Resurfacing intervals (Someday review, Delegated follow-up)
  - Notification preferences
  - Window geometry reset
  - Database statistics and maintenance
- **Help Dialog**: Searchable help system with tab hiding
  - Six help categories (Getting Started, Focus Mode, Task Management, Priority System, Shortcuts, FAQ)
  - Real-time search with match highlighting
  - Automatic tab hiding for zero-match searches
  - Match counts displayed in tab titles
  - Clear button for quick search reset
- **Keyboard Shortcuts Dialog**: Quick reference for all shortcuts
  - Organized by category (General, Navigation, Focus Mode, Task List, Dialogs)
  - Searchable shortcut list
  - Always accessible via Ctrl+? or F1
- **Review Dialogs**: Dedicated interfaces for each task state
  - Review Deferred Tasks: See all tasks with start dates
  - Review Delegated Tasks: Track delegated work with follow-up dates
  - Review Someday/Maybe: Periodic review of postponed ideas
  - Batch actions for state transitions
- **Task History Dialog**: Complete audit trail for every task
  - Chronological change log
  - Shows who changed what and when
  - Filter by change type
  - Export history to text file
- **Subtask Breakdown Dialog**: Break complex tasks into smaller pieces
  - Create multiple subtasks from parent task
  - Automatic dependency linking
  - Parent task deletion after breakdown
  - Preserve original task properties
- **Dependency Graph View**: Visual task dependency visualization
  - Interactive graph with node navigation
  - Click to focus on specific tasks
  - Detect and display circular dependencies
  - Export graph as image

#### Data Management
- **SQLite Database**: Local, privacy-focused data storage
  - All data stored in %APPDATA%\OneTaskAtATime\onetaskattime.db
  - No cloud sync, no external servers
  - ACID compliance for data integrity
  - Foreign key constraints enabled
  - Automatic schema migrations
- **Export Functionality**: Comprehensive data backup
  - Export to JSON format
  - Includes tasks, contexts, tags, dependencies, history
  - Human-readable format for easy inspection
  - Configurable export filters (state, date range)
- **Import Functionality**: Data restoration and migration
  - Import from JSON exports
  - Schema validation before import
  - Merge or replace options
  - Conflict resolution strategies
  - Import preview with statistics
- **Data Reset Service**: Clean slate option with safety
  - Full database reset with confirmation
  - Optional export before reset
  - Cannot be undone (explicit warning)
- **Task History Service**: Complete change tracking
  - Every task modification logged
  - Timestamp and change type recorded
  - Queryable history for audit trails

#### Customization
- **Theme System**: Multiple visual themes
  - Light theme (default, high contrast)
  - Dark theme (easy on eyes, low light environments)
  - System theme (follows OS preferences)
  - Custom theme support via QSS files
  - Dynamic theme switching without restart
- **Font Scaling**: Accessibility support
  - Adjustable font sizes (Small, Medium, Large, Extra Large)
  - Applies globally across application
  - Persisted in settings
- **Column Management**: Customizable task list
  - Show/hide any column
  - Reorder columns via drag-and-drop
  - Per-column sort direction
  - Settings saved per user
- **Notification Preferences**: Control notification behavior
  - Enable/disable toast notifications
  - Configure resurfacing intervals
  - Sound preferences (if implemented)

### Technical Details
- **Language**: Python 3.10+
- **GUI Framework**: PyQt5 5.15+
- **Database**: SQLite 3
- **Scheduling**: APScheduler for background tasks
- **Notifications**: winotify for Windows toast notifications
- **Testing**: 726 comprehensive tests with 100% pass rate
  - Unit tests for all algorithms (Elo, priority, ranking)
  - Integration tests for database operations
  - UI tests for all dialogs and views
  - Command pattern tests for undo/redo
  - Service layer tests for business logic
- **Code Quality**:
  - Type hints throughout codebase
  - Comprehensive docstrings
  - PEP 8 compliant
  - Modular architecture with clear separation of concerns

### Platform Support
- **Windows 11**: Fully tested and supported
- **Windows 10**: Expected to work (not formally tested)
- **Linux/macOS**: Not supported in v1.0 (future consideration)

### Documentation
- Complete user guide with step-by-step instructions
- Installation guide for Windows
- Troubleshooting guide for common issues
- Known issues and limitations documented
- Inline help with WhatsThis tooltips
- Searchable help dialog
- Keyboard shortcuts reference

### Performance
- Tested with 10,000+ tasks
- Sub-second task list filtering and sorting
- Efficient Elo calculation algorithm
- Background task resurfacing without UI blocking
- Database indexing for fast queries

### Security & Privacy
- All data stored locally on user's machine
- No telemetry or analytics collection
- No network requests
- No user tracking
- Open source and auditable

---

## Release Notes

OneTaskAtATime v1.0.0 is the first production release of this GTD-inspired task management application. The application is designed for Windows users who want to focus on execution rather than endless task organization.

### Key Highlights

1. **Focus Mode**: Reduces decision fatigue by showing one task at a time
2. **Smart Prioritization**: Elo-based ranking ensures the most important task is always first
3. **Task Resurfacing**: Automatically reminds you about deferred and delegated tasks
4. **Privacy-First**: All data stays on your computer, no cloud sync required
5. **Fully Tested**: 726 passing tests ensure reliability and stability

### Known Limitations

See KNOWN_ISSUES.md for details on:
- Windows 11 only (formally tested)
- No cloud synchronization
- No mobile app
- No recurring task support (planned for v1.1)
- Performance tested to 10,000 tasks

### Getting Started

1. Download the installer from GitHub Releases
2. Run OneTaskAtATime-1.0.0-Setup.exe
3. Launch the application from Start Menu
4. Complete the welcome wizard
5. Press Ctrl+N to create your first task

For detailed instructions, see INSTALLATION_GUIDE.md and USER_GUIDE.md.

### Feedback & Support

- Report bugs: https://github.com/cdavis/OneTaskAtATime/issues
- Feature requests: https://github.com/cdavis/OneTaskAtATime/discussions
- Documentation: See docs/ folder

### License

MIT License - See LICENSE file for full text

---

[1.0.0]: https://github.com/cdavis/OneTaskAtATime/releases/tag/v1.0.0
