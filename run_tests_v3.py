import ccxt
import pandas as pd
import ta
import numpy as np
import time

SYMBOL = 'ETH/USDT'
INITIAL_INR = 30000
USDT_TO_INR = 83.5
FEE = 0.001

def get_data(tf='15m', days=60):
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
            break

    df = pd.DataFrame(all_ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    df.drop_duplicates(subset=['ts'], inplace=True)
    df.sort_values('ts', inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

def apply_indicators(df):
    df['rsi'] = ta.momentum.RSIIndicator(close=df['c'], window=14).rsi()
    bb = ta.volatility.BollingerBands(close=df['c'], window=20, window_dev=2.5)
    df['bb_l'] = bb.bollinger_lband()
    df['bb_h'] = bb.bollinger_hband()
    return df

def simulate_strategy(df, name):
    bal_usdt = INITIAL_INR / USDT_TO_INR
    initial_usdt = bal_usdt
    eth_held = 0
    trades = 0
    wins = 0
    entry_price = 0
    entry_index = 0
    
    for i in range(50, len(df)):
        curr = df.iloc[i-1]
        next_open = df.iloc[i]['o']
        
        # BUY LOGIC: Extreme oversold bounce
        if eth_held == 0:
            if curr['c'] <= curr['bb_l'] and curr['rsi'] < 30:
                entry_price = next_open
                entry_index = i
                eth_held = (bal_usdt * (1 - FEE)) / entry_price
                bal_usdt = 0
                trades += 1
        # SELL LOGIC: Take profit OR Time-Based Stop Loss (Don't hold bags)
        else:
            profit_pct = (next_open - entry_price) / entry_price
            bars_held = i - entry_index
            
            # Target 1% profit, OR sell if held for more than 16 bars (4 hours) OR stop loss 2%
            if profit_pct >= 0.01 or bars_held >= 16 or profit_pct <= -0.02:
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

if __name__ == "__main__":
    df_15m = apply_indicators(get_data('15m', 60))
    simulate_strategy(df_15m, "15m Extreme Scalper (1% TP, 2% SL, 4H Max Hold)")
