from src.trading_engine.engine import TradingEngine

if __name__ == "__main__":
    try:
        engine = TradingEngine()
        engine.run()
    except KeyboardInterrupt:
        print("\nStopping the engine...")
    except Exception as e:
        print(f"Failed to start engine: {e}")
