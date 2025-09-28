# FILE: run_optimizer.py

import yaml
import itertools
import traceback
from backtest import Backtest, BacktestLogger

def generate_strategy_combinations(strategy_grid):
    """
    Generates all possible combinations of strategy parameters from the grid.
    
    Args:
        strategy_grid (list): The list of strategy configurations from the optimizer file.

    Returns:
        A generator that yields each unique combination of strategies.
    """
    # Extract parameter grids for each strategy
    strategy_param_options = []
    for strategy_config in strategy_grid:
        if not strategy_config.get('enabled', True):
            continue
            
        param_grid = strategy_config['params']
        # Get all combinations of parameters for a single strategy
        keys, values = zip(*param_grid.items())
        param_combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
        
        # Store the strategy name with each of its parameter combinations
        strategy_param_options.append([
            {'name': strategy_config['name'], 'params': p} for p in param_combinations
        ])

    # Generate combinations across all strategies
    if not strategy_param_options:
        yield []
    else:
        for combination in itertools.product(*strategy_param_options):
            yield list(combination)

def run_optimizer(config_path):
    """
    Orchestrates the parameter grid search optimization process.
    """
    print(f"--- Loading Optimizer Configuration from '{config_path}' ---")
    with open(config_path, 'r') as f:
        optimizer_config = yaml.safe_load(f)

    # --- Initialize Components ---
    base_config = {
        'backtest_settings': optimizer_config['backtest_settings'],
        'tickers': optimizer_config['tickers']
    }
    strategy_grid = optimizer_config['strategy_grid']
    
    # Generate all unique combinations of strategies and their parameters
    all_combinations = list(generate_strategy_combinations(strategy_grid))
    total_runs = len(all_combinations)
    
    print(f"\nGenerated {total_runs} unique backtest configurations to run.")
    
    # Initialize the master logger once for all backtests
    master_logger = BacktestLogger()

    # --- Run Backtests for Each Combination ---
    for i, strategy_combination in enumerate(all_combinations):
        run_number = i + 1
        print("\n" + "="*80)
        print(f"--- Running Backtest {run_number} of {total_runs} ---")
        
        # Create a deep copy of the base config and add the current strategy combo
        current_config = base_config.copy()
        current_config['strategies'] = strategy_combination
        
        # Create a unique config name for logging purposes
        config_name_parts = []
        for strat in strategy_combination:
            params_str = "_".join([f"{k}{v}" for k, v in strat['params'].items()])
            config_name_parts.append(f"{strat['name']}({params_str})")
        config_identifier = "+".join(config_name_parts)
        
        print(f"Config: {config_identifier}")

        try:
            # Instantiate and run the backtest with the current configuration
            backtest = Backtest(config=current_config)
            backtest.run(logger=master_logger, config_filename=config_identifier)
            
        except Exception as e:
            print(f"\nERROR during backtest run {run_number} ({config_identifier}).")
            print(f"Error details: {e}")
            traceback.print_exc()
            print("-" * 80)

    print("\n" + "="*80)
    print("--- Optimizer Run Finished ---")
    print(f"Completed {total_runs} backtests. Results logged in 'master_backtest_log.csv'.")

if __name__ == '__main__':
    # The optimizer will always use this specific config file name.
    optimizer_config_file = 'optimizer_config.yaml'
    run_optimizer(optimizer_config_file)
