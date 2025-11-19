# Implementation Plan: Multi-Portfolio Dataset Split

**Branch**: `0006-multi-portfolio-dataset-split` | **Date**: November 19, 2025 | **Spec**: /specs/0006-multi-portfolio-dataset-split/spec.md
**Input**: Feature specification from `/specs/0006-multi-portfolio-dataset-split/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement proportion-based dataset splitting (7:2:1 ratios) for multi-currency crypto portfolios, replacing fixed date ranges with configurable proportions to handle varying symbol start dates. Add data volume validation with configurable thresholds (minimum 1000, warning 5000 samples). Technical approach involves modifying DatasetH class to support proportion integers in workflow.json segments, calculating date ranges from proportions in convert_to_qlib.py, integrating validation in workflow_crypto.py, and updating configuration files.

## Technical Context

**Language/Version**: Python 3.x  
**Primary Dependencies**: Qlib, pandas, numpy, PostgreSQL  
**Storage**: PostgreSQL for OHLCV crypto data  
**Testing**: pytest  
**Target Platform**: Linux  
**Project Type**: single (quantitative trading framework)  
**Performance Goals**: NEEDS CLARIFICATION (not specified in feature spec)  
**Constraints**: Fair handling of varying start dates across crypto symbols, maintain backward compatibility with date-based splits  
**Scale/Scope**: Multi-portfolio crypto trading with multiple symbols, proportion-based data segmentation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- TDD Compliance: All new features must follow Red-Green-Refactor cycle with unit and integration tests.
- Test Coverage: Ensure project maintains >=70% overall test coverage.
- Spec-Driven Development: Feature must align with SDD principles for quality and completeness.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
qlib/
├── data/
│   └── dataset.py          # Modify DatasetH class for proportion support
scripts/
├── convert_to_qlib.py      # Add proportion-based date calculation
└── workflow_crypto.py      # Add data volume validation
config/
└── workflow.json           # Update dataset.segments and add dataset_validation
tests/
├── unit/                   # Add unit tests for proportion splitting
├── integration/            # Add integration tests for validation
└── [existing test files]
```

**Structure Decision**: Existing qlib project structure with targeted modifications to data handling components, workflow scripts, and configuration files. No new major directories added; changes are backward-compatible extensions to existing classes and scripts.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
