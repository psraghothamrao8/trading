import ccxt
import pandas as pd
import ta
import numpy as np

SYMBOL = 'SOL/USDT'
TIMEFRAME = '5m'

def test():
    ex = ccxt.binance()
    df = pd.DataFrame(ex.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=1000), columns=['ts','o','h','l','c','v'])
    df['ema_9'] = ta.trend.EMAIndicator(df['c'], window=9).ema_indicator()
    df['ema_21'] = ta.trend.EMAIndicator(df['c'], window=21).ema_indicator()
    df['rsi'] = ta.momentum.RSIIndicator(df['c'], window=14).rsi()
    df['typ'] = (df['h']+df['l']+df['c'])/3
    df['vwap'] = (df['typ']*df['v']).cumsum() / df['v'].cumsum()

    bal = 30000 / 83.5
    initial = bal
    coin = 0
    trades = 0

    for i in range(50, len(df)):
        curr = df.iloc[i-1]
        prev = df.iloc[i-2]
        price = df.iloc[i]['o']

        if coin == 0:
            if prev['c'] < prev['ema_9'] and curr['c'] > curr['ema_9'] and curr['c'] > curr['vwap'] and 55 < curr['rsi'] < 75:
                coin = (bal * 0.999) / price
                bal = 0
                entry = price
                trades += 1
        else:
            profit = (price - entry) / entry
            if profit >= 0.012 or profit <= -0.006 or curr['c'] < curr['ema_21']:
                bal = coin * price * 0.999
                coin = 0
                trades += 1

    final = bal if coin == 0 else coin * df.iloc[-1]['c']
    roi = ((final - initial)/initial)*100
    print(f"VWAP Scalper | Trades: {trades} | ROI: {roi:.2f}%")

test()
