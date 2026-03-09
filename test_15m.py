import pandas as pd
import ta
import numpy as np

print("Loading 1 year of 5m data...")
df_5m = pd.read_csv('sol_1yr_5m.csv')
df_5m['ts'] = pd.to_datetime(df_5m['ts'])
df_5m.set_index('ts', inplace=True)

# Resample to 15m data
print("Resampling to 15m data...")
df_15m = df_5m.resample('15min').agg({
    'o': 'first',
    'h': 'max',
    'l': 'min',
    'c': 'last',
    'v': 'sum'
}).dropna()

df_15m['rsi'] = ta.momentum.RSIIndicator(df_15m['c'], window=14).rsi()
bb = ta.volatility.BollingerBands(df_15m['c'], window=20, window_dev=2.5)
df_15m['bb_l'] = bb.bollinger_lband()
df_15m['ema_200'] = ta.trend.EMAIndicator(df_15m['c'], window=200).ema_indicator()
df_15m = df_15m.reset_index()

FEE = 0.001
INITIAL_USD = 360.0

def test_15m_holy_grail():
    bal = INITIAL_USD
    coin = 0.0
    trades = 0
    wins = 0
    peak_bal = bal
    max_dd = 0.0
    
    for i in range(200, len(df_15m)):
        curr = df_15m.iloc[i-1]
        price = df_15m.iloc[i]['o']
        
        if coin == 0:
            # 🟢 BUY: Panic dip in uptrend or deep panic
            if curr['c'] <= curr['bb_l'] and curr['rsi'] < 30 and curr['c'] > curr['ema_200']:
                coin = (bal * (1-FEE)) / price
                bal = 0.0
                entry = price
                trades += 1
        else:
            profit = (price - entry) / entry
            
            # 🔴 SELL: 1.5% TP or -3% SL
            if profit >= 0.015 or profit <= -0.03 or curr['rsi'] > 70: 
                bal = coin * price * (1-FEE)
                if bal > (INITIAL_USD if trades==1 else prev_bal):
                    wins += 1
                coin = 0.0
                trades += 1
                
        # Drawdown tracking
        curr_val = bal if coin == 0 else bal + (coin * curr['c'] * (1-FEE))
        if curr_val > peak_bal: peak_bal = curr_val
        dd = (curr_val - peak_bal) / peak_bal
        if dd < max_dd: max_dd = dd
        
        prev_bal = bal if coin == 0 else bal + (coin * curr['c'] * (1-FEE))

    final_val = bal + (coin * df_15m.iloc[-1]['c'] * (1-FEE))
    roi = ((final_val - INITIAL_USD) / INITIAL_USD) * 100
    win_rate = (wins / (trades/2) * 100) if trades > 0 else 0
    
    print("\n--- 15M 'Holy Grail' Attempt (Spot) ---")
    print(f"Trades: {trades//2} (Complete rounds)")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Final Balance: ${final_val:.2f}")
    print(f"Total ROI: {roi:.2f}%")
    print(f"Max Drawdown: {max_dd*100:.2f}%")

test_15m_holy_grail()
