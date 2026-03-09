import pandas as pd
import numpy as np
from trading_notifier import calculate_indicators, check_for_signals

def test_pipeline():
    print("--- Detailed Signal Crossover Test ---")
    
    # 1. Create Bullish Crossover Mock Data
    # MACD Cross happens when MACD line goes from BELOW Signal to ABOVE Signal
    # RSI should be < 70
    # RSI (14) defaults to average gains/losses. To get RSI < 70 we need some flat periods.
    
    # Let's create a price movement that starts flat then goes up
    # 100 * 50 then [101, 102, 103, 104, 105, 106, 107, 108, 109, 110]
    prices = [100.0] * 60 + [101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0]
    timestamps = pd.date_range(start='2024-01-01', periods=len(prices), freq='1h')
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'close': prices,
        'open': prices,
        'high': prices,
        'low': prices,
        'volume': [1000] * len(prices)
    })
    
    df = calculate_indicators(df)
    
    # 2. Find a crossover point
    # check_for_signals uses index -2 (the last closed candle)
    # Let's iterate and see if a signal occurs anywhere in our mock data
    signal_found = False
    for i in range(20, len(df)):
        subset = df.iloc[:i+1]
        signal, reason, price, sig_time = check_for_signals(subset)
        if signal:
            print(f"Step 1: SUCCESS - Signal Detected at index {i}!")
            print(f"  - Signal: {signal}")
            print(f"  - Reason: {reason}")
            print(f"  - Price: ${price}")
            signal_found = True
            break
            
    if not signal_found:
        print("Step 1: FAILED - No BUY/SELL signal detected with this mock data. (Note: MACD crossover can be subtle).")

    # 3. Check technical indicators integrity
    latest_rsi = df['rsi'].iloc[-1]
    latest_macd = df['macd'].iloc[-1]
    latest_signal = df['macd_signal'].iloc[-1]
    
    print("\n--- Final Indicator Values (Index -1) ---")
    print(f"  - RSI: {latest_rsi:.2f} (Expected: ~100 if only going up, ~50 if flat)")
    print(f"  - MACD: {latest_macd:.4f}")
    print(f"  - Signal: {latest_signal:.4f}")
    
    if not np.isnan(latest_rsi) and not np.isnan(latest_macd):
        print("\nSUCCESS: Indicators are calculating properly (No NaN values).")
    else:
        print("\nFAILURE: Indicators contain NaN values (check window sizes).")

if __name__ == "__main__":
    test_pipeline()
