import pandas as pd
import numpy as np

def run_stress_test():
    print("--- DCA STRATEGY RECOVERY TEST ---")
    
    # Simulate Price: 100 -> 90 (Crash) -> 105 (Recovery)
    prices = [100, 98, 96, 94, 92, 90, 92, 94, 96, 98, 100, 102, 104, 106]
    rsi_vals = [30, 25, 20, 15, 10, 5, 15, 25, 35, 45, 55, 65, 75, 85]
    
    state = {"bullets_used": 0, "total_invested": 0.0, "coin_amount": 0.0, "avg_price": 0.0}
    bullet_size = 75.0 
    dca_drop = -0.015
    tp_target = 0.012
    fee = 0.001
    
    for i, p in enumerate(prices):
        rsi = rsi_vals[i]
        
        # BUY
        if state['bullets_used'] == 0:
            if rsi < 35:
                state['bullets_used'] = 1
                state['total_invested'] = bullet_size
                state['coin_amount'] = (bullet_size * (1-fee)) / p
                state['avg_price'] = p
                print(f"Step {i}: [BUY 1] Price: {p}, Avg: {state['avg_price']:.2f}")
        elif state['bullets_used'] < 4:
            drop = (p - state['avg_price']) / state['avg_price']
            if drop <= dca_drop:
                state['bullets_used'] += 1
                state['total_invested'] += bullet_size
                state['coin_amount'] += (bullet_size * (1-fee)) / p
                state['avg_price'] = state['total_invested'] / (state['coin_amount'] / (1-fee))
                print(f"Step {i}: [BUY {state['bullets_used']}] Price: {p}, New Avg: {state['avg_price']:.2f}, Drop: {drop*100:.1f}%")
        
        # SELL
        if state['bullets_used'] > 0:
            profit = (p - state['avg_price']) / state['avg_price']
            if profit >= tp_target:
                print(f"Step {i}: [SELL ALL] Price: {p}, Profit: {profit*100:.2f}%")
                state = {"bullets_used": 0, "total_invested": 0.0, "coin_amount": 0.0, "avg_price": 0.0}

    if state['bullets_used'] == 0:
        print("\nPASS: Strategy successfully recovered and exited in profit after a 10% crash.")
    else:
        print("\nFAIL: Strategy still stuck.")

run_stress_test()
