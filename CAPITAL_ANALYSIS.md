# Capital Requirements & Position Sizing Analysis
# Dhan Algorithmic Trading System

## 💰 CAPITAL REQUIREMENTS ANALYSIS

Based on the algorithm parameters and Indian stock market conditions:

### **🎯 Minimum Capital Requirements:**

**1. Absolute Minimum:** ₹10,000
- Hard-coded minimum in the system
- Only for testing/learning purposes
- Very limited trading opportunities

**2. Practical Minimum:** ₹50,000
- Can trade 1-2 positions effectively
- Limited diversification
- Higher risk concentration

**3. Recommended Capital:** ₹1,00,000 - ₹2,00,000
- Optimal for the 5-position strategy
- Good diversification across stocks
- Balanced risk management

**4. Ideal Capital:** ₹5,00,000+
- Full algorithm potential
- Multiple simultaneous positions
- Lower risk per position
- Better compounding opportunities

---

## 📊 POSITION SIZING CALCULATION

### **Algorithm Logic:**
```python
risk_amount = available_capital * 0.02  # 2% max risk per trade
price_risk = entry_price - stop_loss    # Price difference
quantity = risk_amount / price_risk     # Maximum shares
```

### **Real Examples:**

#### **Example 1: RELIANCE (₹2,500 per share)**
- Entry Price: ₹2,500
- Stop Loss: ₹2,450 (2% stop loss)
- Price Risk: ₹50 per share

**Capital vs Quantity:**
| Capital | Risk Amount (2%) | Max Quantity | Position Value | Risk % |
|---------|------------------|--------------|----------------|--------|
| ₹50,000 | ₹1,000 | 20 shares | ₹50,000 | 100% |
| ₹1,00,000 | ₹2,000 | 40 shares | ₹1,00,000 | 100% |
| ₹2,00,000 | ₹4,000 | 80 shares | ₹2,00,000 | 100% |
| ₹5,00,000 | ₹10,000 | 200 shares | ₹5,00,000 | 100% |

*Note: 100% position means single stock trading*

#### **Example 2: TCS (₹3,200 per share)**
- Entry Price: ₹3,200
- Stop Loss: ₹3,136 (2% stop loss)
- Price Risk: ₹64 per share

**Capital vs Quantity:**
| Capital | Risk Amount (2%) | Max Quantity | Position Value | % of Capital |
|---------|------------------|--------------|----------------|--------------|
| ₹50,000 | ₹1,000 | 15 shares | ₹48,000 | 96% |
| ₹1,00,000 | ₹2,000 | 31 shares | ₹99,200 | 99% |
| ₹2,00,000 | ₹4,000 | 62 shares | ₹1,98,400 | 99% |
| ₹5,00,000 | ₹10,000 | 156 shares | ₹4,99,200 | 100% |

---

## 🎯 MULTI-POSITION SCENARIOS

### **With ₹2,00,000 Capital (5 max positions):**

**Scenario: 3 Active Positions**
1. **RELIANCE:** 26 shares (₹65,000) - 32.5% of capital
2. **TCS:** 20 shares (₹64,000) - 32% of capital  
3. **HDFCBANK:** 25 shares (₹37,500) - 18.75% of capital
4. **Cash Reserve:** ₹33,500 - 16.75% (for new opportunities)

**Total Risk:** ₹4,000 (2% of total capital)
**Diversification:** Good across sectors

### **With ₹5,00,000 Capital (5 max positions):**

**Scenario: 5 Active Positions**
1. **RELIANCE:** 40 shares (₹1,00,000) - 20%
2. **TCS:** 31 shares (₹99,200) - 19.8%
3. **HDFCBANK:** 33 shares (₹49,500) - 9.9%
4. **INFY:** 35 shares (₹52,500) - 10.5%
5. **SBIN:** 100 shares (₹60,000) - 12%

**Total Risk:** ₹10,000 (2% of total capital)
**Cash Reserve:** ₹1,38,800 (27.8%)

---

## ⚙️ POSITION SIZING FACTORS

### **1. Stock Price Impact:**
- **High-priced stocks** (₹2000+): Fewer shares, higher capital requirement
- **Medium-priced stocks** (₹500-2000): Balanced quantities
- **Low-priced stocks** (₹100-500): More shares, easier entry

### **2. Volatility Impact:**
- **Low volatility stocks:** Smaller stop losses = More shares
- **High volatility stocks:** Larger stop losses = Fewer shares

### **3. Capital Efficiency:**
```python
# Maximum 20% per position (built-in safety)
max_position_value = capital * 0.20
if (entry_price * quantity) > max_position_value:
    quantity = max_position_value / entry_price
```

---

## 📈 PROFIT POTENTIAL BY CAPITAL

### **₹1,00,000 Capital:**
- **Per Trade Profit:** ₹2,000 - ₹6,000 (2-6%)
- **Monthly Potential:** ₹8,000 - ₹25,000 (8-25%)
- **Trades per Month:** 4-8 trades

### **₹2,00,000 Capital:**
- **Per Trade Profit:** ₹4,000 - ₹12,000 (2-6%)
- **Monthly Potential:** ₹16,000 - ₹50,000 (8-25%)
- **Trades per Month:** 6-12 trades

### **₹5,00,000 Capital:**
- **Per Trade Profit:** ₹10,000 - ₹30,000 (2-6%)
- **Monthly Potential:** ₹40,000 - ₹1,25,000 (8-25%)
- **Trades per Month:** 8-15 trades

---

## 🛡️ RISK MANAGEMENT BY CAPITAL

### **Capital-Based Risk Limits:**
| Capital | Max Risk/Trade | Max Daily Loss | Max Positions | Reserve Cash |
|---------|----------------|----------------|---------------|--------------|
| ₹50K | ₹1,000 | ₹2,500 | 2 | 20% |
| ₹1L | ₹2,000 | ₹5,000 | 3 | 25% |
| ₹2L | ₹4,000 | ₹10,000 | 4 | 25% |
| ₹5L | ₹10,000 | ₹25,000 | 5 | 30% |

---

## 💡 RECOMMENDATIONS

### **For Beginners (₹50K - ₹1L):**
- Start with 1-2 positions maximum
- Focus on high-confidence signals (80%+)
- Use paper trading first
- Conservative 1.5% risk per trade

### **For Intermediate (₹1L - ₹3L):**
- 3-4 maximum positions
- Full 2% risk per trade
- Diversify across sectors
- Monitor closely

### **For Advanced (₹3L+):**
- Full 5 position capacity
- Advanced strategies
- Consider adding more stocks to universe
- Implement portfolio optimization

---

## ⚠️ IMPORTANT NOTES

1. **Minimum Lot Sizes:** Some stocks have minimum quantities
2. **Brokerage Costs:** ₹20 per trade affects small positions
3. **Slippage:** Market orders may get filled at different prices
4. **Margin Requirements:** CNC requires full capital
5. **Settlement Cycles:** T+2 settlement for equity delivery

**Bottom Line:** Start with ₹1,00,000 minimum for effective algorithmic trading with proper risk management!