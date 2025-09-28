# webapp.py
import streamlit as st
import yaml
import os
import traceback
from backtest import Backtest, BacktestLogger
from datetime import datetime

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="v1engine Backtester")
st.title("📈 v1engine Trading Strategy Backtester")

# --- Sidebar for User Inputs ---
st.sidebar.header("Backtest Configuration")

# Load available config files to populate default settings
config_files = sorted([f for f in os.listdir('.') if f.startswith('config') and f.endswith('.yaml')])
selected_config_file = st.sidebar.selectbox("Load Base Configuration", config_files)

with open(selected_config_file, 'r') as f:
    base_config = yaml.safe_load(f)

# --- UI Widgets to Set Parameters ---
settings = base_config['backtest_settings']
start_date = st.sidebar.date_input("Start Date", value=datetime.strptime(settings['start_date'], '%Y-%m-%d'))
end_date = st.sidebar.date_input("End Date", value=datetime.strptime(settings['end_date'], '%Y-%m-%d'))
initial_cash = st.sidebar.number_input("Initial Cash", value=settings['initial_cash'], step=10000.0)
top_n = st.sidebar.number_input("Top N Positions", value=settings.get('top_n_positions', 5), min_value=1, step=1)

# Dynamically list available strategy files
strategy_files = [f for f in os.listdir('.') if f.startswith('strategy_') and f.endswith('.py')]
available_strategies = [s.replace('strategy_', '').replace('.py', '') for s in strategy_files]
# Let user select multiple strategies
selected_strategies = st.sidebar.multiselect("Select Strategies to Run", available_strategies, default=['bb', 'macd'])

# --- Main Execution ---
if st.sidebar.button("🚀 Run Backtest"):
    if not selected_strategies:
        st.error("Please select at least one strategy.")
    else:
        # <<< START: This is the new, improved logic >>>

        # This dictionary maps the user-friendly names from the multiselect
        # widget to the exact Python class names found in your strategy files.
        STRATEGY_CLASS_MAP = {
            'bb': 'BollingerStrategy',
            'bb2': 'Bollinger2Strategy',
            'bbXrsi': 'BollingerRsiStrategy',
            'bbXrsi2': 'BollingerRsi2Strategy',
            'bbXrsi3': 'BollingerRsi3Strategy',
            'fibb': 'FibonacciStrategy',
            'keltner': 'KeltnerStrategy',
            'keltner2': 'Keltner2Strategy',
            'keltner3': 'Keltner3Strategy',
            'macd': 'MacdStrategy',
            'macd2': 'Macd2Strategy',
            'macd3': 'Macd3Strategy',
            'momentum': 'MomentumStrategy',
            'momentum2': 'Momentum2Strategy',
            'momentum3': 'Momentum3Strategy',
            'rsi': 'RsiStrategy',
            'rsi2': 'Rsi2Strategy',
            'smaXrsi': 'SmaRsiStrategy',
            'smaXrsi2': 'SmaRsi2Strategy',
            'smaXrsi3': 'SmaRsi3Strategy',
            'stoch': 'StochasticStrategy',
            'stoch2': 'Stochastic2Strategy',
            'stochSpread': 'StochSpreadStrategy',
            'zscore': 'ZScoreStrategy'
            # Add any other strategies here as you create them
        }

        # 1. Dynamically construct the config dictionary from user inputs
        run_config = {
            'backtest_settings': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'initial_cash': initial_cash,
                'top_n_positions': top_n,
                'benchmark_ticker': 'SPY',
                'stop_loss': {},
                'take_profit': {}
            },
            'tickers': base_config['tickers'],
            'strategies': []
        }
        
        # 2. Add selected strategy configurations using the mapping
        for short_name in selected_strategies:
            if short_name in STRATEGY_CLASS_MAP:
                class_name = STRATEGY_CLASS_MAP[short_name]
                run_config['strategies'].append({
                    'name': class_name, 
                    'params': {} # Note: We are not setting params in this UI yet
                })
            else:
                st.warning(f"Warning: Strategy '{short_name}' is selected but not found in the mapping dictionary. It will be skipped.")
        
        # <<< END: This is the new, improved logic >>>

        st.info("Configuration created. Running simulation... This may take a moment.")
        
        with st.spinner('Executing backtest...'):
            try:
                master_logger = BacktestLogger()
                backtest_instance = Backtest(config=run_config)
                
                backtest_instance.run(logger=master_logger, config_filename="streamlit_run")
                output_dir = backtest_instance.output_dir

                st.success(f"Backtest complete! Results from folder: `{output_dir}`")

                col1, col2 = st.columns(2)

                with col1:
                    st.header("Performance Chart")
                    chart_path = os.path.join(output_dir, 'performance_chart.png')
                    if os.path.exists(chart_path):
                        st.image(chart_path)
                    else:
                        st.warning("Performance chart not found.")
                
                with col2:
                    st.header("Performance Report")
                    report_path = os.path.join(output_dir, 'performance_report.txt')
                    if os.path.exists(report_path):
                        with open(report_path, 'r') as f:
                            st.text(f.read())
                    else:
                        st.warning("Performance report not found.")

            except Exception as e:
                st.error(f"An error occurred during the backtest: {e}")
                st.code(traceback.format_exc())