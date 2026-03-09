import ccxt
import pandas as pd
import ta
import numpy as np

# Strategy: 4H/1H Combined Trend & Reversion (The "Safe & Profit" Strategy)

SYMBOL = 'ETH/USDT'
TIMEFRAME = '1h'
LIMIT = 2000 # ~83 days
INITIAL_INR = 30000
USDT_TO_INR = 83.5

def get_data():
    ex = ccxt.binance()
    ohlcv = ex.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=LIMIT)
    df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
    return df

def apply_indicators(df):
    df['rsi'] = ta.momentum.RSIIndicator(close=df['c'], window=14).rsi()
    # Trend Filter EMA 200
    df['ema_200'] = ta.trend.EMAIndicator(close=df['c'], window=200).ema_indicator()
    # MACD for strong signals
    macd = ta.trend.MACD(close=df['c'], window_slow=26, window_fast=12, window_sign=9)
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    return df

def run():
    df = apply_indicators(get_data())
    bal_usdt = INITIAL_INR / USDT_TO_INR
    initial = bal_usdt
    eth = 0
    trades = 0
    
    for i in range(200, len(df)):
        curr = df.iloc[i-1]
        prev = df.iloc[i-2]
        price = df.iloc[i]['o']
        
        # BUY: MACD Bullish Cross + Above EMA 200 (Long Term Trend)
        cross_up = (prev['macd'] < prev['macd_signal']) and (curr['macd'] > curr['macd_signal'])
        if cross_up and curr['c'] > curr['ema_200'] and eth == 0:
            eth = (bal_usdt * 0.999) / price
            bal_usdt = 0
            trades += 1
            
        # SELL: MACD Bearish Cross OR RSI > 70
        cross_down = (prev['macd'] > prev['macd_signal']) and (curr['macd'] < prev['macd_signal'])
        if (cross_down or curr['rsi'] > 70) and eth > 0:
            bal_usdt = eth * price * 0.999
            eth = 0
            trades += 1
            
    final_bal = bal_usdt if eth == 0 else eth * df.iloc[-1]['c']
    roi = ((final_bal - initial) / initial) * 100
    print(f"Trades in 83 days: {trades}")
    print(f"Final: ₹{final_bal * USDT_TO_INR:.2f} | ROI: {roi:.2f}%")

if __name__ == "__main__":
    run()
