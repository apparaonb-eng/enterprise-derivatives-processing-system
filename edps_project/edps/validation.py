"""Pre-confirmation trade validation rules."""
from typing import List

from .models import OptionType, Product, Trade
from .pricing import MarketData

MAX_TRADE_NOTIONAL = 100_000_000


def validate_trade(trade: Trade, md: MarketData, approved_counterparties: set) -> List[str]:
    """Return a list of error messages; empty list means the trade is valid."""
    errors = []
    if trade.counterparty not in approved_counterparties:
        errors.append(f"Counterparty '{trade.counterparty}' is not approved")
    if trade.notional <= 0:
        errors.append("Notional must be positive")
    if trade.notional > MAX_TRADE_NOTIONAL:
        errors.append(f"Notional exceeds limit of {MAX_TRADE_NOTIONAL:,}")
    if trade.strike <= 0:
        errors.append("Strike / fixed rate must be positive")
    if trade.maturity_date <= trade.trade_date:
        errors.append("Maturity date must be after trade date")
    if trade.trade_date > md.valuation_date:
        errors.append("Trade date cannot be in the future")
    if trade.product == Product.OPTION and trade.option_type not in (OptionType.CALL, OptionType.PUT):
        errors.append("Option trades require option_type CALL or PUT")
    if not md.has(trade):
        errors.append(f"No market data for underlying '{trade.underlying}'")
    return errors
