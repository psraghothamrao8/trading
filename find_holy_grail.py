import ccxt
import pandas as pd
import ta
import time

COINS = ['SOL/USDT', 'DOGE/USDT', 'PEPE/USDT', 'AVAX/USDT']
TIMEFRAME = '5m'
DAYS = 30
FEE = 0.001

def get_data(symbol):
    ex = ccxt.binance()
    limit = 1000
    total_candles = DAYS * 288
    all_ohlcv = []
    since = ex.milliseconds() - (total_candles * 5 * 60 * 1000)
    while len(all_ohlcv) < total_candles:
        try:
            ohlcv = ex.fetch_ohlcv(symbol, TIMEFRAME, since=since, limit=limit)
            if not ohlcv: break
            since = ohlcv[-1][0] + 1
            all_ohlcv.extend(ohlcv)
            time.sleep(0.1)
        except: break
    df = pd.DataFrame(all_ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
    return df

def test_strategy(df, symbol):
    # RSI & Bollinger Bands
    df['rsi'] = ta.momentum.RSIIndicator(df['c'], window=7).rsi()
    bb = ta.volatility.BollingerBands(df['c'], window=20, window_dev=2.5)
    df['bb_l'] = bb.bollinger_lband()
    df['ema_200'] = ta.trend.EMAIndicator(df['c'], window=200).ema_indicator()
    
    bal = 30000 / 83.5
    initial = bal
    coin = 0
    trades = 0
    
    tp = 0.015 # 1.5% profit per trade
    
    for i in range(200, len(df)):
        curr = df.iloc[i-1]
        price = df.iloc[i]['o']
        
        if coin == 0:
            # Aggressive Buy: Oversold + Below lower BB
            if curr['rsi'] < 25 and curr['c'] <= curr['bb_l'] and curr['c'] > curr['ema_200']:
                coin = (bal * (1 - FEE)) / price
                bal = 0
                entry = price
                trades += 1
        else:
            profit = (price - entry) / entry
            # Only sell in profit (Holding bags if it drops - classic spot scalping risk)
            if profit >= tp:
                bal = coin * price * (1 - FEE)
                coin = 0
                trades += 1
                
    final = bal if coin == 0 else coin * df.iloc[-1]['c']
    roi = ((final - initial) / initial) * 100
    print(f"{symbol} | Trades: {trades} | ROI: {roi:.2f}% | Final Bal: ${final:.2f}")

for c in COINS:
    df = get_data(c)
    test_strategy(df, c)
