"""Simple valuation models for forwards, European options and swaps."""
import math
from dataclasses import dataclass, field
from datetime import date

from .models import OptionType, Product, Trade


@dataclass
class MarketData:
    valuation_date: date
    risk_free_rate: float = 0.05
    spots: dict = field(default_factory=dict)        # underlying -> spot
    vols: dict = field(default_factory=dict)         # underlying -> volatility
    float_rates: dict = field(default_factory=dict)  # index -> floating rate

    def has(self, trade: Trade) -> bool:
        if trade.product == Product.SWAP:
            return trade.underlying in self.float_rates
        if trade.product == Product.OPTION:
            return trade.underlying in self.spots and trade.underlying in self.vols
        return trade.underlying in self.spots


def year_fraction(start: date, end: date) -> float:
    return max((end - start).days, 0) / 365.0


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def black_scholes(spot, strike, t, r, vol, option_type: OptionType) -> float:
    if t <= 0 or vol <= 0:
        intrinsic = spot - strike if option_type == OptionType.CALL else strike - spot
        return max(intrinsic, 0.0)
    d1 = (math.log(spot / strike) + (r + 0.5 * vol**2) * t) / (vol * math.sqrt(t))
    d2 = d1 - vol * math.sqrt(t)
    df = math.exp(-r * t)
    if option_type == OptionType.CALL:
        return spot * _norm_cdf(d1) - strike * df * _norm_cdf(d2)
    return strike * df * _norm_cdf(-d2) - spot * _norm_cdf(-d1)


def present_value(trade: Trade, md: MarketData) -> float:
    """Mark-to-market value of the trade from our point of view."""
    t = year_fraction(md.valuation_date, trade.maturity_date)
    r = md.risk_free_rate

    if trade.product == Product.FORWARD:
        spot = md.spots[trade.underlying]
        return trade.sign * trade.notional * (spot - trade.strike * math.exp(-r * t))

    if trade.product == Product.OPTION:
        price = black_scholes(md.spots[trade.underlying], trade.strike, t, r,
                              md.vols[trade.underlying], trade.option_type)
        return trade.sign * trade.notional * price

    if trade.product == Product.SWAP:
        float_rate = md.float_rates[trade.underlying]
        annuity = t if r == 0 else (1 - math.exp(-r * t)) / r
        # BUY = pay fixed: gains when the floating rate is above the fixed rate
        return trade.sign * trade.notional * (float_rate - trade.strike) * annuity

    raise ValueError(f"Unsupported product {trade.product}")


def settlement_amount(trade: Trade, md: MarketData) -> float:
    """Cash amount exchanged at maturity (cash settled, our point of view)."""
    if trade.product == Product.FORWARD:
        return trade.sign * trade.notional * (md.spots[trade.underlying] - trade.strike)
    if trade.product == Product.OPTION:
        spot = md.spots[trade.underlying]
        intrinsic = spot - trade.strike if trade.option_type == OptionType.CALL else trade.strike - spot
        return trade.sign * trade.notional * max(intrinsic, 0.0)
    if trade.product == Product.SWAP:
        # final semi-annual period net payment
        return trade.sign * trade.notional * (md.float_rates[trade.underlying] - trade.strike) * 0.5
    raise ValueError(f"Unsupported product {trade.product}")
