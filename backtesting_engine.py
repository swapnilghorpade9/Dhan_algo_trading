import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class BacktestEngine:
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = {}
        self.closed_trades = []
        self.equity_curve = []
        self.daily_returns = []
        
    def simulate_trade(self, entry_date: datetime, exit_date: datetime, 
                      entry_price: float, exit_price: float, quantity: int,
                      strategy: str, symbol: str) -> Dict:
        """Simulate a single trade"""
        # Calculate trade metrics
        gross_pnl = (exit_price - entry_price) * quantity
        commission = 20  # Flat ₹20 per trade
        net_pnl = gross_pnl - commission
        
        # Calculate returns
        trade_return = net_pnl / (entry_price * quantity)
        hold_days = (exit_date - entry_date).days
        
        trade_record = {
            'entry_date': entry_date,
            'exit_date': exit_date,
            'symbol': symbol,
            'strategy': strategy,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'quantity': quantity,
            'gross_pnl': gross_pnl,
            'commission': commission,
            'net_pnl': net_pnl,
            'return_pct': trade_return * 100,
            'hold_days': hold_days
        }
        
        self.closed_trades.append(trade_record)
        self.capital += net_pnl
        
        return trade_record
    
    def backtest_strategy(self, historical_data: Dict[str, pd.DataFrame], 
                         strategy_signals: Dict[str, List]) -> Dict:
        """Run comprehensive backtest"""
        
        # Process all signals chronologically
        all_signals = []
        for symbol, signals in strategy_signals.items():
            for signal in signals:
                signal['symbol'] = symbol
                all_signals.append(signal)
        
        # Sort by timestamp
        all_signals.sort(key=lambda x: x['timestamp'])
        
        # Process signals
        for signal in all_signals:
            if signal['signal_type'] == 'BUY':
                self._process_buy_signal(signal, historical_data)
        
        # Calculate performance metrics
        return self.calculate_performance_metrics()
    
    def _process_buy_signal(self, signal: Dict, historical_data: Dict[str, pd.DataFrame]):
        """Process buy signal and simulate trade lifecycle"""
        symbol = signal['symbol']
        entry_price = signal['entry_price']
        target_price = signal['target_price']
        stop_loss = signal['stop_loss']
        
        if symbol not in historical_data:
            return
        
        df = historical_data[symbol]
        entry_date = signal['timestamp']
        
        # Find entry point in historical data
        entry_idx = df.index.get_loc(entry_date, method='nearest')
        
        # Calculate position size (2% risk)
        risk_amount = self.capital * 0.02
        risk_per_share = entry_price - stop_loss
        quantity = int(risk_amount / risk_per_share) if risk_per_share > 0 else 1
        
        # Check if we have enough capital
        required_capital = entry_price * quantity
        if required_capital > self.capital * 0.2:  # Max 20% per position
            quantity = int(self.capital * 0.2 / entry_price)
        
        if quantity <= 0:
            return
        
        # Simulate trade outcome
        exit_price = None
        exit_date = None
        exit_reason = ""
        
        # Look for exit conditions in subsequent data
        for i in range(entry_idx + 1, min(entry_idx + 5 * 24, len(df))):  # Max 5 days
            current_price = df['close'].iloc[i]
            current_date = df.index[i]
            
            # Check stop loss
            if current_price <= stop_loss:
                exit_price = stop_loss
                exit_date = current_date
                exit_reason = "STOP_LOSS"
                break
            
            # Check target
            elif current_price >= target_price:
                exit_price = target_price
                exit_date = current_date
                exit_reason = "TARGET"
                break
        
        # If no exit condition met, exit at last price
        if exit_price is None:
            exit_price = df['close'].iloc[min(entry_idx + 5 * 24, len(df) - 1)]
            exit_date = df.index[min(entry_idx + 5 * 24, len(df) - 1)]
            exit_reason = "TIME_EXIT"
        
        # Record trade
        trade = self.simulate_trade(
            entry_date, exit_date, entry_price, exit_price,
            quantity, signal['strategy'], symbol
        )
        
        trade['exit_reason'] = exit_reason
        
    def calculate_performance_metrics(self) -> Dict:
        """Calculate comprehensive performance metrics"""
        if not self.closed_trades:
            return {}
        
        df_trades = pd.DataFrame(self.closed_trades)
        
        # Basic metrics
        total_trades = len(df_trades)
        winning_trades = len(df_trades[df_trades['net_pnl'] > 0])
        losing_trades = len(df_trades[df_trades['net_pnl'] < 0])
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        
        # P&L metrics
        total_pnl = df_trades['net_pnl'].sum()
        gross_profit = df_trades[df_trades['net_pnl'] > 0]['net_pnl'].sum()
        gross_loss = abs(df_trades[df_trades['net_pnl'] < 0]['net_pnl'].sum())
        
        # Return metrics
        total_return = (self.capital - self.initial_capital) / self.initial_capital * 100
        avg_return_per_trade = df_trades['return_pct'].mean()
        
        # Risk metrics
        max_loss = df_trades['net_pnl'].min()
        max_gain = df_trades['net_pnl'].max()
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf
        
        # Time metrics
        avg_hold_days = df_trades['hold_days'].mean()
        
        # Strategy breakdown
        strategy_performance = df_trades.groupby('strategy').agg({
            'net_pnl': ['sum', 'mean', 'count'],
            'return_pct': 'mean'
        }).round(2)
        
        # Exit reason analysis
        exit_analysis = df_trades['exit_reason'].value_counts()
        
        metrics = {
            'total_return_pct': round(total_return, 2),
            'total_pnl': round(total_pnl, 2),
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate_pct': round(win_rate, 2),
            'avg_return_per_trade': round(avg_return_per_trade, 2),
            'profit_factor': round(profit_factor, 2),
            'max_gain': round(max_gain, 2),
            'max_loss': round(max_loss, 2),
            'avg_hold_days': round(avg_hold_days, 2),
            'final_capital': round(self.capital, 2),
            'strategy_performance': strategy_performance,
            'exit_analysis': exit_analysis,
            'trades_df': df_trades
        }
        
        return metrics
    
    def plot_performance(self, metrics: Dict):
        """Create performance visualization plots"""
        if not self.closed_trades:
            print("No trades to plot")
            return
        
        df_trades = metrics['trades_df']
        
        # Create subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Backtest Performance Analysis', fontsize=16)
        
        # 1. Equity curve
        df_trades['cumulative_pnl'] = df_trades['net_pnl'].cumsum()
        df_trades['equity'] = self.initial_capital + df_trades['cumulative_pnl']
        
        axes[0, 0].plot(df_trades['exit_date'], df_trades['equity'])
        axes[0, 0].set_title('Equity Curve')
        axes[0, 0].set_xlabel('Date')
        axes[0, 0].set_ylabel('Portfolio Value (₹)')
        axes[0, 0].grid(True)
        
        # 2. Returns distribution
        axes[0, 1].hist(df_trades['return_pct'], bins=20, alpha=0.7, edgecolor='black')
        axes[0, 1].axvline(df_trades['return_pct'].mean(), color='red', linestyle='--', 
                          label=f'Mean: {df_trades["return_pct"].mean():.2f}%')
        axes[0, 1].set_title('Returns Distribution')
        axes[0, 1].set_xlabel('Return %')
        axes[0, 1].set_ylabel('Frequency')
        axes[0, 1].legend()
        axes[0, 1].grid(True)
        
        # 3. Strategy performance
        strategy_pnl = df_trades.groupby('strategy')['net_pnl'].sum()
        axes[1, 0].bar(strategy_pnl.index, strategy_pnl.values)
        axes[1, 0].set_title('P&L by Strategy')
        axes[1, 0].set_xlabel('Strategy')
        axes[1, 0].set_ylabel('Total P&L (₹)')
        axes[1, 0].tick_params(axis='x', rotation=45)
        
        # 4. Monthly returns heatmap
        df_trades['year_month'] = df_trades['exit_date'].dt.to_period('M')
        monthly_returns = df_trades.groupby('year_month')['net_pnl'].sum()
        
        # Create monthly heatmap data
        if len(monthly_returns) > 1:
            monthly_df = monthly_returns.reset_index()
            monthly_df['year'] = monthly_df['year_month'].dt.year
            monthly_df['month'] = monthly_df['year_month'].dt.month
            
            pivot_table = monthly_df.pivot(index='year', columns='month', values='net_pnl')
            
            sns.heatmap(pivot_table, annot=True, fmt='.0f', cmap='RdYlGn', 
                       ax=axes[1, 1], center=0)
            axes[1, 1].set_title('Monthly P&L Heatmap')
        else:
            axes[1, 1].text(0.5, 0.5, 'Insufficient data for heatmap', 
                           ha='center', va='center', transform=axes[1, 1].transAxes)
            axes[1, 1].set_title('Monthly P&L Heatmap')
        
        plt.tight_layout()
        plt.show()
        
        # Print summary
        self.print_performance_summary(metrics)
    
    def print_performance_summary(self, metrics: Dict):
        """Print detailed performance summary"""
        print("\n" + "="*60)
        print("BACKTEST PERFORMANCE SUMMARY")
        print("="*60)
        
        print(f"Initial Capital: ₹{self.initial_capital:,.2f}")
        print(f"Final Capital: ₹{metrics['final_capital']:,.2f}")
        print(f"Total Return: {metrics['total_return_pct']}%")
        print(f"Total P&L: ₹{metrics['total_pnl']:,.2f}")
        
        print(f"\nTRADE STATISTICS:")
        print(f"Total Trades: {metrics['total_trades']}")
        print(f"Winning Trades: {metrics['winning_trades']}")
        print(f"Losing Trades: {metrics['losing_trades']}")
        print(f"Win Rate: {metrics['win_rate_pct']}%")
        
        print(f"\nRISK METRICS:")
        print(f"Profit Factor: {metrics['profit_factor']}")
        print(f"Average Return per Trade: {metrics['avg_return_per_trade']}%")
        print(f"Maximum Gain: ₹{metrics['max_gain']:,.2f}")
        print(f"Maximum Loss: ₹{metrics['max_loss']:,.2f}")
        print(f"Average Hold Period: {metrics['avg_hold_days']} days")
        
        print(f"\nEXIT ANALYSIS:")
        for reason, count in metrics['exit_analysis'].items():
            percentage = (count / metrics['total_trades']) * 100
            print(f"{reason}: {count} trades ({percentage:.1f}%)")
        
        print(f"\nSTRATEGY PERFORMANCE:")
        print(metrics['strategy_performance'].to_string())

def generate_sample_backtest():
    """Generate sample backtest with synthetic data"""
    # Create sample historical data
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
    
    symbols = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY']
    historical_data = {}
    
    for symbol in symbols:
        # Generate synthetic price data
        np.random.seed(42 + len(symbol))  # Consistent but different for each symbol
        
        price_data = []
        base_price = 1000 + np.random.normal(0, 200)  # Starting price
        
        for i in range(len(dates)):
            # Random walk with slight upward bias
            change = np.random.normal(0.001, 0.02)  # 0.1% daily return, 2% volatility
            base_price *= (1 + change)
            
            # Create OHLC data
            high = base_price * (1 + abs(np.random.normal(0, 0.01)))
            low = base_price * (1 - abs(np.random.normal(0, 0.01)))
            close = base_price
            volume = int(np.random.normal(1000000, 200000))
            
            price_data.append({
                'open': base_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': max(volume, 100000)
            })
        
        df = pd.DataFrame(price_data, index=dates)
        historical_data[symbol] = df
    
    # Generate sample signals
    strategy_signals = {
        'RELIANCE': [
            {
                'timestamp': pd.Timestamp('2023-03-15'),
                'signal_type': 'BUY',
                'entry_price': 950.0,
                'target_price': 1000.0,  # 5.26% target
                'stop_loss': 931.0,      # 2% stop loss
                'strategy': 'MOMENTUM',
                'confidence': 0.8
            },
            {
                'timestamp': pd.Timestamp('2023-06-20'),
                'signal_type': 'BUY',
                'entry_price': 1050.0,
                'target_price': 1120.0,  # 6.67% target
                'stop_loss': 1029.0,     # 2% stop loss
                'strategy': 'BREAKOUT',
                'confidence': 0.85
            }
        ],
        'TCS': [
            {
                'timestamp': pd.Timestamp('2023-04-10'),
                'signal_type': 'BUY',
                'entry_price': 3200.0,
                'target_price': 3360.0,  # 5% target
                'stop_loss': 3136.0,     # 2% stop loss
                'strategy': 'MEAN_REVERSION',
                'confidence': 0.75
            }
        ]
    }
    
    # Run backtest
    backtest = BacktestEngine(initial_capital=100000)
    results = backtest.backtest_strategy(historical_data, strategy_signals)
    
    # Display results
    if results:
        backtest.plot_performance(results)
    
    return backtest, results

if __name__ == "__main__":
    # Run sample backtest
    print("Running Sample Backtest...")
    backtest_engine, results = generate_sample_backtest()