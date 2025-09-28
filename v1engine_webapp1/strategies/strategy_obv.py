# FILE: strategies/strategy_obv.py

import pandas as pd
import numpy as np
from strategy_base import Strategy

class ObvStrategy(Strategy):
    """
    Implements a trading strategy based on the On-Balance Volume (OBV) indicator
    crossing over its own moving average.

    - A buy signal is generated when the OBV line crosses above its Simple
      Moving Average (SMA), indicating positive volume momentum.
    - The raw signal score is a normalized value representing the strength of
      the crossover: (OBV - OBV_SMA) / OBV_StdDev.
    - A sell signal is generated when the OBV crosses below its SMA.
    """
    def __init__(self, data_handler, obv_sma_period=20):
        """
        Initializes the ObvStrategy.

        Args:
            data_handler (DataHandler): An instance of the DataHandler.
            obv_sma_period (int): The lookback period for the OBV's moving
                                  average and standard deviation.
        """
        super().__init__(data_handler)
        self.obv_sma_period = obv_sma_period

    def _calculate_obv(self, close, volume):
        """Calculates the On-Balance Volume."""
        # OBV is the cumulative sum of volume, signed by price change
        signed_volume = volume * np.sign(close.diff())
        return signed_volume.cumsum().fillna(0)

    def generate_signals(self):
        """
        Generates buy/sell signals for all tickers based on the OBV crossover logic.

        Returns:
            pd.DataFrame: A DataFrame with raw scores for all tickers and dates.
        """
        signals_df = pd.DataFrame()
        for ticker in self.tickers:
            hist_data = self.data_handler.data.get(ticker)
            if hist_data is None or len(hist_data) < self.obv_sma_period:
                continue

            # 1. Calculate OBV and its moving average/standard deviation
            obv = self._calculate_obv(hist_data['close'], hist_data['volume'])
            obv_sma = obv.rolling(window=self.obv_sma_period).mean()
            obv_stdev = obv.rolling(window=self.obv_sma_period).std()

            # 2. Initialize signals series
            signals = pd.Series(0.0, index=hist_data.index, name=ticker)

            # 3. Generate Buy Signal
            # Condition: OBV crosses above its SMA
            buy_mask = (obv > obv_sma) & (obv.shift(1) <= obv_sma.shift(1))

            # Avoid division by zero for the score calculation
            valid_stdev_mask = obv_stdev > 0
            final_buy_mask = buy_mask & valid_stdev_mask

            if final_buy_mask.any():
                # Score = Z-score of OBV relative to its moving average
                score = (obv[final_buy_mask] - obv_sma[final_buy_mask]) / obv_stdev[final_buy_mask]
                signals[final_buy_mask] = score

            # 4. Generate Sell Signal
            # Condition: OBV crosses below its SMA
            sell_mask = (obv < obv_sma) & (obv.shift(1) >= obv_sma.shift(1))
            signals[sell_mask] = -1.0

            # 5. Append to the master DataFrame
            signals_df = pd.concat([signals_df, signals], axis=1)

        return signals_df.fillna(0)