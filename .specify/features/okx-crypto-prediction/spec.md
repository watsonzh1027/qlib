# OKX Crypto Trading Prediction System

## Overview

Implement a cryptocurrency trading prediction system that integrates with OKX exchange using Qlib framework. The system will collect contract K-line data, process it using Qlib's capabilities, generate predictions using LGBModel, and produce trading decisions based on analysis results.

## User Scenarios & Testing

### Primary User Flow
1. System connects to OKX exchange API
2. Retrieves contract K-line data for specified trading pairs
3. Processes data through Qlib pipeline
4. Generates predictions using LGBModel
5. Produces trading signals and decisions
6. Outputs analysis results and performance metrics

### Test Scenarios
1. Exchange Connection
   - Verify successful OKX API connection
   - Validate data retrieval for multiple timeframes
   - Confirm error handling for API issues

2. Data Processing
   - Verify K-line data normalization
   - Confirm feature generation
   - Validate data pipeline integrity

3. Model Prediction
   - Test model training process
   - Validate prediction accuracy
   - Verify signal generation logic

## Functional Requirements

1. Data Collection
   - Must connect to OKX exchange API securely
   - Must retrieve contract K-line data with configurable timeframes
   - Must handle API rate limits and connection errors gracefully

2. Data Processing
   - Must normalize raw K-line data using Qlib formats
   - Must support 15-minute minimum timeframe for K-line data
   - Must utilize Qlib's built-in feature processors for technical analysis
   - Must prepare features for model input
   - Must support processing for top 20 trading pairs by volume

3. Model Training & Prediction
   - Must implement LGBModel training pipeline using Qlib's feature set
   - Must generate predictions for future price movements
   - Must evaluate model performance metrics
   - Must scale predictions across top 20 trading pairs

4. Trading Decisions
   - Must generate clear trading signals
   - Must provide confidence scores for predictions
   - Must output analysis results in readable format

## Success Criteria

1. Data Quality
   - Successfully retrieves data for 95% of API calls
   - Processes K-line data with < 1% error rate
   - Maintains data consistency across pipeline stages

2. Model Performance
   - Achieves minimum 55% directional accuracy
   - Generates predictions within 1-second latency
   - Provides reliable confidence metrics

3. System Reliability
   - Maintains 99% uptime for data collection
   - Handles API errors without system crashes
   - Completes full prediction cycle within specified timeframe

## Assumptions

1. OKX API access is available and configured
2. Required trading pairs are supported by the exchange
3. Sufficient historical data is available for model training
4. System has adequate computational resources

## Dependencies

1. External:
   - OKX Exchange API access
   - Trading pair availability
   - Network connectivity

2. Internal:
   - Qlib framework installation with complete feature set
   - LGBModel implementation
   - Data processing pipeline optimized for 15-minute intervals
   - Volume tracking system for top 20 pairs selection

## Key Entities

1. Data Entities:
   - K-line data (OHLCV) at 15-minute intervals
   - Qlib-provided technical features
   - Volume rankings for pair selection
   - Model features
   - Predictions
   - Trading signals

2. System Components:
   - OKX API connector
   - Data processor
   - Model trainer
   - Signal generator
   - Analysis reporter

## Out of Scope

1. Actual trade execution
2. Risk management system
3. Portfolio optimization
4. Real-time market making
5. Multiple exchange support

## Implementation Notes

1. Trading Pairs:
   - System will automatically track and update top 20 pairs by volume
   - Volume calculations based on 24h rolling window
   - Pair list updates daily

2. Timeframe Implementation:
   - Primary timeframe: 15-minute intervals
   - Data aggregation available for longer timeframes
   - Historical data storage optimized for 15-minute granularity

3. Feature Engineering:
   - Utilizing Qlib's native feature processors
   - Alpha158 and Alpha360 feature sets as baseline
   - Custom feature processors must align with Qlib's architecture
