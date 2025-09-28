import pandas as pd
from strategy_base import Strategy
import numpy as np

class BollingerRsi2Strategy(Strategy):
    """
    A combined strategy using Bollinger Bands and RSI (Option 2 Score).
    - A buy signal is generated when the price crosses below the lower Bollinger
      Band, and RSI indicates an oversold condition. The raw signal score is based
      on the penetration depth of the price relative to the channel width.
    - A sell signal is generated when the price crosses above the upper
      Bollinger Band, and RSI indicates an overbought condition.
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

        # Handle potential division by zero in loss
        rs = gain / loss
        rs[loss == 0] = np.inf # If loss is zero, RS is infinite
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def generate_signals(self):
        """
        Generates signals based on Bollinger Bands and RSI. The raw score
        is calculated from the price penetration depth.

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
            
            # --- Score Calculation (Option 2) ---
            # Buy signal: Price crosses below the lower band AND RSI is oversold.
            buy_mask = ((close < lower_band) & (close.shift(1) >= lower_band.shift(1)) &
                        (rsi < self.rsi_oversold))
            
            # Calculate the channel width and avoid division by zero
            band_width = upper_band - lower_band
            valid_width_mask = band_width > 0
            
            # Combine the buy trigger with the valid width condition
            final_buy_mask = buy_mask & valid_width_mask
            
            # The raw signal score is the penetration depth normalized by channel width.
            if final_buy_mask.any():
                signals[final_buy_mask] = (lower_band[final_buy_mask] - close[final_buy_mask]) / band_width[final_buy_mask]
            
            # Sell signal: Price crosses above the upper band AND RSI is overbought.
            sell_mask = ((close > upper_band) & (close.shift(1) <= upper_band.shift(1)) &
                         (rsi > self.rsi_overbought))
            signals[sell_mask] = -1.0
            
            signals_df = pd.concat([signals_df, signals], axis=1)

        return signals_df.fillna(0)
