import pandas as pd
from strategy_base import Strategy

class bbXrsiV2Strategy(Strategy):
    """
    Implements a mean reversion strategy using Bollinger Bands and RSI.

    - A buy signal is generated when the price crosses below the lower Bollinger
      Band and the RSI is in the oversold region. The signal's strength is
      determined by how deeply the RSI is oversold.
    - A sell signal (exit) is generated when the price reverts to the mean by
      crossing back above the middle Bollinger Band.
    """
    def __init__(self, data_handler, bband_period=20, bband_std_dev=2.0,
                 rsi_period=14, rsi_oversold_threshold=30):
        """
        Initializes the MeanReversionBBRSIStrategy.

        Args:
            data_handler (DataHandler): An instance of the DataHandler.
            bband_period (int): The period for Bollinger Bands calculation.
            bband_std_dev (float): The number of standard deviations for the bands.
            rsi_period (int): The period for RSI calculation.
            rsi_oversold_threshold (int): The RSI threshold for an oversold signal.
        """
        super().__init__(data_handler)
        self.bb_period = bband_period
        self.bb_std_dev = bband_std_dev
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold_threshold

    def _calculate_rsi(self, prices, period):
        """Calculates the Relative Strength Index (RSI)."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def generate_signals(self):
        """
        Generates signals for all tickers based on the BB+RSI mean reversion logic.

        Returns:
            pd.DataFrame: A DataFrame with raw scores for all tickers and dates.
        """
        signals_df = pd.DataFrame()
        for ticker in self.tickers:
            hist_data = self.data_handler.data.get(ticker)
            if hist_data is None or len(hist_data) < self.bb_period:
                continue

            close = hist_data['close']

            # 1. Calculate Bollinger Bands
            middle_band = close.rolling(window=self.bb_period).mean()
            std_dev = close.rolling(window=self.bb_period).std()
            lower_band = middle_band - (self.bb_std_dev * std_dev)

            # 2. Calculate RSI
            rsi = self._calculate_rsi(close, self.rsi_period)

            # 3. Generate Signals
            signals = pd.Series(0.0, index=hist_data.index, name=ticker)

            # --- Buy Signal Condition ---
            # Price crosses below the lower Bollinger Band AND RSI is oversold.
            buy_mask = ((close < lower_band) & (close.shift(1) >= lower_band.shift(1)) &
                        (rsi < self.rsi_oversold))

            # The raw signal score is how far the RSI is into oversold territory.
            # A lower RSI gives a higher positive score.
            signals[buy_mask] = self.rsi_oversold - rsi[buy_mask]

            # --- Sell Signal (Exit) Condition ---
            # Price crosses above the middle band (mean).
            sell_mask = (close > middle_band) & (close.shift(1) <= middle_band.shift(1))
            signals[sell_mask] = -1.0

            signals_df = pd.concat([signals_df, signals], axis=1)

        return signals_df.fillna(0)