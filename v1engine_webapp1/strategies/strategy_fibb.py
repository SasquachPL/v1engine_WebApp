import pandas as pd
import numpy as np
from strategy_base import Strategy

class FibonacciStrategy(Strategy):
    """
    A strategy using Fibonacci Retracement levels.
    - It identifies a trend over a lookback period.
    - In an uptrend, a buy signal is generated when the price bounces
      off a Fibonacci support level.
    - In a downtrend, a sell signal is generated when the price is
      rejected by a Fibonacci resistance level.
    """
    def __init__(self, data_handler, lookback_period=50, retracement_levels=None):
        """
        Initializes the FibonacciRetracementStrategy.

        Args:
            data_handler (DataHandler): An instance of the DataHandler.
            lookback_period (int): The number of days to look back to find the
                                   swing high and low for defining the trend.
            retracement_levels (list, optional): A list of Fibonacci levels to
                                                 monitor. Defaults to [0.382, 0.5, 0.618].
        """
        super().__init__(data_handler)
        self.lookback_period = lookback_period
        # Set default retracement levels if none are provided
        if retracement_levels is None:
            self.retracement_levels = [0.382, 0.5, 0.618]
        else:
            self.retracement_levels = retracement_levels

    def generate_signals(self):
        """
        Generates signals based on bounces from Fibonacci Retracement levels.

        Returns:
            pd.DataFrame: A DataFrame with signals for all tickers and dates.
        """
        signals_df = pd.DataFrame()
        for ticker in self.tickers:
            hist_data = self.data_handler.data.get(ticker)
            if hist_data is None or len(hist_data) < self.lookback_period:
                continue
            
            # Ensure 'low' and 'high' columns are present, fallback to 'close' if not
            if 'low' not in hist_data.columns or 'high' not in hist_data.columns:
                hist_data['low'] = hist_data['close']
                hist_data['high'] = hist_data['close']

            # 1. Identify the swing high and low over the lookback period
            swing_low = hist_data['low'].rolling(window=self.lookback_period).min()
            swing_high = hist_data['high'].rolling(window=self.lookback_period).max()
            
            trend_range = swing_high - swing_low
            # Avoid division by zero if the range is flat
            trend_range[trend_range == 0] = np.nan

            # 2. Determine the trend direction
            # We define an uptrend if the close is in the upper half of the range,
            # and a downtrend if it's in the lower half.
            midpoint = swing_low + (trend_range / 2)
            is_uptrend = hist_data['close'] > midpoint
            is_downtrend = hist_data['close'] <= midpoint

            # 3. Get previous and current close for bounce detection
            prev_close = hist_data['close'].shift(1)
            current_close = hist_data['close']

            # 4. Generate signals based on bounces
            signals = pd.Series(0, index=hist_data.index, name=ticker)
            
            for level in self.retracement_levels:
                # Calculate support level for an uptrend
                support_level = swing_high - (trend_range * level)
                
                # Calculate resistance level for a downtrend
                resistance_level = swing_low + (trend_range * level)

                # Buy Signal: Price was below support and now is above (a bounce)
                buy_bounce = (is_uptrend) & (prev_close < support_level) & (current_close > support_level)
                signals[buy_bounce] = 1
                
                # Sell Signal: Price was above resistance and now is below (a rejection)
                sell_bounce = (is_downtrend) & (prev_close > resistance_level) & (current_close < resistance_level)
                signals[sell_bounce] = -1

            signals_df = pd.concat([signals_df, signals], axis=1)

        return signals_df.fillna(0)
