# TODO: Fix train_lgb.py argument parser to match user command

- [x] Update argument parser in main() to use --features, --model-out, --report-out
- [x] Modify train_from_features function signature to accept model_out and report_out
- [x] Adjust saving logic in train_from_features to use provided file paths
- [x] Remove unused import write_parquet
- [ ] Test the script with the original command
