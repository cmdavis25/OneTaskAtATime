"""
Quick test runner for dialog invocation tests.

This script activates the virtual environment and runs the dialog tests
to verify that the mocking infrastructure fixes work correctly.
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

print("Running dialog invocation tests...")
print("=" * 80)

# Run the specific test class
result = subprocess.run(
    [
        str(venv_python),
        "-m",
        "pytest",
        "tests/ui/test_main_window.py::TestDialogInvocations",
        "-v",
        "--tb=short"
    ],
    cwd=str(project_root),
    capture_output=False
)

sys.exit(result.returncode)
