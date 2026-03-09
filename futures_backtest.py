import ccxt
import pandas as pd
import ta
import numpy as np
import time

SYMBOL = 'SOL/USDT'
TIMEFRAME = '15m'
DAYS = 365
FEE = 0.0004 # Binance Futures Maker/Taker avg (0.04%)
LEVERAGE = 3 # 3x Leverage

def fetch_data():
    ex = ccxt.binance()
    limit = 1000
    total_candles = DAYS * 96
    all_ohlcv = []
    since = ex.milliseconds() - (total_candles * 15 * 60 * 1000)
    
    print(f"Fetching {DAYS} days of {TIMEFRAME} Futures data for {SYMBOL}...")
    while len(all_ohlcv) < total_candles:
        try:
            ohlcv = ex.fetch_ohlcv(SYMBOL, TIMEFRAME, since=since, limit=limit)
            if not ohlcv: break
            since = ohlcv[-1][0] + 1
            all_ohlcv.extend(ohlcv)
            time.sleep(0.1)
        except Exception:
            time.sleep(2)
            
    df = pd.DataFrame(all_ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    return df

def run_multi_strategy(df):
    # --- INDICATORS ---
    # 1. Macro Trend (4H equivalent)
    df['ema_macro'] = ta.trend.EMAIndicator(df['c'], window=800).ema_indicator() 
    
    # 2. Local Trend (1H equivalent)
    df['ema_local'] = ta.trend.EMAIndicator(df['c'], window=200).ema_indicator()
    
    # 3. Momentum & Reversion
    df['rsi'] = ta.momentum.RSIIndicator(df['c'], window=14).rsi()
    macd = ta.trend.MACD(df['c'])
    df['macd'] = macd.macd()
    df['macd_s'] = macd.macd_signal()
    
    # 4. Volatility (ATR) for dynamic targets
    df['atr'] = ta.volatility.AverageTrueRange(df['h'], df['l'], df['c'], window=14).average_true_range()

    # --- SIMULATION ---
    bal_usdt = 360.0 # 30,000 INR
    initial = bal_usdt
    position = 0 # 1 = Long, -1 = Short, 0 = Flat
    entry_price = 0
    trades = 0
    wins = 0
    max_dd = 0
    peak_bal = initial
    
    for i in range(800, len(df)):
        curr = df.iloc[i-1]
        prev = df.iloc[i-2]
        price = df.iloc[i]['o']
        
        # --- MACRO REGIME DETECTION ---
        bull_market = curr['c'] > curr['ema_macro']
        bear_market = curr['c'] < curr['ema_macro']
        
        if position == 0:
            # 🟢 STRATEGY 1: PULLBACK LONG (Only in Bull Market)
            long_cond = bull_market and curr['c'] > curr['ema_local'] and prev['macd'] < prev['macd_s'] and curr['macd'] > curr['macd_s'] and curr['rsi'] < 50
            
            # 🔴 STRATEGY 2: BEAR RALLY SHORT (Only in Bear Market)
            short_cond = bear_market and curr['c'] < curr['ema_local'] and prev['macd'] > prev['macd_s'] and curr['macd'] < curr['macd_s'] and curr['rsi'] > 50
            
            if long_cond:
                position = 1
                entry_price = price
                # Risk 2% of capital per trade
                position_size = bal_usdt * LEVERAGE
                # Dynamic TP/SL based on ATR
                sl_dist = curr['atr'] * 2
                sl_p = entry_price - sl_dist
                tp_p = entry_price + (sl_dist * 2) # 1:2 RR
                bal_usdt -= (position_size * FEE) # Entry Fee
                trades += 1
                
            elif short_cond:
                position = -1
                entry_price = price
                position_size = bal_usdt * LEVERAGE
                sl_dist = curr['atr'] * 2
                sl_p = entry_price + sl_dist
                tp_p = entry_price - (sl_dist * 2)
                bal_usdt -= (position_size * FEE)
                trades += 1
                
        else:
            # Manage Open Position
            if position == 1:
                profit_pct = (price - entry_price) / entry_price
                if price >= tp_p:
                    bal_usdt += (position_size * profit_pct) - (position_size * FEE)
                    if (position_size * profit_pct) > 0: wins += 1
                    position = 0
                elif price <= sl_p:
                    bal_usdt += (position_size * profit_pct) - (position_size * FEE)
                    position = 0
                    
            elif position == -1:
                profit_pct = (entry_price - price) / entry_price
                if price <= tp_p:
                    bal_usdt += (position_size * profit_pct) - (position_size * FEE)
                    if (position_size * profit_pct) > 0: wins += 1
                    position = 0
                elif price >= sl_p:
                    bal_usdt += (position_size * profit_pct) - (position_size * FEE)
                    position = 0
                    
        # Track DD
        if bal_usdt > peak_bal: peak_bal = bal_usdt
        dd = (bal_usdt - peak_bal) / peak_bal
        if dd < max_dd: max_dd = dd
        
        # Stop trading if blown up
        if bal_usdt < 50:
            print("ACCOUNT LIQUIDATED")
            break

    roi = ((bal_usdt - initial) / initial) * 100
    win_rate = (wins / trades * 100) if trades > 0 else 0
    print(f"\n--- Professional 3x Multi-Regime Strategy ---")
    print(f"Trades: {trades}")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Final Balance: ${bal_usdt:.2f} (₹{bal_usdt * 83.5:.2f})")
    print(f"Total ROI: {roi:.2f}%")
    print(f"Max Drawdown: {max_dd*100:.2f}%")

if __name__ == "__main__":
    df = fetch_data()
    run_multi_strategy(df)
