import pandas as pd
import ta

df = pd.read_csv('sol_1yr_5m.csv')
df['ts'] = pd.to_datetime(df['ts'])

# Resample to 4H
df_4h = df.resample('4h', on='ts').agg({
    'o': 'first', 'h': 'max', 'l': 'min', 'c': 'last', 'v': 'sum'
}).dropna().reset_index()

# 4H Macro Indicators
df_4h['ema_50'] = ta.trend.EMAIndicator(df_4h['c'], window=50).ema_indicator()
df_4h['ema_200'] = ta.trend.EMAIndicator(df_4h['c'], window=200).ema_indicator()
df_4h['rsi'] = ta.momentum.RSIIndicator(df_4h['c'], window=14).rsi()

FEE = 0.0004 
LEVERAGE = 3 # Safe Leverage
INITIAL = 360.0

bal = INITIAL
pos = 0 
entry = 0
trades = 0
wins = 0
max_dd = 0
peak = bal

for i in range(200, len(df_4h)):
    curr = df_4h.iloc[i-1]
    prev = df_4h.iloc[i-2]
    price = df_4h.iloc[i]['o']
    
    # 🟢 BUY: Macro Uptrend (EMA50 > EMA200) + RSI Pullback (< 45)
    if pos == 0:
        if curr['ema_50'] > curr['ema_200'] and curr['rsi'] < 40 and prev['rsi'] >= 40:
            pos = 1
            entry = price
            size = bal * LEVERAGE
            bal -= (size * FEE)
            trades += 1
            
        # 🔴 SHORT: Macro Downtrend (EMA50 < EMA200) + RSI Rally (> 60)
        elif curr['ema_50'] < curr['ema_200'] and curr['rsi'] > 60 and prev['rsi'] <= 60:
            pos = -1
            entry = price
            size = bal * LEVERAGE
            bal -= (size * FEE)
            trades += 1
            
    elif pos == 1:
        profit = (price - entry) / entry
        if profit >= 0.05: # 5% Market move = 15% ROI
            bal += (size * profit) - (size * FEE)
            wins += 1; pos = 0
        elif profit <= -0.03: # 3% Stop Loss
            bal += (size * profit) - (size * FEE)
            pos = 0
            
    elif pos == -1:
        profit = (entry - price) / entry
        if profit >= 0.05:
            bal += (size * profit) - (size * FEE)
            wins += 1; pos = 0
        elif profit <= -0.03:
            bal += (size * profit) - (size * FEE)
            pos = 0
            
    if bal > peak: peak = bal
    dd = (bal - peak) / peak
    if dd < max_dd: max_dd = dd

print("\n--- 4H MACRO TREND + 3x LEVERAGE (The Salary Maker) ---")
print(f"Trades: {trades}")
print(f"Win Rate: {(wins/trades)*100 if trades > 0 else 0:.1f}%")
print(f"Final Balance: ${bal:.2f}")
print(f"ROI: {((bal-INITIAL)/INITIAL)*100:.2f}%")
print(f"Max DD: {max_dd*100:.2f}%")
