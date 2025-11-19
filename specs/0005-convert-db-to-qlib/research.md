# Technical Research: Convert Database to Qlib Format

**Feature**: specs/0005-convert-db-to-qlib
**Date**: 2025-11-17

## Database Connectivity Options

### PostgreSQL Adapters for Python

**Option 1: psycopg2 (Recommended)**
- Mature, high-performance PostgreSQL adapter
- Binary protocol support for better performance
- Connection pooling capabilities
- Widely used in production environments

**Option 2: psycopg2-binary**
- Pre-compiled version of psycopg2
- Easier installation (no C compiler needed)
- Same API as psycopg2

**Option 3: sqlalchemy**
- ORM with PostgreSQL support
- More abstraction but additional complexity
- Better for complex queries, overkill for simple data extraction

**Decision**: Use psycopg2-binary for simplicity and performance. The feature only needs basic SELECT queries for kline data extraction.

### Database Schema Analysis

**Existing Schema** (from project research):
- Table: `kline_data` or similar
- Columns: timestamp, symbol, interval, open, high, low, close, volume
- Indexes: timestamp, symbol for efficient querying

**Integration Approach**:
- Query by symbol and date range
- Support multiple intervals (1m, 15m, etc.)
- Handle large result sets with cursor-based fetching

## Qlib Data Format Requirements

**Binary Format Structure**:
- Directory structure: `data/{interval}/{symbol}/`
- File naming: `{symbol}.{interval}.bin`
- Data format: Custom Qlib binary format

**Existing Implementation**:
- `DumpDataCrypto` class handles conversion
- `validate_data_integrity()` ensures data quality
- Supports multiple symbols and intervals

**Extension Points**:
- Add database data source to existing conversion pipeline
- Maintain compatibility with CSV input
- Support data merging from multiple sources

## Data Processing Pipeline

### Current Flow (CSV):
1. Read CSV files
2. Validate data integrity
3. Convert to Qlib binary format
4. Save to directory structure

### Enhanced Flow (Database + CSV):
1. Determine data sources (database, CSV, or both)
2. Read data from selected sources
3. Merge and deduplicate data
4. Validate integrity
5. Convert to Qlib format
6. Save with progress tracking

## Performance Considerations

**Database Query Optimization**:
- Use indexed columns (timestamp, symbol)
- Implement pagination for large datasets
- Connection pooling to avoid overhead

**Memory Management**:
- Process data in batches
- Stream results for large queries
- Monitor memory usage during conversion

**Progress Tracking**:
- Report progress by symbol/interval
- Estimate completion time
- Handle interruptions gracefully

## Error Handling Strategy

**Connection Errors**:
- Retry with exponential backoff
- Log connection failures
- Preserve partial results

**Data Quality Issues**:
- Validate data during extraction
- Log warnings for missing data
- Skip invalid records with reporting

**File System Errors**:
- Check disk space before conversion
- Handle permission issues
- Atomic writes for data integrity

## Testing Strategy

**Unit Tests**:
- Database connection mocking
- Data extraction validation
- Error condition handling

**Integration Tests**:
- End-to-end conversion with test database
- Multi-source data merging
- Performance validation

**Data Validation**:
- Compare converted data with source
- Verify Qlib compatibility
- Check data integrity preservation

## Security Considerations

**Database Credentials**:
- Use environment variables or config files
- No hardcoded credentials
- Secure connection strings

**Data Access**:
- Read-only database access
- Minimal required permissions
- Audit logging for data access

## Deployment Considerations

**Environment Setup**:
- Add PostgreSQL dependencies to requirements
- Document database setup requirements
- Provide connection configuration examples

**Backward Compatibility**:
- Existing CSV functionality unchanged
- Default behavior maintains current interface
- New options are additive

## Implementation Approach

**Incremental Development**:
1. Add database connection class
2. Implement basic data extraction
3. Add source selection logic
4. Integrate with existing conversion pipeline
5. Add comprehensive error handling
6. Implement performance optimizations
7. Add detailed conversion reporting with statistics

**Code Organization**:
- Extend existing `convert_to_qlib.py`
- Add `PostgreSQLStorage` class
- Maintain clean separation of concerns
- Follow existing code patterns</content>
<parameter name="filePath">/home/watson/work/qlib-crypto/specs/0005-convert-db-to-qlib/research.md