# api.py
"""
Flask REST API backend for the Options Trading application.
"""
import sys
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

# Add project root to Python path
# This assumes api.py is in the project root, and src is a subdirectory
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config import get_settings
from src.db_client import AzureSqlClient
from src.options_service import process_underlying_once
from src.option_fetcher import _normalize_underlying
from src.trend_service import fetch_option_trend_data

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


@app.route('/api/stocks/count', methods=['GET'])
def get_stock_count():
    """Debug endpoint to check total stock count in database."""
    try:
        settings = get_settings_safe()
        db = AzureSqlClient(settings)
        db.connect()
        count = db.get_stock_count()
        db.close()
        return jsonify({"total_count": count}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/stocks/search', methods=['POST'])
def search_stocks():
    """
    Search for stocks by name, optionally filtered by segment.
    Request body: {"query": "Reliance", "segment": "NSE"}  # segment is optional
    Response: {"matches": [{"tradingsymbol": "...", "name": "...", "exchange": "..."}, ...]}
    """
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        segment = data.get('segment', '').strip() or None  # Optional segment filter
        
        if not query:
            return jsonify({"error": "Query parameter is required"}), 400
        
        settings = get_settings_safe()
        db = AzureSqlClient(settings)
        db.connect()
        
        # No limit - return all matching results
        matches = db.search_stocks_by_name(query, limit=None, segment=segment)
        db.close()
        
        matches_data = [
            {
                "tradingsymbol": s.tradingsymbol,
                "name": s.name,
                "exchange": s.exchange,
                "segment": s.segment,
            }
            for s in matches
        ]
        
        return jsonify({"matches": matches_data}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------- Options: REFRESH (Kite -> DB) -----------------


@app.route("/api/options/process", methods=["POST"])
def process_options():
    """
    Refresh options data for a selected underlying.

    Request body:
      {"tradingsymbol": "NIFTY"} or {"tradingsymbol": "RELIANCE"}

    Behavior:
      - Fetch latest NFO instruments from Kite
      - Filter for underlying
      - Upsert OptionInstrument
      - Fetch quotes + IV/Greeks
      - Insert into OptionSnapshot + OptionSnapshotCalc
    """
    import logging
    import traceback

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        logger.info("Received /api/options/process request")
        data = request.get_json()

        if not data:
            logger.error("No JSON data in request")
            return jsonify({"error": "Request body is required", "success": False}), 400

        tradingsymbol_raw = (data.get("tradingsymbol") or "").strip()
        if not tradingsymbol_raw:
            logger.error("Missing tradingsymbol in request")
            return jsonify(
                {"error": "tradingsymbol is required", "success": False}
            ), 400

        # Normalize the underlying name (e.g., "NIFTY50" -> "NIFTY")
        normalized_underlying = _normalize_underlying(tradingsymbol_raw)
        if not normalized_underlying:
            logger.error(f"Invalid tradingsymbol: {tradingsymbol_raw}")
            return jsonify(
                {"error": "Invalid tradingsymbol", "success": False}
            ), 400

        logger.info(f"Starting options processing for {tradingsymbol_raw} (normalized: {normalized_underlying})")

        try:
            settings = get_settings_safe()
        except Exception as e:
            logger.error(f"Failed to get settings: {e}")
            return jsonify(
                {
                    "error": f"Configuration error: {str(e)}",
                    "success": False,
                }
            ), 500

        logger.info(f"Fetching and processing options for {normalized_underlying}...")

        try:
            contracts, snapshots = process_underlying_once(normalized_underlying, settings)
            logger.info(f"Completed: {contracts} contracts, {snapshots} snapshots")

            return jsonify(
                {
                    "success": True,
                    "message": (
                        f"Processed {contracts} option contracts and "
                        f"inserted {snapshots} snapshots for {normalized_underlying}"
                    ),
                    "option_count": contracts,
                    "snapshot_count": snapshots,
                    "underlying_symbol": normalized_underlying,
                    "original_input": tradingsymbol_raw,
                }
            ), 200
        except Exception as proc_error:
            logger.error(f"Error in process_underlying_once: {proc_error}")
            traceback.print_exc()
            return jsonify(
                {
                    "error": f"Processing error: {str(proc_error)}",
                    "success": False,
                    "message": f"Error processing options: {str(proc_error)}",
                }
            ), 500

    except Exception as e:
        import traceback

        error_msg = str(e)
        logger.error(f"Unexpected error in process_options: {error_msg}")
        traceback.print_exc()
        return jsonify(
            {
                "error": error_msg,
                "success": False,
                "message": f"Unexpected error: {error_msg}",
            }
        ), 500

# ----------------- Options: VIEW latest chain (DB only) -----------------


@app.route("/api/options/latest", methods=["GET"])
def get_latest_options():
    """
    View latest option chain for a given underlying, from DB only.

    Request:
      GET /api/options/latest?tradingsymbol=NIFTY

    Response:
      {
        "underlying": "NIFTY",
        "count": 123,
        "rows": [
          {
            "option_instrument_id": ...,
            "underlying": "...",
            "tradingsymbol": "...",
            "strike": ...,
            "expiry": "...",
            "instrument_type": "CE"/"PE",
            "snapshot_time": "...",
            "underlying_price": ...,
            "last_price": ...,
            "bid_price": ...,
            "bid_qty": ...,
            "ask_price": ...,
            "ask_qty": ...,
            "volume": ...,
            "open_interest": ...,
            "implied_volatility": ...,
            "delta": ...,
            "gamma": ...,
            "theta": ...,
            "vega": ...
          },
          ...
        ]
      }
    """
    try:
        tradingsymbol_raw = (request.args.get("tradingsymbol") or "").strip()
        if not tradingsymbol_raw:
            return (
                jsonify(
                    {"error": "tradingsymbol query param is required", "success": False}
                ),
                400,
            )

        # Normalize the underlying name (e.g., "NIFTY50" -> "NIFTY")
        normalized_underlying = _normalize_underlying(tradingsymbol_raw)
        if not normalized_underlying:
            return (
                jsonify(
                    {"error": "Invalid tradingsymbol", "success": False}
                ),
                400,
            )

        settings = get_settings_safe()
        db = AzureSqlClient(settings)
        db.connect()
        rows = db.fetch_latest_option_chain_for_underlying(normalized_underlying)
        db.close()

        return (
            jsonify(
                {
                    "success": True,
                    "underlying": normalized_underlying,
                    "original_input": tradingsymbol_raw,
                    "count": len(rows),
                    "rows": rows,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ----------------- Options: HISTORICAL TREND -----------------


@app.route("/api/options/trend", methods=["GET"])
def get_option_trend():
    """
    Get historical trend data for a specific option instrument.
    
    Request:
      GET /api/options/trend?option_instrument_id=123&days=30
    
    Response:
      {
        "success": true,
        "option_instrument_id": 123,
        "tradingsymbol": "NIFTY25DEC24000CE",
        "strike": 24000.0,
        "expiry": "2024-12-25",
        "instrument_type": "CE",
        "data_points": [
          {
            "date": "2024-11-01",
            "timestamp": "2024-11-01T10:00:00",
            "underlying_price": 24050.0,
            "option_price": 150.5,
            "implied_volatility": 0.18,
            "delta": 0.45,
            "gamma": 0.001,
            "theta": -5.2,
            "vega": 12.5
          },
          ...
        ]
      }
    """
    try:
        option_instrument_id = request.args.get("option_instrument_id")
        days = request.args.get("days", "30")
        
        if not option_instrument_id:
            return jsonify({
                "success": False,
                "error": "option_instrument_id query param is required"
            }), 400
        
        try:
            option_instrument_id = int(option_instrument_id)
            days = int(days)
        except ValueError:
            return jsonify({
                "success": False,
                "error": "option_instrument_id and days must be integers"
            }), 400
        
        settings = get_settings_safe()
        trend_data = fetch_option_trend_data(
            option_instrument_id=option_instrument_id,
            days=days,
            settings=settings,
        )
        
        return jsonify({
            "success": True,
            **trend_data,
        }), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    # Increase timeout for long-running requests
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
