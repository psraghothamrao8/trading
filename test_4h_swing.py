import pandas as pd
import ta
import numpy as np

print("Loading 1 year of 5m data...")
df_5m = pd.read_csv('sol_1yr_5m.csv')
df_5m['ts'] = pd.to_datetime(df_5m['ts'])
df_5m.set_index('ts', inplace=True)

# Resample to 4H data for macro reliable mean reversion
print("Resampling to 4h data...")
df_4h = df_5m.resample('4h').agg({
    'o': 'first',
    'h': 'max',
    'l': 'min',
    'c': 'last',
    'v': 'sum'
}).dropna()

df_4h['rsi'] = ta.momentum.RSIIndicator(df_4h['c'], window=14).rsi()
df_4h['ema_200'] = ta.trend.EMAIndicator(df_4h['c'], window=200).ema_indicator()
df_4h = df_4h.reset_index()

FEE = 0.001
INITIAL_USD = 360.0

def test_4h_swing():
    bal = INITIAL_USD
    coin = 0.0
    trades = 0
    wins = 0
    peak_bal = bal
    max_dd = 0.0
    
    for i in range(200, len(df_4h)):
        curr = df_4h.iloc[i-1]
        prev = df_4h.iloc[i-2]
        price = df_4h.iloc[i]['o']
        
        if coin == 0:
            # 🟢 BUY: Deep fear (RSI < 25)
            # Or moderate fear (RSI < 30) but in an uptrend (Price > EMA 200)
            if curr['rsi'] < 25 or (curr['rsi'] < 30 and curr['c'] > curr['ema_200']):
                coin = (bal * (1-FEE)) / price
                bal = 0.0
                entry = price
                trades += 1
        else:
            # 🔴 SELL: RSI recovers to median (55) or TP/SL hit
            profit = (price - entry) / entry
            
            # Dynamic TP/SL or time-based
            if curr['rsi'] > 55 or profit >= 0.05 or profit <= -0.10: # 5% target, 10% hard macro stop
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

    final_val = bal + (coin * df_4h.iloc[-1]['c'] * (1-FEE))
    roi = ((final_val - INITIAL_USD) / INITIAL_USD) * 100
    win_rate = (wins / (trades/2) * 100) if trades > 0 else 0
    
    print("\n--- 4H Swing Trading (Mean Reversion) ---")
    print(f"Trades: {trades//2} (Complete rounds)")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Final Balance: ${final_val:.2f}")
    print(f"Total ROI: {roi:.2f}%")
    print(f"Max Drawdown: {max_dd*100:.2f}%")

test_4h_swing()
