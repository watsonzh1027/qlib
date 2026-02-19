Status: CLOSED
Created: 2026-02-18 22:00:00

Problem Description
- Hyperparameter tuning fails in model stage with: "can't find a freq from [] that can resample to 60min".
- Root cause: in scripts/train_sample_model.py, get_data_dir_for_freq appended the frequency suffix even when data.bin_data_dir already included it, producing non-existent paths like data/qlib_data/crypto_60min_60min.

Final Solution
- Make get_data_dir_for_freq idempotent by detecting an existing _{freq} suffix and normalizing trailing slashes.
- Add unit tests to cover suffix append, idempotent behavior, and trailing slash normalization.

Crucial Update Log
- 2026-02-18: Identified double-suffix provider_uri as the source of empty support_freq.
- 2026-02-18: Added tests in tests/test_train_sample_model.py for get_data_dir_for_freq.
- 2026-02-18: Updated get_data_dir_for_freq to avoid double-appending and normalize trailing slashes.
- 2026-02-18: Awaiting user confirmation by re-running tuning after tests.
- 2026-02-18: Tuning failed with Optuna dynamic categorical space because an existing study used different frequency choices.
- 2026-02-18: Updated model tuning study name to include allowed frequencies, isolating incompatible studies.
- 2026-02-18: Found base_config workflow frequency mutated across trials due to shallow copy, changing categorical choices order.
- 2026-02-18: Switched to deep copies and computed allowed_freqs once per study to stabilize Optuna choices.
- 2026-02-18: User confirmed model tuning completed successfully without Optuna errors.
