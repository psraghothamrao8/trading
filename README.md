# The Omni-Directional Margin Engine (V59) 📈

An autonomous, multi-asset crypto trading system designed for consistent **2.4% net equity profit** per cycle using **2x Spot Margin**.

## 🚀 Overview
Transitioned from simple spot trading to a sophisticated long/short margin harvesting system. This engine is designed to generate a consistent "salary" from the crypto markets, regardless of whether the trend is bullish or bearish.

**The "Titan Six" Basket:**
The bot monitors a diversified basket of high-liquidity assets:
*   **BTC, ETH, SOL, AVAX, DOGE, SUI**

## 🧠 Strategy: V59 Logic
*   **Macro Filtering:** Uses an **800-period EMA** (15m timeframe) to determine the macro regime.
    *   **Above 800 EMA:** Bull Market -> Only **Long** trades (borrow USDT to buy).
    *   **Below 800 EMA:** Bear Market -> Only **Short** trades (borrow coin to sell).
*   **Entry Precision:**
    *   **Long:** Wait for an RSI "Panic Dip" (< 35).
    *   **Short:** Wait for an RSI "Greed Spike" (> 65).
*   **Safety Nets (DCA):** Employs an **ATR-based DCA grid** (up to 4 safety bullets) to catch true bottoms/tops during pullbacks.
*   **Profit Target:** Aims for a **1.2% market move**, which results in **~2.4% profit** on 2x leveraged capital.
*   **Capital Management:** Fixed $360 portfolio, split into 6 buckets. Non-compounding strategy ensures profits are extracted and risk is capped.

## 🛠️ Setup Instructions

### 1. Prerequisites
Ensure you have Python 3.8+ installed.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy the example environment file and fill in your Telegram credentials:
```bash
cp .env.example .env
```
Edit `.env` and add:
*   `TELEGRAM_BOT_TOKEN`: Your bot token from @BotFather.
*   `TELEGRAM_CHAT_ID`: Your chat ID from @userinfobot.

### 4. Run the Engine
```bash
python trading_notifier.py
```
The bot will check the markets every 5 minutes and send actionable signals to your Telegram.

## 📊 How to Trade
When you receive a signal via Telegram:
1.  **🟢 OPEN MARGIN LONG:** Borrow USDT on Binance Margin, buy the coin.
2.  **🔴 OPEN MARGIN SHORT:** Borrow the Coin on Binance Margin, sell it to USDT.
3.  **🏁 CLOSE MARGIN:** Repay the loan on Binance to lock in your profit.

## ⚠️ Disclaimer
*This is for educational and experimental purposes. Margin trading involves risk. While 2x leverage is conservative, always monitor your liquidation prices and never trade with money you cannot afford to lose.*
