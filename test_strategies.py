import pandas as pd
import ta
import numpy as np

# Load the data we already fetched
df = pd.read_csv('sol_1yr_5m.csv')
df['ts'] = pd.to_datetime(df['ts'])

# --- Calculate indicators ---
df['rsi'] = ta.momentum.RSIIndicator(df['c'], window=14).rsi()
df['ema_200'] = ta.trend.EMAIndicator(df['c'], window=200).ema_indicator()
df['ema_1000'] = ta.trend.EMAIndicator(df['c'], window=1000).ema_indicator() # Approx 3.5 days trend

# Bollinger Bands
bb = ta.volatility.BollingerBands(df['c'], window=20, window_dev=2.5)
df['bb_l'] = bb.bollinger_lband()
df['bb_h'] = bb.bollinger_hband()

FEE = 0.001
INITIAL_USD = 360.0 # ~30,000 INR

def simulate(name, logic_fn):
    bal_usd = INITIAL_USD
    coin = 0.0
    trades = 0
    wins = 0
    max_dd = 0.0
    peak_bal = bal_usd
    
    state = {}
    
    for i in range(1000, len(df)):
        curr = df.iloc[i-1]
        prev = df.iloc[i-2]
        price = df.iloc[i]['o']
        
        # Execute custom logic
        bal_usd, coin, trades, wins, state = logic_fn(i, curr, prev, price, bal_usd, coin, trades, wins, state)
        
        # Track drawdown
        current_val = bal_usd + (coin * price * (1-FEE))
        if current_val > peak_bal:
            peak_bal = current_val
        dd = (current_val - peak_bal) / peak_bal
        if dd < max_dd:
            max_dd = dd

    final_val = bal_usd + (coin * df.iloc[-1]['c'] * (1-FEE))
    roi = ((final_val - INITIAL_USD) / INITIAL_USD) * 100
    win_rate = (wins / trades * 100) if trades > 0 else 0
    print(f"{name} | Trades: {trades} | Win%: {win_rate:.1f}% | Final: ${final_val:.2f} | ROI: {roi:.2f}% | Max DD: {max_dd*100:.2f}%")

# --- STRATEGY 1: WIDE DCA GRID (MACRO UPTREND ONLY) ---
def logic_wide_dca(i, curr, prev, price, bal, coin, trades, wins, state):
    max_bullets = 4
    if not state:
        state = {'bullets': 0, 'invested': 0.0, 'avg': 0.0, 'bullet_size': bal / max_bullets}
    
    if state['bullets'] == 0:
        # Initial Entry: Deep oversold AND Macro Uptrend (Price > EMA 1000)
        if curr['rsi'] < 30 and curr['c'] > curr['ema_1000']:
            cost = state['bullet_size']
            bal -= cost
            coin += (cost * (1-FEE)) / price
            state['invested'] += cost
            state['bullets'] = 1
            state['avg'] = price
    elif state['bullets'] < max_bullets:
        # Wide dynamic drops: -3%, -6%, -12%
        drop = (price - state['avg']) / state['avg']
        target_drop = [-0.03, -0.06, -0.12][state['bullets'] - 1]
        
        if drop <= target_drop and curr['rsi'] < 35:
            cost = state['bullet_size']
            bal -= cost
            coin += (cost * (1-FEE)) / price
            state['invested'] += cost
            state['bullets'] += 1
            state['avg'] = state['invested'] / (coin / (1-FEE))
            
    if state['bullets'] > 0:
        current_val = coin * price * (1-FEE)
        profit = (current_val - state['invested']) / state['invested']
        
        # Target 1.5% net profit
        if profit >= 0.015:
            bal += current_val
            wins += 1
            trades += 1
            coin = 0.0
            state = {}
            
    return bal, coin, trades, wins, state

# --- STRATEGY 2: HARD STOP SCALPER ---
def logic_hard_stop(i, curr, prev, price, bal, coin, trades, wins, state):
    if coin == 0:
        # Buy: Panic bounce in an uptrend
        if curr['c'] <= curr['bb_l'] and curr['rsi'] < 30 and curr['c'] > curr['ema_200']:
            coin = (bal * (1-FEE)) / price
            bal = 0.0
            state['entry'] = price
    else:
        profit = (price - state['entry']) / state['entry']
        # TP 2%, SL 1%
        if profit >= 0.02 or profit <= -0.01:
            bal = coin * price * (1-FEE)
            if bal > INITIAL_USD: wins += 1 # Simplified win tracking
            trades += 1
            coin = 0.0
            state = {}
            
    return bal, coin, trades, wins, state

# --- STRATEGY 3: RSI DIVERGENCE + ATR TRAILING STOP ---
def logic_atr_trail(i, curr, prev, price, bal, coin, trades, wins, state):
    if coin == 0:
        # Buy: RSI crosses above 30 from below (momentum shifting up)
        if prev['rsi'] < 30 and curr['rsi'] >= 30 and curr['c'] > curr['ema_1000']:
            coin = (bal * (1-FEE)) / price
            bal = 0.0
            state['entry'] = price
            state['highest'] = price
    else:
        profit = (price - state['entry']) / state['entry']
        if price > state['highest']: state['highest'] = price
        
        # Take profit at 1.5%
        if profit >= 0.015:
            bal = coin * price * (1-FEE)
            wins += 1
            trades += 1
            coin = 0.0
            state = {}
        # Trailing stop: If drops 1.5% from peak while in trade
        elif (state['highest'] - price) / state['highest'] >= 0.015:
            bal = coin * price * (1-FEE)
            trades += 1
            coin = 0.0
            state = {}
            
    return bal, coin, trades, wins, state

print("\nRunning 1-Year Mega-Backtest (100,000+ Candles)...")
simulate("1. Wide DCA Grid (Uptrend Only)", logic_wide_dca)
simulate("2. Hard Stop Loss Scalper (TP 2%, SL 1%)", logic_hard_stop)
simulate("3. RSI Momentum + Trailing Stop", logic_atr_trail)

