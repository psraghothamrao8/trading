import ccxt
import pandas as pd
import ta
import numpy as np
import time

SYMBOL = 'SOL/USDT'
TIMEFRAME = '5m'
DAYS = 30
FEE = 0.001

def get_data():
    ex = ccxt.binance()
    limit = 1000
    total_candles = DAYS * 288
    all_ohlcv = []
    since = ex.milliseconds() - (total_candles * 5 * 60 * 1000)
    while len(all_ohlcv) < total_candles:
        try:
            ohlcv = ex.fetch_ohlcv(SYMBOL, TIMEFRAME, since=since, limit=limit)
            if not ohlcv: break
            since = ohlcv[-1][0] + 1
            all_ohlcv.extend(ohlcv)
            time.sleep(0.1)
        except: break
    return pd.DataFrame(all_ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])

def test_aggressive(df):
    bb = ta.volatility.BollingerBands(df['c'], window=20, window_dev=2)
    df['bb_l'] = bb.bollinger_lband()
    df['bb_h'] = bb.bollinger_hband()
    df['rsi'] = ta.momentum.RSIIndicator(df['c'], window=7).rsi()
    df['ema_200'] = ta.trend.EMAIndicator(df['c'], window=200).ema_indicator()
    
    bal = 30000 / 83.5
    initial = bal
    coin = 0
    trades = 0
    
    for i in range(200, len(df)):
        curr = df.iloc[i-1]
        price = df.iloc[i]['o']
        
        if coin == 0:
            # Aggressive Buy: Touches lower BB + RSI < 40 (More frequent)
            if curr['c'] <= curr['bb_l'] and curr['rsi'] < 40 and curr['c'] > curr['ema_200']:
                coin = (bal * (1 - FEE)) / price
                bal = 0
                entry = price
                trades += 1
        else:
            profit = (price - entry) / entry
            # Sell at 1% profit or upper BB
            if profit >= 0.01 or curr['c'] >= curr['bb_h'] or profit <= -0.015:
                bal = coin * price * (1 - FEE)
                coin = 0
                trades += 1
                
    final = bal if coin == 0 else coin * df.iloc[-1]['c']
    roi = ((final - initial) / initial) * 100
    print(f"Aggressive | Trades: {trades} | ROI: {roi:.2f}%")

test_aggressive(get_data())
