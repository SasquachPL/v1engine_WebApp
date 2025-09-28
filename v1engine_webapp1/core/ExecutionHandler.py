import pandas as pd
from datetime import timedelta



class ExecutionHandler:
    """
    Simulates the execution of trade orders, applying transaction costs
    such as commission and slippage.
    """
    # MODIFICATION: The constructor now accepts a pre-computed list of trading days
    def __init__(self, data_handler, trading_days, commission=1.0, slippage_percent=0.0001):
        """
        Initializes the ExecutionHandler.

        Args:
            data_handler (DataHandler): An instance of the DataHandler to get price data.
            trading_days (pd.DatetimeIndex): A pre-computed index of all valid trading days
                                             for the backtest period.
        """
        self.data_handler = data_handler
        self.trading_days = trading_days  # Store the list of valid trading days
        self.commission = commission
        self.slippage_percent = slippage_percent

    # MODIFICATION: This method is now much faster, using the trading_days list for a direct lookup
    def _get_next_trading_day(self, date):
        """
        Finds the next valid trading day from a given date using the pre-computed list.

        Args:
            date (pd.Timestamp): The starting date.

        Returns:
            pd.Timestamp or None: The next trading day, or None if no more trading days are available.
        """
        # searchsorted finds the insertion point for 'date' to maintain order.
        # Using side='right' ensures that if 'date' itself is a trading day, we start looking from the next one.
        current_day_loc = self.trading_days.searchsorted(date, side='right')

        # Check if the location is within the bounds of our trading days list
        if current_day_loc < len(self.trading_days):
            return self.trading_days[current_day_loc]
        else:
            # If not, it means we are at or after the last trading day in our backtest period
            return None

    def execute_order(self, order, date, current_positions):
        """
        Executes a single order, returning a fill event with execution details.

        Args:
            order (dict): The order to execute from the Portfolio.
            date (str or pd.Timestamp): The date the order was generated.
            current_positions (dict): The portfolio's current holdings.

        Returns:
            dict or None: A fill event dictionary, or None if execution fails.
        """
        order_date = pd.to_datetime(date)
        execution_day = self._get_next_trading_day(order_date)

        if execution_day is None:
            print(f"Warning: No trading day found after {order_date.date()} for {order['ticker']}. Cannot execute.")
            return None

        # Get the market data for the day the trade will actually execute
        execution_day_data = self.data_handler.get_latest_data(execution_day)
        ticker_data = execution_day_data.get(order['ticker'])

        if ticker_data is None:
            print(f"Warning: No data for {order['ticker']} on execution day {execution_day.date()}. Order cannot be filled.")
            return None

        # Use the 'Typical Price' for the execution day (average of high, low, close)
        high_price = ticker_data['high']
        low_price = ticker_data['low']
        close_price = ticker_data['close']
        execution_price = (high_price + low_price + close_price) / 3.0

        if execution_price == 0:
            return None # Cannot execute on a zero-price stock

        # Apply slippage cost
        if order['type'] == 'BUY':
            execution_price *= (1 + self.slippage_percent)
        elif order['type'] == 'SELL':
            execution_price *= (1 - self.slippage_percent)

        quantity = order['quantity']
        # If the order is to sell all shares, get the quantity from current positions
        if quantity == 'ALL':
            # ----- THIS IS THE CORRECTED LINE -----
            quantity = current_positions.get(order['ticker'], {}).get('shares', 0)

        if quantity <= 0:
            return None # No shares to trade

        # Create the fill event
        fill_event = {
            'type': order['type'],
            'ticker': order['ticker'],
            'quantity': quantity,
            'price': execution_price,
            'commission': self.commission
        }

        return fill_event


if __name__ == '__main__':
    # --- Example Usage ---
    # This example requires running the main backtest.py, as ExecutionHandler
    # is now dependent on the trading_days list created there. A standalone
    # run here would require mocking that data.
    
    print("--- ExecutionHandler Standalone Example ---")
    print("NOTE: This script is designed to be a component of the main backtest.")
    print("To run a full example, please execute 'backtest.py'.")

    # To demonstrate, we can create a mock DataHandler and a sample trading_days list
    if 'DataHandler' not in locals():
        from DataHandler import DataHandler # Assuming it exists for the example
    
    if 'Portfolio' not in locals():
        from portfolio import Portfolio
        
    print("\\nSetting up mock environment...")
    data_handler = DataHandler(csv_dir='data')
    
    if data_handler.tickers:
        # Create a sample trading days index
        sample_trading_days = pd.date_range(start='2023-11-01', end='2023-11-30', freq='B') # Business days
        
        # 1. Create an ExecutionHandler instance with the mock data
        execution_handler = ExecutionHandler(data_handler, sample_trading_days)
        
        # 2. Setup a mock portfolio and a sample order
        portfolio = Portfolio(data_handler)
        sample_ticker = data_handler.tickers[0]
        order_date = '2023-11-14' # A Tuesday
        
        portfolio.positions[sample_ticker] = 100
        sample_order = {'type': 'SELL', 'ticker': sample_ticker, 'quantity': 'ALL'}
        
        print(f"\\nGenerated order on {order_date}: {sample_order}")
        
        # 3. Execute the order
        fill = execution_handler.execute_order(sample_order, order_date, portfolio.positions)
        
        print("\\n--- Executed Fill Event ---")
        if fill:
            print(fill)
            next_day = execution_handler._get_next_trading_day(pd.to_datetime(order_date))
            print(f"Order generated on {order_date}, executed on the next trading day: {next_day.date()}")
        else:
            print("Order could not be filled.")