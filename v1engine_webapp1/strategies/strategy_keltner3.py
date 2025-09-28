import pandas as pd
from strategy_base import Strategy

class Keltner3Strategy(Strategy):
    """
    Implements a Keltner Channel breakout strategy.
    Method 3: The raw buy signal is an ATR-based Z-Score: (Close - EMA) / ATR.
    """
    def __init__(self, data_handler, ema_period=20, atr_multiplier=2.0, atr_period=14):
        """
        Initializes the KeltnerStrategy.
        """
        super().__init__(data_handler)
        self.period = ema_period
        self.atr_multiplier = atr_multiplier
        self.atr_period = atr_period

    def generate_signals(self):
        """
        Generates buy/sell signals. The raw buy signal is the ATR-based Z-Score.
        """
        signals_df = pd.DataFrame()
        for ticker in self.tickers:
            hist_data = self.data_handler.data.get(ticker)
            if hist_data is None or len(hist_data) < self.period:
                continue

            # Calculate Keltner Channels
            ema = hist_data['close'].ewm(span=self.period, adjust=False).mean()
            high_low = hist_data['high'] - hist_data['low']
            high_close = abs(hist_data['high'] - hist_data['close'].shift())
            low_close = abs(hist_data['low'] - hist_data['close'].shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = tr.ewm(span=self.atr_period, adjust=False).mean()
            
            upper_band = ema + (atr * self.atr_multiplier)

            # Create signals
            signals = pd.Series(0.0, index=hist_data.index, name=ticker)

            # --- MODIFICATION START (METHOD 3) ---
            # Buy signal: Price crosses above the upper Keltner Channel.
            buy_mask = (hist_data['close'] > upper_band) & (hist_data['close'].shift(1) <= upper_band.shift(1))
            
            # The raw signal is the distance from the EMA, measured in ATR units.
            # Avoid division by zero.
            valid_atr = atr[buy_mask] > 0
            if valid_atr.any():
                signal_mask = buy_mask & (atr > 0)
                signals[signal_mask] = (hist_data['close'][signal_mask] - ema[signal_mask]) / atr[signal_mask]

            # Sell signal: Price crosses below the EMA.
            signals[(hist_data['close'] < ema) & (hist_data['close'].shift(1) >= ema.shift(1))] = -1
            # --- MODIFICATION END ---
            
            signals_df = pd.concat([signals_df, signals], axis=1)

        return signals_df.fillna(0)