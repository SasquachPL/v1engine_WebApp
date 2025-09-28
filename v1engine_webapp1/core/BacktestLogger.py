# FILE: BacktestLogger.py

import os
import csv
import json
from datetime import datetime

class BacktestLogger:
    """
    Handles logging the results of each backtest run to a master CSV file.
    This provides a comprehensive, at-a-glance history of all simulations.
    """
    def __init__(self, log_file='master_backtest_log.csv'):
        """
        Initializes the logger.

        Args:
            log_file (str): The name of the master log file to be created.
        """
        self.log_file = log_file
        self.fieldnames = [
            'run_timestamp', 'output_folder', 'config_file', 'start_date', 'end_date',
            'initial_cash', 'ending_value', 'total_return_pct', 'annualized_return_pct',
            'sharpe_ratio', 'max_drawdown_pct', 'strategies_used', 'top_n_positions',
            'stop_loss_config', 'take_profit_config', 'tickers_used'
        ]
        self._initialize_log_file()

    def _initialize_log_file(self):
        """
        Creates the log file with a header row if it doesn't already exist.
        """
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()

    def log_backtest_result(self, config_filename, reporter):
        """
        Appends a new record to the master log file from a completed backtest.

        Args:
            config_filename (str): The name of the configuration file used.
            reporter (PerformanceReporter): The reporter object containing all results.
        """
        print("\n--- Appending results to master log ---")
        try:
            # --- 1. Extract Key Metrics from the Reporter ---
            equity = reporter.equity_curve
            settings = reporter.backtest_settings
            
            total_return = (equity.iloc[-1] / equity.iloc[0]) - 1
            days = len(equity)
            annualized_return = ((1 + total_return) ** (252 / days)) - 1 if days > 0 else 0
            sharpe = reporter._calculate_sharpe_ratio()
            max_drawdown = reporter._calculate_max_drawdown()

            # --- 2. Format Complex Data for CSV ---
            # Convert list of strategy objects to a clean string
            strategies_str = ", ".join([s.__class__.__name__ for s in reporter.strategies])
            
            # Convert risk management dicts to JSON strings for easy storage
            sl_config_str = json.dumps(settings.get('stop_loss', {}))
            tp_config_str = json.dumps(settings.get('take_profit', {}))
            
            # Join tickers into a single string
            tickers_str = ", ".join(reporter.tickers)

            # --- 3. Assemble the Log Entry ---
            log_entry = {
                'run_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'output_folder': reporter.output_dir,
                'config_file': config_filename,
                'start_date': equity.index[0].strftime('%Y-%m-%d'),
                'end_date': equity.index[-1].strftime('%Y-%m-%d'),
                'initial_cash': settings.get('initial_cash', 0),
                'ending_value': f"{equity.iloc[-1]:.2f}",
                'total_return_pct': f"{total_return:.2%}",
                'annualized_return_pct': f"{annualized_return:.2%}",
                'sharpe_ratio': f"{sharpe:.2f}",
                'max_drawdown_pct': f"{max_drawdown:.2%}",
                'strategies_used': strategies_str,
                'top_n_positions': settings.get('top_n_positions', 'N/A'),
                'stop_loss_config': sl_config_str,
                'take_profit_config': tp_config_str,
                'tickers_used': tickers_str
            }

            # --- 4. Write to the CSV File ---
            with open(self.log_file, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writerow(log_entry)
                
            print(f"Successfully saved results to '{self.log_file}'")

        except Exception as e:
            print(f"Error: Could not write to master log file. {e}")