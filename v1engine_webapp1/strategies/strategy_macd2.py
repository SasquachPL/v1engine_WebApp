import pandas as pd
from strategy_base import Strategy

class Macd2Strategy(Strategy):
    """
    Implements a MACD (Moving Average Convergence Divergence) trading strategy.
    A buy signal is generated when the MACD line crosses above the signal line.
    The strength of the buy signal is the difference between the MACD and signal lines.
    A sell signal is generated when the MACD line crosses below the signal line.
    """
    def __init__(self, data_handler, short_ema_period=12, long_ema_period=26, signal_period=9):
        """
        Initializes the MacdStrategy.

        Args:
            data_handler (DataHandler): An instance of the DataHandler.
            short_ema_period (int): The short-term EMA period.
            long_ema_period (int): The long-term EMA period.
            signal_period (int): The EMA period for the signal line.
        """
        super().__init__(data_handler)
        self.short_window = short_ema_period
        self.long_window = long_ema_period
        self.signal_window = signal_period

    def generate_signals(self):
        """
        Generates buy/sell signals for all tickers over the entire data period
        based on the MACD crossover. The buy signal is now a raw score.

        Returns:
            pd.DataFrame: A DataFrame with signals for all tickers and dates.
        """
        signals_df = pd.DataFrame()
        for ticker in self.tickers:
            hist_data = self.data_handler.data.get(ticker)
            if hist_data is None or hist_data.empty:
                continue

            # Calculate the Short and Long-term Exponential Moving Averages (EMAs)
            short_ema = hist_data['close'].ewm(span=self.short_window, adjust=False).mean()
            long_ema = hist_data['close'].ewm(span=self.long_window, adjust=False).mean()

            # Calculate the MACD line and Signal line
            macd_line = short_ema - long_ema
            signal_line = macd_line.ewm(span=self.signal_window, adjust=False).mean()

            # Create signals based on the crossover
            signals = pd.Series(0.0, index=hist_data.index, name=ticker)
            
            # --- MODIFICATION START ---
            # Buy signal: MACD crosses above Signal line
            # The raw signal strength is the difference between the MACD line and the signal line.
            buy_mask = (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))
            signals[buy_mask] = macd_line[buy_mask] - signal_line[buy_mask]
            
            # Sell signal: MACD crosses below Signal line
            signals[(macd_line < signal_line) & (macd_line.shift(1) >= signal_line.shift(1))] = -1
            # --- MODIFICATION END ---
            
            signals_df = pd.concat([signals_df, signals], axis=1)

        return signals_df.fillna(0)