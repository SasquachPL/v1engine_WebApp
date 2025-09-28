import pandas as pd
from strategy_base import Strategy

class BollingerRsiStrategy(Strategy):
    """
    A combined strategy using Bollinger Bands and the Relative Strength Index (RSI).
    - A buy signal is generated when the price crosses below the lower Bollinger
      Band, and the RSI indicates an oversold condition. The raw signal score is
      based on how deeply the RSI is in the oversold territory.
    - A sell signal is generated when the price crosses above the upper
      Bollinger Band, and the RSI indicates an overbought condition.
    """
    def __init__(self, data_handler, bband_period=20, bband_std_dev=2.0,
                 rsi_period=14, rsi_oversold_threshold=30, rsi_overbought_threshold=70):
        """
        Initializes the BollingerRsiStrategy.

        Args:
            data_handler (DataHandler): An instance of the DataHandler.
            bband_period (int): The period for Bollinger Bands calculation.
            bband_std_dev (float): The number of standard deviations for the bands.
            rsi_period (int): The period for RSI calculation.
            rsi_oversold_threshold (int): The RSI threshold for an oversold signal.
            rsi_overbought_threshold (int): The RSI threshold for an overbought signal.
        """
        super().__init__(data_handler)
        self.bb_period = bband_period
        self.bb_std_dev = bband_std_dev
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold_threshold
        self.rsi_overbought = rsi_overbought_threshold

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
        Generates signals for all tickers over the entire data period using
        Bollinger Bands and RSI.

        Returns:
            pd.DataFrame: A DataFrame with raw scores for all tickers and dates.
        """
        signals_df = pd.DataFrame()
        for ticker in self.tickers:
            hist_data = self.data_handler.data.get(ticker)
            if hist_data is None or len(hist_data) < self.bb_period:
                continue

            close = hist_data['close']
            
            # Calculate Bollinger Bands
            middle_band = close.rolling(window=self.bb_period).mean()
            std_dev = close.rolling(window=self.bb_period).std()
            upper_band = middle_band + (self.bb_std_dev * std_dev)
            lower_band = middle_band - (self.bb_std_dev * std_dev)

            # Calculate RSI
            rsi = self._calculate_rsi(close, self.rsi_period)

            # Generate signals
            signals = pd.Series(0.0, index=hist_data.index, name=ticker)
            
            # --- MODIFICATION START ---
            # Buy signal: A crossover event where price moves below the lower band AND RSI is oversold.
            buy_mask = ((close < lower_band) & (close.shift(1) >= lower_band.shift(1)) &
                        (rsi < self.rsi_oversold))
            
            # The raw signal score is how far the RSI is into oversold territory.
            # A lower RSI gives a higher score.
            signals[buy_mask] = self.rsi_oversold - rsi[buy_mask]
            
            # Sell signal: A crossover event where price moves above the upper band AND RSI is overbought.
            sell_mask = ((close > upper_band) & (close.shift(1) <= upper_band.shift(1)) &
                         (rsi > self.rsi_overbought))
            signals[sell_mask] = -1.0
            # --- MODIFICATION END ---

            signals_df = pd.concat([signals_df, signals], axis=1)

        return signals_df.fillna(0)