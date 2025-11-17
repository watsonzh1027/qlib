# Output Format Configuration

## Overview
The data collector now supports configurable output formats through the `data_collection.output` parameter in `config/workflow.json`.

## Configuration Options

### In workflow.json
```json
{
  "data_collection": {
    "output": "csv",  // or "db"
    // ... other settings
  }
}
```

### Command Line Override
```bash
# Use CSV output (default)
python scripts/okx_data_collector.py

# Use database output
python scripts/okx_data_collector.py --output db

# Override config with CSV
python scripts/okx_data_collector.py --output csv
```

## Output Format Options

- **`"csv"`** (default): Save data to CSV files in the `data/klines` directory
- **`"db"`**: Save data to PostgreSQL database (requires database configuration)

## Priority Order
1. Command line `--output` parameter (highest priority)
2. `data_collection.output` in `workflow.json`
3. Default to `"csv"` if not specified

## Database Configuration
When using `"db"` output format, ensure the database section in `workflow.json` is properly configured:

```json
{
  "database": {
    "host": "localhost",
    "database": "qlib_crypto",
    "user": "crypto_user",
    "password": "change_me_in_production",
    "port": 5432
  }
}
```

Or use environment variables with `--db-env` flag.</content>
<parameter name="filePath">/home/watson/work/qlib-crypto/docs/output_format_config.md