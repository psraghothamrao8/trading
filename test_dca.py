import ccxt
import pandas as pd
import ta
import numpy as np
import time

COINS = ['SOL/USDT', 'DOGE/USDT', 'BTC/USDT', 'SUI/USDT']
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
    return pd.DataFrame(all_ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])

def test_dca_strategy(df, symbol):
    df['rsi'] = ta.momentum.RSIIndicator(df['c'], window=14).rsi()
    
    bal_usdt = 30000 / 83.5
    initial = bal_usdt
    
    max_bullets = 5
    bullet_size = bal_usdt / max_bullets
    
    coin_held = 0
    bullets_used = 0
    avg_price = 0
    trades_closed = 0
    
    for i in range(50, len(df)):
        curr = df.iloc[i-1]
        price = df.iloc[i]['o']
        
        # BUY
        if bullets_used == 0:
            if curr['rsi'] < 30: # Initial entry
                cost = bullet_size
                bal_usdt -= cost
                coin_held += (cost * (1 - FEE)) / price
                bullets_used += 1
                avg_price = price
        elif bullets_used < max_bullets:
            drop_pct = (price - avg_price) / avg_price
            if drop_pct <= -0.02 and curr['rsi'] < 35: # DCA at 2% drops
                cost = bullet_size
                bal_usdt -= cost
                new_coins = (cost * (1 - FEE)) / price
                total_cost = (bullets_used * bullet_size) + cost
                coin_held += new_coins
                bullets_used += 1
                avg_price = total_cost / coin_held
        
        # SELL
        if coin_held > 0:
            total_invested = bullets_used * bullet_size
            current_value = coin_held * price * (1 - FEE)
            net_profit_pct = (current_value - total_invested) / total_invested
            
            if net_profit_pct >= 0.015: # Target 1.5% net profit on the bag
                bal_usdt += current_value
                coin_held = 0
                bullets_used = 0
                avg_price = 0
                trades_closed += 1
                
    final = bal_usdt if coin_held == 0 else bal_usdt + (coin_held * df.iloc[-1]['c'] * (1-FEE))
    roi = ((final - initial) / initial) * 100
    print(f"{symbol} DCA | Closed Trades: {trades_closed} | ROI: {roi:.2f}% | Final Bal: ${final:.2f}")

for c in COINS:
    df = get_data(c)
    test_dca_strategy(df, c)
