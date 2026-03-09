import pandas as pd
import ta
import numpy as np

df = pd.read_csv('sol_1yr_5m.csv')
df['ts'] = pd.to_datetime(df['ts'])

# Resample to 4H
df_4h = df.resample('4h', on='ts').agg({
    'o': 'first', 'h': 'max', 'l': 'min', 'c': 'last', 'v': 'sum'
}).dropna().reset_index()

# 4H Indicators
df_4h['ema_20'] = ta.trend.EMAIndicator(df_4h['c'], window=20).ema_indicator()
df_4h['ema_50'] = ta.trend.EMAIndicator(df_4h['c'], window=50).ema_indicator()
df_4h['atr'] = ta.volatility.AverageTrueRange(df_4h['h'], df_4h['l'], df_4h['c'], window=14).average_true_range()

FEE = 0.0004 # Binance Futures VIP 0
LEVERAGE = 2 # Extremely safe 2x Leverage
INITIAL = 360.0

bal = INITIAL
pos = 0 # 1=Long, -1=Short
entry = 0
trades = 0
wins = 0
max_dd = 0
peak = bal

for i in range(50, len(df_4h)):
    curr = df_4h.iloc[i-1]
    prev = df_4h.iloc[i-2]
    price = df_4h.iloc[i]['o']
    
    cross_up = prev['ema_20'] < prev['ema_50'] and curr['ema_20'] > curr['ema_50']
    cross_down = prev['ema_20'] > prev['ema_50'] and curr['ema_20'] < curr['ema_50']
    
    if pos == 0:
        if cross_up:
            pos = 1
            entry = price
            size = bal * LEVERAGE
            bal -= (size * FEE)
            trades += 1
            # Trend following - no TP, dynamic SL
        elif cross_down:
            pos = -1
            entry = price
            size = bal * LEVERAGE
            bal -= (size * FEE)
            trades += 1
    elif pos == 1:
        # Exit Long on Bear Cross
        if cross_down:
            profit_pct = (price - entry) / entry
            bal += (size * profit_pct) - (size * FEE)
            if profit_pct > 0: wins += 1
            # Reverse to Short
            pos = -1
            entry = price
            size = bal * LEVERAGE
            bal -= (size * FEE)
            trades += 1
    elif pos == -1:
        # Exit Short on Bull Cross
        if cross_up:
            profit_pct = (entry - price) / entry
            bal += (size * profit_pct) - (size * FEE)
            if profit_pct > 0: wins += 1
            # Reverse to Long
            pos = 1
            entry = price
            size = bal * LEVERAGE
            bal -= (size * FEE)
            trades += 1
            
    if bal > peak: peak = bal
    dd = (bal - peak) / peak
    if dd < max_dd: max_dd = dd

print("\n--- 4H Continuous Reversal (2x Leverage) ---")
print(f"Trades: {trades}")
print(f"Win Rate: {(wins/trades)*100 if trades > 0 else 0:.1f}%")
print(f"Final Balance: ${bal:.2f}")
print(f"ROI: {((bal-INITIAL)/INITIAL)*100:.2f}%")
print(f"Max DD: {max_dd*100:.2f}%")
