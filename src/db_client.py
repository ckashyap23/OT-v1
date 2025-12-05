# src/db_client.py
from typing import Iterable, List, Optional, Dict
import pyodbc

from .config import Settings
from .models import StockInstrument, OptionInstrument, OptionData


class AzureSqlClient:
    def __init__(self, settings: Settings) -> None:
        self._conn_str = settings.azure_sql_conn_str
        self._conn: Optional[pyodbc.Connection] = None
        
        if not self._conn_str:
            raise RuntimeError(
                "AZURE_SQL_CONN_STR is missing in .env file.\n"
                "Format: DRIVER={SQL Server};SERVER=server.database.windows.net,1433;DATABASE=mydb;UID=username;PWD=password"
            )

    def connect(self) -> None:
        if self._conn is None:
            try:
                # For Azure SQL, we may need to add encryption and other parameters
                # Try the connection string as-is first
                self._conn = pyodbc.connect(self._conn_str, timeout=10)
            except pyodbc.Error as e:
                error_msg = str(e)
                suggestions = []
                
                if "does not exist" in error_msg or "access denied" in error_msg:
                    suggestions.append(
                        "1. Verify the server name is correct (e.g., yourserver.database.windows.net)"
                    )
                    suggestions.append(
                        "2. Check that your IP address is allowed in Azure SQL firewall rules"
                    )
                    suggestions.append(
                        "3. Verify username and password are correct"
                    )
                    suggestions.append(
                        "4. Ensure the database name is correct"
                    )
                    suggestions.append(
                        "5. For Azure SQL, you may need to add: Encrypt=yes;TrustServerCertificate=no"
                    )
                
                raise RuntimeError(
                    f"Failed to connect to Azure SQL: {e}\n\n"
                    f"Troubleshooting steps:\n" + "\n".join(suggestions) + "\n\n"
                    f"Connection string format for Azure SQL:\n"
                    f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER=server.database.windows.net,1433;"
                    f"DATABASE=mydb;UID=username;PWD=password;Encrypt=yes;TrustServerCertificate=no"
                ) from e

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> pyodbc.Connection:
        if self._conn is None:
            raise RuntimeError("DB not connected. Call connect() first.")
        return self._conn

    # ---------- STOCKS (StockDB) ----------

    def rebuild_stock_db(self, stocks: Iterable[StockInstrument]) -> None:
        stocks = list(stocks)
        cursor = self.conn.cursor()

        cursor.execute("TRUNCATE TABLE dbo.StockDB;")

        if stocks:
            cursor.fast_executemany = True
            rows = [
                (
                    s.exchange,
                    s.tradingsymbol,
                    s.name,
                    s.instrument_token,
                    s.segment,
                    s.tick_size,
                    s.lot_size,
                )
                for s in stocks
            ]

            cursor.executemany(
                """
                INSERT INTO dbo.StockDB (
                    exchange,
                    tradingsymbol,
                    name,
                    instrument_token,
                    segment,
                    tick_size,
                    lot_size
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

        self.conn.commit()

    def search_stocks_by_name(self, query: str, limit: int = 10) -> List[StockInstrument]:
        cursor = self.conn.cursor()
        pattern = f"%{query}%"

        sql = f"""
        SELECT TOP {limit}
            exchange,
            tradingsymbol,
            name,
            instrument_token,
            segment,
            tick_size,
            lot_size
        FROM dbo.StockDB
        WHERE name LIKE ? OR tradingsymbol LIKE ?
        ORDER BY tradingsymbol
        """

        cursor.execute(sql, (pattern, pattern))
        rows = cursor.fetchall()

        results: List[StockInstrument] = []
        for r in rows:
            results.append(
                StockInstrument(
                    exchange=r.exchange,
                    tradingsymbol=r.tradingsymbol,
                    name=r.name,
                    instrument_token=r.instrument_token,
                    segment=r.segment,
                    tick_size=float(r.tick_size) if r.tick_size is not None else None,
                    lot_size=int(r.lot_size) if r.lot_size is not None else None,
                )
            )
        return results

    # ---------- OPTION INSTRUMENTS ----------

    def upsert_option_instruments(
        self, options: Iterable[OptionInstrument]
    ) -> None:
        options = list(options)
        if not options:
            return

        cursor = self.conn.cursor()

        tokens = {o.instrument_token for o in options}
        params = ",".join("?" for _ in tokens)

        existing_tokens: set[int] = set()
        if tokens:
            cursor.execute(
                f"""
                SELECT instrument_token
                FROM dbo.OptionInstrument
                WHERE instrument_token IN ({params})
                """,
                list(tokens),
            )
            for row in cursor.fetchall():
                existing_tokens.add(int(row.instrument_token))

        new_options = [o for o in options if o.instrument_token not in existing_tokens]
        if new_options:
            cursor.fast_executemany = True
            rows = [
                (
                    o.fetch_date,
                    o.instrument_token,
                    o.underlying,
                    o.exchange,
                    o.tradingsymbol,
                    o.name,
                    o.strike,
                    o.expiry,
                    o.instrument_type,
                    o.lot_size,
                    o.tick_size,
                    o.segment,
                )
                for o in new_options
            ]
            cursor.executemany(
                """
                INSERT INTO dbo.OptionInstrument (
                    fetch_date,
                    instrument_token,
                    underlying,
                    exchange,
                    tradingsymbol,
                    name,
                    strike,
                    expiry,
                    instrument_type,
                    lot_size,
                    tick_size,
                    segment
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            self.conn.commit()

    def get_option_instrument_ids_by_token(
        self, tokens: Iterable[int]
    ) -> Dict[int, int]:
        token_list = list(tokens)
        if not token_list:
            return {}

        params = ",".join("?" for _ in token_list)
        cursor = self.conn.cursor()
        cursor.execute(
            f"""
            SELECT instrument_token, id
            FROM dbo.OptionInstrument
            WHERE instrument_token IN ({params})
            """,
            token_list,
        )

        mapping: Dict[int, int] = {}
        for row in cursor.fetchall():
            mapping[int(row.instrument_token)] = int(row.id)
        return mapping

    # ---------- OPTION DATA (snapshots) ----------

    def bulk_insert_option_data(self, data_rows: Iterable[OptionData]) -> None:
        data_list = list(data_rows)
        if not data_list:
            return

        cursor = self.conn.cursor()
        cursor.fast_executemany = True

        rows = [
            (
                d.option_instrument_id,
                d.snapshot_time,
                d.underlying_price,
                d.last_price,
                d.bid_price,
                d.bid_qty,
                d.ask_price,
                d.ask_qty,
                d.volume,
                d.open_interest,
                d.implied_volatility,
                d.delta,
                d.gamma,
                d.theta,
                d.vega,
            )
            for d in data_list
        ]

        cursor.executemany(
            """
            INSERT INTO dbo.OptionData (
                option_instrument_id,
                snapshot_time,
                underlying_price,
                last_price,
                bid_price,
                bid_qty,
                ask_price,
                ask_qty,
                volume,
                open_interest,
                implied_volatility,
                delta,
                gamma,
                theta,
                vega
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()
