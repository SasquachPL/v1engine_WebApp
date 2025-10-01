import streamlit as st
import pandas as pd
import yaml
import os
import sys
from datetime import datetime

# --- Add Project to Python Path ---
# This allows us to import modules from your project (core, strategies, etc.)
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_path)

# --- Import Your Backtesting Components ---
# We wrap this in a try-except block to guide the user if something is wrong
try:
    from backtest import Backtest, BacktestLogger, STRATEGY_MAPPING
except ImportError as e:
    st.error(f"Failed to import a necessary component from your project: {e}")
    st.info("Please make sure 'webapp.py' is in the root directory of your 'v1engine' project.")
    st.stop()


# --- Page Configuration ---
st.set_page_config(
    page_title="V1Engine Backtester",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📈 V1Engine Multi-Strategy Backtester")

st.subheader("🕵️‍♂️ File Content Diagnostic")
spy_path = os.path.join(project_path, 'data', 'daily_spy.csv')
if not os.path.exists(spy_path):
    st.error(f"CRITICAL: The file 'daily_spy.csv' does NOT exist at the expected path: {spy_path}")
else:
    try:
        with open(spy_path, 'r') as f:
            file_content = f.read(500) # Read the first 500 characters
        st.text("Contents of 'daily_spy.csv':")
        st.code(file_content, language="text")
        if "git-lfs" in file_content:
            st.warning("‼️ This looks like a Git LFS pointer file, not a real CSV. This is the cause of the error.")
        else:
            st.success("✅ The file appears to be a valid CSV.")
    except Exception as e:
        st.error(f"Could not read the file 'daily_spy.csv'. Error: {e}")


st.write("Configure your simulation parameters in the sidebar on the left and click 'Run Backtest' to see the results.")

# --- Helper Function to get Ticker Symbols ---
@st.cache_data
def get_available_tickers():
    """Scans the data directory to find all available CSV files."""
    data_dir = os.path.join(project_path, 'data')
    if not os.path.exists(data_dir):
        return []
    tickers = [f.replace('daily_', '').replace('.csv', '').upper() for f in os.listdir(data_dir) if f.startswith('daily_') and f.endswith('.csv')]
    return sorted(tickers)

# --- Sidebar for User Inputs ---
with st.sidebar:
    st.header("⚙️ Simulation Configuration")

    # --- Section 1: Core Backtest Settings ---
    st.subheader("Backtest Settings")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=datetime(2022, 1, 1))
    with col2:
        end_date = st.date_input("End Date", value=datetime(2023, 12, 31))

    initial_cash = st.number_input("Initial Cash ($)", min_value=1000, value=100000, step=1000)
    # --- MODIFIED WIDGETS ---
    top_n = st.number_input("Top N Positions to Hold", min_value=1, value=10, step=1, help="The maximum number of assets to hold at any time based on signal strength.")
    rebalancing_freq = st.number_input("Rebalancing Frequency (Days)", min_value=1, value=1, step=1, help="How often to re-evaluate and trade the portfolio. 1 = Daily.")

    st.subheader("Trading Costs")
    commission = st.number_input("Commission per Trade ($)", min_value=0.0, value=1.0, step=0.01)
    slippage = st.number_input("Slippage (%)", min_value=0.0, value=0.01, step=0.001, format="%.3f", help="The percentage difference between the expected and actual execution price.")

    # --- Section 2: Ticker Selection ---
    st.subheader("Asset Universe")
    available_tickers = get_available_tickers()
    if not available_tickers:
        st.warning("No data files found in the 'data/' directory.")
        selected_tickers = []
    else:
        try:
            with open('config1.yaml', 'r') as f:
                default_config = yaml.safe_load(f)
                default_tickers = [t.upper() for t in default_config.get('tickers', [])]
        except FileNotFoundError:
            default_tickers = available_tickers[:20]

        selected_tickers = st.multiselect(
            "Select Tickers to Trade",
            options=available_tickers,
            default=default_tickers,
            help="Choose the assets to include in the simulation."
        )

    # --- Section 3: Strategy Selection & Configuration ---
    st.subheader("Strategy Configuration")
    strategy_names = list(STRATEGY_MAPPING.keys())
    selected_strategy_names = st.multiselect(
        "Select Strategies",
        options=strategy_names,
        default=['MomentumStrategy', 'RsiStrategy']
    )

    strategy_configs = []
    # --- ALL SLIDERS REPLACED WITH NUMBER INPUTS ---
    for strat_name in selected_strategy_names:
        with st.expander(f"Parameters for {strat_name}", expanded=True):
            params = {}
            # Momentum Group
            if 'Momentum' in strat_name:
                params['momentum_window'] = st.number_input(f"Momentum Window", min_value=1, value=10, step=1, key=f"{strat_name}_mw")
            # RSI & BollingerRSI Group
            elif 'Rsi' in strat_name and 'Sma' not in strat_name:
                if 'BollingerRsi' in strat_name:
                    params['bband_period'] = st.number_input("BBand Period", min_value=1, value=20, step=1, key=f"{strat_name}_bb_p")
                    params['bband_std_dev'] = st.number_input("BBand Std Dev", min_value=0.1, value=2.0, step=0.1, key=f"{strat_name}_bb_std")
                params['rsi_period'] = st.number_input(f"RSI Period", min_value=1, value=14, step=1, key=f"{strat_name}_rsi_p")
                params['rsi_oversold_threshold'] = st.number_input(f"RSI Oversold", min_value=0, max_value=100, value=30, step=1, key=f"{strat_name}_rsi_os")
                params['rsi_overbought_threshold'] = st.number_input(f"RSI Overbought", min_value=0, max_value=100, value=70, step=1, key=f"{strat_name}_rsi_ob")
            # SMA Crossover + RSI Group
            elif 'SmaRsi' in strat_name:
                params['short_window'] = st.number_input(f"Short SMA Window", min_value=1, value=50, step=1, key=f"{strat_name}_sma_s")
                params['long_window'] = st.number_input(f"Long SMA Window", min_value=1, value=200, step=1, key=f"{strat_name}_sma_l")
                params['rsi_period'] = st.number_input(f"RSI Period", min_value=1, value=14, step=1, key=f"{strat_name}_rsi_p")
                params['rsi_threshold'] = st.number_input(f"RSI Threshold", min_value=0, max_value=100, value=50, step=1, key=f"{strat_name}_rsi_t")
            # Keltner Channel Group
            elif 'Keltner' in strat_name:
                params['ema_period'] = st.number_input("EMA Period", min_value=1, value=20, step=1, key=f"{strat_name}_kelt_ema")
                params['atr_multiplier'] = st.number_input("ATR Multiplier", min_value=0.1, value=2.0, step=0.1, key=f"{strat_name}_kelt_atr_m")
                params['atr_period'] = st.number_input("ATR Period", min_value=1, value=14, step=1, key=f"{strat_name}_kelt_atr_p")
            # Bollinger Bands Group
            elif strat_name in ['BollingerStrategy', 'Bollinger2Strategy']:
                params['bband_period'] = st.number_input("BBand Period", min_value=1, value=20, step=1, key=f"{strat_name}_bb_p")
                params['bband_std_dev'] = st.number_input("BBand Std Dev", min_value=0.1, value=2.0, step=0.1, key=f"{strat_name}_bb_std")
            # MACD Group
            elif 'Macd' in strat_name:
                params['short_ema_period'] = st.number_input("Short EMA Period", min_value=1, value=12, step=1, key=f"{strat_name}_macd_s")
                params['long_ema_period'] = st.number_input("Long EMA Period", min_value=1, value=26, step=1, key=f"{strat_name}_macd_l")
                params['signal_period'] = st.number_input("Signal Line Period", min_value=1, value=9, step=1, key=f"{strat_name}_macd_sig")
            # Stochastic Group
            elif 'Stoch' in strat_name:
                params['k_period'] = st.number_input("%K Period", min_value=1, value=14, step=1, key=f"{strat_name}_stoch_k")
                params['d_period'] = st.number_input("%D Period", min_value=1, value=3, step=1, key=f"{strat_name}_stoch_d")
                params['oversold_threshold'] = st.number_input("Oversold Threshold", min_value=0, max_value=100, value=20, step=1, key=f"{strat_name}_stoch_os")
                params['overbought_threshold'] = st.number_input("Overbought Threshold", min_value=0, max_value=100, value=80, step=1, key=f"{strat_name}_stoch_ob")
            # Z-Score Strategy
            elif strat_name == 'ZScoreStrategy':
                params['lookback_period'] = st.number_input("Lookback Period", min_value=1, value=20, step=1, key=f"{strat_name}_z_p")
                params['buy_threshold'] = st.number_input("Buy Threshold (Z-Score)", value=-2.0, step=0.1, key=f"{strat_name}_z_buy")
            # Fibonacci Strategy
            elif strat_name == 'FibonacciStrategy':
                params['lookback_period'] = st.number_input("Lookback Period", min_value=1, value=50, step=1, key=f"{strat_name}_fib_p")
            elif strat_name == 'ObvStrategy':
                params['obv_sma_period'] = st.number_input("SMA Period", min_value=1, value=40, step=1, key=f"{strat_name}_obv_p")
            elif strat_name == 'ObvRocStrategy':
                params['roc_period'] = st.number_input("Rate of Change Period", min_value=1, value=10, step=1, key=f"{strat_name}_obv_r")

            strategy_configs.append({'name': strat_name, 'params': params})

    # --- Run Button ---
    run_button = st.button("🚀 Run Backtest", type="primary", use_container_width=True)


# --- Main Area for Displaying Results ---
if run_button:
    if not selected_tickers:
        st.error("Please select at least one ticker.")
    elif not strategy_configs:
        st.error("Please select at least one strategy.")
    else:
        st.session_state.config = {
            'backtest_settings': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'initial_cash': initial_cash,
                'benchmark_ticker': 'SPY',
                'top_n_positions': top_n,
                'rebalancing_frequency': rebalancing_freq,
                'commission_per_trade': commission,
                'slippage_percent': slippage / 100.0,
                'stop_loss': {},
                'take_profit': {},
            },
            'tickers': selected_tickers,
            'strategies': strategy_configs
        }

        with st.spinner("Please wait, the simulation is running... This may take a moment."):
            try:
                data_dir = os.path.join(project_path, 'data')
                master_logger = BacktestLogger()
                backtest = Backtest(config=st.session_state.config, data_path=data_dir)
                backtest.run(logger=master_logger, config_filename="Streamlit_Run")
                st.session_state.backtest_results = backtest
                st.success("Backtest simulation completed successfully!")

            except Exception as e:
                st.error(f"An error occurred during the backtest execution.")
                st.exception(e)
                st.session_state.backtest_results = None

# --- Display results if they exist in the session state ---
if 'backtest_results' in st.session_state and st.session_state.backtest_results:
    results = st.session_state.backtest_results
    output_dir = results.output_dir

    st.header("📊 Performance Results")

    try:
        equity_curve = results.equity_curve
        total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1

        log_df = pd.read_csv('master_backtest_log.csv')
        latest_run_metrics = log_df.iloc[-1]
        sharpe = latest_run_metrics['sharpe_ratio']
        max_drawdown = latest_run_metrics['max_drawdown_pct']

        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Total Return", f"{total_return:.2%}")
        kpi2.metric("Sharpe Ratio", f"{sharpe}")
        kpi3.metric("Max Drawdown", f"{max_drawdown}")

    except Exception as e:
        st.warning(f"Could not calculate all KPIs. The backtest ran, but there was an issue reading the result logs. Error: {e}")

    chart_path = os.path.join(output_dir, 'performance_chart.png')
    report_path = os.path.join(output_dir, 'performance_report.txt')

    tab1, tab2, tab3, tab4 = st.tabs(["Performance Chart", "Detailed Report", "Portfolio Log", "Trade Log"])

    with tab1:
        if os.path.exists(chart_path):
            st.image(chart_path, use_column_width=True)
        else:
            st.warning("Performance chart not found.")

    with tab2:
        if os.path.exists(report_path):
            with open(report_path, 'r') as f:
                st.text(f.read())
        else:
            st.warning("Performance report text file not found.")

    with tab3:
        portfolio_log_path = os.path.join(output_dir, 'portfolio_log.csv')
        if os.path.exists(portfolio_log_path):
            df_port = pd.read_csv(portfolio_log_path)
            st.dataframe(df_port)
        else:
            st.warning("Portfolio log not found.")

    with tab4:
        trades_log_path = os.path.join(output_dir, 'trades_log.csv')
        if os.path.exists(trades_log_path):
            df_trades = pd.read_csv(trades_log_path)
            st.dataframe(df_trades)
        else:
            st.warning("Trades log not found.")