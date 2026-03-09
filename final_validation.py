import pandas as pd
import ta
import numpy as np
import os

# Configuration
SYMBOL = 'SOL/USDT'
TIMEFRAME = '4h'
INITIAL_USD = 360.0
LEVERAGE = 3
FEE = 0.0004
TARGET_MOVE = 0.04
STOP_LOSS = -0.02

def validate():
    if not os.path.exists('sol_1yr_5m.csv'):
        print("Data file missing. Run previous fetch scripts first.")
        return

    # 1. Load and Resample Data
    df_raw = pd.read_csv('sol_1yr_5m.csv')
    df_raw['ts'] = pd.to_datetime(df_raw['ts'])
    df = df_raw.resample('4h', on='ts').agg({
        'o': 'first', 'h': 'max', 'l': 'min', 'c': 'last', 'v': 'sum'
    }).dropna().reset_index()

    # 2. Indicators
    df['ema_50'] = ta.trend.EMAIndicator(df['c'], window=50).ema_indicator()
    df['ema_200'] = ta.trend.EMAIndicator(df['c'], window=200).ema_indicator()
    df['rsi'] = ta.momentum.RSIIndicator(df['c'], window=14).rsi()

    # 3. Simulation
    bal = INITIAL_USD
    pos = 0 # 1=Long, -1=Short
    entry = 0
    trades = 0
    wins = 0
    peak = bal
    max_dd = 0

    for i in range(200, len(df)):
        curr = df.iloc[i-1]
        prev = df.iloc[i-2]
        price = df.iloc[i]['o']
        
        # BUY/SHORT Condition
        if pos == 0:
            bull = curr['ema_50'] > curr['ema_200']
            bear = curr['ema_50'] < curr['ema_200']
            
            # Long: Bull Market + RSI Pullback
            if bull and curr['rsi'] < 40 and prev['rsi'] >= 40:
                pos = 1
                entry = price
                size = bal * LEVERAGE
                bal -= (size * FEE)
                trades += 1
            # Short: Bear Market + RSI Rally
            elif bear and curr['rsi'] > 60 and prev['rsi'] <= 60:
                pos = -1
                entry = price
                size = bal * LEVERAGE
                bal -= (size * FEE)
                trades += 1
        
        # EXIT Condition
        else:
            if pos == 1:
                profit_pct = (price - entry) / entry
                if profit_pct >= TARGET_MOVE or profit_pct <= STOP_LOSS:
                    bal += (size * profit_pct) - (size * FEE)
                    if profit_pct > 0: wins += 1
                    pos = 0
            elif pos == -1:
                profit_pct = (entry - price) / entry
                if profit_pct >= TARGET_MOVE or profit_pct <= STOP_LOSS:
                    # In short, profit is positive if price < entry.
                    # Our formula (entry-price)/entry handles this.
                    # However, if profit_pct is calculated as (entry - price) / entry
                    # a drop from 100 to 96 is (100-96)/100 = 0.04 (Profit)
                    # a rise from 100 to 102 is (100-102)/100 = -0.02 (Loss)
                    bal += (size * profit_pct) - (size * FEE)
                    if profit_pct > 0: wins += 1
                    pos = 0

        if bal > peak: peak = bal
        dd = (bal - peak) / peak
        if dd < max_dd: max_dd = dd

    print(f"--- FINAL 1-YEAR VALIDATION: {SYMBOL} 4H ---")
    print(f"Initial: ${INITIAL_USD:.2f} | Final: ${bal:.2f}")
    print(f"Total ROI: {((bal-INITIAL_USD)/INITIAL_USD)*100:.2f}%")
    print(f"Win Rate: {(wins/trades)*100 if trades > 0 else 0:.1f}% ({wins}/{trades})")
    print(f"Max Drawdown: {max_dd*100:.2f}%")

validate()
