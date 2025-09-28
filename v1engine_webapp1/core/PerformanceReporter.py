import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime

class PerformanceReporter:
    """
    Analyzes the performance of a backtest and generates a summary report
    and a performance chart within a uniquely timestamped folder.
    """
    def __init__(self, equity_curve, benchmark_data, strategies, tickers, backtest_settings, portfolio, output_dir='results'):
        """
        Initializes the PerformanceReporter.

        Args:
            equity_curve (pd.Series): A Series of the portfolio's total value
                                      over time, with dates as the index.
            benchmark_data (pd.Series): A Series of the benchmark's closing
                                        prices, with dates as the index.
            strategies (list): A list of the strategy objects used in the backtest.
            tickers (list): A list of the ticker symbols used in the backtest.
            backtest_settings (dict): The settings dictionary from the config file.
            portfolio (Portfolio): The portfolio object with trade history.
            output_dir (str): The parent directory to save result folders.
        """
        self.equity_curve = equity_curve
        self.benchmark = benchmark_data
        self.strategies = strategies
        self.tickers = tickers
        self.backtest_settings = backtest_settings
        self.portfolio = portfolio
        self.output_dir = output_dir

        # Align the benchmark to the equity curve's dates
        self.aligned_benchmark = self.benchmark.reindex(self.equity_curve.index).ffill()

        # Calculate returns
        self.portfolio_returns = self.equity_curve.pct_change().fillna(0)
        self.benchmark_returns = self.aligned_benchmark.pct_change().fillna(0)

    def _calculate_max_drawdown(self):
        """
        Calculates the maximum drawdown of the portfolio.
        Drawdown is the percentage decline from a previous peak.
        """
        running_max = self.equity_curve.cummax()
        drawdown = (self.equity_curve - running_max) / running_max
        max_drawdown = drawdown.min()
        return max_drawdown

    def _calculate_sharpe_ratio(self, risk_free_rate=0.0):
        """
        Calculates the Sharpe Ratio.

        Args:
            risk_free_rate (float): The annual risk-free rate.
        """
        if self.portfolio_returns.std() < 1e-8:
            return 0.0
        
        excess_returns = self.portfolio_returns - (risk_free_rate / 252)
        sharpe_ratio = (excess_returns.mean() / excess_returns.std()) * np.sqrt(252)
        return sharpe_ratio

    def generate_report(self):
        """
        Calculates all performance metrics and generates an enhanced text report.
        """
        print("\n--- Generating Performance Report ---")
        
        total_days = len(self.equity_curve)
        start_value = self.equity_curve.iloc[0]
        end_value = self.equity_curve.iloc[-1]
        total_pl = end_value - start_value
        total_return_pct = (end_value / start_value) - 1
        annualized_return = ((1 + total_return_pct) ** (252 / total_days)) - 1 if total_days > 0 else 0.0
        max_drawdown = self._calculate_max_drawdown()
        sharpe_ratio = self._calculate_sharpe_ratio()

        report = [
            f"Backtest Performance Report",
            f"top_n_positions: {self.backtest_settings.get('top_n_positions', 'N/A')}",
            "="*50,
            "Key Performance Metrics",
            "-"*50,
            f"Period: {self.equity_curve.index[0].date()} to {self.equity_curve.index[-1].date()}",
            f"Starting Portfolio Value: ${start_value:,.2f}",
            f"Ending Portfolio Value:   ${end_value:,.2f}",
            f"Total Profit/Loss:        ${total_pl:,.2f}",
            f"Total Return:             {total_return_pct:.2%}",
            "-"*50,
            f"Annualized Return:        {annualized_return:.2%}",
            f"Sharpe Ratio:             {sharpe_ratio:.2f}",
            f"Maximum Drawdown:         {max_drawdown:.2%}",
        ]

        sl_tp_report = []
        sl_config = self.backtest_settings.get('stop_loss', {})
        tp_config = self.backtest_settings.get('take_profit', {})

        if sl_config and sl_config.get('value', 0) != 0:
            sl_type = sl_config.get('type', 'N/A')
            sl_value = sl_config.get('value', 'N/A')
            sl_tp_report.append(f"  Stop Loss: {sl_type} at {sl_value}")

        if tp_config and tp_config.get('value', 0) != 0:
            tp_type = tp_config.get('type', 'N/A')
            tp_value = tp_config.get('value', 'N/A')
            sl_tp_report.append(f"  Take Profit: {tp_type} at {tp_value}")

        if sl_tp_report:
            report.append("\n" + "="*50)
            report.append("Risk Management Parameters")
            report.append("="*50)
            report.extend(sl_tp_report)

        report.append("\n" + "="*50)
        report.append("Strategy Parameters")
        report.append("="*50)
        for strategy in self.strategies:
            report.append(f"--- Strategy: {strategy.__class__.__name__} ---")
            params = strategy.get_params()
            for param, value in params.items():
                report.append(f"  {param}: {value}")
        
        report.append("\n" + "="*50)
        report.append(f"Tickers Used in Simulation ({len(self.tickers)})")
        report.append("="*50)
        
        ticker_lines = []
        line_length = 10
        for i in range(0, len(self.tickers), line_length):
             ticker_lines.append("  " + ", ".join(self.tickers[i:i+line_length]))
        report.extend(ticker_lines)
        report.append("="*50)
        
        report_str = "\n".join(report)
        
        print(report_str)

        filename = 'performance_report.txt'
        file_path = os.path.join(self.output_dir, filename)
        with open(file_path, 'w') as f:
            f.write(report_str)
        print(f"Report saved to {file_path}")

    def generate_metrics_file(self):
        """Generates the performance metrics file."""
        print("\n--- Generating Performance Metrics File ---")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'performance_metrics_{timestamp}.txt'
        file_path = os.path.join(self.output_dir, filename)

        with open(file_path, 'w') as f:
            f.write("Performance Metrics\n")
            f.write("="*50 + "\n\n")

            # 1. Total number of tickers bought and sold
            total_tickers_traded = len(self.portfolio.trade_history)
            f.write(f"Total number of tickers traded: {total_tickers_traded}\n\n")

            # 2. Top 20 earning tickers
            ticker_pnl = {ticker: sum(trade['pnl'] for trade in trades) for ticker, trades in self.portfolio.trade_history.items()}
            
            top_earners = sorted(ticker_pnl.items(), key=lambda item: item[1], reverse=True)[:20]
            top_losers = sorted(ticker_pnl.items(), key=lambda item: item[1])[:20]

            f.write("Top 20 Earning Tickers\n")
            f.write("-" * 50 + "\n")
            f.write("{:<5} {:<10} {:<15} {:<50}\n".format("Nr.", "Ticker", "Total P/L", "Date Held (P/L)"))
            f.write("-" * 50 + "\n")
            for i, (ticker, pnl) in enumerate(top_earners):
                date_held_str = ", ".join([f"{trade['entry_date'].strftime('%d/%m/%Y')} - {trade['exit_date'].strftime('%d/%m/%Y')} (${trade['pnl']:.2f})" for trade in self.portfolio.trade_history[ticker]])
                f.write("{:<5} {:<10} ${:<14.2f} {:<50}\n".format(i + 1, ticker.upper(), pnl, date_held_str))
            
            f.write("\n\n")

            # 3. Top 20 losing tickers
            f.write("Top 20 Losing Tickers\n")
            f.write("-" * 50 + "\n")
            f.write("{:<5} {:<10} {:<15} {:<50}\n".format("Nr.", "Ticker", "Total P/L", "Date Held (P/L)"))
            f.write("-" * 50 + "\n")
            for i, (ticker, pnl) in enumerate(top_losers):
                date_held_str = ", ".join([f"{trade['entry_date'].strftime('%d/%m/%Y')} - {trade['exit_date'].strftime('%d/%m/%Y')} (${trade['pnl']:.2f})" for trade in self.portfolio.trade_history[ticker]])
                f.write("{:<5} {:<10} ${:<14.2f} {:<50}\n".format(i + 1, ticker.upper(), pnl, date_held_str))

        print(f"Metrics file saved to {file_path}")

    def plot_performance(self):
        """
        Generates and saves a plot of portfolio value vs. benchmark.
        """
        normalized_benchmark = (self.aligned_benchmark / self.aligned_benchmark.iloc[0]) * self.equity_curve.iloc[0]

        plt.style.use('seaborn-v0_8-darkgrid')
        fig, ax = plt.subplots(figsize=(14, 8))
        
        ax.plot(self.equity_curve.index, self.equity_curve, label='Portfolio', color='royalblue', lw=2)
        ax.plot(normalized_benchmark.index, normalized_benchmark, label='Benchmark (SPY)', color='gray', linestyle='--', lw=2)

        ax.set_title(f'Portfolio Performance vs. Benchmark', fontsize=16, pad=20)
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Portfolio Value ($)', fontsize=12)
        ax.legend(fontsize=12)
        fig.autofmt_xdate()
        plt.grid(True)
        plt.tight_layout()

        filename = 'performance_chart.png'
        file_path = os.path.join(self.output_dir, filename)
        plt.savefig(file_path, dpi=300)
        print(f"Chart saved to {file_path}")
        plt.close()