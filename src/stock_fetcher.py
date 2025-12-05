# src/stock_fetcher.py
from typing import Iterable, List

from .models import StockInstrument


def extract_stock_instruments(
    instruments_dump: Iterable[dict],
) -> List[StockInstrument]:
    """
    Take Kite's NSE instruments dump and keep only equity instruments (instrument_type == 'EQ'),
    mapping to our StockInstrument dataclass.
    """
    results: List[StockInstrument] = []

    for inst in instruments_dump:
        # Only equities
        if inst.get("instrument_type") != "EQ":
            continue

        stock = StockInstrument(
            exchange=inst.get("exchange", ""),
            tradingsymbol=inst.get("tradingsymbol", ""),
            name=inst.get("name"),
            instrument_token=int(inst.get("instrument_token", 0)),
            segment=inst.get("segment"),
            tick_size=float(inst.get("tick_size", 0.0))
            if inst.get("tick_size") is not None
            else None,
            lot_size=int(inst.get("lot_size", 0))
            if inst.get("lot_size") is not None
            else None,
        )
        results.append(stock)

    return results
