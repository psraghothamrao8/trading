import pandas as pd
import ta
import numpy as np

df = pd.read_csv('sol_1yr_5m.csv')
df['ts'] = pd.to_datetime(df['ts'])

# Resample to 1H
df_1h = df.resample('1h', on='ts').agg({
    'o': 'first', 'h': 'max', 'l': 'min', 'c': 'last', 'v': 'sum'
}).dropna().reset_index()

df_1h['ema_200'] = ta.trend.EMAIndicator(df_1h['c'], window=200).ema_indicator()
df_1h['rsi'] = ta.momentum.RSIIndicator(df_1h['c'], window=14).rsi()

FEE = 0.0004 
LEVERAGE = 5 # 5x Leverage
INITIAL = 360.0

bal = INITIAL
pos = 0 
entry = 0
trades = 0
wins = 0
max_dd = 0
peak = bal

for i in range(200, len(df_1h)):
    curr = df_1h.iloc[i-1]
    prev = df_1h.iloc[i-2]
    price = df_1h.iloc[i]['o']
    
    # 🟢 BUY: Deep Drop in Uptrend
    if pos == 0:
        if curr['c'] > curr['ema_200'] and curr['rsi'] < 30:
            pos = 1
            entry = price
            size = bal * LEVERAGE
            bal -= (size * FEE)
            trades += 1
            
        # 🔴 SHORT: Exhaustion in Downtrend
        elif curr['c'] < curr['ema_200'] and curr['rsi'] > 70:
            pos = -1
            entry = price
            size = bal * LEVERAGE
            bal -= (size * FEE)
            trades += 1
            
    elif pos == 1:
        # Exit Long: Target 1% (5% leveraged) OR Time/RSI Stop
        profit = (price - entry) / entry
        if profit >= 0.01:
            bal += (size * profit) - (size * FEE)
            wins += 1; pos = 0
        elif profit <= -0.015: # Stop Loss 1.5%
            bal += (size * profit) - (size * FEE)
            pos = 0
            
    elif pos == -1:
        profit = (entry - price) / entry
        if profit >= 0.01:
            bal += (size * profit) - (size * FEE)
            wins += 1; pos = 0
        elif profit <= -0.015:
            bal += (size * profit) - (size * FEE)
            pos = 0
            
    if bal > peak: peak = bal
    dd = (bal - peak) / peak
    if dd < max_dd: max_dd = dd

print("\n--- 1H Sniper L/S (5x Leverage) ---")
print(f"Trades: {trades}")
print(f"Win Rate: {(wins/trades)*100 if trades > 0 else 0:.1f}%")
print(f"Final Balance: ${bal:.2f}")
print(f"ROI: {((bal-INITIAL)/INITIAL)*100:.2f}%")
print(f"Max DD: {max_dd*100:.2f}%")
