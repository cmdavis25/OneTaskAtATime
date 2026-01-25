"""
Full UI test suite runner.

This script activates the virtual environment and runs all UI tests
to verify test pass rate and ensure no dialogs appear on screen.
"""

import subprocess
import sys
from pathlib import Path

# Get project root
project_root = Path(__file__).parent

# Activate virtual environment and run tests
venv_python = project_root / "onetask_env" / "Scripts" / "python.exe"

if not venv_python.exists():
    print(f"ERROR: Virtual environment not found at {venv_python}")
    sys.exit(1)

print("Running full UI test suite...")
print("=" * 80)
print("IMPORTANT: Watch for any dialogs appearing on screen.")
print("If dialogs appear, the mocking fix did not work.")
print("=" * 80)
print()

# Run all UI tests
result = subprocess.run(
    [
        str(venv_python),
        "-m",
        "pytest",
        "tests/ui/",
        "-v",
        "--tb=short"
    ],
    cwd=str(project_root),
    capture_output=False
)

sys.exit(result.returncode)
