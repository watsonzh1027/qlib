import json
from datetime import datetime, timedelta
import os
import re

class ConfigManager:
    def __init__(self, config_path="config/workflow.json"):
        self.config_path = config_path
        self.config = self._load_config()

    def _convert_ccxt_freq_to_qlib(self, ccxt_freq):
        """
        Convert CCXT frequency format to qlib frequency format.

        CCXT format: 15m, 1h, 1d, etc.
        Qlib format: 15min, 1hour, 1day, etc.
        """
        # Map CCXT time units to qlib time units
        unit_map = {
            'm': 'min',
            'h': 'hour',
            'd': 'day',
            'w': 'week',
            'M': 'month'
        }

        # Use regex to parse CCXT format (e.g., "15m" -> "15min")
        match = re.match(r'^(\d+)([mhdwM])$', ccxt_freq)
        if match:
            number, unit = match.groups()
            qlib_unit = unit_map.get(unit, unit)
            return f"{number}{qlib_unit}"

        # If no match, return as-is (might already be in qlib format)
        return ccxt_freq

    def _load_config(self):
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

    def get(self, section, key, default=None):
        return self.config.get(section, {}).get(key, default)

    def get_with_defaults(self, section, key, default=None):
        value = self.get(section, key, default)
        if key == "start_time" and value is None:
            return (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        elif key == "end_time" and value is None:
            return datetime.now().strftime("%Y-%m-%d")
        elif key == "limit" and value is None:
            return 1000
        return value

    def get_workflow_config(self):
        """
        Get workflow-specific configuration parameters.

        Returns:
            dict: Workflow configuration with defaults
        """
        return {
            "start_time": self.get_with_defaults("workflow", "start_time", "2021-01-01"),
            "end_time": self.get_with_defaults("workflow", "end_time", "2024-01-01"),
            "frequency": self.get("workflow", "frequency", "15m"),
            "instruments_limit": self.get("workflow", "instruments_limit", 50)
        }

    def get_model_config(self):
        """
        Get model configuration parameters.

        Returns:
            dict: Model configuration
        """
        return {
            "type": self.get("model", "type", "GBDT"),
            "learning_rate": self.get("model", "learning_rate", 0.1),
            "num_boost_round": self.get("model", "num_boost_round", 100)
        }

    def get_model_config_full(self):
        """
        Get complete model configuration for qlib model initialization.

        Returns:
            dict: Full model configuration including class, module_path, and kwargs
        """
        return self.config.get("model_config_full", {})

    def get_data_handler_config(self):
        """
        Get data handler configuration with resolved placeholders.

        Returns:
            dict: Data handler configuration with resolved template values
        """
        config = self.config.get("data_handler_config", {}).copy()

        # Resolve template placeholders
        def resolve_placeholders(obj):
            if isinstance(obj, str):
                if obj == "<workflow.start_time>":
                    return self.get_workflow_config()["start_time"]
                elif obj == "<workflow.end_time>":
                    return self.get_workflow_config()["end_time"]
                elif obj == "<workflow.frequency>":
                    freq = self.get_workflow_config()["frequency"]
                    return self._convert_ccxt_freq_to_qlib(freq)
                elif obj == "<data.symbols>":
                    # Convert CCXT symbols to qlib format for qlib compatibility
                    ccxt_symbols = self.get_crypto_symbols()
                    return [symbol.replace('/', '') for symbol in ccxt_symbols]
                else:
                    return obj
            elif isinstance(obj, dict):
                return {k: resolve_placeholders(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [resolve_placeholders(item) for item in obj]
            else:
                return obj

        return resolve_placeholders(config)

    def get_crypto_symbols(self):
        """
        Load crypto symbols from the configured symbols file.

        Returns:
            list: List of crypto symbols
        """
        symbols_file = self.config.get("data", {}).get("symbols", "config/top50_symbols.json")

        # If symbols_file is relative, make it relative to project root
        if not os.path.isabs(symbols_file):
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            symbols_file = os.path.join(project_root, symbols_file)

        try:
            with open(symbols_file, "r") as f:
                data = json.load(f)
                return data.get("symbols", [])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load symbols from {symbols_file}: {e}")
            return []

    def get_dataset_config(self):
        """
        Get dataset configuration with resolved placeholders.

        Returns:
            dict: Dataset configuration with resolved template values
        """
        config = self.config.get("dataset", {}).copy()

        # Resolve template placeholders
        def resolve_placeholders(obj):
            if isinstance(obj, str):
                if obj == "<data_handler_config>":
                    return self.get_data_handler_config()
                elif obj == "<workflow.start_time>":
                    return self.get_workflow_config()["start_time"]
                elif obj == "<workflow.end_time>":
                    return self.get_workflow_config()["end_time"]
                elif obj == "<workflow.frequency>":
                    freq = self.get_workflow_config()["frequency"]
                    return self._convert_ccxt_freq_to_qlib(freq)
                elif obj == "<data.symbols>":
                    # Convert CCXT symbols to qlib format for qlib compatibility
                    ccxt_symbols = self.get_crypto_symbols()
                    return [symbol.replace('/', '') for symbol in ccxt_symbols]
                else:
                    return obj
            elif isinstance(obj, dict):
                return {k: resolve_placeholders(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [resolve_placeholders(item) for item in obj]
            else:
                return obj

        return resolve_placeholders(config)

    def get_trading_config(self):
        """
        Get trading configuration parameters.

        Returns:
            dict: Trading configuration
        """
        return self.config.get("trading", {})

    def get_backtest_config(self):
        """
        Get backtest configuration parameters.

        Returns:
            dict: Backtest configuration
        """
        return self.config.get("backtest", {})

    def get_port_analysis_config(self):
        """
        Get port analysis configuration with resolved placeholders.

        Returns:
            dict: Port analysis configuration with resolved template values
        """
        config = self.config.get("port_analysis", {}).copy()

        # Resolve template placeholders
        def resolve_placeholders(obj):
            if isinstance(obj, str):
                if obj == "<trading.strategy_topk>":
                    return self.get_trading_config().get("strategy_topk", 50)
                elif obj == "<trading.strategy_n_drop>":
                    return self.get_trading_config().get("strategy_n_drop", 5)
                elif obj == "<backtest.start_time>":
                    return self.get_backtest_config().get("start_time", self.get_workflow_config()["start_time"])
                elif obj == "<backtest.end_time>":
                    return self.get_backtest_config().get("end_time", self.get_workflow_config()["end_time"])
                elif obj == "<backtest.account>":
                    return self.get_backtest_config().get("account", 1000000)
                elif obj == "<backtest.exchange_kwargs>":
                    return self.get_backtest_config().get("exchange_kwargs", {})
                elif obj == "<trading.open_cost>":
                    return self.get_trading_config().get("open_cost", 0.001)
                elif obj == "<trading.close_cost>":
                    return self.get_trading_config().get("close_cost", 0.001)
                elif obj == "<trading.min_cost>":
                    return self.get_trading_config().get("min_cost", 0.001)
                else:
                    return obj
            elif isinstance(obj, dict):
                return {k: resolve_placeholders(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [resolve_placeholders(item) for item in obj]
            else:
                return obj

        return resolve_placeholders(config)

    def load_config(self):
        """
        Public method to reload and return the configuration.

        Returns:
            dict: The loaded configuration.
        """
        self.config = self._load_config()
        return self.config

# Example usage
if __name__ == "__main__":
    config_manager = ConfigManager()
    start_time = config_manager.get_with_defaults("data_collection", "start_time")
    end_time = config_manager.get_with_defaults("data_collection", "end_time")
    limit = config_manager.get_with_defaults("data_collection", "limit")

    print(f"Start Time: {start_time}")
    print(f"End Time: {end_time}")
    print(f"Limit: {limit}")