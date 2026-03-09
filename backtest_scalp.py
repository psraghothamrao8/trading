import ccxt
import pandas as pd
import ta
import numpy as np

# --- 15-Minute Scalping Strategy (Optimized for 1% Daily) ---
SYMBOL = 'ETH/USDT'
TIMEFRAME = '15m'
LIMIT = 3000  # Approx 31 days
INITIAL_INR = 30000
USDT_TO_INR = 83.5
FEE = 0.001 

def get_data():
    ex = ccxt.binance()
    ohlcv = ex.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=LIMIT)
    df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
    return df

def apply_indicators(df):
    # RSI
    df['rsi'] = ta.momentum.RSIIndicator(close=df['c'], window=14).rsi()
    # Bollinger Bands
    bb = ta.volatility.BollingerBands(close=df['c'], window=20, window_dev=2.5) # Wider bands to avoid fakeouts
    df['bb_l'] = bb.bollinger_lband()
    df['bb_h'] = bb.bollinger_hband()
    return df

def simulate():
    df = apply_indicators(get_data())
    bal_usdt = INITIAL_INR / USDT_TO_INR
    initial = bal_usdt
    eth = 0
    trades = 0
    wins = 0
    entry_price = 0
    
    # 0.8% Profit Target to clear fees and hit roughly 0.6% net profit per trade
    TAKE_PROFIT = 0.008  
    
    for i in range(50, len(df)):
        curr = df.iloc[i-1]
        price = df.iloc[i]['o']
        
        # BUY: Price pierces bottom band AND RSI is deeply oversold (< 30)
        if curr['c'] <= curr['bb_l'] and curr['rsi'] < 30 and eth == 0:
            eth = (bal_usdt * (1 - FEE)) / price
            bal_usdt = 0
            entry_price = price
            trades += 1
            
        # SELL: Strict Take Profit hit OR reaches upper band
        elif eth > 0:
            profit_pct = (price - entry_price) / entry_price
            
            if profit_pct >= TAKE_PROFIT or curr['c'] >= curr['bb_h']:
                bal_usdt = eth * price * (1 - FEE)
                if bal_usdt > (eth * entry_price): wins += 1
                eth = 0
                trades += 1
                
    final = bal_usdt if eth == 0 else eth * df.iloc[-1]['c']
    roi = ((final - initial) / initial) * 100
    win_rate = (wins / (trades/2)) * 100 if trades > 0 else 0
    
    print(f"--- 15M Scalping For 1% Daily ---")
    print(f"Days Simulated: ~31 days")
    print(f"Total Trades: {trades}")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Final Balance: ₹{final * USDT_TO_INR:.2f}")
    print(f"ROI: {roi:.2f}%")

if __name__ == "__main__":
    simulate()
