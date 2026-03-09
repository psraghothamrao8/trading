import ccxt
import pandas as pd
import ta
import numpy as np
import time

SYMBOL = 'ETH/USDT'
INITIAL_INR = 30000
USDT_TO_INR = 83.5
FEE = 0.001

def get_data(tf='1h', days=60):
    ex = ccxt.binance()
    limit = 1000
    if tf == '1h':
        total_candles = days * 24
        ms_per_candle = 60 * 60 * 1000
    elif tf == '4h':
        total_candles = days * 6
        ms_per_candle = 4 * 60 * 60 * 1000
    elif tf == '15m':
        total_candles = days * 96
        ms_per_candle = 15 * 60 * 1000
        
    all_ohlcv = []
    since = ex.milliseconds() - (total_candles * ms_per_candle)
    
    print(f"Fetching {days} days of {tf} data...")
    while len(all_ohlcv) < total_candles:
        try:
            ohlcv = ex.fetch_ohlcv(SYMBOL, tf, since=since, limit=limit)
            if not ohlcv: break
            since = ohlcv[-1][0] + 1
            all_ohlcv.extend(ohlcv)
            time.sleep(0.2)
        except Exception as e:
            print(f"Error: {e}")
            break

    df = pd.DataFrame(all_ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    df.drop_duplicates(subset=['ts'], inplace=True)
    df.sort_values('ts', inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

def apply_indicators(df):
    df['rsi'] = ta.momentum.RSIIndicator(close=df['c'], window=14).rsi()
    df['ema_10'] = ta.trend.EMAIndicator(close=df['c'], window=10).ema_indicator()
    df['ema_20'] = ta.trend.EMAIndicator(close=df['c'], window=20).ema_indicator()
    df['ema_50'] = ta.trend.EMAIndicator(close=df['c'], window=50).ema_indicator()
    df['ema_200'] = ta.trend.EMAIndicator(close=df['c'], window=200).ema_indicator()
    
    macd = ta.trend.MACD(close=df['c'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    
    bb = ta.volatility.BollingerBands(close=df['c'], window=20, window_dev=2)
    df['bb_l'] = bb.bollinger_lband()
    df['bb_h'] = bb.bollinger_hband()
    return df

def simulate_strategy(df, name, buy_cond, sell_cond):
    bal_usdt = INITIAL_INR / USDT_TO_INR
    initial_usdt = bal_usdt
    eth_held = 0
    trades = 0
    wins = 0
    entry_price = 0
    
    for i in range(200, len(df)):
        curr = df.iloc[i-1]
        prev = df.iloc[i-2]
        next_open = df.iloc[i]['o']
        
        if eth_held == 0:
            if buy_cond(curr, prev, next_open):
                entry_price = next_open
                eth_held = (bal_usdt * (1 - FEE)) / entry_price
                bal_usdt = 0
                trades += 1
        else:
            profit_pct = (next_open - entry_price) / entry_price
            if sell_cond(curr, prev, profit_pct, next_open):
                exit_price = next_open
                bal_usdt = eth_held * exit_price * (1 - FEE)
                if bal_usdt > (initial_usdt if trades == 1 else prev_bal):
                    wins += 1
                eth_held = 0
                trades += 1
                
        prev_bal = bal_usdt if eth_held == 0 else eth_held * curr['c']

    final_val = bal_usdt if eth_held == 0 else eth_held * df.iloc[-1]['c']
    roi = ((final_val - initial_usdt) / initial_usdt) * 100
    win_rate = (wins / (trades/2)) * 100 if trades > 0 else 0
    print(f"--- {name} ---")
    print(f"Trades: {trades} | Win Rate: {win_rate:.1f}% | ROI: {roi:.2f}%")
    print("")

def run_tests():
    print("Testing 1H Timeframe Strategies...")
    df_1h = apply_indicators(get_data('1h', 60))
    
    # 1. MACD Cross with EMA200 Filter
    def buy_macd(curr, prev, price):
        return (prev['macd'] < prev['macd_signal']) and (curr['macd'] > curr['macd_signal']) and curr['c'] > curr['ema_200']
    def sell_macd(curr, prev, profit, price):
        return (prev['macd'] > prev['macd_signal']) and (curr['macd'] < curr['macd_signal']) or profit > 0.02 or profit < -0.02

    simulate_strategy(df_1h, "1H MACD + EMA200 (Take 2% / Stop 2%)", buy_macd, sell_macd)

    # 2. Golden Cross (EMA 10/20) + RSI
    def buy_ema(curr, prev, price):
        return (prev['ema_10'] < prev['ema_20']) and (curr['ema_10'] > curr['ema_20']) and curr['rsi'] < 60
    def sell_ema(curr, prev, profit, price):
        return (prev['ema_10'] > prev['ema_20']) and (curr['ema_10'] < curr['ema_20'])

    simulate_strategy(df_1h, "1H EMA 10/20 Crossover (Trend Follow)", buy_ema, sell_ema)
    
    # 3. Safe Dip Buyer (Only in uptrend)
    def buy_dip(curr, prev, price):
        return curr['c'] > curr['ema_200'] and curr['c'] <= curr['bb_l']
    def sell_dip(curr, prev, profit, price):
        return profit >= 0.015 or profit <= -0.03 or curr['c'] >= curr['ema_20']

    simulate_strategy(df_1h, "1H Safe Dip Buyer (Target 1.5%)", buy_dip, sell_dip)

if __name__ == "__main__":
    run_tests()
