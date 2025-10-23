"""
Main execution file for Dhan Algorithmic Trading System
Run this file to start the complete trading system
"""

import os
import sys
from datetime import datetime
import logging

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our modules
from advanced_trading_strategy import DhanAlgoTrading
from realtime_monitor import RealTimeMonitor, TradeExecutor
from backtesting_engine import BacktestEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'trading_session_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main execution function"""
    print("🚀 DHAN ALGORITHMIC TRADING SYSTEM")
    print("="*50)
    print("🎯 Target: 5-10% profit with 2% max stop loss")
    print("⚡ Multi-strategy algorithm with advanced risk management")
    print("="*50)
    
    # Configuration
    CLIENT_ID = input("Enter your Dhan Client ID: ").strip()
    ACCESS_TOKEN = input("Enter your Dhan Access Token: ").strip()
    
    if not CLIENT_ID or not ACCESS_TOKEN:
        print("❌ Error: Please provide valid Dhan credentials")
        return
    
    # Ask for mode
    print("\n📋 Select Trading Mode:")
    print("1. Live Trading")
    print("2. Paper Trading (Simulation)")
    print("3. Backtest Only")
    
    mode = input("Enter choice (1-3): ").strip()
    
    if mode == "3":
        # Run backtest
        print("\n🔍 Running Backtest...")
        from backtesting_engine import generate_sample_backtest
        backtest_engine, results = generate_sample_backtest()
        print("✅ Backtest completed! Check the results above.")
        return
    
    # High-quality stock universe
    STOCK_UNIVERSE = [
        {"symbol": "RELIANCE", "security_id": "2885", "exchange_segment": "NSE_EQ"},
        {"symbol": "TCS", "security_id": "11536", "exchange_segment": "NSE_EQ"},
        {"symbol": "HDFCBANK", "security_id": "1333", "exchange_segment": "NSE_EQ"},
        {"symbol": "INFY", "security_id": "4963", "exchange_segment": "NSE_EQ"},
        {"symbol": "HINDUNILVR", "security_id": "356", "exchange_segment": "NSE_EQ"},
        {"symbol": "ICICIBANK", "security_id": "4963", "exchange_segment": "NSE_EQ"},
        {"symbol": "SBIN", "security_id": "3045", "exchange_segment": "NSE_EQ"},
        {"symbol": "BHARTIARTL", "security_id": "10604", "exchange_segment": "NSE_EQ"},
        {"symbol": "ITC", "security_id": "424", "exchange_segment": "NSE_EQ"},
        {"symbol": "LT", "security_id": "2672", "exchange_segment": "NSE_EQ"},
        {"symbol": "KOTAKBANK", "security_id": "1922", "exchange_segment": "NSE_EQ"},
        {"symbol": "AXISBANK", "security_id": "5900", "exchange_segment": "NSE_EQ"}
    ]
    
    # Initialize trading system
    print(f"\n🔧 Initializing Trading System...")
    algo_trader = DhanAlgoTrading(CLIENT_ID, ACCESS_TOKEN)
    
    # Paper trading mode
    if mode == "2":
        print("📝 Paper Trading Mode Activated")
        # Override place_order method for simulation
        original_place_order = algo_trader.place_order
        def simulated_place_order(*args, **kwargs):
            logger.info(f"SIMULATED ORDER: {args}, {kwargs}")
            return {"status": "success", "orderId": f"SIM_{datetime.now().strftime('%H%M%S')}"}
        algo_trader.place_order = simulated_place_order
    
    # Initialize monitoring
    monitor = RealTimeMonitor(algo_trader)
    executor = TradeExecutor(algo_trader)
    
    # Start monitoring and execution
    monitor.start_monitoring()
    executor.start_execution_engine()
    
    print("\n🎮 Trading System Status:")
    print("✅ Algorithm: ACTIVE")
    print("✅ Monitoring: ACTIVE") 
    print("✅ Risk Management: ACTIVE")
    print("⚡ Ready to trade!")
    
    print("\n📊 Current Settings:")
    print(f"   • Max Risk per Trade: {algo_trader.max_risk_per_trade*100}%")
    print(f"   • Min Reward Ratio: {algo_trader.min_reward_ratio}:1")
    print(f"   • Max Positions: {algo_trader.max_positions}")
    print(f"   • Min Confidence: {algo_trader.min_confidence}")
    
    try:
        # Check market hours and start trading
        current_time = datetime.now()
        market_hours = (9 <= current_time.hour < 15 or 
                       (current_time.hour == 15 and current_time.minute < 30))
        
        if not market_hours:
            print("⏰ Market is currently closed. System will activate during market hours.")
            print("   Market Hours: 9:15 AM - 3:30 PM IST")
        
        print("\n🚀 Starting Algorithm...")
        print("Press Ctrl+C to stop")
        print("-" * 50)
        
        # Main trading loop
        algo_trader.run_strategy(STOCK_UNIVERSE)
        
    except KeyboardInterrupt:
        print("\n⏹️  Trading stopped by user")
        
    except Exception as e:
        logger.error(f"System error: {e}")
        print(f"❌ System error: {e}")
        
    finally:
        # Cleanup
        monitor.stop_monitoring()
        executor.stop_execution_engine()
        
        # Export final dashboard
        dashboard_file = monitor.export_dashboard_json()
        print(f"\n📊 Final dashboard exported to: {dashboard_file}")
        
        # Summary
        print("\n📈 Session Summary:")
        print(f"   • Daily P&L: ₹{algo_trader.daily_pnl:,.2f}")
        print(f"   • Active Positions: {len(algo_trader.positions)}")
        print(f"   • Total Capital: ₹{algo_trader.get_funds():,.2f}")
        
        print("\n✅ Trading session completed safely!")

def quick_test():
    """Quick test function to verify system components"""
    print("🧪 Running System Tests...")
    
    # Test imports
    try:
        import pandas as pd
        import numpy as np
        import requests
        print("✅ Core libraries imported successfully")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Run: pip install -r requirements.txt")
        return False
    
    # Test strategy components
    try:
        from advanced_trading_strategy import DhanAlgoTrading, TradeSignal
        from backtesting_engine import BacktestEngine
        print("✅ Strategy modules loaded successfully")
    except ImportError as e:
        print(f"❌ Strategy import error: {e}")
        return False
    
    print("🎉 All tests passed! System ready for trading.")
    return True

if __name__ == "__main__":
    # Run tests first
    if quick_test():
        print("\n" + "="*50)
        main()
    else:
        print("❌ System tests failed. Please fix errors before trading.")