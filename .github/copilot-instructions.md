# GitHub Copilot Instructions for qlib-crypto

## TDD (Test-Driven Development)
- Write tests before implementing features
- Ensure all tests pass before committing code
- Follow the red-green-refactor cycle
- tests folder: /tests
  - Unit tests
  - Integration tests
  - End-to-end tests
- include coverage reports

## Environment Setup
- This project uses qlib environment
- Always run `conda activate qlib` before any operations
- Remind users to activate qlib environment when suggesting terminal commands

## Error Handling and Debugging
**Critical Rule: ONE ERROR AT A TIME**

When multiple errors occur during debugging:
- ✅ ONLY fix one error per iteration
- ❌ NEVER attempt to fix multiple unrelated errors simultaneously
- **Required workflow:**
  1. Identify and fix ONE error
  2. Provide code for testing
  3. WAIT for user confirmation
  4. ONLY proceed to next error after explicit user permission

> You MUST NOT solve the next error without explicit user approval.

## Issue Documentation
After each problem is resolved, create an issue file in `issues/` directory:

**Naming convention:** `<number>-<description>.md`
- Example: `0001-fix_chrono_header_issue.md`
- Number starts from 0001, sequential, no duplicates

**Required content:**
- Detailed problem description
- Complete solution
- **Important:** Document all successful steps taken during resolution
- Purpose: Future reference and learning

## Code Suggestions
When suggesting code changes:
- Always consider the qlib environment context
- Verify compatibility with qlib framework
- Follow the one-error-at-a-time principle
