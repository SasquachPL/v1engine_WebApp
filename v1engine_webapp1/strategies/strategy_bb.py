import pandas as pd
from strategy_base import Strategy

class BollingerStrategy(Strategy):
    """
    Implements a Bollinger Bands (BB) trading strategy.
    A buy signal is generated when the price breaks above the upper BB.
    The strength of the buy signal is the Z-score of the closing price.
    A sell signal is generated when the price crosses below the middle band.
    """
    def __init__(self, data_handler, bband_period=20, bband_std_dev=2.0):
        """
        Initializes the BbStrategy.

        Args:
            data_handler (DataHandler): An instance of the DataHandler.
            period (int): The moving average period for the Bollinger Bands.
            std_dev (float): The number of standard deviations for the bands.
        """
        super().__init__(data_handler)
        self.period = bband_period
        self.std_dev = bband_std_dev

    def generate_signals(self):
        """
        Generates buy/sell signals for all tickers. The buy signal is a raw
        score based on the Z-score of the closing price during a breakout.

        Returns:
            pd.DataFrame: A DataFrame with signals for all tickers and dates.
        """
        signals_df = pd.DataFrame()
        for ticker in self.tickers:
            hist_data = self.data_handler.data.get(ticker)
            if hist_data is None or hist_data.empty:
                continue

            # Calculate Bollinger Bands
            close = hist_data['close']
            middle_band = close.rolling(window=self.period).mean()
            std_dev_val = close.rolling(window=self.period).std()
            upper_band = middle_band + (std_dev_val * self.std_dev)
            
            # Create signals
            signals = pd.Series(0.0, index=hist_data.index, name=ticker)

            # --- MODIFICATION START ---
            # Buy signal: Price crosses above the upper band.
            # The raw signal strength is the Z-score of the price.
            buy_mask = (close > upper_band) & (close.shift(1) <= upper_band.shift(1))
            
            # Calculate Z-Score only for the breakout moments to be efficient
            # Z-Score = (Price - Mean) / Std Dev
            # Avoid division by zero
            valid_std_dev = std_dev_val[buy_mask] > 0
            if valid_std_dev.any():
                signals[buy_mask & (std_dev_val > 0)] = (close[buy_mask & (std_dev_val > 0)] - middle_band[buy_mask & (std_dev_val > 0)]) / std_dev_val[buy_mask & (std_dev_val > 0)]

            # Sell signal: Price crosses below the middle band after a buy
            signals[(close < middle_band) & (close.shift(1) >= middle_band.shift(1))] = -1
            # --- MODIFICATION END ---
            
            signals_df = pd.concat([signals_df, signals], axis=1)

        return signals_df.fillna(0)