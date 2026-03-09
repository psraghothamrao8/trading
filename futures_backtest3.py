import pandas as pd
import ta
import numpy as np

df = pd.read_csv('sol_1yr_5m.csv')
df['ts'] = pd.to_datetime(df['ts'])

# Resample to 1H
df_1h = df.resample('1h', on='ts').agg({
    'o': 'first', 'h': 'max', 'l': 'min', 'c': 'last', 'v': 'sum'
}).dropna().reset_index()

# 1H Indicators
df_1h['rsi'] = ta.momentum.RSIIndicator(df_1h['c'], window=14).rsi()
df_1h['ema_200'] = ta.trend.EMAIndicator(df_1h['c'], window=200).ema_indicator()
df_1h['atr'] = ta.volatility.AverageTrueRange(df_1h['h'], df_1h['l'], df_1h['c'], window=14).average_true_range()

FEE = 0.0004 
LEVERAGE = 3 # 3x Leverage
INITIAL = 360.0

bal = INITIAL
pos = 0 # 1=Long, -1=Short
entry = 0
trades = 0
wins = 0
max_dd = 0
peak = bal

for i in range(200, len(df_1h)):
    curr = df_1h.iloc[i-1]
    price = df_1h.iloc[i]['o']
    
    bull_market = curr['c'] > curr['ema_200']
    bear_market = curr['c'] < curr['ema_200']
    
    if pos == 0:
        # Long: Bull market + RSI Oversold (< 35)
        if bull_market and curr['rsi'] < 35:
            pos = 1
            entry = price
            size = bal * LEVERAGE
            bal -= (size * FEE)
            # TP = 3%, SL = 1.5% (2:1 Ratio)
            tp_p = entry * 1.03
            sl_p = entry * 0.985
            trades += 1
            
        # Short: Bear market + RSI Overbought (> 65)
        elif bear_market and curr['rsi'] > 65:
            pos = -1
            entry = price
            size = bal * LEVERAGE
            bal -= (size * FEE)
            tp_p = entry * 0.97
            sl_p = entry * 1.015
            trades += 1
    elif pos == 1:
        if price >= tp_p:
            bal += (size * 0.03) - (size * FEE)
            wins += 1; pos = 0
        elif price <= sl_p:
            bal += (size * -0.015) - (size * FEE)
            pos = 0
    elif pos == -1:
        if price <= tp_p:
            bal += (size * 0.03) - (size * FEE)
            wins += 1; pos = 0
        elif price >= sl_p:
            bal += (size * -0.015) - (size * FEE)
            pos = 0
            
    if bal > peak: peak = bal
    dd = (bal - peak) / peak
    if dd < max_dd: max_dd = dd

print("\n--- 1H Long/Short Mean Reversion (3x Leverage) ---")
print(f"Trades: {trades}")
print(f"Win Rate: {(wins/trades)*100 if trades > 0 else 0:.1f}%")
print(f"Final Balance: ${bal:.2f}")
print(f"ROI: {((bal-INITIAL)/INITIAL)*100:.2f}%")
print(f"Max DD: {max_dd*100:.2f}%")
