import pandas as pd
import ta
import numpy as np

print("Loading 1 year of 5m data...")
df_5m = pd.read_csv('sol_1yr_5m.csv')
df_5m['ts'] = pd.to_datetime(df_5m['ts'])

# Calculate indicators
df_5m['ema_200'] = ta.trend.EMAIndicator(df_5m['c'], window=200).ema_indicator()
df_5m['rsi'] = ta.momentum.RSIIndicator(df_5m['c'], window=14).rsi()
macd = ta.trend.MACD(df_5m['c'])
df_5m['macd'] = macd.macd()
df_5m['macd_s'] = macd.macd_signal()
df_5m['atr'] = ta.volatility.AverageTrueRange(df_5m['h'], df_5m['l'], df_5m['c'], window=14).average_true_range()

FEE = 0.001
INITIAL_USD = 360.0

def test_breakout():
    bal = INITIAL_USD
    coin = 0.0
    trades = 0
    wins = 0
    peak_bal = bal
    max_dd = 0.0
    
    for i in range(200, len(df_5m)):
        curr = df_5m.iloc[i-1]
        prev = df_5m.iloc[i-2]
        price = df_5m.iloc[i]['o']
        
        if coin == 0:
            # 🟢 BUY: MACD Cross Up + Above EMA 200
            if (prev['macd'] < prev['macd_s']) and (curr['macd'] > curr['macd_s']) and curr['c'] > curr['ema_200']:
                coin = (bal * (1-FEE)) / price
                bal = 0.0
                entry = price
                # TP 1%, SL 0.5% (High Frequency Scalp)
                tp_p = entry * 1.01
                sl_p = entry * 0.995
                trades += 1
        else:
            if price >= tp_p:
                bal = coin * price * (1-FEE)
                wins += 1
                coin = 0.0
                trades += 1
            elif price <= sl_p:
                bal = coin * price * (1-FEE)
                coin = 0.0
                trades += 1
            # Time exit: max hold 12 bars (1 hour)
            elif curr['macd'] < curr['macd_s']:
                bal = coin * price * (1-FEE)
                coin = 0.0
                trades += 1
                
        # Drawdown tracking
        curr_val = bal if coin == 0 else bal + (coin * curr['c'] * (1-FEE))
        if curr_val > peak_bal: peak_bal = curr_val
        dd = (curr_val - peak_bal) / peak_bal
        if dd < max_dd: max_dd = dd

    final_val = bal if coin == 0 else bal + (coin * df_5m.iloc[-1]['c'] * (1-FEE))
    roi = ((final_val - INITIAL_USD) / INITIAL_USD) * 100
    win_rate = (wins / (trades/2) * 100) if trades > 0 else 0
    
    print("\n--- 5M Momentum Breakout (1 Year) ---")
    print(f"Trades: {trades//2} (Complete rounds)")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Final Balance: ${final_val:.2f}")
    print(f"Total ROI: {roi:.2f}%")
    print(f"Max Drawdown: {max_dd*100:.2f}%")

test_breakout()
