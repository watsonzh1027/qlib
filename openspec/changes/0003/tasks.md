# Tasks: 0003-modify-convert-to-qlib

## Task List

1. **Review current convert_to_qlib.py**: Analyze existing code and identify incorrect Parquet conversion logic.
2. **Study dump_bin.py**: Understand DumpDataAll class and binary conversion process, noting that calendars are not needed for crypto data.
3. **Update imports**: Add necessary imports from dump_bin.py or refactor to use its classes.
4. **Implement dynamic freq**: If freq matches interval, extract interval value from OHLCV file's interval column and use it as freq (e.g., "15m").
5. **Modify data loading**: Change from Parquet output to binary conversion using DumpDataAll, skipping calendar generation.
6. **Integrate config**: Ensure bin_data_dir from workflow.json is used (data/qlib_data/crypto).
# Tasks: 0003-modify-convert-to-qlib

## Task List

- [x] Review current convert_to_qlib.py: Analyzed existing code and identified incorrect Parquet conversion logic.
- [x] Study dump_bin.py: Understood DumpDataAll class and binary conversion process, noting that calendars are not needed for crypto data.
- [x] Update imports: Added necessary imports from dump_bin.py or refactor to use its classes.
- [x] Implement dynamic freq: Extracted interval value from OHLCV file's interval column and used it as freq (e.g., "15m").
- [x] Modify data loading: Changed from Parquet output to binary conversion using DumpDataAll, skipping calendar generation.
- [x] Integrate config: Ensured bin_data_dir from workflow.json is used (data/qlib_data/crypto).
- [x] Handle crypto specifics: Set date_field_name="timestamp", exclude "interval,symbol". Used dynamic freq.
- [x] Update instruments generation: Adapted to binary format requirements without calendars.
- [x] Add validation: Retained validate_data_integrity for data integrity checks.
- [x] Test conversion: Ran on sample data and verified bin files in qlib_data/crypto (instruments and features only).
- [x] Update documentation: Updated module docstrings and comments to reflect binary conversion.
- [x] Validate with openspec: Ran `openspec validate 0003 --strict` and resolved issues.
- [x] Integration test: Verified converted data structure and Qlib compatibility.
8. **Update instruments generation**: Adapt to binary format requirements without calendars.
9. **Add validation**: Ensure data integrity before conversion.
10. **Test conversion**: Run on sample data and verify bin files in qlib_data/crypto (instruments and features only).
11. **Update documentation**: Reflect changes in module docstrings and comments.
12. **Validate with openspec**: Run `openspec validate 0003 --strict` and resolve issues.
13. **Integration test**: Ensure converted data works with Qlib backtesting.