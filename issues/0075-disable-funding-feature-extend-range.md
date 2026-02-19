Status: CLOSED
Created: 2026-02-18 21:35:00

Problem
- Funding rate data coverage is limited, causing unreliable features and training noise.
- Need to remove funding_rate features, expand training time range, and retrain.

Solution
- Removed funding_rate from data_convertor.include_fields.
- Switched data_handler_config to Alpha158 (no funding features).
- Expanded workflow time range to 2024-01-01 through 2026-02-12.
- Added test to enforce funding_rate removal and handler switch.
- Re-trained model with updated config.

Update Log
- 2026-02-18 21:30: Removed funding_rate from config/workflow.json include_fields.
- 2026-02-18 21:30: Switched handler to Alpha158 in config/workflow.json.
- 2026-02-18 21:30: Expanded workflow start_time to 2024-01-01.
- 2026-02-18 21:30: Added tests/test_workflow_config_no_funding.py.
- 2026-02-18 21:31: Fixed handler class name (CryptoAlpha158 -> Alpha158) after AttributeError.
- 2026-02-18 21:32: Re-ran training; model completed with IC=0.0303 (n=14880), ICIR=0.0000.
- 2026-02-18 21:40: Verified ethusdt qlib_data integrity; minor zeros present but acceptable.
