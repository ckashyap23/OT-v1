# Scripts Documentation

This document provides detailed information about the scripts in the `scripts/` directory, explaining what each script does, how to run it, prerequisites, and expected outcomes.

---

## Table of Contents

1. [get_kite_access_token.py](#get_kite_access_tokenpy)
2. [daily_intraday_stock_option.py](#daily_intraday_stock_optionpy)

---

## get_kite_access_token.py

### Purpose
This script is a **one-time setup script** that authenticates with Zerodha Kite Connect API and saves the access token to a file. The access token is required for all subsequent API calls to fetch market data.

### Prerequisites
1. **Environment Variables** (must be set in `.env` file in project root):
   - `KITE_API_KEY`: Your Zerodha Kite Connect API key
   - `KITE_API_SECRET`: Your Zerodha Kite Connect API secret
   - `KITE_ACCESS_TOKEN_PATH`: (Optional) Path to save the access token file. Defaults to `kite_access_token.txt` in project root.

2. **Zerodha Account**: You must have a Zerodha trading account with Kite Connect API access enabled.

### How to Run
```bash
python scripts/get_kite_access_token.py
```

### Step-by-Step Execution Flow

1. **Script Initialization**:
   - Loads environment variables from `.env` file
   - Validates that `KITE_API_KEY` and `KITE_API_SECRET` are present
   - Creates the token file directory if it doesn't exist

2. **Login URL Generation**:
   - Creates a KiteConnect instance with your API key
   - Generates a login URL that you need to open in your browser

3. **User Interaction**:
   - Script prints the login URL to console
   - **You must**: 
     - Open the URL in your browser
     - Log in to your Zerodha account
     - Complete 2FA (Two-Factor Authentication)
     - After successful login, you'll be redirected to a URL like: `http://127.0.0.1/?request_token=XXXXX&status=success`
     - Copy the **ENTIRE redirect URL** from the browser address bar

4. **Token Extraction**:
   - Paste the redirect URL when prompted by the script
   - Script extracts the `request_token` from the URL query parameters

5. **Access Token Generation**:
   - Script exchanges the `request_token` for a permanent `access_token` using your API secret
   - This access token is valid until you revoke it or it expires (typically 24 hours, but can be longer)

6. **Token Storage**:
   - Saves the access token to the file specified by `KITE_ACCESS_TOKEN_PATH` (or default `kite_access_token.txt`)
   - The file contains only the access token string (no newlines or extra formatting)

### Important Notes
- **One-time setup**: You typically only need to run this script once, or when your access token expires/gets revoked
- **Token validity**: Access tokens from Kite Connect typically expire after 24 hours, but can last longer. You'll need to re-run this script if your token expires
- **Security**: The access token file should be kept secure and not committed to version control (add to `.gitignore`)
- **File location**: The token file is created in the project root by default, or in the path specified by `KITE_ACCESS_TOKEN_PATH`

### Next Steps
After successfully running this script, you can proceed to run other scripts that require Kite API access, such as:
- `daily_intraday_stock_option.py`
- `bootstrap_instruments.py`
- `backfill_nifty_options_30d.py`

---

## daily_intraday_stock_option.py

### Purpose
This script performs **daily intraday data collection** for stock/option instruments. It:
1. Updates the stock and option instrument databases with latest instruments from Kite
2. Fetches 5-minute historical candle data for NIFTY and BANKNIFTY options
3. Creates snapshots at specific times (09:15 AM and/or 15:15 PM) with calculated IV and Greeks
4. Stores the snapshot data in the database for analysis

### Prerequisites
1. **Environment Variables** (must be set in `.env` file):
   - `KITE_API_KEY`: Your Zerodha Kite Connect API key
   - `KITE_API_SECRET`: Your Zerodha Kite Connect API secret
   - `KITE_ACCESS_TOKEN_PATH`: Path to access token file (default: `kite_access_token.txt`)
   - `AZURE_SQL_CONN_STR`: Azure SQL Database connection string

2. **Access Token**: Must have run `get_kite_access_token.py` successfully and have a valid access token file


### How to Run
```bash
python scripts/daily_intraday_stock_option.py
```

**Expected Output:**
```
Inserted OptionData snapshot rows for today's 5-min candles.
Daily intraday snapshot run complete.
```

### Important Notes

1. **Scheduling**: This script is designed to be run **twice daily**:
   - **Morning**: Schedule around 09:20 AM to capture 09:15 AM snapshot
   - **Afternoon**: Schedule around 15:20 PM to capture 15:15 PM snapshot

2. **Idempotency**: The script uses upsert logic, so it's safe to run multiple times:
   - Stock/option instruments: Only new instruments are added
   - Snapshots: Should have unique constraint on `(option_instrument_id, snapshot_time)` to prevent duplicates

3. **Performance**: 
   - Processing 2000+ options can take 10-30 minutes depending on API response times
   - Script processes options sequentially to respect API rate limits
   - Progress is logged every 100 options

4. **Data Quality**:
   - Only snapshots where both index and option candles exist at the same timestamp are created
   - IV and Greeks are only calculated when valid price data is available
   - Missing data (bid/ask) is set to NULL in historical candles

5. **Underlyings**: Currently hardcoded to process only NIFTY and BANKNIFTY. To add more:
   - Modify line 102: `interesting_underlyings = [u for u in ("NIFTY", "BANKNIFTY", "FINNIFTY") if u in underlying_to_token]`

### Database Schema Requirements

The script expects these tables to exist:

- **StockDB**: Stores stock/index instruments
- **OptionInstrument**: Stores option contract definitions
- **OptionSnapshot**: Stores raw option price/volume/OI data
- **OptionSnapshotCalc**: Stores calculated IV and Greeks

### Next Steps After Running

After successful execution:
1. Data is available in `OptionSnapshot` and `OptionSnapshotCalc` tables
2. Can be queried for analysis, backtesting, or visualization
3. Historical trend analysis can be performed using the collected snapshots
