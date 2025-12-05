# scripts/build_stock_db.py
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

from src.config import get_settings
from src.db_client import AzureSqlClient
from src.kite_client import KiteClient
from src.stock_fetcher import extract_stock_instruments

load_dotenv()


def main() -> None:
    settings = get_settings()

    kite_client = KiteClient(settings)
    kite_client.authenticate()

    print("Fetching NSE equity instruments from Kite...")
    instruments_dump = kite_client.fetch_instruments_equity()
    print(f"Got {len(instruments_dump)} raw NSE instruments")

    # Filter to stock instruments (EQ) and map to our model
    stocks = extract_stock_instruments(instruments_dump)
    print(f"Filtered down to {len(stocks)} equity instruments (EQ)")

    db = AzureSqlClient(settings)
    db.connect()
    print("Rebuilding StockDB table...")
    db.rebuild_stock_db(stocks)
    db.close()

    print("StockDB refresh complete.")


if __name__ == "__main__":
    main()
