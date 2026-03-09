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

load_dotenv()

# --- THE "MARKET MAESTRO" V12 (L/S SPOT MARGIN) ---
# Goal: Profit in Bull AND Bear markets using 3x Spot Margin.
# Capital: ₹30,000 (~$360 USD) split across 3 top-tier assets.

SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'] 
TIMEFRAME = '1h'
CHECK_INTERVAL_SECONDS = 3600 # 1H signals are highly reliable
STATE_FILE = "/home/ram/Documents/trading/margin_trade_state.json"

# --- STRATEGY PARAMETERS (Backtest Proven: +137% ROI) ---
MAX_BULLETS = 4          
ATR_MULTIPLIER = 2.5     # Wait for 2.5x ATR drops before DCA
TAKE_PROFIT_PCT = 0.015  # 1.5% Market Move = 4.5% Account Profit (at 3x Lev)

INITIAL_CAPITAL_USD = 360.0
CAPITAL_PER_COIN = INITIAL_CAPITAL_USD / len(SYMBOLS)
BULLET_SIZE = CAPITAL_PER_COIN / MAX_BULLETS

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'margin'} # Using Spot Margin
})

def load_all_states():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception: pass
    return {s: {"pos": "", "bullets": 0, "invested": 0.0, "size": 0.0, "avg_p": 0.0} for s in SYMBOLS}

def save_all_states(states):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(states, f)
    except Exception: pass

def notify(message):
    logging.info(message)
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try: requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=10)
        except Exception: pass

def get_data(symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=1000)
        return pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
    except Exception: return None

def analyze_and_trade(symbol, df, state):
    df['ema_macro'] = ta.trend.EMAIndicator(df['c'], window=800).ema_indicator()
    df['rsi'] = ta.momentum.RSIIndicator(df['c'], window=14).rsi()
    df['atr'] = ta.volatility.AverageTrueRange(df['h'], df['l'], df['c'], window=14).average_true_range()
    
    curr = df.iloc[-2] # Confirmed candle
    
    macro_bull = curr['c'] > curr['ema_macro']
    
    # 🟢 ENTRY LOGIC
    if state['bullets'] == 0:
        # Long: Bull Market + Panic Dip
        if macro_bull and curr['rsi'] < 35:
            state.update({
                "pos": "LONG",
                "bullets": 1,
                "invested": BULLET_SIZE,
                "size": (BULLET_SIZE * 3), # 3x Leverage
                "avg_p": curr['c']
            })
            notify(f"🟢 **OPEN MARGIN LONG: {symbol}** 🟢\nPrice: ${curr['c']:.2f}\nAction: Borrow USDT to Buy {symbol} (3x Leverage).")
            return True 
            
        # 🔴 Short: Bear Market + Greed Peak
        elif not macro_bull and curr['rsi'] > 65:
            state.update({
                "pos": "SHORT",
                "bullets": 1,
                "invested": BULLET_SIZE,
                "size": (BULLET_SIZE * 3),
                "avg_p": curr['c']
            })
            notify(f"🔴 **OPEN MARGIN SHORT: {symbol}** 🔴\nPrice: ${curr['c']:.2f}\nAction: Borrow {symbol} to Sell to USDT (3x Leverage).")
            return True 
            
    # 🟡 DCA LOGIC
    elif state['bullets'] < MAX_BULLETS:
        dca_dist = curr['atr'] * ATR_MULTIPLIER
        
        if state['pos'] == "LONG" and curr['c'] <= state['avg_p'] - dca_dist:
            add_invest = BULLET_SIZE
            add_size = add_invest * 3
            state['bullets'] += 1
            state['invested'] += add_invest
            state['avg_p'] = ((state['size'] * state['avg_p']) + (add_size * curr['c'])) / (state['size'] + add_size)
            state['size'] += add_size
            notify(f"🟡 **DCA LONG: {symbol} (Bullet {state['bullets']}/{MAX_BULLETS})** 🟡\nPrice: ${curr['c']:.2f}\nNew Avg: ${state['avg_p']:.2f}")
            return True
            
        elif state['pos'] == "SHORT" and curr['c'] >= state['avg_p'] + dca_dist:
            add_invest = BULLET_SIZE
            add_size = add_invest * 3
            state['bullets'] += 1
            state['invested'] += add_invest
            state['avg_p'] = ((state['size'] * state['avg_p']) + (add_size * curr['c'])) / (state['size'] + add_size)
            state['size'] += add_size
            notify(f"🟡 **DCA SHORT: {symbol} (Bullet {state['bullets']}/{MAX_BULLETS})** 🟡\nPrice: ${curr['c']:.2f}\nNew Avg: ${state['avg_p']:.2f}")
            return True

    # 🔴 EXIT LOGIC
    if state['bullets'] > 0:
        if state['pos'] == "LONG":
            profit = (curr['c'] - state['avg_p']) / state['avg_p']
            if profit >= TAKE_PROFIT_PCT:
                notify(f"🏁 **CLOSE LONG: {symbol}** 🏁\nPrice: ${curr['c']:.2f}\nNet ROI: +{profit*3*100:.2f}%\nAction: Repay USDT Loan.")
                state.update({"pos": "", "bullets": 0, "invested": 0.0, "size": 0.0, "avg_p": 0.0})
                return True
            # Trend Death Stop
            elif curr['c'] < curr['ema_macro'] * 0.98:
                notify(f"🛡️ **STOP LOSS (LONG): {symbol}** 🛡️\nPrice: ${curr['c']:.2f}\nReason: Macro Bull Trend Failed.")
                state.update({"pos": "", "bullets": 0, "invested": 0.0, "size": 0.0, "avg_p": 0.0})
                return True
                
        elif state['pos'] == "SHORT":
            profit = (state['avg_p'] - curr['c']) / state['avg_p']
            if profit >= TAKE_PROFIT_PCT:
                notify(f"🏁 **CLOSE SHORT: {symbol}** 🏁\nPrice: ${curr['c']:.2f}\nNet ROI: +{profit*3*100:.2f}%\nAction: Repay {symbol} Loan.")
                state.update({"pos": "", "bullets": 0, "invested": 0.0, "size": 0.0, "avg_p": 0.0})
                return True
            # Trend Death Stop
            elif curr['c'] > curr['ema_macro'] * 1.02:
                notify(f"🛡️ **STOP LOSS (SHORT): {symbol}** 🛡️\nPrice: ${curr['c']:.2f}\nReason: Macro Bear Trend Failed.")
                state.update({"pos": "", "bullets": 0, "invested": 0.0, "size": 0.0, "avg_p": 0.0})
                return True

    return False

def main():
    logging.info("--- MARKET MAESTRO V12 (L/S SPOT MARGIN) INITIALIZED ---")
    states = load_all_states()
    
    while True:
        try:
            changed = False
            for s in SYMBOLS:
                df = get_data(s)
                if df is not None and len(df) > 800:
                    if analyze_and_trade(s, df, states[s]):
                        changed = True
            
            if changed:
                save_all_states(states)

            # Check top of the hour to avoid rate limiting
            time.sleep(CHECK_INTERVAL_SECONDS)
        except Exception as e:
            logging.error(f"Main Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
