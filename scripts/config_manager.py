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

# Example usage
if __name__ == "__main__":
    config_manager = ConfigManager()
    start_time = config_manager.get_with_defaults("data_collection", "start_time")
    end_time = config_manager.get_with_defaults("data_collection", "end_time")
    limit = config_manager.get_with_defaults("data_collection", "limit")

    print(f"Start Time: {start_time}")
    print(f"End Time: {end_time}")
    print(f"Limit: {limit}")