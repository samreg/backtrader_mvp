# 📋 YAML CONFIG STRUCTURE - GUIDE FOR AI ASSISTANTS

This document defines the **MANDATORY** structure for all YAML configuration files in this project.

**CRITICAL**: When creating new config files, you MUST include ALL sections, even if some values are defaults or empty.

---

## 🎯 COMPLETE STRUCTURE TEMPLATE

```yaml
# ============================================================
# CONFIGURATION [STRATEGY_NAME] - [DESCRIPTION]
# ============================================================

# === DONNÉES ===
data:
  symbol: "NAS100"                      # REQUIRED: Trading symbol
  timeframe: "3min"                     # REQUIRED: Timeframe (1min, 3min, 5min, etc.)
  months: 6                             # REQUIRED: Number of months for MT5 download
  file: "data/NAS100_3min.csv"          # REQUIRED: CSV file path
  use_specific_csv_file: false          # REQUIRED: true = use 'file', false = auto-generate from symbol+timeframe
  start_date: null                      # OPTIONAL: Filter start date (null = all data)
  end_date: null                        # OPTIONAL: Filter end date (null = all data)

# === EXÉCUTION ===
execution:
  auto_download: true                   # REQUIRED: Auto-download from MT5 if data missing
  auto_html: true                       # REQUIRED: Auto-generate HTML dashboard
  auto_open_browser: true               # REQUIRED: Auto-open browser
  refresh_data_days: 1                  # REQUIRED: Re-download if data older than X days

# === BROKER (for main_backtest_generic.py) ===
broker:
  initial_cash: 10000                   # REQUIRED
  commission: 0.0                       # REQUIRED
  slippage: 0.0                         # REQUIRED

# === STRATEGY ===
strategy:
  name: "StrategyClassName"             # REQUIRED: Must match Python class name
  
  # Strategy-specific parameters follow...
  # (See strategy-specific sections below)
```

---

## ⚠️ CRITICAL RULES

### Rule 1: ALL SECTIONS REQUIRED

**NEVER** create a config file missing any of these sections:
- `data` ✅
- `execution` ✅
- `broker` ✅ (if using main_backtest_generic.py)
- `strategy` ✅

### Rule 2: ALL REQUIRED FIELDS

Within each section, **NEVER** omit required fields:

**data section:**
- `symbol` ✅
- `timeframe` ✅
- `months` ✅
- `file` ✅
- `use_specific_csv_file` ✅

**execution section:**
- `auto_download` ✅
- `auto_html` ✅
- `auto_open_browser` ✅
- `refresh_data_days` ✅

**broker section (if using main_backtest_generic.py):**
- `initial_cash` ✅
- `commission` ✅
- `slippage` ✅

### Rule 3: CONSISTENCY

Use consistent field names across all configs:
- ✅ `sl_min_pips` (not `min_sl_distance_pips`)
- ✅ `sl_max_pips` (not `max_sl_distance_pips`)
- ✅ `bb_period` (not `bollinger_period`)

---

## 📝 STRATEGY-SPECIFIC SECTIONS

### For BollingerBreakout Strategy

```yaml
strategy:
  name: "BollingerBreakout"
  
  # Trading Windows (OPTIONAL but include structure)
  trading_windows:
    enabled: false                      # true/false
    timezone: "Europe/Paris"            # If enabled
    windows: []                         # If enabled: ["Monday[13:00-16:00]", ...]
  
  # Bollinger Bands
  bb_period: 20
  bb_std: 1.5
  
  # RSI
  rsi_period: 14
  rsi_overbought: 70
  rsi_oversold: 30
  
  # Stop Loss
  sl_lookback: 5
  sl_offset_pips: 5
  sl_min_pips: 20
  sl_max_pips: 100
  
  # Take Profits
  tp1_ratio: 0.5
  enable_breakeven: true
  breakeven_offset: 2
  
  # Position Sizing
  risk_per_trade: 100
  
  # Anti flip-flop
  anti_flip_flop_enabled: true
  anti_flip_flop_pips: 20
```

### For RSI_Amplitude Strategy

```yaml
strategy:
  name: "RSI_Amplitude"
  
  # Trading Windows (OPTIONAL but include structure)
  trading_windows:
    enabled: false
    timezone: "Europe/Paris"
    windows: []
  
  # RSI
  rsi_period: 14
  rsi_long_threshold: 20
  rsi_short_threshold: 80
  
  # Stop Loss
  sl_lookback: 3
  sl_min_pips: 10
  sl_max_pips: 200
  
  # Take Profit
  tp1_rr: 1.0
  tp2_rr: 2.0
  tp1_ratio: 0.5
  tp2_ratio: 0.5
  
  # Features
  enable_breakeven: true
  
  # Capital & Risk
  capital: 10000
  risk_per_trade: 0.01
  
  # Costs
  cost_rate: 0.0002
  breakeven_offset: 0.0006
```

---

## 🔍 VALIDATION CHECKLIST

Before creating a new config file, verify:

- [ ] All 4 main sections present (data, execution, broker, strategy)
- [ ] All required fields in data section
- [ ] All required fields in execution section
- [ ] All required fields in broker section (if applicable)
- [ ] Strategy name matches Python class name
- [ ] trading_windows structure present (even if disabled)
- [ ] No typos in field names
- [ ] Consistent naming conventions used
- [ ] Comments explain non-obvious parameters

---

## 📚 EXAMPLES OF CORRECT CONFIGS

### Example 1: Simple Config (24/7 trading)

```yaml
# ============================================================
# CONFIGURATION BOLLINGER BREAKOUT - TRADING 24/7
# ============================================================

data:
  symbol: "NAS100"
  timeframe: "3min"
  months: 6
  file: "data/NAS100_3min.csv"
  use_specific_csv_file: true
  start_date: null
  end_date: null

execution:
  auto_download: false
  auto_html: true
  auto_open_browser: true
  refresh_data_days: 1

broker:
  initial_cash: 10000
  commission: 0.0
  slippage: 0.0

strategy:
  name: "BollingerBreakout"
  
  trading_windows:
    enabled: false
  
  bb_period: 20
  bb_std: 1.5
  rsi_period: 14
  rsi_overbought: 70
  rsi_oversold: 30
  sl_lookback: 5
  sl_offset_pips: 5
  sl_min_pips: 20
  sl_max_pips: 100
  tp1_ratio: 0.5
  enable_breakeven: true
  breakeven_offset: 2
  risk_per_trade: 100
  anti_flip_flop_enabled: true
  anti_flip_flop_pips: 20
```

### Example 2: With Trading Windows

```yaml
# ============================================================
# CONFIGURATION BOLLINGER BREAKOUT - WITH TRADING WINDOWS
# ============================================================

data:
  symbol: "NAS100"
  timeframe: "3min"
  months: 6
  file: "data/NAS100_3min.csv"
  use_specific_csv_file: true
  start_date: "2024-01-01"
  end_date: "2024-12-31"

execution:
  auto_download: false
  auto_html: true
  auto_open_browser: true
  refresh_data_days: 1

broker:
  initial_cash: 10000
  commission: 0.0
  slippage: 0.0

strategy:
  name: "BollingerBreakout"
  
  trading_windows:
    enabled: true
    timezone: "Europe/Paris"
    windows:
      - "Monday[13:00-16:00]"
      - "Tuesday[09:00-11:30]"
      - "Friday[08:00-12:00]"
  
  bb_period: 20
  bb_std: 1.5
  rsi_period: 14
  rsi_overbought: 70
  rsi_oversold: 30
  sl_lookback: 5
  sl_offset_pips: 5
  sl_min_pips: 20
  sl_max_pips: 100
  tp1_ratio: 0.5
  enable_breakeven: true
  breakeven_offset: 2
  risk_per_trade: 100
  anti_flip_flop_enabled: true
  anti_flip_flop_pips: 20
```

---

## ❌ COMMON MISTAKES TO AVOID

### Mistake 1: Missing Section

```yaml
# ❌ BAD - Missing execution section
data:
  symbol: "NAS100"
  timeframe: "3min"
  months: 6

strategy:
  name: "BollingerBreakout"
```

**Error**: `KeyError: 'execution'`

### Mistake 2: Missing Required Field

```yaml
# ❌ BAD - Missing 'months' field
data:
  symbol: "NAS100"
  timeframe: "3min"
  file: "data/NAS100_3min.csv"
  use_specific_csv_file: true
```

**Error**: `KeyError: 'months'`

### Mistake 3: Inconsistent Field Names

```yaml
# ❌ BAD - Using old field names
strategy:
  min_sl_distance_pips: 10  # Should be sl_min_pips
  max_sl_distance_pips: 100 # Should be sl_max_pips
```

---

## 🔄 MIGRATION FROM OLD CONFIGS

If you find an old config missing fields, add them:

```yaml
# Old config (incomplete)
data:
  symbol: "NAS100"
  timeframe: "3min"

# Add missing fields:
data:
  symbol: "NAS100"
  timeframe: "3min"
  months: 6                      # ADD THIS
  file: "data/NAS100_3min.csv"   # ADD THIS
  use_specific_csv_file: false   # ADD THIS
  start_date: null               # ADD THIS
  end_date: null                 # ADD THIS
```

---

## 🎯 SUMMARY FOR AI ASSISTANTS

When creating a new YAML config file:

1. **ALWAYS** start with the complete template above
2. **NEVER** omit any required section
3. **NEVER** omit any required field
4. Use consistent field names
5. Include trading_windows structure (even if disabled: false)
6. Add helpful comments
7. Follow the examples provided
8. Double-check against the validation checklist

**Remember**: A missing field will cause a `KeyError` at runtime!

---

## 📎 QUICK REFERENCE

**Minimum sections**:
- data (7 fields required)
- execution (4 fields required)
- broker (3 fields required if using main_backtest_generic.py)
- strategy (name + strategy-specific parameters)

**Optional but recommended**:
- start_date / end_date for filtering data
- trading_windows for time-based filters
- Comments explaining non-obvious parameters

---

✅ Use this guide every time you create a new config file  
✅ Validate against the checklist before saving  
✅ Keep configs consistent across the project  
✅ Update this guide if new required fields are added  
