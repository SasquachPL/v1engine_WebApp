import pandas as pd
from strategy_base import Strategy

class StochSpreadStrategy(Strategy):
    """
    Implements a Stochastic Oscillator trading strategy.
    Method 1: The buy signal strength is the magnitude of the K-D spread at the crossover.
    """
    def __init__(self, data_handler, k_period=14, d_period=3, oversold_threshold=20, overbought_threshold=80):
        """
        Initializes the StochStrategy.
        """
        super().__init__(data_handler)
        self.k_period = k_period
        self.d_period = d_period
        self.oversold_threshold = oversold_threshold
        self.overbought_threshold = overbought_threshold

    def generate_signals(self):
        """
        Generates buy/sell signals. The raw buy signal is the spread between %K and %D.
        """
        signals_df = pd.DataFrame()
        for ticker in self.tickers:
            hist_data = self.data_handler.data.get(ticker)
            if hist_data is None or len(hist_data) < self.k_period:
                continue

            # Calculate Stochastic Oscillator values
            low_min = hist_data['low'].rolling(window=self.k_period).min()
            high_max = hist_data['high'].rolling(window=self.k_period).max()
            percent_k = 100 * ((hist_data['close'] - low_min) / (high_max - low_min))
            percent_d = percent_k.rolling(window=self.d_period).mean()

            # Create signals
            signals = pd.Series(0.0, index=hist_data.index, name=ticker)
            
            # --- MODIFICATION START (METHOD 1) ---
            # Buy signal: %K crosses above %D in the oversold zone.
            buy_mask = ((percent_k > percent_d) & (percent_k.shift(1) <= percent_d.shift(1)) &
                        (percent_k < self.oversold_threshold))
            
            # The raw signal is the magnitude of the crossover spread.
            signals[buy_mask] = percent_k[buy_mask] - percent_d[buy_mask]

            # Sell signal: %K crosses below %D in the overbought zone.
            signals[(percent_k < percent_d) & (percent_k.shift(1) >= percent_d.shift(1)) &
                    (percent_k > self.overbought_threshold)] = -1
            # --- MODIFICATION END ---
            
            signals_df = pd.concat([signals_df, signals], axis=1)

        return signals_df.fillna(0)