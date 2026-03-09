import pandas as pd
import ta
import numpy as np

# Load the previously fetched 1-year SOL 5m data
df_raw = pd.read_csv('sol_1yr_5m.csv')
df_raw['ts'] = pd.to_datetime(df_raw['ts'])

# Resample to 15m for cleaner "Day Trading" signals
df = df_raw.resample('15min', on='ts').agg({
    'o': 'first', 'h': 'max', 'l': 'min', 'c': 'last', 'v': 'sum'
}).dropna().reset_index()

# Indicators
df['ema_200'] = ta.trend.EMAIndicator(df['c'], window=200).ema_indicator()
df['rsi_2'] = ta.momentum.RSIIndicator(df['c'], window=2).rsi() # Very fast for scalping dips
df['rsi_14'] = ta.momentum.RSIIndicator(df['c'], window=14).rsi()

FEE = 0.001
INITIAL_USD = 360.0

def simulate_spot_salary():
    bal = INITIAL_USD
    initial = bal
    coin = 0.0
    trades = 0
    wins = 0
    entry_p = 0
    
    # Track daily performance
    df['date'] = df['ts'].dt.date
    daily_roi = []
    
    for i in range(200, len(df)):
        curr = df.iloc[i-1]
        price = df.iloc[i]['o']
        
        if coin == 0:
            # 🟢 THE "SNIPER DIP" ENTRY
            # 1. Macro Trend Up (Price > EMA 200)
            # 2. Extreme 2-bar RSI Panic (< 10)
            if curr['c'] > curr['ema_200'] and curr['rsi_2'] < 10:
                coin = (bal * (1 - FEE)) / price
                bal = 0.0
                entry_p = price
                trades += 1
        else:
            # 🔴 THE "QUICK PROFIT" EXIT
            profit = (price - entry_p) / entry_p
            # Exit if 2-bar RSI recovers (> 70) OR 1.5% target hit
            if curr['rsi_2'] > 70 or profit >= 0.015 or profit <= -0.03:
                bal = coin * price * (1 - FEE)
                if bal > (INITIAL_USD if trades == 1 else prev_bal): wins += 1
                coin = 0.0
                trades += 1
        
        prev_bal = bal if coin == 0 else bal + (coin * curr['c'] * (1 - FEE))

    final = bal if coin == 0 else bal + (coin * df.iloc[-1]['c'] * (1 - FEE))
    print(f"--- Spot Salary Strategy (SOL 15m) ---")
    print(f"Trades: {trades//2} | Win Rate: {(wins/(trades/2)*100 if trades>0 else 0):.1f}%")
    print(f"Final Balance: ${final:.2f} (₹{final*83.5:.2f})")
    print(f"Total ROI: {((final-initial)/initial)*100:.2f}%")

simulate_spot_salary()
