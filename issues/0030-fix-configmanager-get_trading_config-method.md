# 0030-fix-configmanager-get_trading_config-method

Status: CLOSED
Created: 2025-11-08 12:00:00

## Problem Description
The `workflow_crypto.py` script was failing with an AttributeError when trying to call `config_manager.get_trading_config()`. The ConfigManager class did not have the `get_trading_config` method implemented, even though the config file contained a "trading" section.

Error details:
```
AttributeError: 'ConfigManager' object has no attribute 'get_trading_config'
```

This occurred at line 103 in `examples/workflow_crypto.py`:
```python
trading_config = config_manager.get_trading_config()
```

## Root Cause
The ConfigManager class was missing the `get_trading_config()` method, which is needed to retrieve the "trading" configuration section from `config/workflow.json`. Other similar methods like `get_workflow_config()`, `get_model_config()`, etc., existed, but `get_trading_config()` was omitted.

## Solution
Added the `get_trading_config()` method to the ConfigManager class in `scripts/config_manager.py`. The method follows the same pattern as other config getters:

```python
def get_trading_config(self):
    """
    Get trading configuration parameters.

    Returns:
        dict: Trading configuration
    """
    return self.config.get("trading", {})
```

This method returns the "trading" section from the config, which includes parameters like open_cost, close_cost, min_cost, strategy_topk, and strategy_n_drop.

## Update Log
- 2025-11-08: Identified the missing method in ConfigManager.
- 2025-11-08: Added `get_trading_config()` method to ConfigManager class.
- 2025-11-08: Verified the script no longer throws the AttributeError (though it may fail later due to environment setup issues unrelated to this fix).