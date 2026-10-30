"""Domain models: trades, enums and the allowed status lifecycle."""
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional


class Product(str, Enum):
    FORWARD = "FORWARD"
    OPTION = "OPTION"
    SWAP = "SWAP"  # simplified: pay/receive fixed vs a floating index


class Direction(str, Enum):
    BUY = "BUY"    # long forward/option, pay-fixed swap
    SELL = "SELL"  # short forward/option, receive-fixed swap


class OptionType(str, Enum):
    CALL = "CALL"
    PUT = "PUT"


class Status(str, Enum):
    NEW = "NEW"
    VALIDATED = "VALIDATED"
    CONFIRMED = "CONFIRMED"
    SETTLED = "SETTLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


# status -> statuses it may move to
TRANSITIONS = {
    Status.NEW: {Status.VALIDATED, Status.REJECTED, Status.CANCELLED},
    Status.VALIDATED: {Status.CONFIRMED, Status.CANCELLED},
    Status.CONFIRMED: {Status.SETTLED, Status.CANCELLED},
    Status.SETTLED: set(),
    Status.REJECTED: set(),
    Status.CANCELLED: set(),
}


@dataclass
class Trade:
    counterparty: str
    product: Product
    direction: Direction
    underlying: str          # asset (e.g. "EURUSD") or floating index (e.g. "SOFR")
    notional: float          # units for forward/option, currency amount for swap
    trade_date: date
    maturity_date: date
    strike: float            # strike price, or fixed rate for a swap
    option_type: Optional[OptionType] = None
    trade_id: Optional[int] = None
    status: Status = Status.NEW
    reject_reason: str = ""

    @property
    def sign(self) -> int:
        return 1 if self.direction == Direction.BUY else -1

    def can_move_to(self, new_status: Status) -> bool:
        return new_status in TRANSITIONS[self.status]
