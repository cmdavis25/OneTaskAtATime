"""
Extract test failures from pytest run.
"""
import subprocess
import sys
import re

# Run pytest with specific flags
result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-s", "--tb=short", "-v"],
    capture_output=True,
    text=True,
    timeout=300
)

# Combine stdout and stderr
output = result.stdout + result.stderr

# Extract summary line
summary_pattern = r'=+ (.+ passed.*) =+'
summary_match = re.search(summary_pattern, output)
if summary_match:
    print(f"\n{summary_match.group(1)}\n")

# Extract failed tests
failed_pattern = r'FAILED ([\w\/\._:]+) - (.*)'
failures = re.findall(failed_pattern, output)

print(f"Found {len(failures)} failures:\n")
for test_name, error_msg in failures:
    print(f"- {test_name}")
    print(f"  Error: {error_msg[:100]}")
    print()

# Write full output to file
with open("full_test_output.txt", "w") as f:
    f.write(output)
print("Full output written to full_test_output.txt")
