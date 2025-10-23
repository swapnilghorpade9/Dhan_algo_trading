import time
import threading
from datetime import datetime
import json
import logging
from typing import Dict, List, Optional
from dataclasses import asdict
import websocket
import requests

logger = logging.getLogger(__name__)

class RealTimeMonitor:
    def __init__(self, dhan_api):
        self.dhan_api = dhan_api
        self.monitoring = False
        self.performance_metrics = {
            'daily_pnl': 0.0,
            'realized_pnl': 0.0,
            'unrealized_pnl': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'current_positions': 0,
            'max_drawdown': 0.0,
            'peak_portfolio_value': 0.0
        }
        
    def start_monitoring(self):
        """Start real-time monitoring"""
        self.monitoring = True
        
        # Start monitoring threads
        position_thread = threading.Thread(target=self._monitor_positions)
        performance_thread = threading.Thread(target=self._track_performance)
        alert_thread = threading.Thread(target=self._monitor_alerts)
        
        position_thread.daemon = True
        performance_thread.daemon = True
        alert_thread.daemon = True
        
        position_thread.start()
        performance_thread.start()
        alert_thread.start()
        
        logger.info("Real-time monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
        logger.info("Real-time monitoring stopped")
    
    def _monitor_positions(self):
        """Monitor position changes every 30 seconds"""
        while self.monitoring:
            try:
                # Update position prices and P&L
                for symbol, position in self.dhan_api.positions.items():
                    # Get current price (in real implementation, use live data feed)
                    df = self.dhan_api.get_historical_data(
                        position.security_id, 
                        position.exchange_segment, 
                        days=1
                    )
                    
                    if df is not None and len(df) > 0:
                        current_price = df['close'].iloc[-1]
                        position.current_price = current_price
                        position.pnl = (current_price - position.entry_price) * position.quantity
                        
                        # Check for alerts
                        self._check_position_alerts(position)
                
                # Update performance metrics
                self._update_performance_metrics()
                
                time.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                logger.error(f"Position monitoring error: {e}")
                time.sleep(60)
    
    def _track_performance(self):
        """Track overall performance metrics"""
        while self.monitoring:
            try:
                # Calculate portfolio metrics
                total_unrealized_pnl = sum([pos.pnl for pos in self.dhan_api.positions.values()])
                current_portfolio_value = self.dhan_api.get_funds() + total_unrealized_pnl
                
                # Update peak and drawdown
                if current_portfolio_value > self.performance_metrics['peak_portfolio_value']:
                    self.performance_metrics['peak_portfolio_value'] = current_portfolio_value
                
                current_drawdown = (self.performance_metrics['peak_portfolio_value'] - current_portfolio_value) / self.performance_metrics['peak_portfolio_value'] * 100
                
                if current_drawdown > self.performance_metrics['max_drawdown']:
                    self.performance_metrics['max_drawdown'] = current_drawdown
                
                # Log performance update
                logger.info(f"Portfolio Value: ₹{current_portfolio_value:,.2f}, "
                          f"Unrealized P&L: ₹{total_unrealized_pnl:,.2f}, "
                          f"Drawdown: {current_drawdown:.2f}%")
                
                time.sleep(60)  # Update every minute
                
            except Exception as e:
                logger.error(f"Performance tracking error: {e}")
                time.sleep(60)
    
    def _monitor_alerts(self):
        """Monitor for various alert conditions"""
        while self.monitoring:
            try:
                # Check daily loss limit
                if self.dhan_api.daily_pnl < self.dhan_api.max_daily_loss:
                    self._send_alert("DAILY_LOSS_LIMIT", 
                                   f"Daily loss limit reached: ₹{self.dhan_api.daily_pnl:,.2f}")
                    self.dhan_api.trading_enabled = False
                
                # Check maximum drawdown
                if self.performance_metrics['max_drawdown'] > 10:  # 10% max drawdown
                    self._send_alert("MAX_DRAWDOWN", 
                                   f"Maximum drawdown exceeded: {self.performance_metrics['max_drawdown']:.2f}%")
                    self.dhan_api.trading_enabled = False
                
                # Check position concentration
                total_portfolio = self.dhan_api.get_funds()
                for symbol, position in self.dhan_api.positions.items():
                    position_value = position.current_price * position.quantity
                    concentration = (position_value / total_portfolio) * 100
                    
                    if concentration > 25:  # 25% max concentration
                        self._send_alert("POSITION_CONCENTRATION", 
                                       f"{symbol} concentration: {concentration:.1f}%")
                
                time.sleep(120)  # Check every 2 minutes
                
            except Exception as e:
                logger.error(f"Alert monitoring error: {e}")
                time.sleep(120)
    
    def _check_position_alerts(self, position):
        """Check individual position for alerts"""
        # Stop loss approach
        distance_to_stop = ((position.current_price - position.stop_loss) / position.current_price) * 100
        
        if distance_to_stop < 0.5:  # Within 0.5% of stop loss
            self._send_alert("STOP_LOSS_APPROACH", 
                           f"{position.symbol} approaching stop loss: {distance_to_stop:.2f}%")
        
        # Target approach
        distance_to_target = ((position.target_price - position.current_price) / position.current_price) * 100
        
        if distance_to_target < 0.5:  # Within 0.5% of target
            self._send_alert("TARGET_APPROACH", 
                           f"{position.symbol} approaching target: {distance_to_target:.2f}%")
        
        # Large unrealized loss
        if position.pnl < -1000:  # ₹1000+ loss
            self._send_alert("LARGE_LOSS", 
                           f"{position.symbol} unrealized loss: ₹{position.pnl:,.2f}")
    
    def _update_performance_metrics(self):
        """Update performance metrics"""
        self.performance_metrics['current_positions'] = len(self.dhan_api.positions)
        self.performance_metrics['unrealized_pnl'] = sum([pos.pnl for pos in self.dhan_api.positions.values()])
    
    def _send_alert(self, alert_type: str, message: str):
        """Send alert (implement notification method)"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        alert_msg = f"[ALERT {timestamp}] {alert_type}: {message}"
        
        logger.warning(alert_msg)
        
        # Here you can implement various notification methods:
        # 1. Email notifications
        # 2. SMS alerts
        # 3. Telegram bot messages
        # 4. Desktop notifications
        # 5. Write to alert file
        
        with open('trading_alerts.log', 'a') as f:
            f.write(f"{alert_msg}\n")
    
    def get_dashboard_data(self) -> Dict:
        """Get real-time dashboard data"""
        positions_data = []
        
        for symbol, position in self.dhan_api.positions.items():
            pos_data = {
                'symbol': symbol,
                'quantity': position.quantity,
                'entry_price': position.entry_price,
                'current_price': position.current_price,
                'pnl': position.pnl,
                'pnl_percent': (position.pnl / (position.entry_price * position.quantity)) * 100,
                'stop_loss': position.stop_loss,
                'target_price': position.target_price,
                'strategy': position.strategy,
                'entry_time': position.entry_time.strftime('%Y-%m-%d %H:%M:%S'),
                'hold_duration': str(datetime.now() - position.entry_time).split('.')[0]
            }
            positions_data.append(pos_data)
        
        dashboard_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'portfolio_summary': {
                'available_funds': self.dhan_api.get_funds(),
                'daily_pnl': self.dhan_api.daily_pnl,
                'unrealized_pnl': self.performance_metrics['unrealized_pnl'],
                'total_positions': len(self.dhan_api.positions),
                'max_positions': self.dhan_api.max_positions,
                'trading_enabled': self.dhan_api.trading_enabled
            },
            'positions': positions_data,
            'performance_metrics': self.performance_metrics.copy()
        }
        
        return dashboard_data
    
    def export_dashboard_json(self, filename: str = None):
        """Export current dashboard data to JSON"""
        if filename is None:
            filename = f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        dashboard_data = self.get_dashboard_data()
        
        with open(filename, 'w') as f:
            json.dump(dashboard_data, f, indent=2, default=str)
        
        logger.info(f"Dashboard data exported to {filename}")
        return filename

class TradeExecutor:
    def __init__(self, dhan_api):
        self.dhan_api = dhan_api
        self.order_queue = []
        self.executing = False
        
    def start_execution_engine(self):
        """Start order execution engine"""
        self.executing = True
        execution_thread = threading.Thread(target=self._process_orders)
        execution_thread.daemon = True
        execution_thread.start()
        logger.info("Trade execution engine started")
    
    def stop_execution_engine(self):
        """Stop execution engine"""
        self.executing = False
        logger.info("Trade execution engine stopped")
    
    def queue_order(self, order_data: Dict):
        """Add order to execution queue"""
        order_data['timestamp'] = datetime.now()
        order_data['status'] = 'QUEUED'
        self.order_queue.append(order_data)
        logger.info(f"Order queued: {order_data['transaction_type']} {order_data['quantity']} {order_data.get('symbol', 'N/A')}")
    
    def _process_orders(self):
        """Process orders from queue"""
        while self.executing:
            try:
                if self.order_queue and self.dhan_api.trading_enabled:
                    order = self.order_queue.pop(0)
                    
                    # Execute order
                    result = self.dhan_api.place_order(
                        order['security_id'],
                        order['exchange_segment'],
                        order['transaction_type'],
                        order['quantity'],
                        order.get('order_type', 'MARKET'),
                        order.get('price', 0)
                    )
                    
                    if result:
                        order['status'] = 'EXECUTED'
                        order['order_id'] = result.get('orderId', 'N/A')
                        logger.info(f"Order executed: {order['transaction_type']} {order['quantity']} {order.get('symbol', 'N/A')}")
                    else:
                        order['status'] = 'FAILED'
                        logger.error(f"Order failed: {order['transaction_type']} {order['quantity']} {order.get('symbol', 'N/A')}")
                        
                        # Retry failed orders (optional)
                        if order.get('retry_count', 0) < 3:
                            order['retry_count'] = order.get('retry_count', 0) + 1
                            order['status'] = 'RETRY'
                            self.order_queue.append(order)
                
                time.sleep(1)  # Process orders every second
                
            except Exception as e:
                logger.error(f"Order execution error: {e}")
                time.sleep(5)

def create_web_dashboard():
    """Create simple HTML dashboard (basic version)"""
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Algo Trading Dashboard</title>
        <meta http-equiv="refresh" content="30">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .summary { background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
            .positions { overflow-x: auto; }
            table { width: 100%; border-collapse: collapse; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            .profit { color: green; }
            .loss { color: red; }
            .status { font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Algorithmic Trading Dashboard</h1>
            <div id="timestamp">Last Updated: {timestamp}</div>
            
            <div class="summary">
                <h2>Portfolio Summary</h2>
                <p>Available Funds: ₹{available_funds:,.2f}</p>
                <p>Daily P&L: <span class="{daily_pnl_class}">₹{daily_pnl:,.2f}</span></p>
                <p>Unrealized P&L: <span class="{unrealized_pnl_class}">₹{unrealized_pnl:,.2f}</span></p>
                <p>Active Positions: {total_positions}/{max_positions}</p>
                <p>Trading Status: <span class="status">{trading_status}</span></p>
            </div>
            
            <div class="positions">
                <h2>Current Positions</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Quantity</th>
                            <th>Entry Price</th>
                            <th>Current Price</th>
                            <th>P&L</th>
                            <th>P&L %</th>
                            <th>Stop Loss</th>
                            <th>Target</th>
                            <th>Strategy</th>
                            <th>Duration</th>
                        </tr>
                    </thead>
                    <tbody>
                        {positions_rows}
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_template

# Usage example in main strategy file
def integrate_monitoring(dhan_algo_trader):
    """Integrate monitoring with main trading system"""
    # Create monitor and executor
    monitor = RealTimeMonitor(dhan_algo_trader)
    executor = TradeExecutor(dhan_algo_trader)
    
    # Start monitoring
    monitor.start_monitoring()
    executor.start_execution_engine()
    
    # Modify the main trading loop to use executor
    def enhanced_execute_signal(signal, security_id, exchange_segment):
        """Enhanced signal execution with queuing"""
        if not dhan_algo_trader.trading_enabled or len(dhan_algo_trader.positions) >= dhan_algo_trader.max_positions:
            return
        
        # Prepare order
        order_data = {
            'security_id': security_id,
            'exchange_segment': exchange_segment,
            'transaction_type': 'BUY',
            'quantity': dhan_algo_trader.calculate_position_size(signal.entry_price, signal.stop_loss, dhan_algo_trader.get_funds()),
            'symbol': signal.symbol,
            'strategy': signal.strategy,
            'confidence': signal.confidence
        }
        
        # Queue order for execution
        executor.queue_order(order_data)
    
    return monitor, executor

if __name__ == "__main__":
    print("Real-time monitoring module loaded successfully!")