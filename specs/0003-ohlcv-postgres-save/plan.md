# Implementation Plan: Save OHLCV Data to PostgreSQL

**Branch**: `0003-ohlcv-postgres-save` | **Date**: 2025-11-14 | **Spec**: specs/0003-ohlcv-postgres-save/spec.md
**Input**: Feature specification from `/specs/0003-ohlcv-postgres-save/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement PostgreSQL database integration for storing OHLCV cryptocurrency data, replacing the current CSV-based storage approach. The solution will use a single partitioned table design with proper indexing, security measures, and performance optimizations to support high-throughput data ingestion and efficient querying.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

## Technical Context

**Language/Version**: Python 3.12 (based on current qlib environment)  
**Primary Dependencies**: psycopg2-binary, SQLAlchemy, pandas  
**Storage**: PostgreSQL 13+ with table partitioning  
**Testing**: pytest with test coverage reporting  
**Target Platform**: Linux server environment  
**Project Type**: Data processing library (single project)  
**Performance Goals**: 5000 records/second ingestion, <50ms query latency for 1M records  
**Constraints**: 99.9% uptime, zero data corruption  
**Scale/Scope**: Multiple cryptocurrency symbols, multiple timeframes, indefinite data retention

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- TDD Compliance: All new features must follow Red-Green-Refactor cycle with unit and integration tests.
- Test Coverage: Ensure project maintains >=70% overall test coverage.
- Spec-Driven Development: Feature must align with SDD principles for quality and completeness.

**Status**: ✅ PASS - Feature follows SDD with complete specification, will implement TDD approach, and maintain test coverage requirements.

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
scripts/
├── postgres_storage.py          # NEW: PostgreSQL storage implementation
├── postgres_config.py           # NEW: Database configuration management
└── okx_data_collector.py        # MODIFIED: Add PostgreSQL saving option

qlib/
├── data/
│   └── storage/
│       └── postgres.py          # NEW: PostgreSQL data provider for qlib
└── contrib/
    └── data/
        └── handler/
            └── postgres_alpha158.py  # NEW: PostgreSQL-compatible data handler

tests/
├── test_postgres_storage.py     # NEW: Unit tests for PostgreSQL storage
├── test_postgres_integration.py # NEW: Integration tests for database operations
└── test_data_quality.py         # MODIFIED: Add PostgreSQL data validation
```

**Structure Decision**: Single project structure with new PostgreSQL storage modules integrated into existing qlib architecture. Database-related code is isolated in dedicated modules while maintaining compatibility with existing CSV-based workflows.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |

## Phase 0: Research

*GATE: Must complete before Phase 1 design. Resolve all technical unknowns.*

### Technical Research Questions

1. **PostgreSQL Partitioning Strategy**
   - How to implement monthly partitioning for OHLCV data?
   - What are the performance implications of partitioning by symbol vs timestamp?
   - How to handle partition maintenance (creation, dropping old partitions)?

2. **Connection Pooling & Performance**
   - What connection pooling library works best with SQLAlchemy and PostgreSQL?
   - How to configure connection pooling for high-throughput ingestion?
   - What are the memory and performance trade-offs?

3. **Data Type Optimization**
   - What PostgreSQL data types provide optimal storage and query performance for crypto prices?
   - How to handle precision for different cryptocurrencies?
   - Should we use DECIMAL, NUMERIC, or floating point types?

4. **Index Strategy**
   - Which indexes are needed for common query patterns (time ranges, symbol filtering)?
   - How to balance index performance vs insertion speed?
   - Should we use partial indexes for frequently accessed data?

5. **Error Handling & Recovery**
   - How to handle duplicate key violations during bulk inserts?
   - What retry strategies for transient database errors?
   - How to implement circuit breaker pattern for database failures?

### Research Deliverables

- `research.md`: Document findings and decisions for each research question
- Performance benchmarks for different partitioning strategies
- Connection pooling configuration recommendations
- Data type precision analysis for crypto data

## Phase 1: Design

*GATE: Must complete before Phase 2 implementation.*

### Data Model

**Database Schema**

**Main OHLCV Table** (`ohlcv_data`):
```sql
CREATE TABLE ohlcv_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    interval VARCHAR(10) NOT NULL,  -- Time interval: '1m', '5m', '1h', '1d', etc.
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    open_price DECIMAL(20,8) NOT NULL,
    high_price DECIMAL(20,8) NOT NULL,
    low_price DECIMAL(20,8) NOT NULL,
    close_price DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    quote_volume DECIMAL(20,8),
    trade_count INTEGER,
    taker_buy_volume DECIMAL(20,8),
    taker_buy_quote_volume DECIMAL(20,8),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(symbol, interval, timestamp)
) PARTITION BY LIST (interval);

-- Example partitions for different intervals
CREATE TABLE ohlcv_data_1m PARTITION OF ohlcv_data
    FOR VALUES IN ('1m')
    PARTITION BY RANGE (timestamp);

CREATE TABLE ohlcv_data_1h PARTITION OF ohlcv_data
    FOR VALUES IN ('1h')
    PARTITION BY RANGE (timestamp);

CREATE TABLE ohlcv_data_1d PARTITION OF ohlcv_data
    FOR VALUES IN ('1d')
    PARTITION BY RANGE (timestamp);
```

**Partitioning Strategy**: Hybrid LIST(interval) + RANGE(timestamp) partitioning for optimal query performance across different time granularities.

**Indexes**:
- Primary key on `id`
- Unique constraint on `(symbol, interval, timestamp)`
- Composite index on `(symbol, interval, timestamp)` for time-series queries
- Interval-specific partial indexes for different retention periods
- Index on `(symbol, interval)` for metadata queries

**Data Types Decision**: DECIMAL(20,8) for prices to handle crypto precision, VARCHAR(10) for interval to support standard time frames, TIMESTAMP WITH TIME ZONE for timezone awareness.

### API Contracts

**PostgreSQL Storage Interface**:
```python
class PostgreSQLStorage:
    def __init__(self, connection_string: str, pool_config: dict = None)
    def save_ohlcv_data(self, data: pd.DataFrame, symbol: str, interval: str) -> bool
    def get_ohlcv_data(self, symbol: str, interval: str, start_date: datetime, end_date: datetime) -> pd.DataFrame
    def get_latest_timestamp(self, symbol: str, interval: str) -> datetime
    def bulk_insert(self, data: List[dict]) -> int
    def get_available_intervals(self, symbol: str) -> List[str]
    def health_check(self) -> bool
```

**Configuration Schema**:
```python
@dataclass
class PostgresConfig:
    host: str
    port: int = 5432
    database: str
    user: str
    password: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    # New: interval-specific settings
    supported_intervals: List[str] = field(default_factory=lambda: ['1m', '5m', '15m', '1h', '4h', '1d'])
    retention_days: Dict[str, int] = field(default_factory=lambda: {
        '1m': 365, '5m': 365, '15m': 730, '1h': 730, '4h': 1095, '1d': -1  # -1 = indefinite
    })
```

### Design Deliverables

- `data-model.md`: Complete entity definitions and relationships
- `contracts/`: API specifications and data contracts
- `quickstart.md`: Feature usage guide
- Architecture diagrams and sequence flows

## Phase 2: Implementation

*GATE: Must complete before Phase 3 testing.*

### Implementation Plan

1. **Database Setup & Migration**
   - Create database schema and initial partitions
   - Implement migration scripts for schema changes
   - Set up database user and permissions

2. **Core Storage Module**
   - Implement PostgreSQL connection management
   - Create OHLCV data insertion methods
   - Implement data retrieval with filtering

3. **Integration with Existing Code**
   - Modify `okx_data_collector.py` to support PostgreSQL output
   - Create qlib data provider for PostgreSQL
   - Update configuration management

4. **Error Handling & Resilience**
   - Implement retry logic for transient failures
   - Add circuit breaker for database unavailability
   - Create comprehensive error logging

### Code Quality Standards

- **Type Hints**: All public methods must have complete type annotations
- **Documentation**: Docstrings for all classes and public methods
- **Error Handling**: Custom exceptions for database-specific errors
- **Logging**: Structured logging with appropriate log levels
- **Performance**: Connection pooling and query optimization

## Phase 3: Testing & Validation

*GATE: Must complete before Phase 4 deployment.*

### Test Strategy

**Unit Tests** (`tests/test_postgres_storage.py`):
- Database connection management
- Data insertion and retrieval
- Error handling scenarios
- Configuration validation

**Integration Tests** (`tests/test_postgres_integration.py`):
- End-to-end data flow from collection to storage
- Bulk insertion performance
- Query performance validation
- Database failure recovery

**Data Quality Tests** (`tests/test_data_quality.py`):
- Data integrity validation
- Duplicate detection and handling
- Schema compliance checks
- Performance benchmarks

### Test Coverage Requirements

- **Unit Tests**: ≥80% coverage for new PostgreSQL modules
- **Integration Tests**: Full end-to-end coverage
- **Performance Tests**: Validate 5000 records/second ingestion target
- **Reliability Tests**: 99.9% uptime simulation

### Validation Deliverables

- Test execution reports with coverage metrics
- Performance benchmark results
- Data integrity validation reports
- Security audit results

## Phase 4: Deployment & Monitoring

*GATE: Must complete before feature completion.*

### Deployment Strategy

1. **Database Setup**
   - Create production database instance
   - Run schema migrations
   - Configure connection pooling

2. **Application Deployment**
   - Deploy PostgreSQL storage modules
   - Update data collection scripts
   - Configure monitoring and alerting

3. **Data Migration**
   - Migrate existing CSV data to PostgreSQL
   - Validate data integrity post-migration
   - Update backup procedures

### Monitoring & Observability

**Metrics to Monitor**:
- Database connection pool utilization
- Query performance (P95 latency)
- Data ingestion rate
- Error rates and types
- Storage utilization

**Alerting Rules**:
- Database connection failures
- Ingestion rate below threshold
- Query latency degradation
- Storage capacity warnings

### Deployment Deliverables

- Deployment scripts and runbooks
- Monitoring dashboard configuration
- Backup and recovery procedures
- Rollback plans

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| PostgreSQL connection pool exhaustion | Medium | High | Implement proper connection pooling with monitoring |
| Data corruption during bulk inserts | Low | Critical | Add transaction management and data validation |
| Performance degradation with large datasets | Medium | High | Implement partitioning and query optimization |
| Schema migration failures | Low | Medium | Create rollback procedures and test migrations |

### Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Database downtime | Low | High | Implement multi-zone deployment and failover |
| Data loss during migration | Low | Critical | Comprehensive backups and validation |
| Security vulnerabilities | Medium | High | Regular security audits and updates |

## Success Metrics

### Performance Targets
- ✅ Data ingestion: ≥5000 records/second sustained across all intervals
- ✅ Query latency: <50ms for 1M records (varies by interval: 1m data faster than 1d)
- ✅ Uptime: ≥99.9% with interval-specific monitoring
- ✅ Data accuracy: 100% (no corruption, proper interval alignment)
- ✅ Multi-interval support: Seamless handling of 1m, 5m, 15m, 1h, 4h, 1d intervals

### Quality Targets
- ✅ Test coverage: ≥70% overall, ≥80% for new code
- ✅ Code quality: Passes all linting and security checks
- ✅ Documentation: Complete API docs and user guides

### Business Value
- ✅ Multi-interval support: Handle all OHLCV timeframes from 1-minute to daily
- ✅ Scalability: Support indefinite data growth with interval-aware partitioning
- ✅ Performance: Optimized queries for different trading strategies (scalping to swing)
- ✅ Reliability: Zero data loss with interval-specific validation
- ✅ Maintainability: Clear separation of concerns with interval-aware architecture
- ✅ Compatibility: Seamless integration with existing workflows across all timeframes
