# --- Trading Cost Configuration ---
# This file centralizes all transaction cost parameters for the backtest.

# Set a fixed commission fee for each trade executed.
# For example, 1.0 means $1.00 per trade.
COMMISSION_PER_TRADE = 1.0

# Slippage is the difference between the expected price of a trade and the price
# at which the trade is actually executed. It's often modeled as a percentage
# of the trade price.
# 0.001 represents a slippage of 0.1%.
# For BUY orders, this will increase the effective execution price.
# For SELL orders, this will decrease the effective execution price.
SLIPPAGE_PERCENT = 0.0001
