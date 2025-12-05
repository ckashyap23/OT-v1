# src/option_fetcher.py
from datetime import date, datetime
from typing import Iterable, List

from .models import OptionInstrument


def _to_date(value) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            pass
    return date.today()


def filter_options_for_underlyings(
    instruments_dump: Iterable[dict],
    underlyings: Iterable[str],
) -> List[OptionInstrument]:
    """
    From the full NFO instruments dump, keep only options (CE/PE)
    for specific underlyings, and map to OptionInstrument model.
    """
    underlying_set = {u.upper().strip() for u in underlyings}
    results: List[OptionInstrument] = []

    for inst in instruments_dump:
        if inst.get("exchange") != "NFO":
            continue

        instrument_type = inst.get("instrument_type")
        if instrument_type not in ("CE", "PE"):
            continue

        name = (inst.get("name") or "").strip().upper()
        if name not in underlying_set:
            continue

        expiry_date = _to_date(inst.get("expiry"))
        fetch_date = date.today()  # Date when this instrument data was fetched

        option = OptionInstrument(
            fetch_date=fetch_date,
            instrument_token=int(inst.get("instrument_token", 0)),
            underlying=name,
            exchange=inst.get("exchange", ""),
            tradingsymbol=inst.get("tradingsymbol", ""),
            name=inst.get("name"),
            strike=float(inst.get("strike", 0.0)),
            expiry=expiry_date,
            instrument_type=instrument_type,
            lot_size=int(inst.get("lot_size", 0)),
            tick_size=float(inst.get("tick_size", 0.0))
            if inst.get("tick_size") is not None
            else None,
            segment=inst.get("segment"),
        )
        results.append(option)

    return results
