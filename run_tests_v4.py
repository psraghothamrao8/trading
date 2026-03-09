import ccxt
import pandas as pd
import ta
import numpy as np

SYMBOL = 'ETH/USDT'
INITIAL_INR = 30000
USDT_TO_INR = 83.5
FEE = 0.001

def get_data():
    ex = ccxt.binance()
    ohlcv = ex.fetch_ohlcv(SYMBOL, '15m', limit=1000)
    df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
    return df

def apply_indicators(df):
    df['ema_9'] = ta.trend.EMAIndicator(close=df['c'], window=9).ema_indicator()
    df['ema_21'] = ta.trend.EMAIndicator(close=df['c'], window=21).ema_indicator()
    return df

def simulate_strategy(df):
    bal_usdt = INITIAL_INR / USDT_TO_INR
    initial_usdt = bal_usdt
    eth_held = 0
    trades = 0
    wins = 0
    entry_price = 0
    
    for i in range(50, len(df)):
        curr = df.iloc[i-1]
        prev = df.iloc[i-2]
        next_open = df.iloc[i]['o']
        
        # BUY LOGIC: EMA 9 crosses above EMA 21
        if eth_held == 0:
            if prev['ema_9'] < prev['ema_21'] and curr['ema_9'] > curr['ema_21']:
                entry_price = next_open
                eth_held = (bal_usdt * (1 - FEE)) / entry_price
                bal_usdt = 0
                trades += 1
        # SELL LOGIC: Take profit 1% OR Stop loss 0.5%
        else:
            profit_pct = (next_open - entry_price) / entry_price
            
            if profit_pct >= 0.01 or profit_pct <= -0.005:
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
    print(f"Trades: {trades} | Win Rate: {win_rate:.1f}% | ROI: {roi:.2f}%")

if __name__ == "__main__":
    df = apply_indicators(get_data())
    simulate_strategy(df)
