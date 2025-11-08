# Design: 0003-modify-convert-to-qlib

## Architectural Reasoning

The current `convert_to_qlib.py` is designed to convert CSV data to Parquet, but Qlib requires binary format (.bin files) for efficient loading and processing. The `dump_bin.py` script provides the correct implementation for converting structured data (OHLCV) to Qlib's binary format, including calendars, instruments, and features. However, for crypto trading data, calendars are not needed—only instruments and features are required.

### Key Design Decisions

1. **Reuse dump_bin Logic**: Instead of duplicating code, modify `convert_to_qlib.py` to instantiate and use `DumpDataAll` or a similar class from `dump_bin.py`, adapting it for crypto data specifics (15m intervals, timestamp fields). Skip calendar generation for crypto data.

2. **Dynamic Freq from Interval**: If the `freq` parameter matches the data's interval, use the value from the `interval` column of the OHLCV file to set `freq` dynamically (e.g., if interval is "15m", set freq="15m"). This ensures precise frequency representation in file names and formats.

3. **Configuration Integration**: Use `ConfigManager` to load paths from `workflow.json`, ensuring `bin_data_dir` points to `data/qlib_data/crypto`.

4. **Data Validation**: Retain or enhance data integrity checks (e.g., timestamp gaps) before conversion.

5. **Error Handling**: Incorporate logging and error handling from `dump_bin.py` to handle conversion failures gracefully.

### Trade-offs

- **Complexity**: Integrating `dump_bin` logic increases coupling but avoids code duplication.
- **Performance**: Binary conversion is more efficient for Qlib but requires careful handling of high-frequency data.
- **Flexibility**: Hardcode crypto-specific parameters (freq="high", date_field="timestamp") to simplify the module. Omit calendars to streamline for continuous trading data. Dynamic freq from interval adds adaptability but requires consistent interval values.

### Implementation Outline

- Load config from `workflow.json`.
- Scan `csv_data_dir` for CSV files.
- For each symbol, validate and prepare data; extract `interval` value to set `freq`.
- Use `DumpDataAll` with appropriate parameters to convert to bin format in `bin_data_dir`, skipping calendar creation.
- Update instruments registry accordingly.