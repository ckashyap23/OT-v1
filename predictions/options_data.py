# options_data.py
import pandas as pd
import pyodbc


def _classify_option_side(row) -> str:
    """
    Classify each option row as 'CALL', 'PUT', or 'UNKNOWN'.

    Priority:
      1. tradingsymbol ending with CE/PE
      2. sign of delta (>=0 => CALL, <0 => PUT)
    """
    sym = str(row.get("tradingsymbol") or "")

    if sym.endswith("CE"):
        return "CALL"
    if sym.endswith("PE"):
        return "PUT"

    delta = row.get("delta")
    try:
        if pd.notna(delta):
            return "CALL" if float(delta) >= 0 else "PUT"
    except Exception:
        pass

    return "UNKNOWN"


def fetch_index_options_eod(
    conn: pyodbc.Connection,
    start_date=None,
    end_date=None,
    view_name: str = "dbo.vw_NiftySnapshotWithUnderlying",
    underlying_like: str = "NIFTY%",   # tolerant: NIFTY, NIFTY 50, etc.
) -> pd.DataFrame:
    """
    Fetch index option snapshots for the given date range, then
    reduce to one "EOD" snapshot per (trade_date, instrument_token)
    by taking the last snapshot_time of the day.

    Returns a DataFrame with at least:
      instrument_token, tradingsymbol, strike, expiry, lot_size,
      underlying_price, option_price, option_volume, open_interest,
      implied_volatility, delta, gamma, trade_date, option_side
    """

    sql = f"""
    SELECT
        instrument_token,
        underlying,
        snapshot_time,
        tradingsymbol,
        instrument_type,
        strike,
        expiry,
        lot_size,
        underlying_price,
        option_price,
        option_volume,
        open_interest,
        implied_volatility,
        delta,
        gamma
    FROM {view_name}
    WHERE option_price IS NOT NULL
      AND underlying LIKE ?
    """
    params = [underlying_like]

    # Convert dates to 'YYYY-MM-DD' strings for pyodbc
    if start_date is not None:
        start_str = pd.to_datetime(start_date).date().isoformat()
        sql += " AND CAST(snapshot_time AS date) >= ?"
        params.append(start_str)

    if end_date is not None:
        end_str = pd.to_datetime(end_date).date().isoformat()
        sql += " AND CAST(snapshot_time AS date) <= ?"
        params.append(end_str)

    sql += " ORDER BY snapshot_time, strike;"

    df = pd.read_sql(sql, conn, params=params)

    if df.empty:
        return df

    df["snapshot_time"] = pd.to_datetime(df["snapshot_time"])
    df["trade_date"] = df["snapshot_time"].dt.normalize()
    df["expiry"] = pd.to_datetime(df["expiry"])

    # Take the LAST snapshot per (trade_date, instrument_token) as "EOD"
    df = (
        df.sort_values(["instrument_token", "snapshot_time"])
          .groupby(["trade_date", "instrument_token"], as_index=False)
          .tail(1)
    )

    # Classify CALL / PUT
    df["option_side"] = df.apply(_classify_option_side, axis=1)

    return df
    
def fetch_option_intraday_prices(
    conn: pyodbc.Connection,
    instrument_tokens,
    start_date,
    end_date,
    view_name: str = "dbo.vw_NiftySnapshotWithUnderlying",
) -> pd.DataFrame:
    """
    Fetch ALL intraday snapshots for the given index instrument_tokens between
    start_date and end_date (inclusive).

    We do NOT filter by exact times in SQL; instead, option_backtest.py
    will treat:
      - earliest snapshot of the day as "entry" (approx 09:15)
      - latest snapshot of the day as "exit"  (approx 15:15)

    Returns DataFrame with columns:
      instrument_token, snapshot_time, trade_date,
      option_price, underlying_price, lot_size
    """
    # Deduplicate & clean tokens
    tokens = sorted({int(t) for t in instrument_tokens if pd.notna(t)})
    if not tokens:
        return pd.DataFrame()

    start_str = pd.to_datetime(start_date).date().isoformat()
    end_str = pd.to_datetime(end_date).date().isoformat()

    # Safety: chunk tokens so the IN clause & parameter count don't explode
    chunk_size = 100  # adjust if needed
    dfs = []

    for i in range(0, len(tokens), chunk_size):
        chunk_tokens = tokens[i : i + chunk_size]
        placeholders = ",".join("?" for _ in chunk_tokens)

        sql = f"""
        SELECT
            instrument_token,
            snapshot_time,
            option_price,
            underlying_price,
            lot_size
        FROM {view_name}
        WHERE instrument_token IN ({placeholders})
          AND CAST(snapshot_time AS date) >= ?
          AND CAST(snapshot_time AS date) <= ?
        ORDER BY instrument_token, snapshot_time;
        """

        params = list(chunk_tokens) + [start_str, end_str]
        chunk_df = pd.read_sql(sql, conn, params=params)
        if not chunk_df.empty:
            dfs.append(chunk_df)

    if not dfs:
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)

    df["snapshot_time"] = pd.to_datetime(df["snapshot_time"])
    df["trade_date"] = df["snapshot_time"].dt.normalize()

    return df