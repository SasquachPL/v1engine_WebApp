import pandas as pd
import numpy as np
from strategy_base import Strategy

class ZScoreStrategy(Strategy):
    """
    Implements a mean reversion strategy using a statistical Z-score.

    - A buy signal is generated when the price deviates significantly below its
      historical mean, indicated by a Z-score falling below a negative threshold.
      The signal's strength is proportional to the magnitude of this deviation.
    - A sell signal (exit) is generated when the Z-score crosses back above 0,
      indicating the price has reverted to its mean.
    """
    def __init__(self, data_handler, lookback_period=20, buy_threshold=-2.0, sell_threshold=0.0):
        """
        Initializes the ZScoreReversionStrategy.

        Args:
            data_handler (DataHandler): An instance of the DataHandler.
            lookback_period (int): The rolling window for calculating the mean and std dev.
            buy_threshold (float): The negative Z-score level to trigger a buy signal.
            sell_threshold (float): The Z-score level to trigger an exit (sell) signal.
        """
        super().__init__(data_handler)
        self.lookback_period = lookback_period
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def generate_signals(self):
        """
        Generates signals for all tickers based on the Z-score mean reversion logic.

        Returns:
            pd.DataFrame: A DataFrame with raw scores for all tickers and dates.
        """
        signals_df = pd.DataFrame()
        for ticker in self.tickers:
            hist_data = self.data_handler.data.get(ticker)
            if hist_data is None or len(hist_data) < self.lookback_period:
                continue

            close = hist_data['close']

            # 1. Calculate the moving average and standard deviation
            sma = close.rolling(window=self.lookback_period).mean()
            std_dev = close.rolling(window=self.lookback_period).std()

            # 2. Calculate the Z-Score
            # Replace infinities from potential division by zero with NaN, then fill
            z_score = (close - sma) / std_dev
            z_score.replace([np.inf, -np.inf], np.nan, inplace=True)
            z_score.fillna(0, inplace=True)

            # 3. Generate Signals
            signals = pd.Series(0.0, index=hist_data.index, name=ticker)

            # --- Buy Signal Condition ---
            # Z-score is below the buy threshold (e.g., -2.0)
            buy_mask = z_score < self.buy_threshold

            # The raw signal score is the negation of the Z-score.
            # This makes a more negative (oversold) Z-score a higher positive score.
            signals[buy_mask] = -z_score[buy_mask]

            # --- Sell Signal (Exit) Condition ---
            # Z-score crosses back above the sell threshold (e.g., 0.0)
            sell_mask = (z_score > self.sell_threshold) & (z_score.shift(1) <= self.sell_threshold)
            signals[sell_mask] = -1.0

            signals_df = pd.concat([signals_df, signals], axis=1)

        return signals_df.fillna(0)