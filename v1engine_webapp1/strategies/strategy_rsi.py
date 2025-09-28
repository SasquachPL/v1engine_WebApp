import pandas as pd
from strategy_base import Strategy

class RsiStrategy(Strategy):
    """
    A trading strategy based on the Relative Strength Index (RSI).
    This strategy generates a scaled buy signal when the RSI is in the oversold
    region and a sell signal when it is in the overbought region.
    """
    def __init__(self, data_handler, rsi_period=14, rsi_oversold_threshold=30, rsi_overbought_threshold=70):
        """
        Initializes the RSIStrategy.
        Args:
            data_handler (DataHandler): An instance of the DataHandler.
            rsi_period (int): The period for RSI calculation.
            oversold_threshold (int): The RSI level below which a stock is considered oversold.
            overbought_threshold (int): The RSI level above which a stock is considered overbought.
        """
        super().__init__(data_handler)
        self.rsi_period = rsi_period
        self.oversold_threshold = rsi_oversold_threshold
        self.overbought_threshold = rsi_overbought_threshold

    def _calculate_rsi(self, series):
        """
        Calculates the Relative Strength Index (RSI) for a given data series.
        """
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def generate_signals(self):
        """
        Generates signals for all tickers based on RSI.
        The buy signal is scaled based on how deep in the oversold territory the RSI is.
        Returns:
            pd.DataFrame: A DataFrame with signals for all tickers and dates.
        """
        signals_df = pd.DataFrame()
        for ticker in self.tickers:
            hist_data = self.data_handler.data.get(ticker)
            if hist_data is None or hist_data.empty:
                continue

            rsi = self._calculate_rsi(hist_data['close'])
            signals = pd.Series(0.0, index=hist_data.index, name=ticker)

            # Generate scaled buy signal for oversold condition
            buy_mask = rsi < self.oversold_threshold
            signals[buy_mask] = (self.oversold_threshold - rsi[buy_mask]) / self.oversold_threshold

            # Generate sell signal for overbought condition
            signals[rsi > self.overbought_threshold] = -1.0

            signals_df = pd.concat([signals_df, signals], axis=1)
            
        return signals_df.fillna(0)