import ccxt
import pandas as pd
import ta
import numpy as np
import time

SYMBOL = 'ETH/USDT'
INITIAL_INR = 30000
USDT_TO_INR = 83.5
FEE = 0.001

def get_data(days=60):
    ex = ccxt.binance()
    limit = 1000
    tf = '15m'
    total_candles = days * 96
    all_ohlcv = []
    since = ex.milliseconds() - (total_candles * 15 * 60 * 1000)
    
    while len(all_ohlcv) < total_candles:
        try:
            ohlcv = ex.fetch_ohlcv(SYMBOL, tf, since=since, limit=limit)
            if not ohlcv: break
            since = ohlcv[-1][0] + 1
            all_ohlcv.extend(ohlcv)
            time.sleep(0.2)
        except Exception:
            break

    df = pd.DataFrame(all_ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    df.drop_duplicates(subset=['ts'], inplace=True)
    df.sort_values('ts', inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

def apply_indicators(df):
    df['rsi'] = ta.momentum.RSIIndicator(close=df['c'], window=14).rsi()
    return df

def simulate_dca(df):
    bal_usdt = INITIAL_INR / USDT_TO_INR
    initial_usdt = bal_usdt
    
    # DCA Settings
    max_bullets = 3
    bullet_size = bal_usdt / max_bullets
    
    eth_held = 0
    avg_price = 0
    bullets_used = 0
    
    trades_closed = 0
    wins = 0
    
    for i in range(50, len(df)):
        curr = df.iloc[i-1]
        next_open = df.iloc[i]['o']
        
        # BUY LOGIC
        if bullets_used == 0:
            # Initial Entry
            if curr['rsi'] < 30:
                cost = bullet_size
                bal_usdt -= cost
                eth_bought = (cost * (1 - FEE)) / next_open
                eth_held += eth_bought
                bullets_used = 1
                avg_price = next_open
        elif bullets_used < max_bullets:
            # DCA Entries
            drop_pct = (next_open - avg_price) / avg_price
            # If price drops 2% for the 2nd bullet, 4% for the 3rd bullet
            threshold = -0.02 if bullets_used == 1 else -0.04
            
            if drop_pct <= threshold and curr['rsi'] < 35:
                cost = bullet_size
                bal_usdt -= cost
                eth_bought = (cost * (1 - FEE)) / next_open
                total_cost = (bullets_used * bullet_size) + cost
                eth_held += eth_bought
                bullets_used += 1
                avg_price = total_cost / eth_held # rough average
        
        # SELL LOGIC
        if eth_held > 0:
            # Calculate true break-even
            total_invested = bullets_used * bullet_size
            current_value = eth_held * next_open * (1 - FEE)
            net_profit_pct = (current_value - total_invested) / total_invested
            
            # Target 1% net profit on the entire bag
            if net_profit_pct >= 0.01:
                bal_usdt += current_value
                wins += 1
                trades_closed += 1
                eth_held = 0
                bullets_used = 0
                avg_price = 0

    final_val = bal_usdt if eth_held == 0 else bal_usdt + (eth_held * df.iloc[-1]['c'] * (1-FEE))
    roi = ((final_val - initial_usdt) / initial_usdt) * 100
    
    print(f"--- 15M DCA Scalper (3 Bullets) ---")
    print(f"Trades Closed: {trades_closed} | Win Rate: 100% (By design, if not stuck)")
    print(f"Final ROI: {roi:.2f}%")
    print(f"Final Value: ₹{final_val * USDT_TO_INR:.2f}")

if __name__ == "__main__":
    df = apply_indicators(get_data(60))
    simulate_dca(df)
