import os
from dotenv import load_dotenv

load_dotenv()

# --- THE "OMNI-DIRECTIONAL MARGIN" ENGINE (FINAL V59) ---
SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'AVAX/USDT', 'DOGE/USDT', 'SUI/USDT'] 
TIMEFRAME = '15m'
CHECK_INTERVAL_SECONDS = 300 

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

STATE_FILE = os.path.join(DATA_DIR, "margin_omni_state.json")
LOG_FILE = os.path.join(DATA_DIR, "trading.log")
TRADE_LOG_FILE = os.path.join(DATA_DIR, "trade.txt")

# --- MATHEMATICAL STRATEGY PARAMETERS ---
LEVERAGE = 2             # 2x Spot Margin
NUM_GRIDS = 2            # 2 overlapping grids per coin
MAX_BULLETS = 4          # 4 Layers of deep DCA safety
ATR_MULTIPLIER = 2.5     # Volatility-scaled DCA steps
TAKE_PROFIT_PCT = 0.012  # 1.2% Market Move = 2.4% Net Equity Profit

# --- CAPITAL MANAGEMENT ---
INITIAL_CAPITAL_USD = 360.0
CAPITAL_PER_COIN = INITIAL_CAPITAL_USD / len(SYMBOLS)
GRID_ALLOCATION = CAPITAL_PER_COIN / NUM_GRIDS
FIXED_BULLET_SIZE = GRID_ALLOCATION / MAX_BULLETS 

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
