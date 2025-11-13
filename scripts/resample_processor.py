import pandas as pd

from qlib.data.dataset.processor import Processor
from qlib.utils.resam import resam_calendar


class ResampleProcessor(Processor):
    def __init__(self, target_freq: str, **kwargs):
        super().__init__()
        self.target_freq = target_freq

    def __call__(self, df: pd.DataFrame):
        # Ensure the index is a DatetimeIndex
        if isinstance(df.index, pd.MultiIndex):
            # For MultiIndex (datetime, instrument), get the datetime level
            if 'datetime' in df.index.names:
                datetime_idx = df.index.get_level_values('datetime')
            else:
                # Assume first level is datetime
                datetime_idx = df.index.get_level_values(0)

            # Convert to DatetimeIndex if not already
            if not isinstance(datetime_idx, pd.DatetimeIndex):
                datetime_idx = pd.to_datetime(datetime_idx)

            # Create new MultiIndex with proper datetime index
            new_index = pd.MultiIndex.from_arrays(
                [datetime_idx, df.index.get_level_values('instrument')],
                names=['datetime', 'instrument']
            )
            df = df.copy()
            df.index = new_index

            # Sort the MultiIndex to ensure lexsort
            df = df.sort_index(level=['datetime', 'instrument'])
        else:
            # Single index case
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)

        # Resample to target frequency using last value
        # For MultiIndex, we need to resample within each instrument group
        if isinstance(df.index, pd.MultiIndex):
            resampled_dfs = []
            for instrument in df.index.get_level_values('instrument').unique():
                instrument_df = df.xs(instrument, level='instrument')
                resampled_instrument = instrument_df.resample(self.target_freq, level='datetime').last()
                resampled_instrument['instrument'] = instrument
                resampled_instrument = resampled_instrument.reset_index().set_index(['datetime', 'instrument'])
                resampled_dfs.append(resampled_instrument)

            if resampled_dfs:
                resampled_df = pd.concat(resampled_dfs)
                # Ensure the final index is sorted
                resampled_df = resampled_df.sort_index(level=['datetime', 'instrument'])
            else:
                resampled_df = df
        else:
            resampled_df = df.resample(self.target_freq).last()

        return resampled_df

    def readonly(self) -> bool:
        return False