import pandas as pd
import ta
import json
import os
from trading_notifier import analyze_signals

def test_signal_generation():
    print("--- RUNTIME LOGIC TEST ---")
    
    # Use consistent 'c' for close price as per the final engine
    prices_pullback = [150] * 250 + [160] * 40 + [155, 154, 153, 152, 151, 150] 
    df_pb = pd.DataFrame({'c': prices_pullback, 'h': prices_pullback, 'l': prices_pullback})
    
    # State: Not in trade
    state = {"in_trade": False, "position": "", "entry_price": 0.0}
    
    # Run logic
    signal, reason = analyze_signals(df_pb, state)
    print(f"Entry Test (Expect LONG or None): {signal}")

    # Test Exit
    state_in = {"in_trade": True, "position": "LONG", "entry_price": 100.0}
    # Create DF where price is 105 (Target Move is 4%, so 104 is TP)
    df_tp = pd.DataFrame({'c': [100]*250 + [105, 105], 'h': [105]*252, 'l': [100]*252})
    signal_tp, reason_tp = analyze_signals(df_tp, state_in)
    print(f"Exit TP Test (Expect CLOSE): {signal_tp}")

    print("\nRUNTIME TEST COMPLETE")

if __name__ == "__main__":
    test_signal_generation()
