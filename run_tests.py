import ccxt
import pandas as pd
import ta
import numpy as np
import time

# --- Rigorous Backtest Engine ---
SYMBOL = 'ETH/USDT'
TIMEFRAME = '15m'
INITIAL_INR = 30000
USDT_TO_INR = 83.5
FEE = 0.001  # Binance 0.1% spot fee

def get_data(days=60):
    ex = ccxt.binance()
    limit = 1000
    # 15m candles per day = 24 * 4 = 96
    total_candles = days * 96
    
    all_ohlcv = []
    since = ex.milliseconds() - (total_candles * 15 * 60 * 1000)
    
    print(f"Fetching approximately {days} days of {TIMEFRAME} data...")
    
    while len(all_ohlcv) < total_candles:
        try:
            ohlcv = ex.fetch_ohlcv(SYMBOL, TIMEFRAME, since=since, limit=limit)
            if not ohlcv:
                break
            since = ohlcv[-1][0] + 1
            all_ohlcv.extend(ohlcv)
            time.sleep(0.5) # Rate limit
        except Exception as e:
            print(f"Error fetching data: {e}")
            break

    df = pd.DataFrame(all_ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    df.drop_duplicates(subset=['ts'], inplace=True)
    df.sort_values('ts', inplace=True)
    df.reset_index(drop=True, inplace=True)
    print(f"Loaded {len(df)} candles. Date range: {df['ts'].min()} to {df['ts'].max()}")
    return df

def apply_indicators(df):
    # RSI
    df['rsi'] = ta.momentum.RSIIndicator(close=df['c'], window=14).rsi()
    # Bollinger Bands
    bb = ta.volatility.BollingerBands(close=df['c'], window=20, window_dev=2.5)
    df['bb_l'] = bb.bollinger_lband()
    df['bb_h'] = bb.bollinger_hband()
    # EMA for trend filter
    df['ema_200'] = ta.trend.EMAIndicator(close=df['c'], window=200).ema_indicator()
    df['ema_50'] = ta.trend.EMAIndicator(close=df['c'], window=50).ema_indicator()
    # ATR for volatility measurement
    df['atr'] = ta.volatility.AverageTrueRange(high=df['h'], low=df['l'], close=df['c'], window=14).average_true_range()
    return df

def simulate_strategy(df, name, buy_cond, sell_cond):
    bal_usdt = INITIAL_INR / USDT_TO_INR
    initial_usdt = bal_usdt
    eth_held = 0
    trades = 0
    wins = 0
    entry_price = 0
    entry_time = None
    
    for i in range(200, len(df)):
        curr = df.iloc[i-1]
        next_open = df.iloc[i]['o']
        
        if eth_held == 0:
            if buy_cond(curr, df, i):
                entry_price = next_open
                eth_held = (bal_usdt * (1 - FEE)) / entry_price
                bal_usdt = 0
                trades += 1
                entry_time = curr['ts']
        else:
            profit_pct = (next_open - entry_price) / entry_price
            if sell_cond(curr, profit_pct, entry_price, entry_time):
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
    
    print(f"--- Strategy: {name} ---")
    print(f"Trades: {trades} (Complete rounds: {trades//2}) | Win Rate: {win_rate:.1f}%")
    print(f"Final Value: ₹{final_val * USDT_TO_INR:.2f} | ROI: {roi:.2f}%")
    print("")

def run_tests():
    df = get_data(60) # Test over 2 months
    df = apply_indicators(df)
    
    # Strategy 1: The Current "Catch the Dip" Strategy
    def buy_v1(curr, df, i):
        return curr['c'] <= curr['bb_l'] and curr['rsi'] < 30

    def sell_v1(curr, profit_pct, entry_price, entry_time):
        return profit_pct >= 0.01 or curr['c'] >= curr['bb_h']

    simulate_strategy(df, "V1: Original 1% Scalper (No Stop Loss)", buy_v1, sell_v1)
    
    # Strategy 2: V1 but with a 3% Stop Loss (to avoid catching falling knives forever)
    def sell_v2(curr, profit_pct, entry_price, entry_time):
        return profit_pct >= 0.01 or curr['c'] >= curr['bb_h'] or profit_pct <= -0.03

    simulate_strategy(df, "V2: V1 + 3% Stop Loss", buy_v1, sell_v2)

    # Strategy 3: Improved Logic - Trend-Filtered Dip Buying
    # Only buy dips if the overall trend is UP (Price > EMA 200) OR at least EMA 50 > EMA 200
    def buy_v3(curr, df, i):
        trend_is_up = curr['ema_50'] > curr['ema_200']
        return trend_is_up and curr['c'] <= curr['bb_l'] and curr['rsi'] < 35

    def sell_v3(curr, profit_pct, entry_price, entry_time):
        # Target 1.2% to cover fees better, stop loss 2.5%
        return profit_pct >= 0.012 or curr['c'] >= curr['bb_h'] or profit_pct <= -0.025

    simulate_strategy(df, "V3: Trend-Filtered BB Bounce + SL", buy_v3, sell_v3)

    # Strategy 4: Breakout Momentum
    # Buy when RSI crosses above 50 in an uptrend, sell at 1% or stop loss 1%
    def buy_v4(curr, df, i):
        prev = df.iloc[i-2]
        return curr['ema_50'] > curr['ema_200'] and prev['rsi'] < 50 and curr['rsi'] > 50

    def sell_v4(curr, profit_pct, entry_price, entry_time):
        return profit_pct >= 0.01 or profit_pct <= -0.01

    simulate_strategy(df, "V4: Momentum Breakout (1:1 Risk/Reward)", buy_v4, sell_v4)

if __name__ == "__main__":
    run_tests()
