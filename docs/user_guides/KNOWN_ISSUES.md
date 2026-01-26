# OneTaskAtATime v1.0.0 - Known Issues and Limitations

This document lists known limitations, minor bugs, and planned improvements for OneTaskAtATime v1.0.0.

**Last Updated:** 2026-01-24

---

## Platform Limitations

### Windows 10 Compatibility (Untested)

**Status:** Not formally tested

**Description:**
OneTaskAtATime v1.0.0 has been thoroughly tested on Windows 11 only. While the application is expected to work on Windows 10 (version 1909+) due to PyQt5's cross-version compatibility, this has not been formally verified.

**Workaround:**
- Try installing on Windows 10 at your own risk
- Report any issues via GitHub Issues
- We'll add Windows 10 support to formal testing in v1.1

**Planned Fix:** Windows 10 testing in v1.1.0

---

### No Linux/macOS Support

**Status:** Not supported

**Description:**
OneTaskAtATime v1.0.0 is Windows-only. Linux and macOS are not supported due to:
- Windows-specific notification library (winotify)
- Windows-specific path handling
- No cross-platform testing infrastructure yet

**Workaround:**
- Use Windows 11 VM on Linux/macOS
- Use Wine (not tested, may not work)

**Planned Fix:** Linux support in v1.2.0, macOS support in v1.3.0

---

## Feature Limitations

### No Cloud Synchronization

**Status:** By design (privacy-first)

**Description:**
All data is stored locally in SQLite database. There is no cloud sync between devices.

**Workaround:**
- Export data from one machine (File → Export Data)
- Transfer JSON file manually (USB, email, cloud storage)
- Import on second machine (File → Import Data → Merge)

**Planned Fix:** Optional self-hosted sync server in v2.0 (Syncthing integration)

---

### No Mobile App

**Status:** Desktop-only application

**Description:**
OneTaskAtATime has no mobile app (Android/iOS). You cannot access your tasks on phone/tablet.

**Workaround:**
- Export tasks to JSON, open in text editor on mobile
- Use remote desktop app to access Windows machine
- Take screenshots of task list for reference

**Planned Fix:** Progressive Web App (PWA) in v2.0, native mobile apps in v3.0

---

### No Task Attachments

**Status:** Not supported

**Description:**
You cannot attach files (PDFs, images, documents) to tasks.

**Workaround:**
- Store files in dedicated folder (e.g., C:\Tasks\Attachments)
- Reference file path in task description
- Example: "Review contract.pdf (see C:\Tasks\Attachments\contract.pdf)"

**Planned Fix:** File attachment support in v1.4.0

---

### No Subtasks (Nested Tasks)

**Status:** By design (flat structure philosophy)

**Description:**
Tasks cannot have subtasks. All tasks are flat in the database.

**Workaround:**
- Use Subtask Breakdown Dialog (Tools → Break Down Task)
- Creates separate tasks linked by dependencies
- Use project tags to group related tasks

**Planned Fix:** Not planned (philosophical design decision)

---

### No Time Tracking

**Status:** Not implemented

**Description:**
You cannot track time spent on tasks (no built-in timer).

**Workaround:**
- Use external time tracker (Toggl, Clockify)
- Manually note time in task description
- Add custom field via database (advanced users only)

**Planned Fix:** Time tracking in v1.5.0

---

## Performance Limitations

### Slow Performance with 10,000+ Tasks

**Status:** Known limitation

**Description:**
The application has been tested with up to 10,000 tasks. Performance may degrade beyond this:
- Task list loading: 2-3 seconds with 10,000 tasks
- Comparison dialog: Slower with 500+ pending comparisons
- Database queries: Indexes help, but large scans are slow

**Workaround:**
- Archive old completed tasks (Export → Delete)
- Filter task list to reduce visible rows
- Optimize database regularly (Settings → Database → Optimize)

**Planned Fix:** Pagination and lazy loading in v1.2.0

---

### Large Export Files (>100 MB)

**Status:** Known limitation

**Description:**
Exporting 50,000+ tasks creates very large JSON files that may:
- Take 30+ seconds to export
- Fail to open in some text editors
- Consume significant memory during import

**Workaround:**
- Export in smaller batches (by date range or state)
- Use chunked export (File → Export → Advanced → Chunked Export)
- Increase Python memory limit if running from source

**Planned Fix:** Streaming export in v1.3.0

---

## UI/UX Minor Issues

### Task List Column Resizing Not Persisted

**Status:** Minor bug

**Description:**
When you resize task list columns, the widths reset on next launch.

**Workaround:**
- Manually resize columns each session
- Or use Column Visibility to hide unwanted columns

**Planned Fix:** v1.0.1 (patch release)

---

## Notification Quirks

### Notifications Suppressed by Windows Focus Assist

**Status:** Windows OS limitation

**Description:**
If Windows Focus Assist is enabled (during presentations, gaming, etc.), OneTaskAtATime notifications will not appear.

**Workaround:**
- Disable Focus Assist (Windows Settings → System → Focus Assist → Off)
- Add OneTaskAtATime to "Priority only" allow list
- Check Notification Panel manually for missed notifications

**Planned Fix:** None (OS behavior)

---

### Toast Notifications Disappear After 5 Seconds

**Status:** winotify library limitation

**Description:**
Windows toast notifications auto-dismiss after 5 seconds. You may miss them if not at computer.

**Workaround:**
- Check Notification Panel for history (View → Notifications)
- Enable Windows Action Center to keep notifications
- Adjust notification duration in Windows Settings (if supported)

**Planned Fix:** Persistent notifications in v1.2.0

---

### No Sound with Notifications on Some Systems

**Status:** Windows configuration issue

**Description:**
Some Windows installations don't play sound with toast notifications, even when enabled.

**Workaround:**
- Windows Settings → System → Notifications → OneTaskAtATime → Play a sound
- Check Windows volume mixer (OneTaskAtATime not muted)
- Test with Windows built-in notification sounds first

**Planned Fix:** None (Windows configuration)

---

## Data Integrity

### Deleted Contexts/Tags Still Show in Filters

**Status:** Minor bug

**Description:**
If you delete a context or project tag, it may still appear in filter dropdowns until restart.

**Workaround:**
- Restart application to refresh filter lists
- Or click "Refresh" button in filter dialog (if available)

**Planned Fix:** v1.0.1 (patch release)

---

### Undo Limited to 50 Actions

**Status:** By design (memory constraint)

**Description:**
The undo stack stores only the last 50 actions. Older actions cannot be undone.

**Workaround:**
- Export data before major changes
- Use task history (Ctrl+H) to audit changes
- Restore from export if needed

**Planned Fix:** Configurable undo limit in v1.1.0

---

### No Undo for Database-Level Operations

**Status:** Known limitation

**Description:**
The following operations cannot be undone:
- Import data (merge or replace)
- Optimize database
- Reset database
- Delete context/tag (cascades to all tasks)

**Workaround:**
- Export data before these operations
- Read confirmation dialogs carefully

**Planned Fix:** Transaction-based undo for imports in v1.2.0

---

## Import/Export Limitations

### Export Format is JSON Only

**Status:** By design

**Description:**
You can only export to JSON format. CSV, Excel, and other formats are not supported.

**Workaround:**
- Use online JSON-to-CSV converter
- Write Python script to convert (sample provided in docs/scripts)
- Use third-party tool (jq, Python pandas)

**Planned Fix:** CSV export in v1.1.0, Excel export in v1.2.0

---

### Import Doesn't Merge Duplicate Tasks Intelligently

**Status:** Known limitation

**Description:**
When importing, if a task with same title exists, the app prompts for each duplicate instead of auto-merging.

**Workaround:**
- Use "Replace All" option to overwrite all duplicates
- Or pre-process JSON file to remove duplicates before import

**Planned Fix:** Smart merge in v1.3.0

---

## Security & Privacy

### No Password Protection

**Status:** Not implemented

**Description:**
The database file is not encrypted. Anyone with access to your Windows user account can read your tasks.

**Workaround:**
- Use Windows user account password
- Enable Windows BitLocker for full-disk encryption
- Store database on encrypted USB drive

**Planned Fix:** Optional database encryption in v1.4.0

---

### No Multi-User Support

**Status:** Single-user application

**Description:**
OneTaskAtATime is designed for single user. There's no user authentication, permissions, or role-based access.

**Workaround:**
- Each Windows user has separate database
- Use separate Windows accounts for each person
- Or manually partition tasks by project tag

**Planned Fix:** Multi-user support in v2.0 (major redesign)

---

## Build and Packaging

### Installer Not Code-Signed

**Status:** Cost limitation ($300+/year for certificate)

**Description:**
The Windows installer is not digitally signed, causing SmartScreen warnings.

**Workaround:**
- Click "More info" → "Run anyway" when SmartScreen appears
- Verify SHA-256 hash matches GitHub release notes
- Download only from official GitHub Releases

**Planned Fix:** Code signing if project funding is secured

---

### No Auto-Update Feature

**Status:** Not implemented

**Description:**
You must manually download and install new versions. No automatic update check or download.

**Workaround:**
- Watch GitHub repository for release notifications
- Subscribe to release RSS feed
- Manually check for updates monthly

**Planned Fix:** Auto-update check in v1.1.0 (prompt to download)

---

## Accessibility

### Screen Reader Support Limited

**Status:** Partial support

**Description:**
OneTaskAtATime has basic screen reader support (accessible labels), but may not be fully navigable with NVDA/JAWS.

**Workaround:**
- Use keyboard shortcuts extensively
- Enable High Contrast mode in Windows
- Report specific accessibility issues for prioritization

**Planned Fix:** Full WCAG 2.1 AA compliance in v1.4.0

---

### No Keyboard-Only Navigation in Graph View

**Status:** Known limitation

**Description:**
The dependency graph requires mouse to navigate. You cannot select nodes with keyboard only.

**Workaround:**
- Use Task List view with keyboard shortcuts
- Use Tab key to navigate between dialogs
- Graph is supplementary visualization only

**Planned Fix:** v1.3.0

---

## Documentation

### No Video Tutorials Yet

**Status:** Planned for post-release

**Description:**
The application ships with text documentation only. No official video tutorials or screencasts.

**Workaround:**
- Read USER_GUIDE.md thoroughly
- Use in-app help (F1)
- Check YouTube for community tutorials (unofficial)

**Planned Fix:** Official tutorial videos in 2 weeks post-release

---

## Contributing

Found an issue not listed here? Please report it!

**GitHub Issues:** https://github.com/cdavis/OneTaskAtATime/issues

**When Reporting:**
- Check if already in KNOWN_ISSUES.md (this file)
- Check if already reported in GitHub Issues
- Provide clear steps to reproduce
- Include Windows version and OneTaskAtATime version

**Issue Priority:**
1. **Critical**: Data loss, crashes, security vulnerabilities
2. **High**: Major features broken, unusable workflows
3. **Medium**: Minor features broken, workarounds exist
4. **Low**: UI polish, cosmetic issues, nice-to-haves

---

## Roadmap Summary

**v1.0.1 (Patch - 2 weeks):**
- Column resize persistence
- Filter refresh on context/tag delete
- Theme switching without restart

**v1.1.0 (Minor - 1 month):**
- Recurring tasks
- CSV export
- Auto-update check
- Configurable undo limit
- Windows 10 formal testing

**v1.2.0 (Minor - 2 months):**
- Task list pagination
- Persistent notifications
- Smart import merge
- Performance optimizations

**v1.3.0 (Minor - 3 months):**
- Streaming large exports
- Graph view improvements
- Keyboard-only navigation

**v1.4.0 (Minor - 4 months):**
- File attachments
- Optional database encryption
- Time tracking
- WCAG 2.1 AA compliance

**v2.0.0 (Major - 6 months):**
- Self-hosted sync server
- Progressive Web App (PWA)
- Multi-user support
- Major UI redesign

---

## Workarounds Summary

For quick reference, here are the most impactful workarounds:

1. **No cloud sync** → Export/Import manually via JSON
2. **No recurring tasks** → Create manually or use Windows Task Scheduler reminder
3. **Slow with 10,000+ tasks** → Archive old completed tasks
4. **No mobile app** → Use remote desktop app to access Windows machine
5. **Notifications suppressed** → Disable Windows Focus Assist
6. **SmartScreen warning** → Click "More info" → "Run anyway"
7. **No undo for imports** → Export data before major operations
8. **No password protection** → Use Windows BitLocker full-disk encryption

---

**Questions or Concerns?**

If you're unsure whether something is a bug or expected behavior, check:
1. This file (KNOWN_ISSUES.md)
2. USER_GUIDE.md
3. TROUBLESHOOTING.md
4. GitHub Issues (search existing)

Still unclear? Open a GitHub Discussion for clarification before filing a bug report.
