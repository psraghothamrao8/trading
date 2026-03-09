# Crypto Trading Notifier 📈

An autonomous crypto trading signal application based on historical quantitative analysis.

## Overview
This application monitors **ETH/USDT** on Binance using a proven MACD and RSI crossover strategy on a 1-hour timeframe to filter out noise. It produces completely objective **BUY** and **SELL** signals.

**Why ETH/USDT?**
It is one of the most liquid, stable, and fundamentally strong cryptocurrencies. For a ₹30,000 spot trading portfolio, it offers the best balance of safety and profit potential without the extreme risks associated with low-cap coins.

## Strategy
*   **Buy:** MACD Bullish Crossover + RSI below 70 (Not overbought).
*   **Sell:** MACD Bearish Crossover + RSI above 30 (Not oversold).
*   Read `STRATEGY.md` for full details.

## Setup Instructions

### 1. Prerequisites
Ensure you have Python 3 installed on your system.
```bash
python3 --version
```

### 2. Install Dependencies
Install the required Python packages:
```bash
pip install -r requirements.txt
```

### 3. Optional: Setup Telegram Notifications (Recommended)
If you want the app to send signals directly to your phone, you can configure Telegram notifications:
1.  Open Telegram, search for `@BotFather`, and create a new bot to get a **Bot Token**.
2.  Search for `@userinfobot` to get your **Chat ID**.
3.  Copy the `.env.example` file to `.env`:
    ```bash
    cp .env.example .env
    ```
4.  Edit the `.env` file and paste your Token and Chat ID.

### 4. Run the Application
Start the notifier. It will run continuously in the background, checking the market every 5 minutes and outputting signals when the specific strategy conditions are met.
```bash
python3 trading_notifier.py
```

## How to Trade with the Signals
1. Wait for the app to output a `🟢 BUY SIGNAL`.
2. Open your Binance app and buy **ETH** using your ₹30,000 (USDT equivalent) in the **Spot** market. *(Tip: You can split your buys, e.g., buy with ₹15,000 first, and keep ₹15,000 to average down if the price drops further).*
3. Hold your ETH patiently.
4. When the app outputs a `🔴 SELL SIGNAL`, open Binance and sell your ETH back to USDT to secure profits (or cut losses).

**Important:** Keep this script running on a server or your PC so it never misses a signal!

*Disclaimer: This is for educational and experimental purposes. Do not use leverage (Futures/Options) with this strategy. Stick exclusively to Spot trading.*# trading
