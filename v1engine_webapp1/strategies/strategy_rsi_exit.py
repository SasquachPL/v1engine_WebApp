import pandas as pd

class RsiExitStrategy:
    """
    A strategy that generates a sell signal if the RSI of an asset
    crosses above a specified threshold.
    """
    def __init__(self, data_handler, rsi_period=14, sell_threshold=70):
        """
        Initializes the RsiExitStrategy.

        Args:
            data_handler (DataHandler): The data handler instance.
            rsi_period (int): The look-back period for calculating RSI.
            sell_threshold (int): The RSI level above which a sell signal is generated.
        """
        self.data_handler = data_handler
        self.rsi_period = rsi_period
        self.sell_threshold = sell_threshold

    def _calculate_rsi(self, series, period):
        """Calculates RSI for a given data series."""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def generate_exit_signal(self, date, ticker):
        """
        Checks if the RSI for a given ticker has crossed the exit threshold.

        Args:
            date (pd.Timestamp): The current date of the backtest.
            ticker (str): The ticker symbol of the asset to check.

        Returns:
            str or None: 'SELL' if the exit condition is met, otherwise None.
        """
        df = self.data_handler.data.get(ticker)
        if df is None or date not in df.index:
            return None

        # Get data up to the current date
        data_up_to_date = df.loc[:date]
        
        if len(data_up_to_date) < self.rsi_period + 1:
            return None # Not enough data to calculate RSI

        # Calculate RSI
        rsi_series = self._calculate_rsi(data_up_to_date['close'], self.rsi_period)
        
        if not rsi_series.empty:
            current_rsi = rsi_series.iloc[-1]
            if current_rsi > self.sell_threshold:
                return 'SELL'
        
        return None