import pandas as pd
import ta
import numpy as np

# Load 5m data
print("Loading 1 year of 5m data...")
df_5m = pd.read_csv('sol_1yr_5m.csv')
df_5m['ts'] = pd.to_datetime(df_5m['ts'])
df_5m.set_index('ts', inplace=True)

# Resample to 1H data for reliable trend following
print("Resampling to 1H data...")
df_1h = df_5m.resample('1h').agg({
    'o': 'first',
    'h': 'max',
    'l': 'min',
    'c': 'last',
    'v': 'sum'
}).dropna()

# Calculate Indicators on 1H
df_1h['ema_50'] = ta.trend.EMAIndicator(df_1h['c'], window=50).ema_indicator()
df_1h['ema_200'] = ta.trend.EMAIndicator(df_1h['c'], window=200).ema_indicator()
df_1h['rsi'] = ta.momentum.RSIIndicator(df_1h['c'], window=14).rsi()
macd = ta.trend.MACD(df_1h['c'])
df_1h['macd'] = macd.macd()
df_1h['macd_s'] = macd.macd_signal()
df_1h['atr'] = ta.volatility.AverageTrueRange(df_1h['h'], df_1h['l'], df_1h['c'], window=14).average_true_range()

df_1h = df_1h.reset_index()

FEE = 0.001
INITIAL_USD = 360.0

def test_1h_trend_following():
    bal = INITIAL_USD
    coin = 0.0
    trades = 0
    wins = 0
    peak_bal = bal
    max_dd = 0.0
    
    # Track trade logs
    for i in range(200, len(df_1h)):
        curr = df_1h.iloc[i-1]
        prev = df_1h.iloc[i-2]
        price = df_1h.iloc[i]['o']
        
        if coin == 0:
            # 🟢 BUY: MACD Cross Up + Above EMA 200 + Strong RSI
            macd_cross = (prev['macd'] < prev['macd_s']) and (curr['macd'] > curr['macd_s'])
            if macd_cross and curr['c'] > curr['ema_200'] and curr['rsi'] > 55:
                # Calculate position size based on ATR to normalize risk
                stop_loss_price = curr['c'] - (curr['atr'] * 2) # 2 ATR Stop Loss
                
                coin = (bal * (1-FEE)) / price
                bal = 0.0
                entry = price
                sl_p = stop_loss_price
                tp_p = entry + ((entry - sl_p) * 2) # 1:2 Risk Reward
                trades += 1
        else:
            # 🔴 SELL: Hit TP or SL or MACD Reversal
            macd_cross_down = (prev['macd'] > prev['macd_s']) and (curr['macd'] < curr['macd_s'])
            
            if price >= tp_p or price <= sl_p or macd_cross_down:
                bal = coin * price * (1-FEE)
                if bal > (INITIAL_USD if trades==1 else prev_bal):
                    wins += 1
                coin = 0.0
                trades += 1
                
        # Drawdown tracking
        curr_val = bal + (coin * curr['c'] * (1-FEE))
        if curr_val > peak_bal: peak_bal = curr_val
        dd = (curr_val - peak_bal) / peak_bal
        if dd < max_dd: max_dd = dd
        
        prev_bal = bal if coin == 0 else bal + (coin * curr['c'] * (1-FEE))

    final_val = bal + (coin * df_1h.iloc[-1]['c'] * (1-FEE))
    roi = ((final_val - INITIAL_USD) / INITIAL_USD) * 100
    win_rate = (wins / (trades/2) * 100) if trades > 0 else 0
    
    print("\n--- 1H ATR Trend Following ---")
    print(f"Trades: {trades//2} (Complete rounds)")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Final Balance: ${final_val:.2f}")
    print(f"Total ROI: {roi:.2f}%")
    print(f"Max Drawdown: {max_dd*100:.2f}%")

test_1h_trend_following()
