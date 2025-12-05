# src/main.py
import sys
from pathlib import Path

# Add project root to Python path when running as script
# This allows the file to be run directly: python src/main.py
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from datetime import date

from src.config import get_settings
from src.db_client import AzureSqlClient
from src.kite_client import KiteClient
from src.option_fetcher import filter_options_for_underlyings
# from src.option_data_fetcher import fetch_option_quotes, map_quotes_to_option_data
from src.stock_search import find_stock_symbol


def run() -> None:
    settings = get_settings()

    # 1) Ask user for stock name
    query_name = input("Enter stock name (e.g., Reliance, TCS): ").strip()
    if not query_name:
        print("No input given, exiting.")
        return

    # 2) Find symbol from StockDB
    db = AzureSqlClient(settings)
    db.connect()

    stock = find_stock_symbol(db, query_name)
    if stock is None:
        db.close()
        return

    underlying_symbol = stock.tradingsymbol.upper()
    # Keep DB connection open for later use

    print(f"\nUsing underlying symbol: {underlying_symbol}")

    # 3) Fetch NFO instruments (all) from Kite
    kite_client = KiteClient(settings)
    kite_client.authenticate()
    instruments_nfo = kite_client.fetch_instruments_nfo()

    # 4) Build OptionInstrument list for this underlying
    option_contracts = filter_options_for_underlyings(
        instruments_dump=instruments_nfo,
        underlyings=[underlying_symbol],
    )
    print(f"Found {len(option_contracts)} option contracts for {underlying_symbol}")

    # 5) ALWAYS save contracts to OptionInstrument table
    db.upsert_option_instruments(option_contracts)

    # 6) Get mapping instrument_token -> OptionInstrument.id
    token_to_id = db.get_option_instrument_ids_by_token(
        o.instrument_token for o in option_contracts
    )

    # 7) Fetch quotes from Kite and map to OptionData
    #quotes_by_token = fetch_option_quotes(kite_client.kite, option_contracts)
    #option_data_rows = map_quotes_to_option_data(token_to_id, quotes_by_token)
    #print(f"Prepared {len(option_data_rows)} OptionData snapshot rows")

    # 8) Save OptionData snapshot
    #db.bulk_insert_option_data(option_data_rows)

    db.close()
    print("Done. OptionInstrument and OptionData updated.")


if __name__ == "__main__":
    run()
