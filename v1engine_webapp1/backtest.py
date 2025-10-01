import pandas as pd
import os
import yaml
from tqdm import tqdm
import traceback
import csv
from datetime import datetime
import json
from collections import defaultdict
import numpy as np

# --- Import All Components ---
try:
    from core.DataDownloader import DataDownloader, ALPHA_VANTAGE_API_KEY
    from core.DataHandler import DataHandler
    from core.portfolio import Portfolio
    from core.ExecutionHandler import ExecutionHandler
    from core.PerformanceReporter import PerformanceReporter
    from core.BacktestLogger import BacktestLogger

    # Import all strategy files
    from strategies.strategy_rsi import RsiStrategy
    from strategies.strategy_rsi2 import Rsi2Strategy
    from strategies.strategy_momentum import MomentumStrategy
    from strategies.strategy_momentum2 import Momentum2Strategy
    from strategies.strategy_momentum3 import Momentum3Strategy
    from strategies.strategy_smaXrsi import SmaRsiStrategy
    from strategies.strategy_smaXrsi2 import SmaRsi2Strategy
    from strategies.strategy_smaXrsi3 import SmaRsi3Strategy
    from strategies.strategy_keltner import KeltnerStrategy
    from strategies.strategy_keltner2 import Keltner2Strategy
    from strategies.strategy_keltner3 import Keltner3Strategy
    from strategies.strategy_bbXrsi import BollingerRsiStrategy
    from strategies.strategy_bbXrsi2 import BollingerRsi2Strategy
    from strategies.strategy_bbXrsi3 import BollingerRsi3Strategy
    from strategies.strategy_bb import BollingerStrategy
    from strategies.strategy_bb2 import Bollinger2Strategy
    from strategies.strategy_macd import MacdStrategy
    from strategies.strategy_macd2 import Macd2Strategy
    from strategies.strategy_macd3 import Macd3Strategy
    from strategies.strategy_stoch import StochasticStrategy
    from strategies.strategy_stoch2 import Stochastic2Strategy
    from strategies.strategy_stochSpread import StochSpreadStrategy
    from strategies.strategy_fibb import FibonacciStrategy
    from strategies.strategy_zscore import ZScoreStrategy
    from strategies.strategy_obv import ObvStrategy
    from strategies.strategy_obvroc import ObvRocStrategy

    
    from strategies.strategy_rsi_exit import RsiExitStrategy

except ImportError as e:
    print(f"Error: A required component file is missing. {e}")
    exit()

class TradeLogger:
    """Logs all executed trades to a CSV file for detailed analysis."""
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.log_file = os.path.join(self.output_dir, 'trades_log.csv')
        self.trade_id = 0
        self._initialize_log_file()

    def _initialize_log_file(self):
        """Creates the CSV file and writes the header row."""
        with open(self.log_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'trade_id', 'timestamp', 'ticker', 'action', 'quantity', 'price',
                'total_cost', 'order_type', 'trigger_reason', 'score'
            ])

    def log_trade(self, timestamp, ticker, action, quantity, price, order_type, trigger_reason, score):
        """Appends a single trade record to the log file."""
        self.trade_id += 1
        total_cost = quantity * price
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                self.trade_id, timestamp, ticker, action, quantity, price,
                total_cost, order_type, trigger_reason, score
            ])

class PortfolioLogger:
    """Logs the state of the portfolio at the end of each trading day."""
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.log_file = os.path.join(self.output_dir, 'portfolio_log.csv')
        self._initialize_log_file()

    def _initialize_log_file(self):
        """Creates the CSV file and writes the header row."""
        with open(self.log_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'total_value', 'invested_value', 'cash', 
                'position_count', 'pnl_realized', 'holdings'
            ])

    def log_portfolio_state(self, timestamp, portfolio):
        """Appends a snapshot of the portfolio's state to the log file."""
        total_value = portfolio.total_value
        cash = portfolio.cash
        invested_value = total_value - cash
        holdings = portfolio.get_holdings_dict(timestamp)
        position_count = len(holdings)
        realized_pnl = portfolio.realized_pnl

        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp, round(total_value, 2), round(invested_value, 2), round(cash, 2),
                position_count, round(realized_pnl, 2), json.dumps(holdings)
            ])



STRATEGY_MAPPING = {
    'MomentumStrategy': MomentumStrategy, 
    'Momentum2Strategy': Momentum2Strategy,
    'Momentum3Strategy': Momentum3Strategy, 
    'RsiStrategy': RsiStrategy,
    'Rsi2Strategy': Rsi2Strategy,
    'SmaRsiStrategy': SmaRsiStrategy, 
    'SmaRsi2Strategy': SmaRsi2Strategy, 
    'SmaRsi3Strategy': SmaRsi3Strategy,
    'KeltnerStrategy': KeltnerStrategy, 
    'Keltner2Strategy': Keltner2Strategy,
    'Keltner3Strategy': Keltner3Strategy,
    'BollingerRsiStrategy': BollingerRsiStrategy,
    'BollingerRsi2Strategy': BollingerRsi2Strategy,
    'BollingerRsi3Strategy': BollingerRsi3Strategy, 
    'BollingerStrategy': BollingerStrategy,
    'Bollinger2Strategy': Bollinger2Strategy,
    'MacdStrategy': MacdStrategy,
    'Macd2Strategy': Macd2Strategy,
    'Macd3Strategy': Macd3Strategy,
    'StochasticStrategy': StochasticStrategy,
    'Stochastic2Strategy': Stochastic2Strategy,
    'StochSpreadStrategy': StochSpreadStrategy,
    'FibonacciStrategy': FibonacciStrategy,
    'ZScoreStrategy': ZScoreStrategy,
    'ObvStrategy': ObvStrategy,
    'ObvRocStrategy': ObvRocStrategy

}
EXIT_STRATEGY_MAPPING = {'RsiExit': RsiExitStrategy}

class Backtest:
    """
    Orchestrates the entire backtesting process, from data handling to
    performance reporting.
    """
    def __init__(self, config, data_path):
        """Initializes the backtesting engine with a given configuration."""
        self.config = config
        settings = self.config['backtest_settings']
        self.start_date = pd.to_datetime(settings['start_date'])
        self.end_date = pd.to_datetime(settings['end_date'])
        self.benchmark_ticker = settings['benchmark_ticker'].lower()
        self.tickers_to_trade = [t.lower() for t in self.config['tickers']]
        self.output_dir = None
        all_required_tickers = list(set(self.tickers_to_trade + [self.benchmark_ticker]))
        self.data_handler = DataHandler(csv_dir=data_path, ticker_list=all_required_tickers)
        
        # --- MODIFICATION START: Read rebalancing frequency from config ---
        # Defaults to 1 (daily) if not specified, ensuring backward compatibility.
        self.rebalancing_frequency = settings.get('rebalancing_frequency', 1)
        # --- MODIFICATION END ---

        stop_loss_config = settings.get('stop_loss', {})
        take_profit_config = settings.get('take_profit', {})
        
        stop_loss_strategy = self._initialize_exit_strategy(stop_loss_config)
        take_profit_strategy = self._initialize_exit_strategy(take_profit_config)

        self.strategies = []
        for strat_config in self.config['strategies']:
            if strat_config.get('enabled', True):
                strat_name = strat_config['name']
                if strat_name in STRATEGY_MAPPING:
                    strat_class = STRATEGY_MAPPING[strat_name]
                    params = strat_config.get('params', {})
                    self.strategies.append(strat_class(self.data_handler, **params))
                else:
                    print(f"Warning: Strategy '{strat_name}' from config not found.")

        self.portfolio = Portfolio(self.data_handler,
                                   initial_cash=settings['initial_cash'],
                                   strategies=self.strategies,
                                   stop_loss_config=stop_loss_config,
                                   take_profit_config=take_profit_config,
                                   stop_loss_strategy=stop_loss_strategy,
                                   take_profit_strategy=take_profit_strategy)

        benchmark_df = self.data_handler.data.get(self.benchmark_ticker)
        if benchmark_df is not None:
            self.trading_days = benchmark_df.loc[self.start_date:self.end_date].index
        else:
            self.trading_days = pd.Index([])
        
        commission = settings.get('commission_per_trade', 1.0)
        slippage = settings.get('slippage_percent', 0.0001)

        self.execution_handler = ExecutionHandler(self.data_handler, self.trading_days, commission, slippage)
        
        self.equity_curve = pd.Series(index=self.trading_days, dtype=float)

    def _initialize_exit_strategy(self, config):
        """Initializes an exit strategy based on the configuration."""
        if config.get('type') == 'indicator':
            strategy_name = config.get('strategy')
            if strategy_name in EXIT_STRATEGY_MAPPING:
                return EXIT_STRATEGY_MAPPING[strategy_name](self.data_handler, **config.get('params', {}))
        return None

    def _precompute_signals(self):
        """
        Pre-computes raw signals for all strategies, returning a list of signal
        DataFrames and a list of strategy names.
        """
        individual_signals_dfs = []
        strategy_names = []
        for strategy in self.strategies:
            # Each strategy returns a DataFrame of raw scores
            individual_signals_dfs.append(strategy.generate_signals())
            strategy_names.append(strategy.__class__.__name__)

        # Align all signal DataFrames to the backtest's trading days and tickers
        aligned_dfs = [
            df.reindex(index=self.trading_days, columns=self.tickers_to_trade).fillna(0)
            for df in individual_signals_dfs
        ]

        return aligned_dfs, strategy_names

    def run(self, logger, config_filename):
        """
        Executes the main backtest loop, normalizing signals daily using a rank-based
        Z-score before generating trade orders.
        """
        results_parent_dir = 'results'
        if not os.path.exists(results_parent_dir):
            os.makedirs(results_parent_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = os.path.join(results_parent_dir, f"v1sim_{timestamp}")
        
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"\n--- Saving results to '{self.output_dir}' ---")
        
        print("\n--- Pre-computing all raw signals ---")
        individual_signals, strategy_names = self._precompute_signals()
        
        print(f"\n--- Starting Multi-Strategy Backtest (Rebalance every {self.rebalancing_frequency} days) ---")
        top_n = self.config['backtest_settings']['top_n_positions']
        
        trade_logger = TradeLogger(output_dir=self.output_dir)
        portfolio_logger = PortfolioLogger(output_dir=self.output_dir)

        # --- MODIFICATION START: Add counter for rebalancing frequency ---
        # Initialize to ensure rebalancing happens on the very first day of the simulation.
        days_since_last_rebalance = self.rebalancing_frequency
        # --- MODIFICATION END ---

        for current_date in tqdm(self.trading_days, desc="Running Backtest"):
            # This logic runs EVERY day to ensure the equity curve is accurate.
            self.portfolio.update_value(current_date)
            self.equity_curve.loc[current_date] = self.portfolio.total_value
            
            # --- MODIFICATION START: Conditional block for rebalancing ---
            # All trading logic is now inside this block, which only runs
            # when the rebalancing frequency is met.
            if days_since_last_rebalance >= self.rebalancing_frequency:
            
                exit_orders = self.portfolio.generate_exit_orders(current_date, trade_logger)
                sold_tickers = set()
                if exit_orders:
                    for order in exit_orders:
                        fill_event = self.execution_handler.execute_order(order, current_date, self.portfolio.positions)
                        if fill_event:
                            self.portfolio.update_positions_from_fill(fill_event, current_date)
                            sold_tickers.add(fill_event['ticker'])

                # --- RANKING & Z-SCORE NORMALIZATION ---
                strategy_specific_scores = defaultdict(dict)
                aggregated_scores_for_date = defaultdict(float)

                for i, strat_df in enumerate(individual_signals):
                    strategy_name = strategy_names[i]
                    
                    if current_date not in strat_df.index:
                        continue

                    daily_scores = strat_df.loc[current_date]
                    buy_signals = daily_scores[daily_scores > 0]
                    
                    if buy_signals.empty:
                        continue

                    ranks = buy_signals.rank(method='dense', ascending=False)

                    if len(ranks) <= 2:
                        normalized_scores = pd.Series(1.0, index=ranks.index)
                    else:
                        mean_rank = ranks.mean()
                        std_dev_rank = ranks.std()
                        
                        if std_dev_rank < 1e-8:
                            normalized_scores = pd.Series(1.0, index=ranks.index)
                        else:
                            z_scores = (mean_rank - ranks) / std_dev_rank
                            normalized_scores = z_scores
                    
                    for ticker, score in normalized_scores.items():
                        if score > 0:
                            strategy_specific_scores[ticker][strategy_name] = score
                            aggregated_scores_for_date[ticker] += score
                
                rebalancing_orders = self.portfolio.generate_rebalancing_orders(
                    date=current_date,
                    aggregated_scores=aggregated_scores_for_date,
                    strategy_specific_scores=strategy_specific_scores,
                    top_n=top_n,
                    sold_due_to_sl_tp=sold_tickers,
                    trade_logger=trade_logger
                )
                
                if rebalancing_orders:
                    for order in rebalancing_orders:
                        fill_event = self.execution_handler.execute_order(order, current_date, self.portfolio.positions)
                        if fill_event:
                            self.portfolio.update_positions_from_fill(fill_event, current_date)
                
                # Reset the counter after a rebalancing day
                days_since_last_rebalance = 1
            else:
                # If not a rebalancing day, just increment the counter
                days_since_last_rebalance += 1
            # --- MODIFICATION END ---

            # Portfolio state is logged daily to get a complete history.
            portfolio_logger.log_portfolio_state(current_date, self.portfolio)
        
        print("\n--- Backtest Simulation Finished ---")
        self.generate_performance_report(logger, config_filename)

    def generate_performance_report(self, logger, config_filename):
        """
        Generates the final performance report and chart by passing all necessary
        data, including backtest settings, to the PerformanceReporter.
        """
        benchmark_prices = self.data_handler.data[self.benchmark_ticker]['close']
        
        reporter = PerformanceReporter(
            equity_curve=self.equity_curve,
            benchmark_data=benchmark_prices,
            strategies=self.strategies,
            tickers=self.data_handler.tickers,
            backtest_settings=self.config['backtest_settings'],
            portfolio=self.portfolio,
            output_dir=self.output_dir
        )
        
        reporter.generate_report()
        reporter.generate_metrics_file()
        reporter.plot_performance()
        
        logger.log_backtest_result(
            config_filename=config_filename,
            reporter=reporter
        )

# --- MODIFICATION START ---
# This block now controls the execution for single runs.
# It allows the Backtest class to be imported by other scripts without
# automatically running the user input section.
if __name__ == '__main__':
    # --- Configuration File Selection for Single Run ---
    config_files = sorted([f for f in os.listdir('.') if f.startswith('config') and f.endswith('.yaml')])
    if not config_files:
        print("Error: No 'config*.yaml' files found in this directory for a single run.")
        exit()

    print("\nPlease choose a configuration file to run a single backtest:")
    for i, filename in enumerate(config_files, 1):
        print(f"  {i}: {filename}")

    choice = 0
    while True:
        try:
            choice_input = input(f"\nEnter the number of the config to use (1-{len(config_files)}): ")
            choice = int(choice_input)
            if 1 <= choice <= len(config_files):
                break
            else:
                print(f"Invalid input. Please enter a number between 1 and {len(config_files)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    selected_filename = config_files[choice - 1]
    print(f"\n--- Loading configuration from '{selected_filename}' ---\n")
    with open(selected_filename, 'r') as f:
        config = yaml.safe_load(f)
    
    # --- Data Download Check ---
    settings = config['backtest_settings']
    tickers = config['tickers']
    all_required_tickers = list(set([t.lower() for t in tickers] + [settings['benchmark_ticker'].lower()]))
    
    if ALPHA_VANTAGE_API_KEY and ALPHA_VANTAGE_API_KEY != "YOUR_ACTUAL_API_KEY_HERE":
        downloader = DataDownloader(api_key=ALPHA_VANTAGE_API_KEY, output_dir='data')
        missing_tickers = [t for t in all_required_tickers if not os.path.exists(os.path.join('data', f"daily_{t}.csv"))]
        if missing_tickers:
            print(f"Missing data for: {missing_tickers}. Downloading now...")
            download_start_date = config.get('download_start_date', '2020-01-01')
            downloader.download_and_save_data(missing_tickers, download_start_date, settings['end_date'])
        else:
            print("All required data files are present.")

    # --- Run Single Backtest ---
    master_logger = BacktestLogger()
    try:
        backtest = Backtest(config=config)
        backtest.run(logger=master_logger, config_filename=selected_filename)
    except (ValueError, KeyError, TypeError) as e:
        print(f"\nAn error occurred during backtest setup or execution: {e}")
        traceback.print_exc()
# --- MODIFICATION END ---
