# FILE: search_backtests.py

import pandas as pd
import argparse

def search_logs(args):
    """
    Searches the master backtest log based on command-line criteria.
    """
    try:
        df = pd.read_csv(args.file)
    except FileNotFoundError:
        print(f"Error: Log file '{args.file}' not found. Please run a backtest first.")
        return

    # Convert percentage and value columns to numeric types for proper sorting/filtering
    df['total_return_numeric'] = df['total_return_pct'].str.rstrip('%').astype(float)
    df['sharpe_ratio'] = pd.to_numeric(df['sharpe_ratio'], errors='coerce')
    df['max_drawdown_numeric'] = df['max_drawdown_pct'].str.rstrip('%').astype(float)

    # --- Apply Filters ---
    if args.strategy:
        df = df[df['strategies_used'].str.contains(args.strategy, case=False, na=False)]
    
    if args.min_sharpe is not None:
        df = df[df['sharpe_ratio'] >= args.min_sharpe]
        
    if args.min_return is not None:
        df = df[df['total_return_numeric'] >= args.min_return]

    # Note: Max Drawdown is negative, so we look for values *greater than* the input
    # e.g., a drawdown of -15% is better (greater) than -25%
    if args.max_drawdown is not None:
        df = df[df['max_drawdown_numeric'] >= args.max_drawdown]

    # --- Sort Results ---
    if args.sort_by:
        sort_col_map = {
            'return': 'total_return_numeric',
            'sharpe': 'sharpe_ratio',
            'date': 'run_timestamp'
        }
        sort_column = sort_col_map.get(args.sort_by, 'run_timestamp')
        df = df.sort_values(by=sort_column, ascending=False)

    # --- Display Results ---
    if df.empty:
        print("No backtests found matching your criteria.")
    else:
        # Select columns to display for a cleaner output
        display_cols = [
            'run_timestamp', 'output_folder', 'config_file', 'total_return_pct',
            'sharpe_ratio', 'max_drawdown_pct', 'strategies_used'
        ]
        print(df[display_cols].to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Search and filter past backtest results.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument(
        '--file', type=str, default='master_backtest_log.csv',
        help='Path to the master log file.'
    )
    parser.add_argument(
        '--strategy', type=str,
        help='Filter by a strategy name (e.g., "RsiStrategy").'
    )
    parser.add_argument(
        '--min-sharpe', type=float,
        help='Show results with a Sharpe Ratio >= VALUE.'
    )
    parser.add_argument(
        '--min-return', type=float,
        help='Show results with a Total Return >= VALUE (e.g., 50 for 50%%).'
    )
    parser.add_argument(
        '--max-drawdown', type=float,
        help='Show results with a Max Drawdown >= VALUE (e.g., -25 for -25%%).'
    )
    parser.add_argument(
        '--sort-by', type=str, choices=['return', 'sharpe', 'date'], default='date',
        help="Sort results by 'return', 'sharpe', or 'date'. Defaults to date."
    )

    args = parser.parse_args()
    search_logs(args)