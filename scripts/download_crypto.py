#  Copyright (c) Microsoft Corporation.
#  Licensed under the MIT License.

import fire
from data_collector.crypto.collector import CryptoCollector, Run


if __name__ == "__main__":
    fire.Fire(Run)
