import pandas as pd

class Strategy:
    """
    Base class for a trading strategy.

    This class provides a blueprint for all strategy implementations. Any new
    strategy should inherit from this class and implement the `generate_signals`
    method.
    """
    def __init__(self, data_handler):
        """
        Initializes the Strategy.

        Args:
            data_handler (DataHandler): An instance of the DataHandler to access market data.
        """
        self.data_handler = data_handler
        self.tickers = data_handler.tickers

    # --- MODIFICATION START ---
    def get_params(self):
        """
        Returns a dictionary of the strategy's parameters for logging.
        This method is designed to be called by the PerformanceReporter.
        
        It copies all instance attributes and then removes the common,
        non-parameter objects.
        """
        # Get a copy of all instance attributes
        params = self.__dict__.copy()
        
        # Remove attributes that are not strategy parameters
        params.pop('data_handler', None)
        params.pop('tickers', None)
        
        return params
    # --- MODIFICATION END ---

    def generate_signals(self, date):
        """
        Generates trading signals for a given date.

        This method must be overridden by any subclass.

        Args:
            date (str or pd.Timestamp): The current date in the backtest simulation.

        Returns:
            dict: A dictionary of trading signals for each ticker,
                  e.g., {'AAPL': 1, 'GOOG': -1}.
                  - 1 represents a buy/long signal.
                  - -1 represents a sell/short signal.
                  - 0 represents a neutral/hold signal.
        """
        raise NotImplementedError("Should implement generate_signals()")
