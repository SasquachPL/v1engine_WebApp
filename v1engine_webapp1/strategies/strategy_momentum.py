import pandas as pd
import os
from strategy_base import Strategy

class MomentumStrategy(Strategy):
    """
    A simple momentum-based trading strategy.
    This strategy generates a buy signal if the stock's price has increased over
    a specified period (momentum window) and a sell signal if it has decreased.
    The strength of the buy signal is the momentum gain itself.
    """
    def __init__(self, data_handler, momentum_window=5):
        """
        Initializes the MomentumStrategy.
        Args:
            data_handler (DataHandler): An instance of the DataHandler.
            momentum_window (int): The number of days to look back to calculate momentum.
        """
        super().__init__(data_handler)
        self.momentum_window = momentum_window

    def generate_signals(self):
        """
        Generates signals for all tickers over the entire data period.
        The signal value is the momentum gain for positive momentum, and -1 for negative momentum.
        Returns:
            pd.DataFrame: A DataFrame with signals for all tickers and dates.
        """
        signals_df = pd.DataFrame()
        for ticker in self.tickers:
            hist_data = self.data_handler.data.get(ticker)
            if hist_data is None or hist_data.empty:
                continue

            momentum = hist_data['close'].pct_change(self.momentum_window)
            
            # Use the momentum value as the signal for positive momentum
            # and keep -1 for negative momentum
            signals = pd.Series(0.0, index=hist_data.index, name=ticker)
            signals[momentum > 0] = momentum[momentum > 0]
            signals[momentum < 0] = -1

            signals_df = pd.concat([signals_df, signals], axis=1)

        return signals_df.fillna(0)