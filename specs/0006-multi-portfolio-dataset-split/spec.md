# Feature Specification: Multi-Portfolio Dataset Split

**Feature Branch**: `0006-multi-portfolio-dataset-split`  
**Created**: November 19, 2025  
**Status**: Draft  
**Input**: User description: "对于多币种原始数据时间范围不同的问题（主要是开始时间不同），在划分训练数据集时，不能按固定的起止时间，而采用设定比例的方法，比如：7:2:1, or 6:2:2 , 由程序自动根据比例来进行数据分割，修改目前 workflow.json 中 dataset.segments 参数的设置方法： \"dataset\": { \"class\": \"DatasetH\", \"module_path\": \"qlib.data.dataset\", \"kwargs\": { \"handler\": \"<data_handler_config>\", \"segments\": { \"train\": [\"2024-01-01\", \"2024-06-01\"], ==> 7, \"valid\": [\"2024-06-01\", \"2024-09-01\"], ==> 2, \"test\": [\"2024-09-01\", \"2024-12-01\"] ==>1 } } },"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure Dataset Splits by Proportion (Priority: P1)

As a data scientist working with cryptocurrency trading data, I want to configure dataset segments using proportions (e.g., 7:2:1) instead of fixed dates, so that symbols with different historical data ranges (especially different start dates) are properly handled during training, validation, and testing splits.

**Why this priority**: This is the core functionality needed to handle multi-asset portfolios where different cryptocurrencies have varying data availability periods, ensuring fair and consistent data splits across all symbols.

**Independent Test**: Can be fully tested by configuring workflow.json with proportion-based segments, running the data conversion and workflow, and verifying that each symbol's data is split according to the specified proportions regardless of their individual date ranges.

**Acceptance Scenarios**:

1. **Given** a workflow.json with `"segments": {"train": 7, "valid": 2, "test": 1}`, **When** the dataset is initialized, **Then** each symbol's available data is automatically split into 70% for training, 20% for validation, and 10% for testing based on its own data range.
2. **Given** symbols with different start dates (e.g., BTC from 2018, AAVE from 2020), **When** using proportion-based splits, **Then** each symbol uses its full available data range for the proportional split, ensuring no symbol is disadvantaged by fixed date boundaries.
3. **Given** a symbol with insufficient data for the requested proportions, **When** the dataset is created, **Then** the system gracefully handles the split by using available data and logs appropriate warnings.

---

### Edge Cases

- What happens when a symbol has very little data that cannot be reasonably split into the requested proportions?
- How does the system handle symbols with data gaps or irregular intervals when calculating proportions?
- What happens if the proportion values don't add up to a reasonable total (e.g., 1:1:1 vs 7:2:1)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept proportion-based segment configuration in workflow.json dataset.segments, where values are integers representing relative proportions instead of date arrays.
- **FR-002**: System MUST automatically calculate split timestamps for each symbol based on its available data range and the specified proportions.
- **FR-003**: System MUST maintain backward compatibility with existing date-based segment configuration.
- **FR-004**: System MUST validate that proportion values are positive integers and provide meaningful error messages for invalid configurations.
- **FR-005**: System MUST handle symbols with insufficient data by using the maximum available data and logging warnings about reduced split quality.
- **FR-006**: System MUST check the total number of training samples across all symbols before starting model training.
- **FR-007**: If the total training samples are less than the configurable minimum threshold (default 1000), system MUST raise an error and terminate the training process.
- **FR-008**: If the total training samples are less than the configurable warning threshold (default 5000), system MUST log a warning message but allow training to continue.
- **FR-009**: The minimum and warning thresholds for training data volume MUST be configurable in workflow.json under the "dataset" section as "dataset_validation".

### Key Entities *(include if feature involves data)*

- **Dataset Configuration**: JSON configuration object containing segment definitions (either date-based or proportion-based)
- **Symbol Data Range**: Time range of available data for each cryptocurrency symbol
- **Split Points**: Calculated timestamps that divide each symbol's data into train/valid/test segments based on proportions
- **Dataset Validation Configuration**: Configuration object for data volume thresholds including minimum_samples (default 1000) and warning_samples (default 5000), located under the "dataset" section in workflow.json

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All configured symbols with sufficient data are successfully split according to specified proportions, with each segment containing the correct relative amount of data.
- **SC-002**: Training workflows complete without errors when using proportion-based splits for multi-asset portfolios with varying data ranges.
- **SC-003**: Data scientists can configure dataset splits in under 1 minute by changing workflow.json segments from date arrays to proportion integers.
- **SC-004**: System maintains 100% backward compatibility with existing date-based segment configurations.
- **SC-005**: System correctly validates training data volume, terminating with error when samples < minimum threshold and warning when samples < warning threshold.
