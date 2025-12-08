# underlying_data.py
import sys
from pathlib import Path
import pyodbc
import pandas as pd
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
load_dotenv()

# Import config after path is set
from src.config import get_settings


def get_db_connection() -> pyodbc.Connection:
    """
    Return a live pyodbc connection using an ODBC-style connection string
    from environment variable (loaded from .env file via dotenv).

    Example .env value:
    AZURE_SQL_CONN_STR="DRIVER={ODBC Driver 18 for SQL Server};SERVER=xxx;
                        DATABASE=yyy;UID=...;PWD=...;Encrypt=yes;
                        TrustServerCertificate=no;"
    """
    settings = get_settings()
    conn_str = settings.azure_sql_conn_str
    if not conn_str:
        raise ValueError(
            "AZURE_SQL_CONN_STR is not set in environment or .env file. "
            "Please set it in your .env file."
        )
    return pyodbc.connect(conn_str)


def fetch_index_daily(
    conn: pyodbc.Connection,
    table_name: str = "dbo.UnderlyingSnapshot",
    underlying: str = "NIFTY",
) -> pd.DataFrame:
    """
    Fetch daily index data from dbo.UnderlyingSnapshot.

    Assumes two snapshots per day:
      - 09:15:00 -> use open_price as open_915
      - 15:15:00 -> use close_price as close_1515

    Returns DataFrame with:
      trade_date, open_915, close_1515
    """

    sql = f"""
    SELECT
        CAST(snapshot_time AS date)            AS trade_date,
        MIN(CASE 
                WHEN CONVERT(time, snapshot_time) = '09:15:00' 
                THEN open_price 
            END)                               AS open_915,
        MIN(CASE 
                WHEN CONVERT(time, snapshot_time) = '15:15:00' 
                THEN close_price 
            END)                               AS close_1515
    FROM {table_name}
    WHERE underlying = ?
    GROUP BY CAST(snapshot_time AS date)
    HAVING 
        MIN(CASE WHEN CONVERT(time, snapshot_time) = '09:15:00' THEN 1 END) = 1
        AND
        MIN(CASE WHEN CONVERT(time, snapshot_time) = '15:15:00' THEN 1 END) = 1
    ORDER BY trade_date;
    """

    df = pd.read_sql(sql, conn, params=[underlying])
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.sort_values("trade_date").reset_index(drop=True)
    return df


if __name__ == "__main__":
    conn = get_db_connection()
    df = fetch_index_daily(conn)
    print(df.head())
    print(df.tail())
    conn.close()
