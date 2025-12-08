# option_backtest.py
import os
import argparse
import pandas as pd

from underlying_data import get_db_connection, fetch_index_daily
from options_data import fetch_option_intraday_prices

PRED_DIR = "predictions"
PRED_FILE_TEMPLATE = "{underlying}_predicted.csv"

DEFAULT_OPTIONS_VIEWS = {
    "NIFTY": "dbo.vw_NiftySnapshotWithUnderlying",
    "BANKNIFTY": "dbo.vw_BankNiftySnapshotWithUnderlying",
}


def _ensure_option_backtest_cols(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "option_entry_date",
        "option_entry_price_0915",
        "option_exit_date",
        "option_closing_price_1515",
        "option_lot_size",
        "option_pnl_per_contract",
        "option_pnl_per_lot",
        "option_return_pct",
        "option_result",
        "option_backtest_status",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = pd.NA
    return df


def main(underlying: str, options_view: str | None):
    underlying = underlying.upper()
    filename = PRED_FILE_TEMPLATE.format(underlying=underlying)
    path = os.path.join(PRED_DIR, filename)

    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"{path} not found. Run index_predictor.py -u {underlying} and option_selector.py -u {underlying} first."
        )

    if options_view is None:
        options_view = DEFAULT_OPTIONS_VIEWS.get(
            underlying, "dbo.vw_NiftySnapshotWithUnderlying"
        )

    preds = pd.read_csv(path, parse_dates=["date"])
    preds["date"] = preds["date"].dt.normalize()
    preds = _ensure_option_backtest_cols(preds)

    backtest_cols = [
        "option_entry_date",
        "option_entry_price_0915",
        "option_exit_date",
        "option_closing_price_1515",
        "option_lot_size",
        "option_pnl_per_contract",
        "option_pnl_per_lot",
        "option_return_pct",
        "option_result",
        "option_backtest_status",
    ]
    for c in backtest_cols:
        preds[c] = pd.NA

    mask = (
        preds["prediction"].isin(["CALL", "PUT"])
        & preds["option_instrument_token"].notna()
    )
    needing = preds[mask].copy()
    if needing.empty:
        print(f"[{underlying}] no rows with CALL/PUT + option_instrument_token to backtest.")
        preds.to_csv(path, index=False)
        return

    conn = get_db_connection()
    try:
        df_daily = fetch_index_daily(conn, underlying=underlying)
        df_daily["trade_date"] = pd.to_datetime(df_daily["trade_date"]).dt.normalize()
        df_daily = df_daily.sort_values("trade_date").reset_index(drop=True)
        df_daily["next_trade_date"] = df_daily["trade_date"].shift(-1)
        next_map = df_daily.set_index("trade_date")["next_trade_date"]
    finally:
        conn.close()

    entry_info = {}
    entry_dates = []
    tokens = set()

    for idx, row in preds[mask].iterrows():
        pred_date = row["date"]
        if pred_date not in next_map.index:
            preds.at[idx, "option_backtest_status"] = "NO_NEXT_TRADE_DATE"
            continue

        entry_date = next_map[pred_date]
        if pd.isna(entry_date):
            preds.at[idx, "option_backtest_status"] = "NO_NEXT_TRADE_DATE"
            continue

        entry_date = pd.to_datetime(entry_date).normalize()
        entry_info[idx] = entry_date
        entry_dates.append(entry_date)

        try:
            token = int(row["option_instrument_token"])
        except Exception:
            preds.at[idx, "option_backtest_status"] = "BAD_TOKEN"
            continue

        tokens.add(token)

    if not entry_dates or not tokens:
        print(f"[{underlying}] no valid entry dates or tokens to backtest.")
        preds.to_csv(path, index=False)
        return

    start_date = min(entry_dates).date()
    end_date = max(entry_dates).date()

    conn = get_db_connection()
    try:
        prices_df = fetch_option_intraday_prices(
            conn,
            instrument_tokens=tokens,
            start_date=start_date,
            end_date=end_date,
            view_name=options_view,
        )
    finally:
        conn.close()

    if prices_df.empty:
        print(f"[{underlying}] no option price data found for required tokens/date range.")
        preds.to_csv(path, index=False)
        return

    prices_df["trade_date"] = pd.to_datetime(prices_df["trade_date"]).dt.normalize()

    lookup = {}
    for (token, trade_date), group in prices_df.groupby(["instrument_token", "trade_date"]):
        group_sorted = group.sort_values("snapshot_time")
        entry_row = group_sorted.iloc[0]
        exit_row = group_sorted.iloc[-1]

        entry_price = float(entry_row["option_price"])
        exit_price = float(exit_row["option_price"])
        lot_size = (
            int(group_sorted["lot_size"].iloc[0])
            if "lot_size" in group_sorted.columns and pd.notna(group_sorted["lot_size"].iloc[0])
            else None
        )

        lookup[(int(token), trade_date)] = {
            "entry_price": entry_price,
            "exit_price": exit_price,
            "lot_size": lot_size,
        }

    for idx, row in preds[mask].iterrows():
        if idx not in entry_info:
            continue

        token = int(row["option_instrument_token"])
        entry_date = entry_info[idx]
        key = (token, entry_date)

        if key not in lookup:
            preds.at[idx, "option_backtest_status"] = "NO_PRICE_DATA"
            continue

        info = lookup[key]
        entry_price = info["entry_price"]
        exit_price = info["exit_price"]
        lot_size = info["lot_size"]

        preds.at[idx, "option_entry_date"] = entry_date
        preds.at[idx, "option_entry_price_0915"] = entry_price
        preds.at[idx, "option_exit_date"] = entry_date
        preds.at[idx, "option_closing_price_1515"] = exit_price

        if lot_size is not None:
            preds.at[idx, "option_lot_size"] = lot_size

        pnl_per_contract = exit_price - entry_price
        preds.at[idx, "option_pnl_per_contract"] = pnl_per_contract

        if lot_size:
            preds.at[idx, "option_pnl_per_lot"] = pnl_per_contract * lot_size

        if entry_price != 0:
            preds.at[idx, "option_return_pct"] = pnl_per_contract / entry_price

        if pnl_per_contract > 0:
            preds.at[idx, "option_result"] = "PROFIT"
        elif pnl_per_contract < 0:
            preds.at[idx, "option_result"] = "LOSS"
        else:
            preds.at[idx, "option_result"] = "BREAKEVEN"

        preds.at[idx, "option_backtest_status"] = "DONE"

    preds = preds.sort_values("date").reset_index(drop=True)
    preds.to_csv(path, index=False)

    print(f"[{underlying}] option backtest recomputed for {len(preds[mask])} rows in {path}")
    print(
        preds.loc[mask, [
            "date",
            "prediction",
            "option_tradingsymbol",
            "option_entry_date",
            "option_entry_price_0915",
            "option_closing_price_1515",
            "option_pnl_per_lot",
            "option_return_pct",
            "option_result",
            "option_backtest_status",
        ]].tail()
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest option trades for NIFTY/BANKNIFTY predictions.")
    parser.add_argument(
        "-u", "--underlying",
        default="NIFTY",
        choices=["NIFTY", "BANKNIFTY"],
        help="Underlying index"
    )
    parser.add_argument(
        "--options-view",
        default=None,
        help="Override options snapshot view name (defaults depend on underlying)"
    )
    args = parser.parse_args()
    main(underlying=args.underlying, options_view=args.options_view)
