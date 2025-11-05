import qlib
from qlib.config import C
from qlib.workflow import R
from qlib.workflow.record_temp import SignalRecord, PortAnaRecord
from qlib.contrib.strategy.signal_strategy import TopkDropoutStrategy
from qlib.contrib.evaluate import risk_analysis
from qlib.data.dataset import DatasetH
from qlib.data.dataset.handler import DataHandlerLP
from qlib.model.base import Model
from qlib.data.dataset.loader import QlibDataLoader  # Import QlibDataLoader
from config_manager import ConfigManager

class SimpleModel(Model):
    """
    A simple model that generates signals based on the close price.
    """
    def fit(self, dataset: DatasetH):
        pass  # No training required for this simple model

    def predict(self, dataset: DatasetH):
        """
        Generate signals based on the close price.

        Args:
            dataset (DatasetH): The dataset to generate signals from.

        Returns:
            pd.Series: A series of signals.
        """
        data = dataset.prepare("test")
        data["signal"] = data[("feature", "close")].rank(pct=True)
        return data["signal"]

# Load configuration
config = ConfigManager("config/workflow.json").load_config()

def run_sample_backtest():
    """
    Run a sample backtest strategy using Qlib-compatible data.
    """
    data_dir = config.get("qlib_data_dir", "data/qlib_data")
    qlib.init(provider_uri=data_dir)

    # Instantiate the model
    model = SimpleModel()

    # Prepare the dataset
    handler_config = {
        "class": "DataHandlerLP",
        "module_path": "qlib.data.dataset.handler",
        "kwargs": {
            "start_time": "2024-01-01",
            "end_time": "2025-01-31",
            "instruments": "",
        },
    }
    # Define example fields and labels
    fields = ["$close", "$open", "$high", "$low", "$volume"]
    names = ["close", "open", "high", "low", "volume"]
    labels = ["$return"]
    label_names = ["return"]

    # Ensure the instruments are set to crypto-related symbols
    market = "crypto"

    # Initialize the DataHandlerLP instance with QlibDataLoader
    data_loader_config = {
        "feature": (fields, names),
        "label": (labels, label_names)
    }
    data_loader = QlibDataLoader(config=data_loader_config)

    data_handler = DataHandlerLP(data_loader=data_loader, **handler_config["kwargs"])

    dataset = DatasetH(
        handler=data_handler,
        segments={"train": ("2024-01-01", "2024-12-31"), "test": ("2025-01-01", "2025-01-31")},
    )

    # Generate signals using the model
    signal = model.predict(dataset)

    # Define the strategy
    strategy = TopkDropoutStrategy(
        signal=signal,  # Pass the generated signal
        topk=50,
        n_drop=5
    )

    # Start the experiment
    with R.start(experiment_name="sample_backtest") as recorder:
        # Record the signal
        signal_record = SignalRecord(model=model, dataset=dataset)
        signal_record.generate()

        # Perform portfolio analysis
        port_ana_record = PortAnaRecord(recorder)
        port_ana_record.generate()
        print("Backtest completed. Results saved in the Qlib experiment directory.")

# Update the entry point to use the centralized configuration
if __name__ == "__main__":
    run_sample_backtest()
