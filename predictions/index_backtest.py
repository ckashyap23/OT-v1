# index_backtest.py
import os
import sys
import argparse
import pandas as pd

from underlying_data import get_db_connection, fetch_index_daily

PRED_DIR = "predictions"
PRED_FILE_TEMPLATE = "{underlying}_predicted.csv"
SIGNIFICANT_MOVE_THRESH = 0.01   # 1% gap => MISSED_CALL / MISSED_PUT for NO_POSITION


def _ensure_backtest_columns(preds: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure the predictions dataframe has all underlying-backtest columns.
    They will be fully overwritten on each run.
    """
    cols = [
        "today_close_1515",
        "next_date",
        "next_open_0915",
        "gap_move_pct",
        "result",
    ]
    for c in cols:
        if c not in preds.columns:
            preds[c] = pd.NA
    return preds


def main(underlying: str):
    underlying = underlying.upper()
    filename = PRED_FILE_TEMPLATE.format(underlying=underlying)
    path = os.path.join(PRED_DIR, filename)
    
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"{path} not found. Run index_predictor.py -u {underlying} first to create predictions."
        )

    # Load predictions
    preds = pd.read_csv(path, parse_dates=["date"])
    preds["date"] = pd.to_datetime(preds["date"]).dt.normalize()
    preds = _ensure_backtest_columns(preds)

    # Load full index daily data
    conn = get_db_connection()
    try:
        df_daily = fetch_index_daily(conn, underlying=underlying)
    finally:
        conn.close()

    df_daily["trade_date"] = pd.to_datetime(df_daily["trade_date"]).dt.normalize()
    df_daily = df_daily.sort_values("trade_date").reset_index(drop=True)

    # Build mapping: date -> next trading date
    df_daily["next_trade_date"] = df_daily["trade_date"].shift(-1)
    next_map = df_daily.set_index("trade_date")["next_trade_date"]

    # Fast lookup for daily data
    daily_by_date = df_daily.set_index("trade_date")

    # ---- full recompute for ALL rows ----
    for idx, row in preds.iterrows():
        date = row["date"]

        # Default: clear values; we'll fill if we can compute
        preds.at[idx, "today_close_1515"] = pd.NA
        preds.at[idx, "next_date"] = pd.NA
        preds.at[idx, "next_open_0915"] = pd.NA
        preds.at[idx, "gap_move_pct"] = pd.NA
        preds.at[idx, "result"] = pd.NA

        if pd.isna(date):
            continue

        # If this date isn't in underlying data, skip
        if date not in daily_by_date.index:
            continue

        # Today's close
        today_close = float(daily_by_date.loc[date, "close_1515"])
        preds.at[idx, "today_close_1515"] = today_close

        # Next trading day
        if date not in next_map.index:
            continue

        next_date = next_map[date]
        if pd.isna(next_date):
            # last available date: no next day yet
            continue

        if next_date not in daily_by_date.index:
            continue

        preds.at[idx, "next_date"] = next_date

        # Next day's 09:15 open
        next_open = float(daily_by_date.loc[next_date, "open_915"])
        preds.at[idx, "next_open_0915"] = next_open

        # Gap move
        gap_move_pct = (next_open - today_close) / today_close if today_close != 0 else 0.0
        preds.at[idx, "gap_move_pct"] = gap_move_pct

        # Tag result based on prediction vs gap direction
        pred = row["prediction"]
        if pred == "CALL":
            result = "CORRECT" if gap_move_pct > 0 else "INCORRECT"
        elif pred == "PUT":
            result = "CORRECT" if gap_move_pct < 0 else "INCORRECT"
        elif pred == "NO_POSITION":
            if abs(gap_move_pct) >= SIGNIFICANT_MOVE_THRESH:
                result = "MISSED_CALL" if gap_move_pct > 0 else "MISSED_PUT"
            else:
                result = "OK_NO_TRADE"
        else:
            # Unknown / empty prediction
            result = pd.NA

        preds.at[idx, "result"] = result

    preds = preds.sort_values("date").reset_index(drop=True)
    preds.to_csv(path, index=False)

    print(f"[{underlying}] Underlying backtest recomputed for {len(preds)} rows in {path}")
    print(
        preds[
            [
                "date",
                "prediction",
                "today_close_1515",
                "next_date",
                "next_open_0915",
                "gap_move_pct",
                "result",
            ]
        ].tail()
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest index predictions (NIFTY/BANKNIFTY).")
    parser.add_argument(
        "-u", "--underlying",
        default="NIFTY",
        choices=["NIFTY", "BANKNIFTY"],
        help="Underlying index"
    )
    args = parser.parse_args()
    main(underlying=args.underlying)
