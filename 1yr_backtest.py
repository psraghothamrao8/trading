import ccxt
import pandas as pd
import ta
import numpy as np
import time
import os

SYMBOL = 'SOL/USDT'
TIMEFRAME = '5m'
DAYS = 365
FEE = 0.001
DATA_FILE = 'sol_1yr_5m.csv'

def fetch_1yr_data():
    if os.path.exists(DATA_FILE):
        print("Data file exists. Loading...")
        df = pd.read_csv(DATA_FILE)
        df['ts'] = pd.to_datetime(df['ts'])
        return df

    ex = ccxt.binance()
    limit = 1000
    total_candles = DAYS * 288
    all_ohlcv = []
    
    # Start time = 1 year ago
    since = ex.milliseconds() - (total_candles * 5 * 60 * 1000)
    
    print(f"Fetching {DAYS} days of {TIMEFRAME} data for {SYMBOL} (~{total_candles} candles)...")
    
    while len(all_ohlcv) < total_candles:
        try:
            ohlcv = ex.fetch_ohlcv(SYMBOL, TIMEFRAME, since=since, limit=limit)
            if not ohlcv: break
            since = ohlcv[-1][0] + 1
            all_ohlcv.extend(ohlcv)
            print(f"Fetched {len(all_ohlcv)} / {total_candles} candles...", end='\r')
            time.sleep(0.1)
        except Exception as e:
            print(f"\nError: {e}")
            time.sleep(5)
    
    print("\nData fetched. Saving to CSV...")
    df = pd.DataFrame(all_ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    df.drop_duplicates(subset=['ts'], inplace=True)
    df.sort_values('ts', inplace=True)
    df.reset_index(drop=True, inplace=True)
    df.to_csv(DATA_FILE, index=False)
    return df

def test_v4_logic(df):
    print("\n--- Running V4 Logic (4 Bullets, 1.5% Drop, No Trend Filter) ---")
    df['rsi'] = ta.momentum.RSIIndicator(df['c'], window=14).rsi()
    
    bal_usdt = 30000 / 83.5 # ~359.28 USDT
    initial = bal_usdt
    max_bullets = 4
    bullet_size = bal_usdt / max_bullets
    
    bullets_used = 0
    total_invested = 0.0
    coin_amount = 0.0
    avg_price = 0.0
    
    trades_closed = 0
    max_drawdown = 0.0
    peak_bal = initial
    
    for i in range(50, len(df)):
        curr = df.iloc[i-1]
        price = df.iloc[i]['o']
        
        # BUY LOGIC
        if bullets_used == 0:
            if curr['rsi'] < 30: # Initial Entry
                cost = bullet_size
                bal_usdt -= cost
                coin_amount += (cost * (1 - FEE)) / price
                total_invested += cost
                bullets_used = 1
                avg_price = price
        elif bullets_used < max_bullets:
            drop_pct = (price - avg_price) / avg_price
            if drop_pct <= -0.015: # 1.5% drop from avg
                cost = bullet_size
                bal_usdt -= cost
                coin_amount += (cost * (1 - FEE)) / price
                total_invested += cost
                bullets_used += 1
                avg_price = total_invested / (coin_amount / (1 - FEE)) # Approximate avg price
        
        # SELL LOGIC
        if bullets_used > 0:
            current_val = coin_amount * price * (1 - FEE)
            net_profit_pct = (current_value - total_invested) / total_invested if 'current_value' in locals() else (current_val - total_invested) / total_invested
            
            # Track drawdown while in trade
            dd = net_profit_pct
            if dd < max_drawdown: max_drawdown = dd
            
            if net_profit_pct >= 0.012: # 1.2% target
                bal_usdt += current_val
                if bal_usdt > peak_bal: peak_bal = bal_usdt
                
                bullets_used = 0
                total_invested = 0.0
                coin_amount = 0.0
                avg_price = 0.0
                trades_closed += 1

    final_val = bal_usdt if bullets_used == 0 else bal_usdt + (coin_amount * df.iloc[-1]['c'] * (1 - FEE))
    roi = ((final_val - initial) / initial) * 100
    
    print(f"Trades Closed: {trades_closed}")
    print(f"Final Balance: ${final_val:.2f} (₹{final_val * 83.5:.2f})")
    print(f"ROI: {roi:.2f}%")
    print(f"Max Floating Drawdown (Bag holding): {max_drawdown*100:.2f}%")
    print("If Drawdown is > 20%, it means capital got stuck for long periods.\n")

if __name__ == "__main__":
    df = fetch_1yr_data()
    test_v4_logic(df)
