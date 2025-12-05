# src/api.py
"""
Flask REST API backend for the Options Trading application.
"""
import sys
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

# Add project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config import get_settings
from src.db_client import AzureSqlClient
from src.kite_client import KiteClient
from src.option_fetcher import filter_options_for_underlyings
from src.models import StockInstrument

app = Flask(__name__)
CORS(app)  # Enable CORS for Flutter app

# Load settings lazily to avoid startup errors
settings = None

def get_settings_safe():
    """Get settings, initializing if needed."""
    global settings
    if settings is None:
        settings = get_settings()
    return settings


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint - should work even if other services fail."""
    try:
        return jsonify({
            "status": "ok",
            "message": "Backend is running"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/api/stocks/search', methods=['POST'])
def search_stocks():
    """
    Search for stocks by name.
    Request body: {"query": "Reliance"}
    Response: {"matches": [{"tradingsymbol": "...", "name": "...", "exchange": "..."}, ...]}
    """
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({"error": "Query parameter is required"}), 400
        
        settings = get_settings_safe()
        db = AzureSqlClient(settings)
        db.connect()
        
        matches = db.search_stocks_by_name(query, limit=10)
        db.close()
        
        matches_data = [
            {
                "tradingsymbol": s.tradingsymbol,
                "name": s.name,
                "exchange": s.exchange,
                "instrument_token": s.instrument_token,
            }
            for s in matches
        ]
        
        return jsonify({"matches": matches_data}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/options/process', methods=['POST'])
def process_options():
    """
    Process option contracts for a selected stock.
    Request body: {"tradingsymbol": "RELIANCE"}
    Response: {"success": true, "message": "...", "option_count": 123}
    """
    try:
        data = request.get_json()
        tradingsymbol = data.get('tradingsymbol', '').strip().upper()
        
        if not tradingsymbol:
            return jsonify({"error": "tradingsymbol is required"}), 400
        
        # Initialize clients
        settings = get_settings_safe()
        db = AzureSqlClient(settings)
        db.connect()
        
        kite_client = KiteClient(settings)
        kite_client.authenticate()
        
        # Fetch NFO instruments
        instruments_nfo = kite_client.fetch_instruments_nfo()
        
        # Filter options for the underlying
        option_contracts = filter_options_for_underlyings(
            instruments_dump=instruments_nfo,
            underlyings=[tradingsymbol],
        )
        
        # Save to database
        db.upsert_option_instruments(option_contracts)
        
        # Get mapping
        token_to_id = db.get_option_instrument_ids_by_token(
            o.instrument_token for o in option_contracts
        )
        
        db.close()
        
        return jsonify({
            "success": True,
            "message": f"Successfully processed {len(option_contracts)} option contracts for {tradingsymbol}",
            "option_count": len(option_contracts),
            "underlying_symbol": tradingsymbol,
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

