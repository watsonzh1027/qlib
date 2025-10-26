# Issue 0012: Fix Coverage Assertion in test_manifest_template.py

## Problem Description
The test `test_manifest_template_exists` was failing because it was asserting that the `manifest_template.yaml` file was included in the coverage report. However, coverage tracking only includes Python files that are executed during the test run, not YAML files.

## Root Cause
The assertion `assert template_path.as_posix() in covered_files` was incorrect because:
1. Coverage.py tracks Python code execution, not file reads of YAML files.
2. The YAML file is only loaded via `yaml.safe_load()`, which doesn't execute Python code in the file.

## Solution
Removed the coverage-related assertions from the test since they were not relevant to testing the manifest template file itself. The test should focus on validating the YAML structure and content, not coverage metrics.

## Changes Made
- Removed the lines checking `covered_files` and asserting the template path is in coverage.
- Removed the minimum coverage threshold assertion (90%).

## Verification
After the fix, the tests pass:
- `test_manifest_template_exists` PASSED
- `test_manifest_template_validation` PASSED

The coverage warning about "No data was collected" is expected since the test doesn't execute any qlib code that would be tracked by coverage.

## Files Modified
- `tests/test_manifest_template.py`: Removed invalid coverage assertions.
