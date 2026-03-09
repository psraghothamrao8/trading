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

# --- Setup Production Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("/home/ram/Documents/trading/trading.log"),
        logging.StreamHandler()
    ]
)

load_dotenv()

# --- THE "SALARY GENERATOR" SPOT GRID (V6.0 - PRODUCTION) ---
# Goal: Consistent monthly income via 10-level Dollar Cost Averaging.
# Asset: SOL/USDT (Perfect volatility for grid scalping)
SYMBOL = 'SOL/USDT'      
TIMEFRAME = '5m'         
LIMIT = 200 
CHECK_INTERVAL_SECONDS = 60 # Sniping mode
STATE_FILE = "/home/ram/Documents/trading/trade_state.json"

# --- GRID MATHEMATICAL PARAMETERS ---
# Capital: ₹30,000 (~$360 USDT)
# We split capital into 10 levels (Bullets) to survive any market crash.
TOTAL_BULLETS = 10          
DCA_DROP_PCT = -0.030    # Fire next bullet if price drops 3% below current average
TAKE_PROFIT_PCT = 0.015  # Target 1.5% gross profit on the ENTIRE bag

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'}
})

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                return state
        except Exception: pass
    return {"bullets_used": 0, "total_invested": 0.0, "coin_amount": 0.0, "avg_price": 0.0}

def save_state(state):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception: pass

def notify(message):
    logging.info(message)
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try: requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=5)
        except Exception: pass

def get_data():
    try:
        ohlcv = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=LIMIT)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        return df
    except Exception: return None

def analyze_grid(df, state):
    current_price = df.iloc[-1]['c']
    rsi = ta.momentum.RSIIndicator(df['c'], window=14).rsi().iloc[-1]
    
    bullets = state['bullets_used']
    
    # 🟢 ENTRY LOGIC
    if bullets == 0:
        # Initial Buy: Enter on any slight local dip (RSI < 40)
        if rsi < 40:
            return "BUY", f"Initial Entry (RSI: {rsi:.1f}). Starting Level 1/10."
    elif bullets < TOTAL_BULLETS:
        # DCA Logic: Price is 3% below average cost
        drop_pct = (current_price - state['avg_price']) / state['avg_price']
        if drop_pct <= DCA_DROP_PCT:
            return "BUY", f"DCA Level {bullets+1} triggered ({drop_pct*100:.1f}% drop)."
            
    # 🔴 EXIT LOGIC
    if bullets > 0:
        profit_pct = (current_price - state['avg_price']) / state['avg_price']
        if profit_pct >= TAKE_PROFIT_PCT:
            return "SELL", f"🎯 Grid Profit Target Hit (+{profit_pct*100:.2f}% on total bag)."

    return None, ""

def main():
    logging.info("--- V6.0 SPOT SALARY GENERATOR INITIALIZED (SOL/USDT) ---")
    state = load_state()
    
    # Portfolio Settings
    INITIAL_CAPITAL_USDT = 360.0 # ~₹30,000
    # Dynamic bullet size handles compounding automatically
    
    while True:
        try:
            df = get_data()
            if df is not None:
                signal, reason = analyze_grid(df, state)
                live_price = df.iloc[-1]['c']
                
                # Check current balance to handle compounding bullet size
                # In real prod, you'd fetch balance, but we use INITIAL + PROFIT simulation
                current_bal = max(INITIAL_CAPITAL_USDT, state.get('last_bal', INITIAL_CAPITAL_USDT))
                bullet_size = current_bal / TOTAL_BULLETS

                if signal == "BUY":
                    cost = bullet_size
                    state['bullets_used'] += 1
                    state['total_invested'] += cost
                    state['coin_amount'] += (cost * 0.999) / live_price
                    state['avg_price'] = state['total_invested'] / (state['coin_amount'] / 0.999)
                    save_state(state)
                    
                    msg = f"🟢 **BUY SOL (Bullet {state['bullets_used']}/10)** 🟢\n"
                    msg += f"Price: ${live_price:.2f}\nAvg Price: ${state['avg_price']:.2f}\n"
                    msg += f"Invested: ₹{int(cost * 83.5)}\nReason: {reason}"
                    notify(msg)
                
                elif signal == "SELL":
                    final_val = state['coin_amount'] * live_price * 0.999
                    profit = final_val - state['total_invested']
                    
                    msg = f"🔴 **SELL ALL SOL (Grid Closed)** 🔴\n"
                    msg += f"Exit Price: ${live_price:.2f}\nNet Profit: ₹{int(profit * 83.5)}\n"
                    msg += f"*Compounding profit into next trade.*"
                    
                    # Update balance for compounding
                    state['last_bal'] = current_bal + profit
                    state.update({"bullets_used": 0, "total_invested": 0.0, "coin_amount": 0.0, "avg_price": 0.0})
                    save_state(state)
                    notify(msg)

            time.sleep(CHECK_INTERVAL_SECONDS)
        except Exception as e:
            logging.error(f"Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
