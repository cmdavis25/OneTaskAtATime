"""
Collect all test failures systematically.
"""
import subprocess
import sys

# Run pytest with machine-readable output
result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-s", "--tb=no", "-v", "--no-header", "-q"],
    capture_output=True,
    text=True,
    timeout=600
)

# Extract output
output = result.stdout + result.stderr

# Write to file
with open("test_results.txt", "w", encoding="utf-8") as f:
    f.write(output)

print("Test results written to test_results.txt")

# Extract and print failed tests
lines = output.split('\n')
failures = [line for line in lines if 'FAILED' in line]

print(f"\nFound {len(failures)} failures:")
for failure in failures:
    print(failure)
