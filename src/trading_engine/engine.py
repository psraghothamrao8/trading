import ccxt
import pandas as pd
import ta
import time
import os
import json
import logging
import requests
from datetime import datetime
from .config import *

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

trade_logger = logging.getLogger('trade_results')
trade_handler = logging.FileHandler(TRADE_LOG_FILE)
trade_handler.setFormatter(logging.Formatter('%(asctime)s: %(message)s'))
trade_logger.addHandler(trade_handler)

class TradingEngine:
    def __init__(self):
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'margin'}
        })
        self.states = self.load_all_states()

    def load_all_states(self):
        current_state = {}
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    current_state = json.load(f)
            except Exception: pass
        
        for s in SYMBOLS:
            if s not in current_state:
                current_state[s] = {
                    "grids": [
                        {"active": False, "pos": 0, "bullets": 0, "invested": 0.0, "size": 0.0, "avg_p": 0.0} 
                        for _ in range(NUM_GRIDS)
                    ]
                }
        return current_state

    def save_all_states(self):
        try:
            tmp_file = STATE_FILE + ".tmp"
            with open(tmp_file, 'w') as f:
                json.dump(self.states, f, indent=4)
            os.replace(tmp_file, STATE_FILE)
        except Exception as e:
            logging.error(f"Error saving state: {e}")

    def notify(self, message):
        logging.info(message)
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            try:
                requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=10)
            except Exception: pass

    def get_data(self, symbol):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=1000)
            if not ohlcv or len(ohlcv) < 850: return None
            return pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        except Exception as e:
            logging.error(f"Error fetching data for {symbol}: {e}")
            return None

    def analyze_and_trade(self, symbol, df):
        # Technical Indicators
        df['ema_macro'] = ta.trend.EMAIndicator(df['c'], window=800).ema_indicator()
        df['rsi'] = ta.momentum.RSIIndicator(df['c'], window=14).rsi()
        df['atr'] = ta.volatility.AverageTrueRange(df['h'], df['l'], df['c'], window=14).average_true_range()
        
        confirmed = df.iloc[-2]
        current = df.iloc[-1]
        
        state = self.states[symbol]
        grids = state['grids']
        state_changed = False
        
        macro_bull = current['c'] > confirmed['ema_macro']
        
        # 🔴 EXIT LOGIC
        for idx, g in enumerate(grids):
            if g['active'] and g['bullets'] > 0:
                # LONG EXIT
                if g['pos'] == 1:
                    profit = (current['c'] - g['avg_p']) / g['avg_p']
                    if profit >= TAKE_PROFIT_PCT:
                        sell_val = g['size'] * profit
                        net_profit_usd = sell_val - (g['size'] * 0.001 * 2)
                        
                        msg = f"🏁 **CLOSE MARGIN LONG {symbol} (Grid {idx+1})** 🏁\nPrice: ${current['c']:.2f}\nNet Profit: ${net_profit_usd:.2f}"
                        self.notify(msg)
                        trade_logger.info(f"SUCCESS: Long {symbol}. Profit: ${net_profit_usd:.2f}")
                        
                        g.update({"active": False, "pos": 0, "bullets": 0, "invested": 0.0, "size": 0.0, "avg_p": 0.0})
                        state_changed = True
                        
                # SHORT EXIT
                elif g['pos'] == -1:
                    profit = (g['avg_p'] - current['c']) / g['avg_p']
                    if profit >= TAKE_PROFIT_PCT:
                        sell_val = g['size'] * profit
                        net_profit_usd = sell_val - (g['size'] * 0.001 * 2)
                        
                        msg = f"🏁 **CLOSE MARGIN SHORT {symbol} (Grid {idx+1})** 🏁\nPrice: ${current['c']:.2f}\nNet Profit: ${net_profit_usd:.2f}"
                        self.notify(msg)
                        trade_logger.info(f"SUCCESS: Short {symbol}. Profit: ${net_profit_usd:.2f}")
                        
                        g.update({"active": False, "pos": 0, "bullets": 0, "invested": 0.0, "size": 0.0, "avg_p": 0.0})
                        state_changed = True

        # 🟢 ENTRY LOGIC 
        open_grids = sum([1 for g in grids if g['active']])
        if open_grids < NUM_GRIDS:
            if macro_bull and confirmed['rsi'] < 35:
                for idx, g in enumerate(grids):
                    if not g['active']:
                        g.update({
                            "active": True, "pos": 1, "bullets": 1, "invested": FIXED_BULLET_SIZE, 
                            "size": FIXED_BULLET_SIZE * LEVERAGE, "avg_p": current['c']
                        })
                        self.notify(f"🟢 **OPEN MARGIN LONG {symbol}** 🟢\nPrice: ${current['c']:.2f}\nReason: Macro Bull + RSI Dip.")
                        state_changed = True
                        break 
                        
            elif not macro_bull and confirmed['rsi'] > 65:
                for idx, g in enumerate(grids):
                    if not g['active']:
                        g.update({
                            "active": True, "pos": -1, "bullets": 1, "invested": FIXED_BULLET_SIZE, 
                            "size": FIXED_BULLET_SIZE * LEVERAGE, "avg_p": current['c']
                        })
                        self.notify(f"🔴 **OPEN MARGIN SHORT {symbol}** 🔴\nPrice: ${current['c']:.2f}\nReason: Macro Bear + RSI Peak.")
                        state_changed = True
                        break 
                        
        # 🟡 DCA LOGIC
        for idx, g in enumerate(grids):
            if g['active'] and g['bullets'] < MAX_BULLETS:
                dca_dist = confirmed['atr'] * ATR_MULTIPLIER
                
                if g['pos'] == 1 and current['c'] <= g['avg_p'] - dca_dist:
                    add_size = FIXED_BULLET_SIZE * LEVERAGE
                    g['avg_p'] = ((g['size'] * g['avg_p']) + (add_size * current['c'])) / (g['size'] + add_size)
                    g['bullets'] += 1
                    g['invested'] += FIXED_BULLET_SIZE
                    g['size'] += add_size
                    self.notify(f"🟡 **DCA LONG {symbol} (Bullet {g['bullets']}/{MAX_BULLETS})** 🟡\nPrice: ${current['c']:.2f}")
                    state_changed = True
                    
                elif g['pos'] == -1 and current['c'] >= g['avg_p'] + dca_dist:
                    add_size = FIXED_BULLET_SIZE * LEVERAGE
                    g['avg_p'] = ((g['size'] * g['avg_p']) + (add_size * current['c'])) / (g['size'] + add_size)
                    g['bullets'] += 1
                    g['invested'] += FIXED_BULLET_SIZE
                    g['size'] += add_size
                    self.notify(f"🟡 **DCA SHORT {symbol} (Bullet {g['bullets']}/{MAX_BULLETS})** 🟡\nPrice: ${current['c']:.2f}")
                    state_changed = True

        return state_changed

    def run(self):
        logging.info("--- OMNI-DIRECTIONAL MARGIN ENGINE INITIALIZED ---")
        while True:
            try:
                changed = False
                for s in SYMBOLS:
                    df = self.get_data(s)
                    if df is not None:
                        if self.analyze_and_trade(s, df):
                            changed = True
                
                if changed:
                    self.save_all_states()

                time.sleep(CHECK_INTERVAL_SECONDS)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logging.error(f"Critical System Error: {e}")
                time.sleep(60)
