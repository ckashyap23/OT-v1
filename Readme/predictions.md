# Predictions Module Documentation

This document provides a quick overview of the prediction system, how `index_predictor.py` and `option_selector.py` work, and the sequence for running all scripts in the `predictions/` folder.

---

## Overview

The predictions module implements a complete workflow for:
1. **Generating NIFTY direction predictions** (CALL/PUT/NO_POSITION)
2. **Selecting optimal option contracts** for each prediction
3. **Backtesting** both predictions and option trades

All scripts work with shared CSV files: `predictions/{UNDERLYING}_predicted.csv` (e.g., `NIFTY_predicted.csv`, `BANKNIFTY_predicted.csv`), which accumulate data through each stage.

---

## Core Scripts

### index_predictor.py

**Purpose**: Generates daily index direction predictions (NIFTY/BANKNIFTY) based on trend analysis.

**How it works**:
- Fetches historical index daily data (09:15 open, 15:15 close) from `UnderlyingSnapshot` table
- Uses a **10-day rolling window** to analyze price trends
- For each date with sufficient history:
  - Calculates trend percentage: `(last_close - first_close) / first_close`
  - Compares last close to mean close
  - Generates prediction:
    - **CALL**: If trend > 0.3% AND last_close > mean_close (expecting upward move)
    - **PUT**: If trend < -0.3% AND last_close < mean_close (expecting downward move)
    - **NO_POSITION**: Otherwise (no clear trend)

**Output**: Adds/updates `predictions/{UNDERLYING}_predicted.csv` with columns:
- `date`: Prediction date (decision made at 15:15 close)
- `prediction`: "CALL", "PUT", or "NO_POSITION"

**Usage**:
```bash
# Generate predictions for NIFTY (default)
python predictions/index_predictor.py -u NIFTY

# Generate predictions for BANKNIFTY
python predictions/index_predictor.py -u BANKNIFTY

# Regenerate all predictions
python predictions/index_predictor.py -u NIFTY --regenerate-all
```

---

### index_backtest.py

**Purpose**: Backtests the accuracy of index direction predictions.

**How it works**:
- For each prediction, checks the **next trading day's 09:15 open** vs **today's 15:15 close**
- Calculates gap move percentage: `(next_open - today_close) / today_close`
- Tags results:
  - **CORRECT**: CALL prediction and gap > 0, or PUT prediction and gap < 0
  - **INCORRECT**: CALL prediction and gap ≤ 0, or PUT prediction and gap ≥ 0
  - **MISSED_CALL/MISSED_PUT**: NO_POSITION but significant move (≥1%) occurred
  - **OK_NO_TRADE**: NO_POSITION and no significant move

**Output**: Updates `{UNDERLYING}_predicted.csv` with backtest columns:
- `today_close_1515`, `next_date`, `next_open_0915`
- `gap_move_pct`, `result`

**Usage**:
```bash
# Backtest NIFTY predictions (default)
python predictions/index_backtest.py -u NIFTY

# Backtest BANKNIFTY predictions
python predictions/index_backtest.py -u BANKNIFTY
```

**Prerequisites**: 
- `index_predictor.py` must be run first to create predictions

---

### option_selector.py

**Purpose**: Selects the best option contract for each CALL/PUT prediction.

**How it works**:
- Reads predictions from `{UNDERLYING}_predicted.csv`
- For each CALL/PUT prediction without an assigned option:
  - Fetches the full options chain at 15:15 for that date from database
  - Applies selection criteria:
    1. **Filter by side**: Only CALL options for CALL predictions, PUT for PUT
    2. **Expiry check**: Exclude same-day expiry options
    3. **Price check**: Only options with positive price
    4. **Nearest expiry**: Select options expiring soonest
    5. **ATM selection**: Choose strike closest to current underlying price
    6. **Liquidity**: Prefer highest volume, then highest open interest
  - Assigns the selected option details to the prediction row

**Output**: Updates `{UNDERLYING}_predicted.csv` with option columns:
- `option_trade_date`, `option_instrument_token`, `option_tradingsymbol`
- `option_strike`, `option_expiry`, `option_type`
- `selection_option_price_1515`

**Usage**:
```bash
# Select options for NIFTY (default)
python predictions/option_selector.py -u NIFTY

# Select options for BANKNIFTY
python predictions/option_selector.py -u BANKNIFTY

# Regenerate all option selections
python predictions/option_selector.py -u NIFTY --regenerate-all
```

**Prerequisites**: 
- `index_predictor.py` and `index_backtest.py` should be run first
- Database must have option snapshot data at 15:15 for the prediction dates

---

---

### option_backtest.py

**Purpose**: Calculates P&L for selected option trades.

**How it works**:
- For predictions with selected options:
  - Entry: Option price at **09:15** on the day after prediction (next trading day)
  - Exit: Option price at **15:15** on the same day (same-day exit strategy)
  - Calculates:
    - P&L per contract: `exit_price - entry_price`
    - P&L per lot: `pnl_per_contract × lot_size`
    - Return percentage: `pnl_per_contract / entry_price`

**Output**: Updates `{UNDERLYING}_predicted.csv` with option backtest columns:
- `option_entry_date`, `option_entry_price_0915`
- `option_exit_date`, `option_closing_price_1515`
- `option_lot_size`, `option_pnl_per_contract`, `option_pnl_per_lot`
- `option_return_pct`, `option_result`, `option_backtest_status`

**Usage**:
```bash
# Backtest options for NIFTY (default)
python predictions/option_backtest.py -u NIFTY

# Backtest options for BANKNIFTY
python predictions/option_backtest.py -u BANKNIFTY
```

**Prerequisites**:
- `index_predictor.py`, `index_backtest.py`, and `option_selector.py` must be run first
- Database must have option snapshot data at both 09:15 and 15:15 for entry/exit dates

---

## Helper Modules

### underlying_data.py

**Purpose**: Database connection and NIFTY daily data fetching utilities.

**Functions**:
- `get_db_connection()`: Creates database connection using `.env` configuration
- `fetch_index_daily()`: Fetches daily index data (09:15 open, 15:15 close) from `UnderlyingSnapshot` table

**Used by**: `index_predictor.py`, `index_backtest.py`, `option_backtest.py`

---

### options_data.py

**Purpose**: Option data fetching utilities from database.

**Functions**:
- `fetch_index_options_eod()`: Fetches full options chain at 15:15 for a date range
- `fetch_option_intraday_prices()`: Fetches 09:15 and 15:15 prices for specific option tokens

**Used by**: `option_selector.py`, `option_backtest.py`

---

## Execution Sequence

**Step 1: Generate Predictions**
```bash
python predictions/index_predictor.py -u NIFTY
# or
python predictions/index_predictor.py -u BANKNIFTY
```
- Generates new predictions for dates with sufficient data
- Creates/updates `{UNDERLYING}_predicted.csv` with prediction column

**Step 2: Backtest Predictions**
```bash
python predictions/index_backtest.py -u NIFTY
# or
python predictions/index_backtest.py -u BANKNIFTY
```
- Backtests prediction accuracy by comparing predictions to actual gap moves
- Updates CSV with prediction accuracy results (`result` column)
- Can be run multiple times as new data becomes available

**Step 3: Select Options**
```bash
python predictions/option_selector.py -u NIFTY
# or
python predictions/option_selector.py -u BANKNIFTY
```
- Selects best option contracts for CALL/PUT predictions
- Updates CSV with option details
- Only processes predictions that don't already have options assigned

**Step 4: Backtest Options**
```bash
python predictions/option_backtest.py -u NIFTY
# or
python predictions/option_backtest.py -u BANKNIFTY
```
- Calculates P&L for selected option trades
- Updates CSV with option performance metrics
- Can be run multiple times as new price data becomes available

## Data Flow

```
Database (UnderlyingSnapshot, OptionSnapshot)
    ↓
index_predictor.py
    ↓
{UNDERLYING}_predicted.csv (predictions)
    ↓
index_backtest.py
    ↓
{UNDERLYING}_predicted.csv (predictions + backtest results)
    ↓
option_selector.py
    ↓
{UNDERLYING}_predicted.csv (predictions + backtest + option selections)
    ↓
option_backtest.py
    ↓
{UNDERLYING}_predicted.csv (complete: predictions + backtest + options + P&L)
```

---

## CSV File Structure

The `{UNDERLYING}_predicted.csv` file accumulates columns as scripts run:

**After index_predictor.py**:
- `date`, `prediction`

**After index_backtest.py**:
- `today_close_1515`, `next_date`, `next_open_0915`, `gap_move_pct`, `result`

**After option_selector.py**:
- `option_trade_date`, `option_instrument_token`, `option_tradingsymbol`
- `option_strike`, `option_expiry`, `option_type`
- `selection_option_price_1515`

**After option_backtest.py**:
- `option_entry_date`, `option_entry_price_0915`
- `option_exit_date`, `option_closing_price_1515`
- `option_lot_size`, `option_pnl_per_contract`, `option_pnl_per_lot`
- `option_return_pct`, `option_result`, `option_backtest_status`

---

## Key Parameters

### index_predictor.py
- `LOOKBACK_DAYS = 10`: Number of days used for trend analysis
- `TREND_THRESH = 0.003`: Minimum 0.3% move to trigger CALL/PUT prediction

### index_backtest.py
- `SIGNIFICANT_MOVE_THRESH = 0.01`: 1% gap threshold for "missed" opportunities

### option_selector.py
- Selection criteria: Nearest expiry, ATM strike, highest volume/OI

---

## Troubleshooting

1. **"File not found" errors**: Run scripts in sequence - each depends on previous outputs
2. **"No option data found"**: Ensure `daily_intraday_stock_option.py` has collected data for the required dates
3. **Missing predictions**: Check that `UnderlyingSnapshot` table has sufficient historical data (at least 10 days)
4. **Option selection fails**: Verify that options exist in database for the prediction dates and that 15:15 snapshots are available

---

## Notes

- All scripts are **idempotent**: Safe to run multiple times
- Scripts only process rows that need updates (skip already processed data)
- The CSV file serves as the central state file - preserve it between runs
- Backtest scripts can be run repeatedly as new data becomes available

