import pandas as pd
from collections import defaultdict
import json
from datetime import datetime

class Portfolio:
    """
    Manages the portfolio's state and handles the generation of all orders,
    including complex exit-condition orders and tracking realized P&L.
    """
    def __init__(self, data_handler, initial_cash=100000.0, strategies=None,
                 stop_loss_config=None, take_profit_config=None,
                 stop_loss_strategy=None, take_profit_strategy=None):
        """
        Initializes the Portfolio.
        """
        self.data_handler = data_handler
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions = defaultdict(lambda: {'shares': 0, 'purchase_price': 0.0, 'entry_date': None})
        self.total_value = initial_cash
        self.tickers = data_handler.tickers
        self.strategies = strategies or []
        self.realized_pnl = 0.0
        self.trade_history = defaultdict(list)
        self.stop_loss_config = stop_loss_config or {}
        self.take_profit_config = take_profit_config or {}
        self.stop_loss_strategy = stop_loss_strategy
        self.take_profit_strategy = take_profit_strategy

    def update_value(self, date):
        """Calculates the total market value of the portfolio on a given date."""
        market_value = 0.0
        latest_data = self.data_handler.get_latest_data(date)
        for ticker, position_details in self.positions.items():
            if position_details['shares'] > 0 and ticker in latest_data:
                market_value += position_details['shares'] * latest_data[ticker]['close']
        self.total_value = self.cash + market_value
        return self.total_value

    def get_holdings_dict(self, date):
        """
        Returns a dictionary of current holdings with their market value,
        formatted for JSON logging.
        """
        holdings = {}
        latest_data = self.data_handler.get_latest_data(date)
        for ticker, position in self.positions.items():
            if position['shares'] > 0:
                market_value = position['shares'] * latest_data.get(ticker, {}).get('close', 0)
                holdings[ticker] = {
                    'shares': position['shares'],
                    'market_value': round(market_value, 2)
                }
        return holdings

    def generate_exit_orders(self, date, trade_logger):
        """
        Checks for all exit conditions (stop-loss, take-profit) and generates sell orders.
        """
        orders = []
        latest_data = self.data_handler.get_latest_data(date)

        for ticker, position in list(self.positions.items()):
            if position['shares'] <= 0 or ticker not in latest_data:
                continue

            purchase_price = position['purchase_price']

            if self.stop_loss_config.get('type') == 'percentage':
                sl_pct = self.stop_loss_config.get('value', 0) / 100.0
                if sl_pct > 0:
                    stop_loss_price = purchase_price * (1 - sl_pct)
                    if latest_data[ticker]['low'] <= stop_loss_price:
                        orders.append({'type': 'SELL', 'ticker': ticker, 'quantity': 'ALL'})
                        if trade_logger:
                            trade_logger.log_trade(date, ticker, 'SELL', position['shares'], stop_loss_price, 'Stop-Loss', f'percentage_stop_loss_{sl_pct*100}%', None)
                        continue

            if self.take_profit_config.get('type') == 'percentage':
                tp_pct = self.take_profit_config.get('value', 0) / 100.0
                if tp_pct > 0:
                    take_profit_price = purchase_price * (1 + tp_pct)
                    if latest_data[ticker]['high'] >= take_profit_price:
                        orders.append({'type': 'SELL', 'ticker': ticker, 'quantity': 'ALL'})
                        if trade_logger:
                            trade_logger.log_trade(date, ticker, 'SELL', position['shares'], take_profit_price, 'Take-Profit', f'percentage_take_profit_{tp_pct*100}%', None)
                        continue

        return orders

    def generate_rebalancing_orders(self, date, aggregated_scores, strategy_specific_scores, top_n=5, sold_due_to_sl_tp=None, trade_logger=None):
        """Generates trade orders based on aggregated strategy scores."""
        if sold_due_to_sl_tp is None: sold_due_to_sl_tp = set()

        # Filter for stocks with a positive score before determining the target portfolio
        positive_scored_stocks = {ticker: score for ticker, score in aggregated_scores.items() if score > 0}

        # Determine target portfolio using the aggregated scores
        long_targets = sorted(positive_scored_stocks, key=positive_scored_stocks.get, reverse=True)[:top_n]
        target_portfolio = {ticker: 'LONG' for ticker in long_targets if ticker not in sold_due_to_sl_tp}

        self.update_value(date)
        target_position_value = self.total_value / top_n if top_n > 0 else 0

        orders = []
        latest_data = self.data_handler.get_latest_data(date)

        # Generate sell orders for positions no longer in the target portfolio
        for ticker in list(self.positions.keys()):
            if self.positions[ticker]['shares'] > 0 and ticker not in target_portfolio:
                orders.append({'type': 'SELL', 'ticker': ticker, 'quantity': 'ALL'})
                if trade_logger and ticker in latest_data:
                    score = aggregated_scores.get(ticker, 0)
                    reason_json = json.dumps(strategy_specific_scores.get(ticker, {}))
                    trade_logger.log_trade(date, ticker, 'SELL', self.positions[ticker]['shares'], latest_data[ticker]['close'],
                                           'Rebalance', score, reason_json)

        # Generate buy/sell orders to align with the target portfolio
        for ticker in target_portfolio:
            if ticker not in latest_data: continue

            current_shares = self.positions.get(ticker, {}).get('shares', 0)
            price = latest_data[ticker]['close']
            if price <= 0: continue

            current_value = current_shares * price
            value_difference = target_position_value - current_value

            quantity_to_trade = int(value_difference / price)
            score = aggregated_scores.get(ticker, 0)
            reason_json = json.dumps(strategy_specific_scores.get(ticker, {}))

            if quantity_to_trade > 0:
                orders.append({'type': 'BUY', 'ticker': ticker, 'quantity': quantity_to_trade})
                if trade_logger:
                    trade_logger.log_trade(date, ticker, 'BUY', quantity_to_trade, price, 'Buy',
                                           score, reason_json)
            elif quantity_to_trade < 0:
                # This part handles reducing a position that's overweight
                quantity_to_sell = min(abs(quantity_to_trade), current_shares)
                if quantity_to_sell > 0:
                    orders.append({'type': 'SELL', 'ticker': ticker, 'quantity': quantity_to_sell})
                    if trade_logger:
                        trade_logger.log_trade(date, ticker, 'SELL', quantity_to_sell, price, 'Rebalance',
                                               score, reason_json)

        return orders

    def update_positions_from_fill(self, fill_event, date):
        """Updates the portfolio's state after a trade is executed."""
        ticker = fill_event['ticker']
        quantity = fill_event['quantity']
        price = fill_event['price']
        trade_cost = quantity * price
        timestamp = date


        if fill_event['type'] == 'BUY':
            current_shares = self.positions[ticker]['shares']
            current_value = current_shares * self.positions[ticker].get('purchase_price', 0)
            new_total_shares = current_shares + quantity
            self.positions[ticker]['purchase_price'] = (current_value + trade_cost) / new_total_shares if new_total_shares > 0 else 0
            self.positions[ticker]['shares'] = new_total_shares
            self.positions[ticker]['entry_date'] = timestamp
            self.cash -= trade_cost
        elif fill_event['type'] == 'SELL':
            purchase_price = self.positions[ticker]['purchase_price']
            profit_loss = (price - purchase_price) * quantity
            self.realized_pnl += profit_loss
            
            entry_date = self.positions[ticker].get('entry_date')
            if entry_date:
                self.trade_history[ticker].append({
                    'pnl': profit_loss,
                    'entry_date': entry_date,
                    'exit_date': timestamp
                })

            self.cash += trade_cost
            self.positions[ticker]['shares'] -= quantity
            if self.positions[ticker]['shares'] == 0:
                self.positions[ticker]['purchase_price'] = 0.0
                self.positions[ticker]['entry_date'] = None


        self.cash -= fill_event.get('commission', 0.0)