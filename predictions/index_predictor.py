# nifty_predictor.py (now supports NIFTY and BANKNIFTY)
import os
import sys
import argparse
import pandas as pd

from underlying_data import get_db_connection, fetch_index_daily

LOOKBACK_DAYS = 10
TREND_THRESH = 0.003          # 0.3% move over last 10 days to call trend
PRED_DIR = "predictions"
PRED_FILE_TEMPLATE = "{underlying}_predicted.csv"   # e.g. NIFTY_predicted.csv


def generate_prediction(window_closes: pd.Series,
                        trend_thresh: float = TREND_THRESH) -> str:
    """
    Use last LOOKBACK_DAYS closes to decide:
      - "CALL" (expect up), "PUT" (expect down), or "NO_POSITION".
    """
    first_close = float(window_closes.iloc[0])
    last_close = float(window_closes.iloc[-1])
    mean_close = float(window_closes.mean())

    trend_pct = (last_close - first_close) / first_close if first_close != 0 else 0.0

    if trend_pct > trend_thresh and last_close > mean_close:
        return "CALL"
    elif trend_pct < -trend_thresh and last_close < mean_close:
        return "PUT"
    else:
        return "NO_POSITION"


def generate_index_predictions(df_daily: pd.DataFrame,
                               lookback_days: int = LOOKBACK_DAYS) -> pd.DataFrame:
    """
    From daily index data with columns:
      trade_date, open_915, close_1515

    Generate one prediction per date where we have at least lookback_days history.
    Each row's 'date' = decision date D (15:15 close known),
    and prediction is for direction of D+1 open.

    Returns DataFrame: [date, prediction]
    """
    df = df_daily.copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.sort_values("trade_date").reset_index(drop=True)

    n = len(df)
    if n < lookback_days:
        raise ValueError("Not enough rows to generate predictions.")

    records = []
    for i in range(lookback_days - 1, n):
        window_start = i - lookback_days + 1
        window_end = i
        window_closes = df.loc[window_start:window_end, "close_1515"]

        pred = generate_prediction(window_closes)
        date = df.loc[i, "trade_date"]

        records.append({
            "date": date,
            "prediction": pred,
        })

    preds = pd.DataFrame(records).sort_values("date").reset_index(drop=True)
    return preds


def append_predictions_to_csv(new_preds: pd.DataFrame,
                              underlying: str,
                              folder: str = PRED_DIR,
                              regenerate_all: bool = False) -> pd.DataFrame:
    """
    Update predictions/{UNDERLYING}_predicted.csv.

    - If regenerate_all=False (default):
        * Append predictions only for dates not already present.
        * Preserve all existing columns/rows.

    - If regenerate_all=True:
        * Replace ALL predictions with new_preds.
        * Only preserve a small set of underlying backtest columns
          (today_close_1515, next_date, next_open_0915, gap_move_pct, result)
          for matching dates. All option-related columns should be recomputed.
    """
    underlying = underlying.upper()
    filename = PRED_FILE_TEMPLATE.format(underlying=underlying)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)

    new_preds = new_preds.copy()
    new_preds["date"] = pd.to_datetime(new_preds["date"])

    if regenerate_all:
        if os.path.isfile(path):
            existing = pd.read_csv(path, parse_dates=["date"])
            if not existing.empty and len(existing.columns) > 2:
                backtest_cols = [
                    "today_close_1515",
                    "next_date",
                    "next_open_0915",
                    "gap_move_pct",
                    "result",
                ]
                available_backtest_cols = [
                    col for col in backtest_cols if col in existing.columns
                ]
                if available_backtest_cols:
                    backtest_data = existing[["date"] + available_backtest_cols]
                    combined = new_preds.merge(backtest_data, on="date", how="left")
                else:
                    combined = new_preds
            else:
                combined = new_preds
        else:
            combined = new_preds
    else:
        if os.path.isfile(path):
            existing = pd.read_csv(path, parse_dates=["date"])
        else:
            existing = pd.DataFrame()

        if existing.empty:
            combined = new_preds
        else:
            new_only = new_preds[~new_preds["date"].isin(existing["date"])]
            combined = pd.concat([existing, new_only], ignore_index=True)

    combined = combined.sort_values("date").reset_index(drop=True)
    combined.to_csv(path, index=False)
    return combined


def main(underlying: str, regenerate_all: bool = False):
    underlying = underlying.upper()
    filename = PRED_FILE_TEMPLATE.format(underlying=underlying)
    path = os.path.join(PRED_DIR, filename)

    conn = get_db_connection()
    try:
        df_daily = fetch_index_daily(conn, underlying=underlying)
    finally:
        conn.close()

    print(f"[{underlying}] fetched {len(df_daily)} days of data")
    print(f"Date range: {df_daily['trade_date'].min()} to {df_daily['trade_date'].max()}")

    new_preds = generate_index_predictions(df_daily)
    print(f"[{underlying}] generated {len(new_preds)} predictions")

    if os.path.isfile(path):
        existing_before = pd.read_csv(path, parse_dates=["date"])
        existing_count_before = len(existing_before)
    else:
        existing_count_before = 0

    combined = append_predictions_to_csv(new_preds, underlying=underlying, regenerate_all=regenerate_all)

    if regenerate_all:
        print(f"[{underlying}] regenerated all {len(combined)} predictions")
    else:
        new_count = len(combined) - existing_count_before
        print(f"[{underlying}] added {new_count} new predictions (total: {len(combined)}, existing: {existing_count_before})")

    print(f"\n[{underlying}] predictions saved to {path}")
    print("\nFirst 5 predictions:")
    print(combined.head())
    print("\nLast 10 predictions:")
    print(combined.tail(10))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate index predictions (NIFTY/BANKNIFTY).")
    parser.add_argument(
        "-u", "--underlying",
        default="NIFTY",
        choices=["NIFTY", "BANKNIFTY"],
        help="Underlying index"
    )
    parser.add_argument(
        "-r", "--regenerate-all",
        action="store_true",
        help="Regenerate all predictions for this underlying"
    )
    args = parser.parse_args()
    main(underlying=args.underlying, regenerate_all=args.regenerate_all)
