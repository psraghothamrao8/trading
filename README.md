# Omni-Directional Margin Trading System (V59)

A quantitative crypto-asset trading engine designed for multi-asset execution using Binance Spot Margin. This system implements a dual-directional strategy (Long/Short) to capture returns across varying market regimes.

## 🏛️ System Architecture

### 1. Trend-Following & Mean Reversion
The system utilizes a hybrid approach to market participation:
*   **Macro Regime Filtering:** An 800-period Exponential Moving Average (EMA) on the 15-minute timeframe defines the primary trend.
*   **Tactical Execution:** Relative Strength Index (RSI) thresholds are used to identify mean-reversion opportunities within the defined trend.
    *   **Bullish Regime (Price > 800 EMA):** Executes long positions on RSI pullbacks (< 35).
    *   **Bearish Regime (Price < 800 EMA):** Executes short positions on RSI extensions (> 65).

### 2. Risk Mitigation & Position Sizing
*   **Asset Diversification:** Capital is distributed across a high-liquidity basket (BTC, ETH, SOL, AVAX, DOGE, SUI).
*   **Dynamic Grid Logic:** Implements an Average True Range (ATR) based DCA (Dollar-Cost Averaging) model with up to 4 safety layers to mitigate volatility-induced drawdown.
*   **Conservative Leverage:** Operates at 2x Spot Margin, significantly reducing liquidation risks compared to traditional futures derivatives.
*   **Capital Preservation:** A non-compounding allocation model ensures that realized profits are isolated from the primary trading capital.

## ⚙️ Technical Specifications
*   **Timeframe:** 15-minute resolution.
*   **Execution Frequency:** 300-second polling interval.
*   **Target ROI:** 1.2% asset price movement (equivalent to ~2.4% equity return at 2x leverage).
*   **Infrastructure:** Python-based engine utilizing `ccxt`, `pandas`, and `ta`.

## 🚀 Deployment & Installation

### 1. Environment Setup
The system requires Python 3.8+ and a dedicated virtual environment.
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration
The engine requires environment variables for secure notification handling:
```bash
cp .env.example .env
```
Configure your `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` within the `.env` file to receive real-time execution alerts.

### 3. Execution
Initialize the trading engine:
```bash
python main.py
```

## 📊 Operational Workflow
The engine provides high-fidelity signals via Telegram for manual or semi-automated execution on the Binance Margin interface:
1.  **Long Entry:** Borrow USDT to establish a long position.
2.  **Short Entry:** Borrow the base asset to establish a short position.
3.  **Position Liquidation:** Utilize the "Repay" function to close positions and realize PnL.

## ⚖️ Disclaimer
This software is provided for educational and research purposes. Quantitative trading involves significant risk. The 2x leverage model is designed for risk mitigation, but market volatility can lead to capital loss. Users should perform their own due diligence before deploying capital.
