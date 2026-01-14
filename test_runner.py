"""Quick test runner to identify which tests complete vs hang."""
import subprocess
import sys

tests = [
    "test_task_lifecycle_someday_workflow",
    "test_comparison_ranking_workflow",
    "test_dependency_blocking_workflow",
    "test_export_import_workflow",
    "test_context_filtering_workflow",
    "test_undo_redo_complete_workflow",
]

for test_name in tests:
    print(f"\n{'='*60}")
    print(f"Testing: {test_name}")
    print('='*60)

    cmd = [
        sys.executable, "-m", "pytest",
        f"tests/e2e/test_core_workflows.py::TestCoreWorkflows::{test_name}",
        "-xvs", "--tb=short"
    ]

    try:
        result = subprocess.run(cmd, timeout=20, capture_output=True, text=True)

        if "PASSED" in result.stdout:
            print(f"[PASS] PASSED")
        elif "FAILED" in result.stdout:
            print(f"[FAIL] FAILED")
            # Print failure details
            lines = result.stdout.split('\n')
            for i, line in enumerate(lines):
                if 'AssertionError' in line or 'assert' in line:
                    print(f"  {line}")
                    if i+1 < len(lines):
                        print(f"  {lines[i+1]}")
        elif "SKIPPED" in result.stdout:
            print(f"[SKIP] SKIPPED")
        else:
            print(f"[UNKN] UNKNOWN")

    except subprocess.TimeoutExpired:
        print(f"[TIME] TIMEOUT - Test hung (likely dialog blocking)")
    except Exception as e:
        print(f"[ERROR] ERROR: {e}")

print(f"\n{'='*60}")
print("Test run complete")
print('='*60)
