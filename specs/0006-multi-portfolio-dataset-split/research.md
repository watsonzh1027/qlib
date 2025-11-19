# Research Findings: Multi-Portfolio Dataset Split

**Date**: November 19, 2025
**Feature**: 0006-multi-portfolio-dataset-split

## Decision: Proportion-Based Dataset Segmentation in Qlib

**Chosen Approach**: Extend Qlib's DatasetH class to support proportion-based segment configuration while maintaining backward compatibility with date-based segments.

**Rationale**:
- Qlib's DatasetH already supports flexible segment definitions via the `segments` parameter
- Proportion calculation can be done at initialization time using pandas date_range operations
- Maintains compatibility with existing workflows that use date ranges

**Alternatives Considered**:
- Custom Dataset subclass: Rejected due to unnecessary complexity and maintenance overhead
- Preprocessing script: Rejected because it separates data logic from dataset definition
- Configuration-only approach: Rejected as it requires runtime proportion calculation in multiple places

## Decision: Data Volume Validation Implementation

**Chosen Approach**: Add validation in the dataset initialization phase with configurable thresholds in workflow.json.

**Rationale**:
- Early validation prevents wasted computation on insufficient data
- Configurable thresholds allow flexibility for different use cases
- Integration with existing logging and error handling patterns

**Alternatives Considered**:
- Validation in training script only: Rejected because dataset creation happens earlier
- Database-level constraints: Rejected due to varying requirements across experiments
- Post-hoc validation: Rejected as it wastes compute resources

## Decision: Error Handling Strategy

**Chosen Approach**: Use Python exceptions for hard failures (< minimum_samples) and logging warnings for soft failures (< warning_samples).

**Rationale**:
- Exceptions provide clear failure signals for automation
- Warnings allow manual override for edge cases
- Consistent with Python and Qlib error handling patterns

**Alternatives Considered**:
- Return codes: Rejected due to complexity in async workflows
- Silent degradation: Rejected as it hides data quality issues
- Configuration-driven behavior: Rejected due to unnecessary complexity

## Decision: Configuration Structure

**Chosen Approach**: Add `dataset_validation` object under the `dataset` section in workflow.json.

**Rationale**:
- Keeps validation config close to dataset config
- Follows existing nested configuration patterns
- Easy to extend with additional validation rules

**Alternatives Considered**:
- Top-level config section: Rejected due to conceptual separation
- Inline with segments: Rejected as it clutters the segments definition
- Environment variables: Rejected due to need for per-experiment configuration

## Technical Implementation Notes

### Qlib DatasetH Extension
- The `segments` parameter accepts both date ranges and proportion specifications
- Proportion format: `{"train": 7, "valid": 2, "test": 1}` (integers summing to total ratio)
- Automatic conversion to date ranges based on available data per symbol

### Data Volume Calculation
- Count total training samples across all configured instruments
- Use pandas operations for efficient counting
- Cache results to avoid repeated calculations

### Integration Points
- Modify `scripts/convert_to_qlib.py` for proportion calculation during data conversion
- Update `scripts/workflow_crypto.py` to include validation calls
- Extend `qlib/data/dataset.py` if needed for proportion support

### Testing Strategy
- Unit tests for proportion calculation logic
- Integration tests for end-to-end validation
- Edge case tests for insufficient data scenarios