# OT-v1 - Options Trading Application

A full-stack application for fetching and processing options trading data from Kite Connect API, with a Flutter UI and Flask backend.

## Project Structure

```
OT-v1/
├── src/                    # Python backend source code
│   ├── api.py              # Flask REST API
│   ├── config.py           # Configuration management
│   ├── db_client.py        # Azure SQL database client
│   ├── kite_client.py      # Kite Connect API client
│   ├── option_fetcher.py   # Options data processing
│   ├── stock_fetcher.py    # Stock data processing
│   ├── stock_search.py     # Stock search functionality
│   └── models.py           # Data models
├── flutter_app/            # Flutter UI application
│   ├── lib/
│   │   └── main.dart       # Main Flutter app
│   └── pubspec.yaml        # Flutter dependencies
├── scripts/                # Utility scripts
│   ├── get_kite_access_token.py
│   └── build_stock_db.py
├── requirements.txt        # Python dependencies
└── .env.example            # Environment variables template
```

## Features

- **Stock Search**: Search for stocks by name and select from matches
- **Options Processing**: Fetch and process option contracts for selected stocks
- **Database Integration**: Store option instruments in Azure SQL Database
- **REST API**: Flask backend with CORS support for Flutter app
- **Minimal UI**: Clean Flutter interface for user interaction

## Setup

### Backend Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables (copy `.env.example` to `.env`):
```bash
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_api_secret
KITE_ACCESS_TOKEN_PATH=.secrets/kite_access_token.txt
AZURE_SQL_CONN_STR=DRIVER={SQL Server};SERVER=...;DATABASE=...;UID=...;PWD=...
TARGET_UNDERLYINGS=NIFTY,BANKNIFTY
```

3. Get Kite access token:
```bash
python scripts/get_kite_access_token.py
```

4. Build stock database:
```bash
python scripts/build_stock_db.py
```

5. Run the API:
```bash
python start_api.py
```

### Flutter UI Setup

1. Install Flutter: https://flutter.dev/docs/get-started/install

2. Navigate to Flutter app:
```bash
cd flutter_app
flutter pub get
```

3. Update API URL in `lib/main.dart`:
   - Change `_apiBaseUrl` to your backend URL

4. Run the app:
```bash
flutter run
```

## Azure Deployment

### Backend (Azure App Service)

See `DEPLOY.md` for detailed manual deployment instructions.

**Quick steps:**
1. Create ZIP with: `src/`, `scripts/`, `requirements.txt`, `gunicorn_config.py`, `startup.sh`, `start_api.py`, `.deployment`, `build.sh`
2. Deploy via Azure Portal (Deployment Center → ZIP Deploy) or Azure CLI
3. Enable auto-build: Set `SCM_DO_BUILD_DURING_DEPLOYMENT=true` and `ENABLE_ORYX_BUILD=true`
4. Set startup command: `gunicorn --bind 0.0.0.0:8000 --timeout 600 --workers 2 --pythonpath /home/site/wwwroot gunicorn_config:application`
5. Configure environment variables in Azure Portal

### Frontend (Azure Static Web Apps)

1. Build Flutter web app:
```bash
cd flutter_app
flutter build web --release
```

2. Deploy to Azure Static Web Apps via Azure Portal

## Development

- Backend API: `http://localhost:5000`
- Flutter app: Run with `flutter run` (defaults to debug mode)

## License

[Your License Here]

