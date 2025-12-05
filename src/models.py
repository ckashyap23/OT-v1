from dataclasses import dataclass
from datetime import date, datetime

@dataclass
class StockInstrument:
    exchange: str
    tradingsymbol: str
    name: str | None
    instrument_token: int
    segment: str | None
    tick_size: float | None
    lot_size: int | None

@dataclass
class OptionInstrument:
    fetch_date: date
    underlying: str
    exchange: str
    tradingsymbol: str
    instrument_token: int
    name: str | None
    strike: float
    expiry: date
    instrument_type: str
    lot_size: int
    tick_size: float | None
    segment: str | None

@dataclass
class OptionData:
    option_instrument_id: int
    snapshot_time: datetime
    underlying_price: float | None
    last_price: float | None
    bid_price: float | None
    bid_qty: int | None
    ask_price: float | None
    ask_qty: int | None
    volume: int | None
    open_interest: int | None
    implied_volatility: float | None
    delta: float | None
    gamma: float | None
    theta: float | None
    vega: float | None  