import ccxt
import pandas as pd
import ta
import time
import os
import json
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv

# --- Professional Production Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("/home/ram/Documents/trading/trading.log"),
        logging.StreamHandler()
    ]
)

# Custom logger for trade results
trade_logger = logging.getLogger('trade_results')
trade_handler = logging.FileHandler("/home/ram/Documents/trading/trade.txt")
trade_handler.setFormatter(logging.Formatter('%(asctime)s: %(message)s'))
trade_logger.addHandler(trade_handler)

load_dotenv()

# --- THE "TITAN V39" ENGINE (PERFECTED PRODUCTION CODE) ---
# Goal: High-frequency "Salary" generation in any Spot market condition.
# Mechanism: Multi-threaded DCA grids with Non-Compounding structure.

SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'AVAX/USDT', 'DOGE/USDT', 'SUI/USDT'] 
TIMEFRAME = '15m'
CHECK_INTERVAL_SECONDS = 300 
STATE_FILE = "/home/ram/Documents/trading/titan_state.json"

# --- MATHEMATICAL STRATEGY PARAMETERS ---
NUM_GRIDS = 4            # 4 Independent Overlapping Grids per coin
MAX_BULLETS = 4          # 4 Layers of safety per grid
ATR_MULTIPLIER = 2.0     # Dynamic volatility padding between DCA buys
TAKE_PROFIT_PCT = 0.012  # Targets ~1% Net ROI after double fees

# --- CAPITAL MANAGEMENT ---
INITIAL_CAPITAL_USD = 360.0 # ~₹30,000 total
CAPITAL_PER_COIN = INITIAL_CAPITAL_USD / len(SYMBOLS)
GRID_ALLOCATION = CAPITAL_PER_COIN / NUM_GRIDS
BULLET_SIZE = GRID_ALLOCATION / MAX_BULLETS

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'}
})

def load_all_states():
    """Robust state loader for Multi-Threaded Grid logic."""
    current_state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                current_state = json.load(f)
        except Exception as e:
            logging.error(f"State Load Error: {e}")
    
    # Ensure every symbol has exactly NUM_GRIDS initialized
    for s in SYMBOLS:
        if s not in current_state:
            current_state[s] = {
                "grids": [
                    {"active": False, "bullets": 0, "invested": 0.0, "coin": 0.0, "avg_p": 0.0} 
                    for _ in range(NUM_GRIDS)
                ],
                "total_profit_usd": 0.0
            }
    return current_state

def save_all_states(states):
    """Atomic save to prevent data corruption during power loss."""
    try:
        tmp_file = STATE_FILE + ".tmp"
        with open(tmp_file, 'w') as f:
            json.dump(states, f, indent=4)
        os.replace(tmp_file, STATE_FILE)
    except Exception as e:
        logging.error(f"State Save Error: {e}")

def notify(message):
    logging.info(message)
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try:
            requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=10)
        except Exception: pass

def get_data(symbol):
    """Fetch recent historical data for indicator stability."""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=300)
        if not ohlcv or len(ohlcv) < 250: return None
        return pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
    except Exception as e:
        logging.error(f"Binance API Error ({symbol}): {e}")
        return None

def analyze_and_trade(symbol, df, state):
    """Core logic for independent Overlapping Grids."""
    df['ema_200'] = ta.trend.EMAIndicator(df['c'], window=200).ema_indicator()
    df['rsi'] = ta.momentum.RSIIndicator(df['c'], window=14).rsi()
    df['atr'] = ta.volatility.AverageTrueRange(df['h'], df['l'], df['c'], window=14).average_true_range()
    
    # We use confirmed candles to avoid flickering signals
    confirmed = df.iloc[-2]
    current = df.iloc[-1]
    
    grids = state['grids']
    state_changed = False
    
    # 🔴 EXIT LOGIC (Process exits first to free up grids)
    for idx, g in enumerate(grids):
        if g['active'] and g['bullets'] > 0:
            profit = (current['c'] - g['avg_p']) / g['avg_p']
            if profit >= TAKE_PROFIT_PCT:
                sell_val = g['coin'] * current['c'] * 0.999
                net_profit_usd = sell_val - g['invested']
                
                msg = f"🔴 **SELL ALL {symbol} (Grid {idx+1})** 🔴\nPrice: ${current['c']:.2f}\nNet Profit: ₹{int(net_profit_usd * 83.5)}"
                notify(msg)
                trade_logger.info(f"SUCCESS: Closed {symbol} Grid {idx+1}. Profit: ${net_profit_usd:.2f} (₹{int(net_profit_usd * 83.5)})")
                
                # Update State
                state['total_profit_usd'] += net_profit_usd
                g.update({"active": False, "bullets": 0, "invested": 0.0, "coin": 0.0, "avg_p": 0.0})
                state_changed = True

    # 🟢 ENTRY LOGIC (Check if we can open a new grid)
    open_grids = sum([1 for g in grids if g['active']])
    if open_grids < NUM_GRIDS:
        # Check macro uptrend (with 10% buffer) and RSI panic
        if confirmed['rsi'] < 35 and current['c'] > (confirmed['ema_200'] * 0.90):
            # Find the first inactive grid and activate it
            for idx, g in enumerate(grids):
                if not g['active']:
                    g.update({
                        "active": True, 
                        "bullets": 1, 
                        "invested": BULLET_SIZE, 
                        "coin": (BULLET_SIZE * 0.999) / current['c'], 
                        "avg_p": current['c']
                    })
                    notify(f"🟢 **BUY {symbol} (Grid {idx+1}, Bullet 1/{MAX_BULLETS})** 🟢\nPrice: ${current['c']:.2f}\nReason: RSI Panic Dip.")
                    state_changed = True
                    break # Only open 1 grid per tick
                    
    # 🟡 DCA LOGIC (Check active grids for dynamic drops)
    for idx, g in enumerate(grids):
        if g['active'] and g['bullets'] < MAX_BULLETS:
            drop_needed = g['avg_p'] - (confirmed['atr'] * ATR_MULTIPLIER)
            if current['c'] <= drop_needed:
                g['bullets'] += 1
                g['invested'] += BULLET_SIZE
                g['coin'] += (BULLET_SIZE * 0.999) / current['c']
                g['avg_p'] = g['invested'] / (g['coin'] / 0.999)
                
                notify(f"🟡 **DCA ADDED: {symbol} (Grid {idx+1}, Bullet {g['bullets']}/{MAX_BULLETS})** 🟡\nPrice: ${current['c']:.2f}\nNew Avg: ${g['avg_p']:.2f}")
                state_changed = True

    return state_changed

def main():
    logging.info("--- TITAN ENGINE V39 STARTING (MULTI-THREADED GRID) ---")
    states = load_all_states()
    
    while True:
        try:
            changed = False
            for s in SYMBOLS:
                df = get_data(s)
                if df is not None:
                    if analyze_and_trade(s, df, states[s]):
                        changed = True
            
            if changed:
                save_all_states(states)

            time.sleep(CHECK_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            logging.info("Shutting down...")
            break
        except Exception as e:
            logging.error(f"Critical System Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
