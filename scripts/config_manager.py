import json
from datetime import datetime, timedelta

class ConfigManager:
    def __init__(self, config_path="config/workflow.json"):
        self.config_path = config_path
        self.config = self._load_config()

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
            "frequency": self.get("workflow", "frequency", "15min"),
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

    def get_trading_config(self):
        """
        Get trading/backtesting configuration parameters.

        Returns:
            dict: Trading configuration
        """
        return {
            "open_cost": self.get("trading", "open_cost", 0.001),
            "close_cost": self.get("trading", "close_cost", 0.001),
            "min_cost": self.get("trading", "min_cost", 0.001),
            "strategy_topk": self.get("trading", "strategy_topk", 50),
            "strategy_n_drop": self.get("trading", "strategy_n_drop", 5)
        }

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