# OneTaskAtATime Troubleshooting Guide

This guide provides solutions to common problems you may encounter while using OneTaskAtATime v1.0.0.

## Table of Contents

- [Application Won't Start](#application-wont-start)
- [Database Errors](#database-errors)
- [Performance Issues](#performance-issues)
- [Theme and Display Problems](#theme-and-display-problems)
- [Notification Issues](#notification-issues)
- [Task Comparison Problems](#task-comparison-problems)
- [Import/Export Failures](#importexport-failures)
- [Keyboard Shortcuts Not Working](#keyboard-shortcuts-not-working)
- [Data Recovery](#data-recovery)
- [Reporting Bugs](#reporting-bugs)

---

## Application Won't Start

### Symptom: Double-clicking icon does nothing

**Possible Causes:**
- Application already running in background
- Corrupted database file
- Missing dependencies
- Insufficient permissions

**Solutions:**

1. **Check if already running:**
   ```
   - Open Task Manager (Ctrl+Shift+Esc)
   - Look for "OneTaskAtATime.exe" in Processes tab
   - If found, click "End Task"
   - Try launching again
   ```

2. **Run as Administrator:**
   ```
   - Right-click the OneTaskAtATime icon
   - Select "Run as administrator"
   - If this works, the issue is permissions-related
   ```

3. **Check database folder permissions:**
   ```
   - Navigate to: %APPDATA%\OneTaskAtATime
   - Right-click folder → Properties → Security
   - Ensure your user account has "Full control"
   - If not, add permissions or contact IT admin
   ```

4. **Rename database to force rebuild:**
   ```
   - Close all OneTaskAtATime instances
   - Navigate to: %APPDATA%\OneTaskAtATime
   - Rename onetaskattime.db to onetaskattime.db.backup
   - Launch application (will create new empty database)
   - If this works, your database was corrupted (see Data Recovery)
   ```

5. **Reinstall application:**
   ```
   - Export your data first (if possible)
   - Uninstall OneTaskAtATime
   - Delete %APPDATA%\OneTaskAtATime folder (backup first!)
   - Reinstall from fresh download
   ```

---

### Symptom: Application crashes immediately with error message

**Error: "Python Runtime Error"**

**Solution:**
- Update Windows to latest version
- Install Visual C++ Redistributables:
  - Download from https://aka.ms/vs/17/release/vc_redist.x64.exe
  - Run installer
  - Restart computer

**Error: "Failed to execute script"**

**Solution:**
- Your antivirus may have quarantined files
- Check antivirus quarantine folder
- Restore quarantined files
- Add OneTaskAtATime to antivirus exclusions

**Error: "DLL load failed"**

**Solution:**
- Missing Qt libraries (PyQt5 issue)
- Reinstall application
- If from source: `pip uninstall PyQt5 && pip install PyQt5`

---

## Database Errors

### Error: "Database is locked"

**Cause:** Another process is accessing the database file.

**Solutions:**

1. **Close duplicate instances:**
   ```
   - Open Task Manager
   - End all OneTaskAtATime.exe processes
   - Delete %APPDATA%\OneTaskAtATime\onetaskattime.db-wal file
   - Delete %APPDATA%\OneTaskAtATime\onetaskattime.db-shm file
   - Restart application
   ```

2. **Check file permissions:**
   ```
   - Navigate to %APPDATA%\OneTaskAtATime
   - Right-click onetaskattime.db → Properties
   - Uncheck "Read-only" if checked
   - Apply changes
   ```

3. **Close database-accessing tools:**
   ```
   - If you opened the database in SQLite browser or similar tool
   - Close that tool completely
   - Try OneTaskAtATime again
   ```

---

### Error: "Database schema mismatch"

**Cause:** Attempting to use database from different version.

**Solution:**
```
The application should auto-migrate the schema.
If this error persists:

1. Export data from old version (if possible)
2. Rename old database:
   %APPDATA%\OneTaskAtATime\onetaskattime.db → onetaskattime_old.db
3. Launch OneTaskAtATime (creates new database)
4. Import data from export file
```

---

### Error: "Failed to create database"

**Cause:** Insufficient disk space or permissions.

**Solutions:**

1. **Check disk space:**
   ```
   - Ensure at least 100 MB free space on C: drive
   - Clean up temporary files if needed
   ```

2. **Check folder permissions:**
   ```
   - Create %APPDATA%\OneTaskAtATime folder manually
   - Grant your user account full control
   - Try launching application again
   ```

---

## Performance Issues

### Symptom: Slow task list loading (10+ seconds)

**Possible Causes:**
- Too many tasks (10,000+)
- Database fragmentation
- Low system resources

**Solutions:**

1. **Optimize database:**
   ```
   - File → Settings → Database → Optimize Database
   - This runs VACUUM command to defragment
   - May take 1-2 minutes for large databases
   ```

2. **Archive old completed tasks:**
   ```
   - Export all completed tasks to JSON
   - Delete completed tasks older than 6 months
   - This reduces database size
   ```

3. **Limit column visibility:**
   ```
   - Task List → Right-click header → Column Visibility
   - Hide columns you don't use
   - Fewer columns = faster rendering
   ```

4. **Close other resource-intensive applications:**
   ```
   - OneTaskAtATime may slow down if RAM is constrained
   - Close browser tabs, other apps
   - Consider upgrading to 8GB+ RAM
   ```

---

### Symptom: Task comparison dialog slow to open

**Cause:** Rendering complex task descriptions with images or long text.

**Solutions:**

1. **Simplify task descriptions:**
   ```
   - Keep descriptions under 500 characters
   - Avoid embedding images (not supported anyway)
   - Use plain text instead of rich formatting
   ```

2. **Reduce comparison queue:**
   ```
   - The dialog may be slow if comparing 50+ tasks
   - Break tasks into smaller priority groups
   - Complete some tasks before comparing more
   ```

---

## Theme and Display Problems

### Symptom: Theme not loading, application looks plain

**Cause:** Missing theme file or corrupted QSS.

**Solutions:**

1. **Reset to default theme:**
   ```
   - File → Settings → Appearance → Theme: Light
   - Click Apply
   - Restart application
   ```

2. **Restore default themes:**
   ```
   - Delete %APPDATA%\OneTaskAtATime\themes folder
   - Restart application (will recreate default themes)
   ```

3. **Check theme file integrity:**
   ```
   - Navigate to %APPDATA%\OneTaskAtATime\themes
   - Ensure light.qss and dark.qss are present
   - Each should be 5-10 KB in size
   - If corrupted, reinstall application
   ```

---

### Symptom: Text too small or too large

**Solution:**
```
- File → Settings → Appearance → Font Size
- Choose Small, Medium, Large, or Extra Large
- Click Apply
- Changes take effect immediately
```

---

### Symptom: Window too small, can't see buttons

**Solution:**
```
- File → Settings → Window → Reset Window Geometry
- This restores default size and position
- Alternatively, maximize the window (Windows key + Up arrow)
```

---

### Symptom: Dark theme is too dark, can't read text

**Cause:** Low contrast on certain monitors.

**Solutions:**

1. **Switch to light theme:**
   ```
   - File → Settings → Appearance → Theme: Light
   ```

2. **Adjust monitor brightness:**
   ```
   - Increase monitor brightness/contrast
   - Use Windows Night Light feature for eye comfort
   ```

3. **Use system theme:**
   ```
   - File → Settings → Appearance → Theme: System
   - Follows your Windows 11 dark/light mode setting
   ```

---

## Notification Issues

### Symptom: Toast notifications not appearing

**Possible Causes:**
- Windows Focus Assist enabled
- Notifications disabled in settings
- winotify module issue

**Solutions:**

1. **Check Focus Assist:**
   ```
   - Open Windows Settings
   - System → Focus Assist
   - Set to "Off" or "Priority only"
   - Add OneTaskAtATime to priority list
   ```

2. **Check notification settings:**
   ```
   - Windows Settings → System → Notifications
   - Find "OneTaskAtATime" in app list
   - Ensure notifications are enabled
   - Enable sound/banners as desired
   ```

3. **Check application settings:**
   ```
   - File → Settings → Notifications
   - Ensure "Enable notifications" is checked
   - Adjust resurfacing intervals if needed
   ```

4. **Test notification manually:**
   ```
   - Create a deferred task with start date = tomorrow
   - Change start date to today
   - You should receive notification within 60 seconds
   - If not, check Windows Event Viewer for errors
   ```

---

### Symptom: Notifications work but no sound

**Solution:**
```
- Windows Settings → System → Notifications
- Click "OneTaskAtATime"
- Enable "Play a sound when a notification arrives"
```

---

## Task Comparison Problems

### Symptom: Comparison dialog appears repeatedly for same tasks

**Cause:** Tasks have identical importance (priority × urgency), triggering comparison loop.

**Solutions:**

1. **Skip uncertain comparisons:**
   ```
   - Click "Skip" button if you can't decide
   - The app will use current Elo ratings
   - Complete some tasks to break ties
   ```

2. **Manually adjust priorities:**
   ```
   - Change base priority of one task (High → Medium)
   - This breaks the tie
   - Resets Elo rating but resolves loop
   ```

3. **Set different due dates:**
   ```
   - Give tasks different due dates
   - This differentiates urgency scores
   - Breaks importance tie
   ```

4. **Use Sequential Ranking:**
   ```
   - Tools → Sequential Ranking
   - Drag tasks into desired order
   - Bypasses pairwise comparison
   ```

---

### Symptom: Elo ratings seem wrong, low-priority task ranked higher

**Explanation:**
Elo ratings work WITHIN priority tiers only. A Low-priority task with Elo 2000 will still rank below a High-priority task with Elo 1000.

**What to check:**
```
- Task List → Sort by Importance column
- Verify High priority tasks are above Medium
- Verify Medium priority tasks are above Low
- If this is not true, there's a bug (report it)
```

**If intentional ranking seems wrong:**
```
- Edit task → Change base priority
- This resets Elo to 1500
- Re-compare tasks to rebuild accurate ranking
```

---

## Import/Export Failures

### Error: "Import failed - Invalid JSON"

**Cause:** Exported file is corrupted or manually edited incorrectly.

**Solutions:**

1. **Validate JSON syntax:**
   ```
   - Open export file in text editor
   - Check for missing brackets, commas
   - Use online JSON validator
   ```

2. **Re-export from source:**
   ```
   - If possible, re-export from original application
   - Ensure export completed successfully
   - Don't interrupt export process
   ```

---

### Error: "Import failed - Schema mismatch"

**Cause:** Attempting to import data from incompatible version.

**Solution:**
```
- Only import files exported from OneTaskAtATime v1.0.0
- Exports from beta versions may not be compatible
- Check file header for version number
```

---

### Symptom: Export succeeds but file is empty or very small

**Cause:** No tasks match export filters.

**Solutions:**

1. **Check export filters:**
   ```
   - File → Export Data
   - Ensure "Include all states" is checked
   - Adjust date range filter
   - Try again
   ```

2. **Verify tasks exist:**
   ```
   - Go to Task List
   - Check task count in status bar
   - If 0 tasks, database is empty (nothing to export)
   ```

---

## Keyboard Shortcuts Not Working

### Symptom: Pressing Ctrl+N doesn't create new task

**Possible Causes:**
- Focus is on a text field
- Conflicting global hotkey
- Keyboard language/layout issue

**Solutions:**

1. **Click outside text fields:**
   ```
   - Shortcuts don't work when typing in text box
   - Click on task list or empty area first
   - Then press Ctrl+N
   ```

2. **Check for global hotkey conflicts:**
   ```
   - Some apps (e.g., NVIDIA overlay) use Ctrl+N
   - Close conflicting applications
   - Or remap conflicting hotkeys
   ```

3. **Use menu alternative:**
   ```
   - File → New Task (always works)
   - Or click toolbar button
   ```

4. **Check keyboard layout:**
   ```
   - Switch to US English keyboard layout
   - Some layouts remap Ctrl combinations
   ```

---

### Symptom: Alt+F doesn't switch to Focus Mode

**Solution:**
```
- Alt shortcuts may conflict with menu access keys
- Use mouse to click "Focus Mode" tab instead
- Or remap shortcuts in Settings (if feature available)
```

---

## Data Recovery

### Scenario: Accidentally deleted important task

**Solution:**
```
1. Go to Task List
2. Change filter to "Show: Trash"
3. Find deleted task
4. Right-click → Restore to Active
5. Task is recovered with all data intact
```

**Note:** Trash is never automatically emptied. Tasks stay there forever unless explicitly purged.

---

### Scenario: Database corrupted, application won't start

**Solution:**

1. **Attempt database repair:**
   ```
   - Download SQLite command-line tool
   - Open Command Prompt in %APPDATA%\OneTaskAtATime
   - Run: sqlite3 onetaskattime.db ".recover" > recovered.sql
   - Run: sqlite3 new.db < recovered.sql
   - Rename onetaskattime.db to onetaskattime_corrupt.db
   - Rename new.db to onetaskattime.db
   - Launch application
   ```

2. **Restore from backup:**
   ```
   - If you exported data recently, use File → Import
   - If Windows backup enabled, restore from shadow copy
   - If no backup, data may be lost
   ```

---

### Scenario: Lost all data after Windows reinstall

**Prevention:**
```
Database is in %APPDATA%\OneTaskAtATime, which is user-profile-specific.
If you created a new Windows user profile, data is in old profile.

To recover:
1. Navigate to C:\Users\OldProfileName\AppData\Roaming\OneTaskAtATime
2. Copy onetaskattime.db
3. Paste to C:\Users\NewProfileName\AppData\Roaming\OneTaskAtATime
4. Launch application
```

---

## Reporting Bugs

If you encounter an issue not listed here, please report it!

### Before Reporting

1. Check KNOWN_ISSUES.md for documented limitations
2. Search existing GitHub Issues
3. Try reproducing on fresh database (create test task)
4. Note exact steps to reproduce

### Information to Include

- **Windows version:** (e.g., Windows 11 Pro 22H2)
- **OneTaskAtATime version:** (Help → About)
- **Installation method:** (Installer, Portable, From Source)
- **Error message:** (exact text, screenshot if possible)
- **Steps to reproduce:**
  1. Do this...
  2. Click that...
  3. Error appears
- **Expected behavior:** What should happen instead
- **Actual behavior:** What actually happened
- **Database size:** Approximate number of tasks
- **Recent actions:** What were you doing before error occurred

### Where to Report

**GitHub Issues:** https://github.com/cdavis/OneTaskAtATime/issues

**Include:**
- Clear title (e.g., "Database locked error on Windows 10")
- All information listed above
- Log file if available (%APPDATA%\OneTaskAtATime\logs)

**Response Time:**
- Critical bugs (data loss, crashes): Within 48 hours
- Major bugs (feature broken): Within 1 week
- Minor bugs (UI glitch): Within 2 weeks
- Feature requests: Considered for future releases

---

## Getting Additional Help

**Community Resources:**
- GitHub Discussions: https://github.com/cdavis/OneTaskAtATime/discussions
- User Guide: USER_GUIDE.md
- In-app help: Press F1

**Built-in Help:**
- Press F1 for searchable help dialog
- Press Ctrl+? for keyboard shortcuts reference
- Press Shift+F1 then click any UI element for context-specific help

**Last Resort:**
- If all else fails, export your data
- Uninstall completely
- Delete %APPDATA%\OneTaskAtATime
- Reinstall fresh
- Import data from export

This usually resolves persistent issues caused by corrupted settings or cache files.
