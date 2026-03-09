import ccxt
import pandas as pd
import ta
import numpy as np

# Backtesting with a 1-hour timeframe (Balanced for Frequency vs Profit)
# Strategy: MACD Crossover + ATR Trailing Stop (Dynamic Exit)

SYMBOL = 'ETH/USDT'
TIMEFRAME = '1h'
LIMIT = 2000 # ~83 days
INITIAL_INR = 30000
USDT_TO_INR = 83.5
FEE = 0.001

def get_data():
    ex = ccxt.binance()
    ohlcv = ex.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=LIMIT)
    df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
    return df

def apply_indicators(df):
    macd = ta.trend.MACD(close=df['c'])
    df['macd'] = macd.macd()
    df['macd_s'] = macd.macd_signal()
    df['rsi'] = ta.momentum.RSIIndicator(close=df['c']).rsi()
    df['ema_200'] = ta.trend.EMAIndicator(close=df['c'], window=200).ema_indicator()
    return df

def run():
    df = apply_indicators(get_data())
    bal_usdt = INITIAL_INR / USDT_TO_INR
    initial = bal_usdt
    eth = 0
    trades = 0
    entry_p = 0
    
    for i in range(200, len(df)):
        curr = df.iloc[i-1]
        prev = df.iloc[i-2]
        price = df.iloc[i]['o']
        
        # BUY: MACD Cross UP + RSI > 50 + Above EMA 200
        cross_up = (prev['macd'] < prev['macd_s']) and (curr['macd'] > curr['macd_s'])
        if cross_up and curr['rsi'] > 50 and curr['c'] > curr['ema_200'] and eth == 0:
            eth = (bal_usdt * (1 - FEE)) / price
            bal_usdt = 0
            entry_p = price
            trades += 1
            
        # SELL: MACD Cross DOWN OR Profit > 5% OR RSI > 75
        elif eth > 0:
            profit = (price - entry_p) / entry_p
            cross_down = (prev['macd'] > prev['macd_s']) and (curr['macd'] < curr['macd_s'])
            if cross_down or profit > 0.05 or curr['rsi'] > 75:
                bal_usdt = eth * price * (1 - FEE)
                eth = 0
                trades += 1
                
    final = bal_usdt if eth == 0 else eth * df.iloc[-1]['c']
    roi = ((final - initial) / initial) * 100
    print(f"Trades in 83 days: {trades} | ROI: {roi:.2f}%")

if __name__ == "__main__":
    run()
