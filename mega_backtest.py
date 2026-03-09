import ccxt
import pandas as pd
import ta
import numpy as np
import time

SYMBOL = 'BTC/USDT'
TIMEFRAME = '15m'
INITIAL_INR = 30000
USDT_TO_INR = 83.5
FEE = 0.001 

def get_data(days=30):
    ex = ccxt.binance()
    limit = 1000
    total_candles = days * 96
    all_ohlcv = []
    since = ex.milliseconds() - (total_candles * 15 * 60 * 1000)
    print(f"Fetching {days} days of {TIMEFRAME} data for {SYMBOL}...")
    while len(all_ohlcv) < total_candles:
        try:
            ohlcv = ex.fetch_ohlcv(SYMBOL, TIMEFRAME, since=since, limit=limit)
            if not ohlcv: break
            since = ohlcv[-1][0] + 1
            all_ohlcv.extend(ohlcv)
            time.sleep(0.1)
        except Exception: break
    return pd.DataFrame(all_ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])

def apply_indicators(df):
    df['rsi'] = ta.momentum.RSIIndicator(df['c'], window=14).rsi()
    return df

def run_simulation(df):
    bal_usdt = INITIAL_INR / USDT_TO_INR
    initial = bal_usdt
    btc = 0
    trades = 0
    wins = 0
    
    # Divergence is hard to code in a simple loop, let's just use RSI < 25 as a proxy for "deep oversold bounce"
    TP = 0.015 
    SL = 0.010 
    
    for i in range(50, len(df)):
        curr = df.iloc[i-1]
        price = df.iloc[i]['o']
        
        if btc == 0:
            # 🟢 BUY: RSI < 25 (Deeply oversold)
            if curr['rsi'] < 25:
                btc = (bal_usdt * (1 - FEE)) / price
                bal_usdt = 0
                entry_p = price
                trades += 1
        else:
            # 🔴 SELL: TP or SL
            profit = (price - entry_p) / entry_p
            if profit >= TP or profit <= -SL:
                bal_usdt = btc * price * (1 - FEE)
                if bal_usdt > prev_bal: wins += 1
                btc = 0; trades += 1
        
        prev_bal = bal_usdt if btc == 0 else btc * curr['c']

    final = bal_usdt if btc == 0 else btc * df.iloc[-1]['c']
    roi = ((final - initial) / initial) * 100
    print(f"BTC 15m Oversold Bounce (30 Days): Trades: {trades} | ROI: {roi:.2f}%")

if __name__ == "__main__":
    df = apply_indicators(get_data(30))
    run_simulation(df)
