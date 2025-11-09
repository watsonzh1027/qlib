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
- **Remind users to activate qlib environment when suggesting terminal commands**

## Error Handling and Debugging
**Critical Rule: FOCUSED RESOLUTION**

When debugging or solving a task:
- **Maintain Focus (No Hallucinations/Drift):** DO NOT lose focus on the current primary problem/issue until it is fully resolved.
- **Workflow:**
  1. Identify the current problem or error.
  2. Implement the fix/solution.
  3. Provide code for testing.
  4. Update the **current** issue file with the steps taken.
  5. **WAIT for user confirmation that the problem is resolved.**
  6. ONLY proceed to the next distinct problem or task after explicit user permission.

### **Error Fixing Scope:**
- ✅ **ONE PRIMARY PROBLEM/ISSUE AT A TIME:** The core focus is on resolving **one specific logical problem or functional issue** (e.g., a bug in data loading, a logic error in an indicator).
- ✅ **BATCH SIMILAR ERRORS:** If the current problem involves **a series of identical or highly related errors** (e.g., missing header imports across five files, or a repetitive typo across a function set), these should be treated as **part of the single current problem** and fixed simultaneously to avoid repetitive modification tasks.
- ❌ NEVER attempt to fix multiple **unrelated** errors or distinct problems simultaneously.

> You MUST NOT start work on a new problem or create a new issue file without explicit user approval confirming the previous problem is solved.

## Issue Documentation
After a specific **problem or issue** is resolved:
- **Rule:** **ONLY ONE ISSUE FILE PER LOGICAL PROBLEM.** Subsequent debugging, refinement, or errors directly caused by the current problem **MUST** be recorded in the existing issue file.
- **Location:** Create an issue file in the `issues/` directory.

**Naming convention:** `<number>-<description>.md`
- Example: `0001-fix_chrono_header_issue.md`
- Number starts from 0001, sequential, no duplicates

**Required content:**
- issue status and create time, 
  e.g., `Status: OPEN|CLOSED`
        `Created: 2025-06-15 10:00:00`
- Detailed problem description (Initial entry).
- Complete final solution.
- **Crucial Update Log:** Document **ALL** steps taken during the resolution process. If a proposed fix fails or a new, related error emerges, **APPEND** the details of the attempt/new error/new fix to the existing issue file.
- **Preservation:** DO NOT cover or significantly modify previous successful or failed steps/descriptions, unless the initial problem description or a preceding judgment was fundamentally incorrect. **Focus on appending new historical progress.**
- Purpose: Future reference and learning, providing a complete debugging history.

## Code Suggestions
When suggesting code changes:
- Always consider the qlib environment context
- Verify compatibility with qlib framework
- Follow the focused resolution and error fixing scope principles

## Project Architecture

### Major Components
- **qlib**: Core library for data handling, modeling, and backtesting.
- **scripts**: Contains executable scripts for running experiments, data collection, and backtesting.
- **tests**: Includes unit tests, integration tests, and end-to-end tests to ensure code quality.
- **data**: Stores datasets used for backtesting and experiments.
- **docs**: Documentation for developers and users, including tutorials and FAQs.

### Data Flow
- Data is loaded using `DataHandler` classes, processed through `Processors`, and passed to models for training and prediction.
- Backtesting involves generating signals, applying strategies, and analyzing portfolio performance.

## Developer Workflows

### Running Tests
- Use the following command to run all tests:
  ```bash
  pytest tests/
  ```
- To check test coverage:
  ```bash
  pytest --cov=qlib tests/
  ```

### Debugging
- Use the `issues/` directory to document and track debugging progress.
- Follow the focused resolution principles outlined above.

 

## Examples
- Refer to `scripts/sample_backtest.py` for an example of running a backtest.
- Check `tests/` for examples of unit and integration tests.

