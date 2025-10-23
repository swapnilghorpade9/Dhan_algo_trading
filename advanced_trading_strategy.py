import requests
import pandas as pd
import numpy as np
import time
import json
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
import threading
from dataclasses import dataclass
import ta
from scipy import stats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_log.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TradeSignal:
    symbol: str
    signal_type: str  # 'BUY' or 'SELL'
    confidence: float  # 0-1 scale
    entry_price: float
    target_price: float
    stop_loss: float
    strategy: str
    timestamp: datetime
    
@dataclass
class Position:
    symbol: str
    security_id: str
    exchange_segment: str
    quantity: int
    entry_price: float
    current_price: float
    stop_loss: float
    target_price: float
    entry_time: datetime
    strategy: str
    pnl: float = 0.0
    
class DhanAlgoTrading:
    def __init__(self, client_id: str, access_token: str):
        self.client_id = client_id
        self.access_token = access_token
        self.base_url = "https://api.dhan.co"
        self.headers = {
            "Content-Type": "application/json",
            "access-token": self.access_token
        }
        
        # Trading parameters
        self.max_risk_per_trade = 0.02  # 2% maximum risk
        self.min_reward_ratio = 2.5     # Minimum 2.5:1 reward-to-risk ratio
        self.max_positions = 5          # Maximum concurrent positions
        self.min_confidence = 0.7       # Minimum signal confidence
        
        # Portfolio tracking
        self.positions: Dict[str, Position] = {}
        self.daily_pnl = 0.0
        self.max_daily_loss = -5000.0   # Maximum daily loss limit
        self.trading_enabled = True
        
    def get_historical_data(self, security_id: str, exchange_segment: str, 
                           days: int = 100) -> Optional[pd.DataFrame]:
        """Get historical data with error handling"""
        try:
            from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            to_date = datetime.now().strftime('%Y-%m-%d')
            
            url = f"{self.base_url}/charts/historical"
            params = {
                "securityId": security_id,
                "exchangeSegment": exchange_segment,
                "instrument": "EQUITY",
                "fromDate": from_date,
                "toDate": to_date
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                data = response.json()
                if data.get('data'):
                    df = pd.DataFrame(data['data'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df.set_index('timestamp', inplace=True)
                    df = df.sort_index()
                    return df
            return None
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return None
    
    def calculate_advanced_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate comprehensive technical indicators"""
        # Price-based indicators
        df['SMA_20'] = ta.trend.sma_indicator(df['close'], window=20)
        df['EMA_12'] = ta.trend.ema_indicator(df['close'], window=12)
        df['EMA_26'] = ta.trend.ema_indicator(df['close'], window=26)
        df['EMA_50'] = ta.trend.ema_indicator(df['close'], window=50)
        
        # Bollinger Bands
        bb_indicator = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
        df['BB_upper'] = bb_indicator.bollinger_hband()
        df['BB_middle'] = bb_indicator.bollinger_mavg()
        df['BB_lower'] = bb_indicator.bollinger_lband()
        df['BB_width'] = (df['BB_upper'] - df['BB_lower']) / df['BB_middle']
        
        # RSI with multiple periods
        df['RSI_14'] = ta.momentum.rsi(df['close'], window=14)
        df['RSI_21'] = ta.momentum.rsi(df['close'], window=21)
        
        # MACD
        macd_indicator = ta.trend.MACD(df['close'])
        df['MACD'] = macd_indicator.macd()
        df['MACD_signal'] = macd_indicator.macd_signal()
        df['MACD_histogram'] = macd_indicator.macd_diff()
        
        # Stochastic Oscillator
        stoch_indicator = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'])
        df['Stoch_K'] = stoch_indicator.stoch()
        df['Stoch_D'] = stoch_indicator.stoch_signal()
        
        # ADX for trend strength
        df['ADX'] = ta.trend.adx(df['high'], df['low'], df['close'], window=14)
        
        # Volume indicators
        df['Volume_SMA'] = ta.volume.volume_sma(df['close'], df['volume'], window=20)
        df['OBV'] = ta.volume.on_balance_volume(df['close'], df['volume'])
        
        # Support and Resistance levels
        df['Resistance'] = df['high'].rolling(window=20).max()
        df['Support'] = df['low'].rolling(window=20).min()
        
        # Volatility
        df['ATR'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
        df['Volatility'] = df['close'].pct_change().rolling(window=20).std() * np.sqrt(252)
        
        # Price patterns
        df['Higher_High'] = (df['high'] > df['high'].shift(1)) & (df['high'].shift(1) > df['high'].shift(2))
        df['Higher_Low'] = (df['low'] > df['low'].shift(1)) & (df['low'].shift(1) > df['low'].shift(2))
        df['Lower_High'] = (df['high'] < df['high'].shift(1)) & (df['high'].shift(1) < df['high'].shift(2))
        df['Lower_Low'] = (df['low'] < df['low'].shift(1)) & (df['low'].shift(1) < df['low'].shift(2))
        
        return df
    
    def breakout_strategy(self, df: pd.DataFrame, symbol: str) -> Optional[TradeSignal]:
        """Breakout strategy for 5-10% profit targets"""
        if len(df) < 50:
            return None
            
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Breakout conditions
        volume_surge = latest['volume'] > latest['Volume_SMA'] * 1.5
        volatility_expansion = latest['BB_width'] > df['BB_width'].rolling(20).mean().iloc[-1] * 1.2
        
        # Bullish breakout
        if (latest['close'] > latest['Resistance'] * 0.998 and
            latest['close'] > latest['BB_upper'] * 0.995 and
            latest['RSI_14'] > 50 and latest['RSI_14'] < 80 and
            latest['ADX'] > 25 and
            volume_surge and volatility_expansion):
            
            entry_price = latest['close']
            stop_loss = max(latest['Support'], entry_price * 0.98)  # 2% max stop loss
            target_price = entry_price * 1.07  # 7% target
            
            confidence = min(0.9, (latest['RSI_14'] - 50) / 30 + 
                           (latest['ADX'] - 25) / 25 + 
                           (latest['volume'] / latest['Volume_SMA'] - 1))
            
            return TradeSignal(
                symbol=symbol,
                signal_type='BUY',
                confidence=confidence,
                entry_price=entry_price,
                target_price=target_price,
                stop_loss=stop_loss,
                strategy='BREAKOUT',
                timestamp=datetime.now()
            )
        
        return None
    
    def momentum_strategy(self, df: pd.DataFrame, symbol: str) -> Optional[TradeSignal]:
        """Momentum strategy with trend following"""
        if len(df) < 50:
            return None
            
        latest = df.iloc[-1]
        
        # Momentum conditions
        ema_bullish = (latest['EMA_12'] > latest['EMA_26'] > latest['EMA_50'])
        rsi_momentum = 55 < latest['RSI_14'] < 75
        macd_bullish = latest['MACD'] > latest['MACD_signal'] and latest['MACD_histogram'] > 0
        stoch_bullish = latest['Stoch_K'] > latest['Stoch_D'] and latest['Stoch_K'] > 50
        
        # Price above key levels
        price_strength = (latest['close'] > latest['SMA_20'] > latest['EMA_50'])
        
        if (ema_bullish and rsi_momentum and macd_bullish and 
            stoch_bullish and price_strength and latest['ADX'] > 20):
            
            entry_price = latest['close']
            stop_loss = max(latest['EMA_26'], entry_price * 0.98)
            target_price = entry_price * 1.06  # 6% target
            
            confidence = min(0.95, (latest['ADX'] / 40) + 
                           (latest['RSI_14'] - 50) / 25 + 0.3)
            
            return TradeSignal(
                symbol=symbol,
                signal_type='BUY',
                confidence=confidence,
                entry_price=entry_price,
                target_price=target_price,
                stop_loss=stop_loss,
                strategy='MOMENTUM',
                timestamp=datetime.now()
            )
        
        return None
    
    def mean_reversion_strategy(self, df: pd.DataFrame, symbol: str) -> Optional[TradeSignal]:
        """Mean reversion strategy for oversold bounces"""
        if len(df) < 50:
            return None
            
        latest = df.iloc[-1]
        
        # Oversold conditions with bounce potential
        oversold_rsi = latest['RSI_14'] < 35 and df['RSI_14'].iloc[-2] < latest['RSI_14']
        bb_bounce = latest['close'] < latest['BB_lower'] * 1.02
        stoch_oversold = latest['Stoch_K'] < 25 and latest['Stoch_K'] > df['Stoch_K'].iloc[-2]
        
        # Support level bounce
        near_support = latest['low'] <= latest['Support'] * 1.01
        
        if oversold_rsi and bb_bounce and stoch_oversold and near_support:
            entry_price = latest['close']
            stop_loss = max(latest['Support'] * 0.99, entry_price * 0.98)
            target_price = min(latest['BB_middle'], entry_price * 1.05)  # 5% target or BB middle
            
            confidence = min(0.85, (35 - latest['RSI_14']) / 20 + 
                           (25 - latest['Stoch_K']) / 25 + 0.2)
            
            return TradeSignal(
                symbol=symbol,
                signal_type='BUY',
                confidence=confidence,
                entry_price=entry_price,
                target_price=target_price,
                stop_loss=stop_loss,
                strategy='MEAN_REVERSION',
                timestamp=datetime.now()
            )
        
        return None
    
    def gap_strategy(self, df: pd.DataFrame, symbol: str) -> Optional[TradeSignal]:
        """Gap trading strategy"""
        if len(df) < 10:
            return None
            
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Gap up with strong volume
        gap_size = (latest['open'] - prev['close']) / prev['close']
        
        if (gap_size > 0.02 and  # 2%+ gap up
            latest['volume'] > latest['Volume_SMA'] * 2 and
            latest['close'] > latest['open'] and  # Continuing the gap direction
            latest['RSI_14'] < 70):
            
            entry_price = latest['close']
            stop_loss = max(latest['open'], entry_price * 0.98)
            target_price = entry_price * (1 + gap_size * 1.5)  # Target based on gap size
            
            confidence = min(0.8, gap_size * 10 + 
                           (latest['volume'] / latest['Volume_SMA'] - 1) * 0.2)
            
            return TradeSignal(
                symbol=symbol,
                signal_type='BUY',
                confidence=confidence,
                entry_price=entry_price,
                target_price=target_price,
                stop_loss=stop_loss,
                strategy='GAP_TRADE',
                timestamp=datetime.now()
            )
        
        return None
    
    def generate_signals(self, symbol: str, security_id: str, exchange_segment: str) -> List[TradeSignal]:
        """Generate signals from all strategies"""
        df = self.get_historical_data(security_id, exchange_segment)
        if df is None or len(df) < 50:
            return []
        
        df = self.calculate_advanced_indicators(df)
        
        signals = []
        
        # Try each strategy
        strategies = [
            self.breakout_strategy,
            self.momentum_strategy,
            self.mean_reversion_strategy,
            self.gap_strategy
        ]
        
        for strategy_func in strategies:
            signal = strategy_func(df, symbol)
            if signal and signal.confidence >= self.min_confidence:
                signals.append(signal)
        
        return signals
    
    def calculate_position_size(self, entry_price: float, stop_loss: float, 
                              available_capital: float) -> int:
        """Calculate position size based on risk management"""
        risk_amount = available_capital * self.max_risk_per_trade
        price_risk = abs(entry_price - stop_loss)
        
        if price_risk > 0:
            max_quantity = int(risk_amount / price_risk)
            return max(1, max_quantity)
        return 1
    
    def place_order(self, security_id: str, exchange_segment: str, transaction_type: str, 
                   quantity: int, order_type: str = "MARKET", price: float = 0) -> Optional[dict]:
        """Place order with Dhan API"""
        url = f"{self.base_url}/orders"
        
        order_data = {
            "dhanClientId": self.client_id,
            "correlationId": f"ALGO_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            "transactionType": transaction_type,
            "exchangeSegment": exchange_segment,
            "productType": "CNC",  # For positional trades
            "orderType": order_type,
            "validity": "DAY",
            "securityId": security_id,
            "quantity": quantity,
            "disclosedQuantity": 0,
            "price": price,
            "triggerPrice": 0,
            "afterMarketOrder": False
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=order_data)
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Order placed: {transaction_type} {quantity} shares of {security_id}")
                return result
            else:
                logger.error(f"Order failed: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Order placement error: {e}")
            return None
    
    def get_funds(self) -> float:
        """Get available funds"""
        try:
            url = f"{self.base_url}/fundlimit"
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                return float(data.get('data', {}).get('availableBalance', 0))
            return 0.0
        except Exception as e:
            logger.error(f"Error fetching funds: {e}")
            return 0.0
    
    def monitor_positions(self):
        """Monitor existing positions for exit conditions"""
        for symbol, position in list(self.positions.items()):
            try:
                # Get current price
                df = self.get_historical_data(position.security_id, position.exchange_segment, days=2)
                if df is None or len(df) == 0:
                    continue
                
                current_price = df['close'].iloc[-1]
                position.current_price = current_price
                position.pnl = (current_price - position.entry_price) * position.quantity
                
                # Check exit conditions
                should_exit = False
                exit_reason = ""
                
                # Stop loss hit
                if current_price <= position.stop_loss:
                    should_exit = True
                    exit_reason = "STOP_LOSS"
                
                # Target achieved
                elif current_price >= position.target_price:
                    should_exit = True
                    exit_reason = "TARGET_ACHIEVED"
                
                # Time-based exit (hold for max 5 days)
                elif (datetime.now() - position.entry_time).days >= 5:
                    should_exit = True
                    exit_reason = "TIME_EXIT"
                
                # Risk management: Exit if daily loss limit reached
                elif self.daily_pnl < self.max_daily_loss:
                    should_exit = True
                    exit_reason = "DAILY_LOSS_LIMIT"
                
                if should_exit:
                    # Place exit order
                    exit_order = self.place_order(
                        position.security_id,
                        position.exchange_segment,
                        "SELL",
                        position.quantity
                    )
                    
                    if exit_order:
                        self.daily_pnl += position.pnl
                        logger.info(f"Position closed: {symbol}, Reason: {exit_reason}, "
                                  f"P&L: {position.pnl:.2f}, Daily P&L: {self.daily_pnl:.2f}")
                        del self.positions[symbol]
                
            except Exception as e:
                logger.error(f"Error monitoring position {symbol}: {e}")
    
    def execute_signal(self, signal: TradeSignal, security_id: str, exchange_segment: str):
        """Execute trading signal"""
        if not self.trading_enabled or len(self.positions) >= self.max_positions:
            return
        
        available_capital = self.get_funds()
        if available_capital < 10000:  # Minimum capital requirement
            logger.warning("Insufficient capital for trading")
            return
        
        # Calculate position size
        quantity = self.calculate_position_size(
            signal.entry_price, signal.stop_loss, available_capital
        )
        
        # Validate risk-reward ratio
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.target_price - signal.entry_price)
        
        if reward / risk < self.min_reward_ratio:
            logger.info(f"Skipping {signal.symbol}: Poor risk-reward ratio {reward/risk:.2f}")
            return
        
        # Place order
        order = self.place_order(security_id, exchange_segment, "BUY", quantity)
        
        if order and order.get('status') == 'success':
            # Create position object
            position = Position(
                symbol=signal.symbol,
                security_id=security_id,
                exchange_segment=exchange_segment,
                quantity=quantity,
                entry_price=signal.entry_price,
                current_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                target_price=signal.target_price,
                entry_time=signal.timestamp,
                strategy=signal.strategy
            )
            
            self.positions[signal.symbol] = position
            logger.info(f"Position opened: {signal.symbol}, Strategy: {signal.strategy}, "
                       f"Confidence: {signal.confidence:.2f}, Target: {signal.target_price:.2f}")
    
    def run_strategy(self, stock_universe: List[Dict]):
        """Main strategy execution loop"""
        logger.info("=== Starting Advanced Algorithm Trading ===")
        
        while self.trading_enabled:
            try:
                current_time = datetime.now()
                
                # Trading hours check (9:15 AM to 3:30 PM IST)
                if not (9 <= current_time.hour < 15 or 
                       (current_time.hour == 15 and current_time.minute < 30)):
                    logger.info("Market closed. Waiting...")
                    time.sleep(300)  # Wait 5 minutes
                    continue
                
                # Monitor existing positions
                self.monitor_positions()
                
                # Generate new signals if we have capacity
                if len(self.positions) < self.max_positions:
                    for stock in stock_universe:
                        try:
                            signals = self.generate_signals(
                                stock['symbol'], 
                                stock['security_id'], 
                                stock['exchange_segment']
                            )
                            
                            # Execute the best signal (highest confidence)
                            if signals:
                                best_signal = max(signals, key=lambda x: x.confidence)
                                if stock['symbol'] not in self.positions:
                                    self.execute_signal(
                                        best_signal, 
                                        stock['security_id'], 
                                        stock['exchange_segment']
                                    )
                            
                        except Exception as e:
                            logger.error(f"Error processing {stock['symbol']}: {e}")
                            continue
                
                # Log status
                logger.info(f"Active positions: {len(self.positions)}, Daily P&L: {self.daily_pnl:.2f}")
                
                # Wait before next cycle
                time.sleep(60)  # 1 minute intervals
                
            except KeyboardInterrupt:
                logger.info("Strategy stopped by user")
                self.trading_enabled = False
                break
            except Exception as e:
                logger.error(f"Strategy error: {e}")
                time.sleep(30)

def main():
    """Main execution function"""
    # Configuration
    CLIENT_ID = "YOUR_DHAN_CLIENT_ID"
    ACCESS_TOKEN = "YOUR_DHAN_ACCESS_TOKEN"
    
    # High-quality stock universe for algorithmic trading
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
        {"symbol": "AXISBANK", "security_id": "5900", "exchange_segment": "NSE_EQ"},
        {"symbol": "MARUTI", "security_id": "10999", "exchange_segment": "NSE_EQ"},
        {"symbol": "ASIANPAINT", "security_id": "62", "exchange_segment": "NSE_EQ"},
        {"symbol": "NESTLEIND", "security_id": "17963", "exchange_segment": "NSE_EQ"}
    ]
    
    # Initialize trading system
    algo_trader = DhanAlgoTrading(CLIENT_ID, ACCESS_TOKEN)
    
    # Start trading
    try:
        algo_trader.run_strategy(STOCK_UNIVERSE)
    except Exception as e:
        logger.error(f"Trading system error: {e}")
    finally:
        logger.info("Trading system shutdown")

if __name__ == "__main__":
    main()