# FILE: strategies/strategy_obv_roc.py

import pandas as pd
import numpy as np
from strategy_base import Strategy

class ObvRocStrategy(Strategy):
    """
    Implements a trading strategy using the Rate of Change (ROC) of the
    On-Balance Volume (OBV) indicator. This is a volume-based momentum strategy.

    - A buy signal is generated when the OBV's ROC over a specified period is
      positive, indicating increasing buying pressure.
    - The raw signal score is the ROC value itself. A higher ROC signifies
      stronger momentum and results in a higher ranking.
    - A sell signal is generated when the OBV's ROC is negative.
    """
    def __init__(self, data_handler, roc_period=10):
        """
        Initializes the ObvRocStrategy.

        Args:
            data_handler (DataHandler): An instance of the DataHandler.
            roc_period (int): The lookback period for calculating the
                              Rate of Change of the OBV.
        """
        super().__init__(data_handler)
        self.roc_period = roc_period

    def _calculate_obv(self, close, volume):
        """Calculates the On-Balance Volume."""
        # OBV is the cumulative sum of volume, signed by price change
        signed_volume = volume * np.sign(close.diff())
        return signed_volume.cumsum().fillna(0)

    def generate_signals(self):
        """
        Generates buy/sell signals for all tickers based on the OBV ROC logic.

        Returns:
            pd.DataFrame: A DataFrame with raw scores for all tickers and dates.
        """
        signals_df = pd.DataFrame()
        for ticker in self.tickers:
            hist_data = self.data_handler.data.get(ticker)
            if hist_data is None or len(hist_data) < self.roc_period:
                continue

            # 1. Calculate OBV
            obv = self._calculate_obv(hist_data['close'], hist_data['volume'])

            # 2. Calculate the Rate of Change of the OBV
            obv_roc = obv.pct_change(periods=self.roc_period)

            # 3. Initialize signals series
            signals = pd.Series(0.0, index=hist_data.index, name=ticker)

            # 4. Generate Buy Signal
            # Condition: OBV ROC is positive. The score is the ROC value.
            buy_mask = obv_roc > 0
            signals[buy_mask] = obv_roc[buy_mask]

            # 5. Generate Sell Signal
            # Condition: OBV ROC is negative.
            sell_mask = obv_roc < 0
            signals[sell_mask] = -1.0

            # 6. Append to the master DataFrame
            signals_df = pd.concat([signals_df, signals], axis=1)

        return signals_df.fillna(0)