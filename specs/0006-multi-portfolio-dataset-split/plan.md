# Implementation Plan: Multi-Portfolio Dataset Split

**Branch**: `0006-multi-portfolio-dataset-split` | **Date**: November 19, 2025 | **Spec**: specs/0006-multi-portfolio-dataset-split/spec.md
**Input**: Feature specification from `/specs/0006-multi-portfolio-dataset-split/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement proportion-based dataset segmentation for multi-currency portfolios in Qlib, replacing fixed date ranges with configurable ratios (e.g., 7:2:1). Add data volume validation with configurable thresholds to ensure sufficient training samples.

## Technical Context

**Language/Version**: Python 3.x (existing project)  
**Primary Dependencies**: Qlib, pandas, numpy, PostgreSQL  
**Storage**: PostgreSQL database for OHLCV data  
**Testing**: pytest for unit and integration tests  
**Target Platform**: Linux server environment  
**Project Type**: Single Python project (quantitative trading library)  
**Performance Goals**: Dataset initialization < 30 seconds for typical portfolios  
**Constraints**: Handle time series data with varying symbol start dates, maintain backward compatibility  
**Scale/Scope**: Support 50+ crypto symbols with 1000+ data points per symbol

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- TDD Compliance: All new features must follow Red-Green-Refactor cycle with unit and integration tests.
- Test Coverage: Ensure project maintains >=70% overall test coverage.
- Spec-Driven Development: Feature must align with SDD principles for quality and completeness.

## Project Structure

### Documentation (this feature)

```text
specs/0006-multi-portfolio-dataset-split/
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
│   ├── dataset.py       # DatasetH class - modify for proportion support
│   └── ops.py           # Data operations
├── config.py            # Configuration handling
└── utils/

scripts/
├── convert_to_qlib.py   # Data conversion - modify for proportion calculation
└── workflow_crypto.py   # Training workflow - add data validation

config/
└── workflow.json        # Configuration - add dataset_validation section

tests/
├── test_dataset_split.py    # New tests for proportion splitting
├── test_data_validation.py  # New tests for data volume checks
└── integration/             # Integration tests
```

**Structure Decision**: Single Python project structure following existing Qlib conventions. Modifications to core dataset.py for proportion support, configuration updates, and new validation logic in workflow scripts.
