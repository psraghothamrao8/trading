import pandas as pd
import numpy as np

df = pd.read_csv('sol_1yr_5m.csv')
df['ts'] = pd.to_datetime(df['ts'])

INITIAL_USD = 360.0 # ₹30,000
FEE = 0.001

def simulate_grid():
    bal = INITIAL_USD
    # Grid settings
    grid_count = 10
    part_size = bal / grid_count
    
    coin_held = 0.0
    invested = 0.0
    avg_price = 0.0
    parts_used = 0
    
    trades = 0
    
    for i in range(1, len(df)):
        price = df.iloc[i]['o']
        
        # 🟢 BUY LOGIC
        if parts_used == 0:
            # Initial entry: RSI < 30
            # For simplicity in grid, just buy the first dip
            coin_held += (part_size * (1-FEE)) / price
            invested += part_size
            avg_price = price
            parts_used = 1
        elif parts_used < grid_count:
            # Buy next part if price drops 3% from average
            if (price - avg_price) / avg_price <= -0.03:
                coin_held += (part_size * (1-FEE)) / price
                invested += part_size
                parts_used += 1
                avg_price = invested / (coin_held / (1-FEE))
        
        # 🔴 SELL LOGIC
        if coin_held > 0:
            profit = (price - avg_price) / avg_price
            if profit >= 0.015: # 1.5% profit on total bag
                bal = (bal - invested) + (coin_held * price * (1-FEE))
                coin_held = 0.0
                invested = 0.0
                parts_used = 0
                trades += 1
                # Recalculate part size for compounding
                part_size = bal / grid_count

    final = bal + (coin_held * df.iloc[-1]['c'] * (1-FEE))
    print(f"--- Spot Grid Strategy (SOL 1yr) ---")
    print(f"Trades: {trades} | Final: ${final:.2f} (₹{final*83.5:.2f})")
    print(f"ROI: {((final-INITIAL_USD)/INITIAL_USD)*100:.2f}%")

simulate_grid()
