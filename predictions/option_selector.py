# option_selector.py
import os
import sys
import argparse
import pandas as pd

from underlying_data import get_db_connection
from options_data import fetch_index_options_eod

PRED_DIR = "predictions"
PRED_FILE_TEMPLATE = "{underlying}_predicted.csv"

# Adjust these if your actual view names differ
DEFAULT_OPTIONS_VIEWS = {
    "NIFTY": "dbo.vw_NiftySnapshotWithUnderlying",
    "BANKNIFTY": "dbo.vw_BankNiftySnapshotWithUnderlying",
}


def _ensure_option_columns(preds: pd.DataFrame) -> pd.DataFrame:
    required_cols = [
        "option_trade_date",
        "option_instrument_token",
        "option_tradingsymbol",
        "option_strike",
        "option_expiry",
        "option_type",
        "selection_option_price_1515",
    ]
    for col in required_cols:
        if col not in preds.columns:
            preds[col] = pd.NA
    return preds


def _clear_option_columns(preds: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "option_trade_date",
        "option_instrument_token",
        "option_tradingsymbol",
        "option_strike",
        "option_expiry",
        "option_type",
        "selection_option_price_1515",
    ]
    for col in cols:
        if col in preds.columns:
            preds[col] = pd.NA
    return preds


def _select_best_option_for_day(chain_df: pd.DataFrame,
                                prediction: str,
                                trade_date: pd.Timestamp):
    if prediction not in ("CALL", "PUT") or chain_df.empty:
        return None

    df = chain_df.copy()
    df = df[df["option_side"] == prediction]
    if df.empty:
        return None

    trade_date_norm = pd.to_datetime(trade_date).normalize()

    df = df[df["expiry"] > trade_date_norm]
    if df.empty:
        return None

    df = df[df["option_price"] > 0]
    if df.empty:
        return None

    df["days_to_expiry"] = (df["expiry"] - trade_date_norm).dt.days
    min_days = df["days_to_expiry"].min()
    df = df[df["days_to_expiry"] == min_days]

    underlying_series = df["underlying_price"].dropna()
    if underlying_series.empty:
        return None
    underlying_price = float(underlying_series.iloc[0])

    df["moneyness"] = (df["strike"] - underlying_price).abs()
    min_m = df["moneyness"].min()
    df = df[df["moneyness"] == min_m]

    if "option_volume" in df.columns and "open_interest" in df.columns:
        df = df.sort_values(["option_volume", "open_interest"], ascending=[False, False])
    elif "open_interest" in df.columns:
        df = df.sort_values("open_interest", ascending=False)
    else:
        df = df.sort_values("strike")

    row = df.iloc[0]

    return {
        "option_trade_date": trade_date_norm,
        "option_instrument_token": int(row["instrument_token"]),
        "option_tradingsymbol": row["tradingsymbol"],
        "option_strike": float(row["strike"]),
        "option_expiry": row["expiry"],
        "option_type": prediction,
        "selection_option_price_1515": float(row["option_price"]),
    }


def main(underlying: str, regenerate_all: bool, options_view: str | None):
    underlying = underlying.upper()
    filename = PRED_FILE_TEMPLATE.format(underlying=underlying)
    path = os.path.join(PRED_DIR, filename)

    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"{path} not found. Run nifty_predictor.py -u {underlying} first."
        )

    if options_view is None:
        options_view = DEFAULT_OPTIONS_VIEWS.get(
            underlying, "dbo.vw_BankNIftysnapshotWithUnderlying"
        )

    preds = pd.read_csv(path, parse_dates=["date"])
    preds["date"] = pd.to_datetime(preds["date"]).dt.normalize()
    preds = _ensure_option_columns(preds)

    if regenerate_all:
        preds = _clear_option_columns(preds)

    if regenerate_all:
        needed_dates = set(
            preds.loc[preds["prediction"].isin(["CALL", "PUT"]), "date"]
        )
    else:
        needed_dates = set()
        for _, row in preds.iterrows():
            if row["prediction"] not in ("CALL", "PUT"):
                continue
            if not (
                pd.isna(row["option_instrument_token"])
                or str(row["option_instrument_token"]).strip() == ""
            ):
                continue
            needed_dates.add(row["date"])

    if not needed_dates:
        print(f"[{underlying}] no predictions need option selection.")
        return

    start_date = min(needed_dates).date()
    end_date = max(needed_dates).date()

    conn = get_db_connection()
    try:
        options_df = fetch_index_options_eod(
            conn,
            start_date=start_date,
            end_date=end_date,
            view_name=options_view,
            underlying_like=f"{underlying}%",
        )
    finally:
        conn.close()

    if options_df.empty:
        print(f"[{underlying}] no option data found for requested dates.")
        return

    options_df["trade_date"] = pd.to_datetime(options_df["trade_date"]).dt.normalize()
    options_by_date = {d: g for d, g in options_df.groupby("trade_date")}

    for idx, row in preds.iterrows():
        pred = row["prediction"]
        if pred not in ("CALL", "PUT"):
            if regenerate_all:
                preds.at[idx, "option_instrument_token"] = pd.NA
            continue

        if (not regenerate_all) and not (
            pd.isna(row["option_instrument_token"])
            or str(row["option_instrument_token"]).strip() == ""
        ):
            continue

        trade_date = row["date"]
        chain_df = options_by_date.get(trade_date)
        if chain_df is None or chain_df.empty:
            continue

        best = _select_best_option_for_day(chain_df, pred, trade_date)
        if not best:
            continue

        for col, val in best.items():
            preds.at[idx, col] = val

    preds = preds.sort_values("date").reset_index(drop=True)
    preds.to_csv(path, index=False)
    print(f"[{underlying}] option selection updated in {path}")
    print(preds.tail())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Select best option instrument for NIFTY/BANKNIFTY predictions.")
    parser.add_argument(
        "-u", "--underlying",
        default="NIFTY",
        choices=["NIFTY", "BANKNIFTY"],
        help="Underlying index"
    )
    parser.add_argument(
        "-r", "--regenerate-all",
        action="store_true",
        help="Recompute options for ALL CALL/PUT predictions"
    )
    parser.add_argument(
        "--options-view",
        default=None,
        help="Override options snapshot view name (defaults depend on underlying)"
    )
    args = parser.parse_args()
    main(underlying=args.underlying, regenerate_all=args.regenerate_all, options_view=args.options_view)
