import pandas as pd
from strategy_base import Strategy

class SmaRsi3Strategy(Strategy):
    """
    Implements a strategy based on SMA crossover confirmed by RSI.
    Method 3: The raw buy signal is the RSI value's distance from the 50 line.
    """
    def __init__(self, data_handler, short_window=50, long_window=200, rsi_period=14, rsi_threshold=50):
        """
        Initializes the SmaXrsiStrategy.
        """
        super().__init__(data_handler)
        self.short_window = short_window
        self.long_window = long_window
        self.rsi_window = rsi_period
        self.rsi_threshold = rsi_threshold

    def generate_signals(self):
        """
        Generates buy/sell signals. The buy signal is RSI - 50.
        """
        signals_df = pd.DataFrame()
        for ticker in self.tickers:
            hist_data = self.data_handler.data.get(ticker)
            if hist_data is None or len(hist_data) < self.long_window:
                continue

            # Calculate SMAs
            short_sma = hist_data['close'].rolling(window=self.short_window).mean()
            long_sma = hist_data['close'].rolling(window=self.long_window).mean()

            # Calculate RSI
            delta = hist_data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_window).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_window).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            # Create signals
            signals = pd.Series(0.0, index=hist_data.index, name=ticker)
            
            # --- MODIFICATION START (METHOD 3) ---
            # Buy signal: Short SMA crosses above Long SMA, and RSI is above threshold.
            buy_mask = ((short_sma > long_sma) & (short_sma.shift(1) <= long_sma.shift(1)) &
                        (rsi > self.rsi_threshold))
            
            # The raw signal is how far the RSI is above the neutral 50 line.
            signals[buy_mask] = rsi[buy_mask] - 50

            # Sell signal: Short SMA crosses below Long SMA.
            signals[(short_sma < long_sma) & (short_sma.shift(1) >= long_sma.shift(1))] = -1
            # --- MODIFICATION END ---
            
            signals_df = pd.concat([signals_df, signals], axis=1)

        return signals_df.fillna(0)