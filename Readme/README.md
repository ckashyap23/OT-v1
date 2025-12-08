# OT-v1 - Options Trading Analytics Platform

A comprehensive full-stack application for fetching, processing, and analyzing options trading data from Zerodha Kite Connect API. Features a Flask REST API backend, Flutter web UI, and advanced prediction/backtesting capabilities.

---

## 🎯 Features

### Core Functionality
- **Stock & Index Search**: Search for stocks, indices from NSE/BSE with filtering by segment
- **Options Chain Management**: Fetch, process, and store option contracts with real-time data
- **IV & Greeks Calculation**: Automatic calculation of Implied Volatility and Option Greeks (Delta, Gamma, Theta, Vega) using Black-Scholes model
- **Historical Trend Analysis**: View 30-day historical trends for any option with interactive charts
- **Real-time Data Collection**: Automated daily snapshots at 09:15 AM and 15:15 PM

### Prediction & Backtesting
- **NIFTY Direction Predictions**: Trend-based prediction system (CALL/PUT/NO_POSITION)
- **Option Selection**: Intelligent option contract selection based on liquidity, moneyness, and expiry
- **Backtesting Framework**: Comprehensive backtesting for both predictions and option trades
- **Performance Analytics**: P&L calculation, return percentages, and accuracy metrics

### User Interface
- **Flutter Web App**: Modern, responsive UI for stock search and option chain visualization
- **Interactive Charts**: Multi-axis charts for price trends, IV, and Greeks using `fl_chart`
- **Real-time Updates**: Refresh option data and view latest snapshots

---

## 📁 Project Structure

```
OT-v1/
├── src/                          # Python backend source code
│   ├── api.py                    # Flask REST API endpoints
│   ├── config.py                 # Configuration management
│   ├── db_client.py              # Azure SQL database client
│   ├── kite_client.py            # Kite Connect API client
│   ├── models.py                 # Data models (StockInstrument, OptionInstrument, OptionData)
│   ├── option_fetcher.py         # Options data processing & IV/Greeks calculation
│   ├── options_service.py        # End-to-end options processing service
│   ├── stock_fetcher.py          # Stock data processing
│   ├── stock_search.py           # Stock search functionality
│   └── trend_service.py          # Historical trend data service
│
├── flutter_app/                  # Flutter web application
│   ├── lib/
│   │   ├── main.dart             # Main Flutter app (stock search, option chain)
│   │   └── trend_view_screen.dart # Historical trend visualization
│   └── pubspec.yaml              # Flutter dependencies
│
├── scripts/                      # Utility and automation scripts
│   ├── get_kite_access_token.py # Kite authentication setup
│   ├── daily_intraday_stock_option.py # Daily data collection
│   ├── bootstrap_instruments.py  # Initial database setup
│   ├── backfill_nifty_options_30d.py # Historical data backfill
│   └── backfill_nifty_underlying_30d.py # Underlying data backfill
│
├── predictions/                  # Prediction and backtesting module
│   ├── nifty_predictor.py        # NIFTY direction prediction generator
│   ├── option_selector.py        # Optimal option contract selector
│   ├── backtest_nifty.py         # Prediction accuracy backtesting
│   ├── option_backtest.py        # Option trade P&L backtesting
│   ├── underlying_data.py        # Underlying data utilities
│   └── options_data.py           # Option data utilities
│
├── api.py                        # Flask app entry point (root level)
├── run_local.py                  # Local development server runner
├── requirements.txt              # Python dependencies
├── scripts.md                    # Detailed scripts documentation
├── predictions.md                # Predictions module documentation
└── README.md                     # This file
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+**
- **Flutter SDK** (for web app)
- **Azure SQL Database** (or SQL Server)
- **Zerodha Kite Connect API** credentials
- **.env file** with required environment variables

### 1. Environment Setup

Create a `.env` file in the project root:

```bash
# Kite Connect API
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_api_secret
KITE_ACCESS_TOKEN_PATH=kite_access_token.txt

# Azure SQL Database
AZURE_SQL_CONN_STR=DRIVER={ODBC Driver 18 for SQL Server};SERVER=your_server.database.windows.net,1433;DATABASE=your_db;UID=your_username;PWD=your_password;Encrypt=yes;TrustServerCertificate=no;

# Optional
TARGET_UNDERLYINGS=NIFTY,BANKNIFTY
```

### 2. Install Dependencies

```bash
# Python dependencies
pip install -r requirements.txt

# Flutter dependencies
cd flutter_app
flutter pub get
cd ..
```

### 3. Initial Setup

```bash
# Step 1: Get Kite access token (one-time setup)
python scripts/get_kite_access_token.py

# Step 2: Bootstrap database with stock/option instruments
python scripts/bootstrap_instruments.py
```

### 4. Run the Application

**Backend (Terminal 1):**
```bash
python run_local.py
# API runs on http://localhost:5000
```

**Frontend (Terminal 2):**
```bash
cd flutter_app
flutter run -d chrome
# Flutter app opens in browser
```

---

## 📚 Documentation

### Scripts Documentation
See **[scripts.md](scripts.md)** for detailed information about:
- `get_kite_access_token.py` - Kite authentication setup
- `daily_intraday_stock_option.py` - Daily data collection workflow

### Predictions Documentation
See **[predictions.md](predictions.md)** for:
- Prediction system overview
- How `nifty_predictor.py` and `option_selector.py` work
- Execution sequence for all prediction scripts
- Backtesting workflow

---

## 🔌 API Endpoints

### Health & Status
- `GET /api/health` - Health check endpoint

### Stock Search
- `GET /api/stocks/search?q={query}&segment={NSE|BSE|INDICES|all}` - Search stocks/indices
- `GET /api/stocks/count` - Get total stock count

### Options Processing
- `POST /api/options/process` - Process options for an underlying (fetches from Kite, calculates IV/Greeks, stores in DB)
  - Body: `{"tradingsymbol": "NIFTY"}`
- `GET /api/options/latest?tradingsymbol={symbol}` - Get latest option chain from database
- `GET /api/options/trend?option_instrument_id={id}&days=30` - Get historical trend data for an option

---

## 🔄 Daily Workflow

### Data Collection (Automated)

**Schedule these scripts to run twice daily:**

1. **Morning (09:20 AM)**: Capture 09:15 AM snapshot
   ```bash
   python scripts/daily_intraday_stock_option.py
   ```

2. **Afternoon (15:20 PM)**: Capture 15:15 PM snapshot
   ```bash
   python scripts/daily_intraday_stock_option.py
   ```

### Prediction Workflow (Optional)

```bash
# 1. Generate predictions
python predictions/nifty_predictor.py

# 2. Backtest predictions (optional)
python predictions/backtest_nifty.py

# 3. Select options for predictions
python predictions/option_selector.py

# 4. Backtest option trades (optional)
python predictions/option_backtest.py
```

See **[predictions.md](predictions.md)** for detailed workflow.

---

## 🗄️ Database Schema

### Core Tables
- **StockDB**: Stock and index instruments (NSE/BSE)
- **OptionInstrument**: Option contract definitions
- **OptionSnapshot**: Raw option price/volume/OI snapshots
- **OptionSnapshotCalc**: Calculated IV and Greeks
- **UnderlyingSnapshot**: Underlying (index) price snapshots

### Views
- **vw_OptionLatestSnapshot**: Latest option chain with calculated data
- **vw_BankNIftysnapshotWithUnderlying**: Options with underlying prices (for predictions)

---

## 🛠️ Development

### Local Development

**Backend:**
```bash
# Run Flask development server
python run_local.py

# Or directly
python api.py
```

**Frontend:**
```bash
cd flutter_app
flutter run -d chrome
```

### Code Structure

- **Backend**: Modular Python code in `src/` with clear separation of concerns
- **Frontend**: Flutter app with Material Design UI
- **Scripts**: Standalone Python scripts for automation and data processing
- **Predictions**: Independent module for prediction and backtesting

---

## 📊 Key Components

### Options Processing Pipeline

1. **Fetch Instruments**: Get NFO instruments from Kite Connect
2. **Filter Options**: Extract CE/PE options for target underlyings
3. **Upsert to DB**: Store option instruments in database
4. **Fetch Quotes**: Get live option prices, volume, OI
5. **Calculate IV/Greeks**: Black-Scholes model calculations
6. **Store Snapshots**: Save raw and calculated data

### Prediction System

1. **Trend Analysis**: 10-day rolling window analysis
2. **Direction Prediction**: CALL/PUT/NO_POSITION based on trend threshold
3. **Option Selection**: Nearest expiry, ATM strike, highest liquidity
4. **Backtesting**: Accuracy and P&L calculation

---

## 🚢 Deployment

### Backend (Azure App Service)

1. Create ZIP with: `src/`, `scripts/`, `api.py`, `requirements.txt`
2. Deploy via Azure Portal (Deployment Center → ZIP Deploy)
3. Set environment variables in Azure Portal
4. Configure startup command (see `scripts.md` for details)

### Frontend (Azure Static Web Apps)

```bash
cd flutter_app
flutter build web --release
# Deploy build/web/ directory to Azure Static Web Apps
```

---

## 🔧 Configuration

### Key Parameters

**Options Processing:**
- Risk-free rate: 7% (annualized, for IV/Greeks calculation)
- Batch size: 1000 rows (for bulk database inserts)

**Predictions:**
- Lookback days: 10 days
- Trend threshold: 0.3% (0.003)
- Significant move threshold: 1% (0.01)

**Data Collection:**
- Snapshot times: 09:15 AM, 15:15 PM
- Supported underlyings: NIFTY, BANKNIFTY (configurable)

---

## 🐛 Troubleshooting

### Common Issues

1. **"Access token file not found"**
   - Run `python scripts/get_kite_access_token.py`

2. **"Too many parameters" SQL error**
   - Fixed in latest version - ensure you have the latest `db_client.py`

3. **"No option data found"**
   - Run `scripts/daily_intraday_stock_option.py` to collect data
   - Or use backfill scripts for historical data

4. **Flutter app not connecting to backend**
   - Check `_apiBaseUrl` in `flutter_app/lib/main.dart`
   - Ensure backend is running on the specified URL
   - Check CORS settings in `api.py`

5. **Database connection errors**
   - Verify `AZURE_SQL_CONN_STR` in `.env`
   - Check firewall rules for Azure SQL Database
   - Ensure ODBC driver is installed

---

## 📝 Notes

- **Idempotency**: All scripts are safe to run multiple times
- **Data Quality**: Only snapshots with valid price data are stored
- **Performance**: Bulk inserts are optimized with batching to handle large datasets
- **Rate Limiting**: Scripts include delays to respect Kite API rate limits

---

## 📄 License

[Your License Here]

---

## 🤝 Contributing

[Contributing guidelines if applicable]

---

## 📞 Support

For detailed documentation:
- **Scripts**: See [scripts.md](scripts.md)
- **Predictions**: See [predictions.md](predictions.md)
- **API**: Check `api.py` for endpoint documentation

For issues:
1. Check prerequisites and environment setup
2. Review script output logs
3. Verify database connectivity
4. Check Kite API authentication status
