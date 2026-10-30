import unittest
from datetime import date

from edps.models import Direction, OptionType, Product, Status, Trade
from edps.pricing import MarketData, black_scholes, present_value
from edps.processor import DerivativesProcessor, ProcessingError
from edps.repository import TradeRepository


def make_proc():
    md = MarketData(date(2026, 10, 30), 0.05, {"EURUSD": 1.09}, {"EURUSD": 0.08}, {"SOFR": 0.043})
    return DerivativesProcessor(TradeRepository(), md, {"ALPHA"})


def forward(**kw):
    base = dict(counterparty="ALPHA", product=Product.FORWARD, direction=Direction.BUY,
                underlying="EURUSD", notional=1_000_000, trade_date=date(2026, 9, 1),
                maturity_date=date(2027, 3, 1), strike=1.07)
    base.update(kw)
    return Trade(**base)


class EdpsTests(unittest.TestCase):
    def test_straight_through_confirms_valid_trade(self):
        proc = make_proc()
        t = proc.process(forward())
        self.assertEqual(t.status, Status.CONFIRMED)

    def test_unapproved_counterparty_rejected(self):
        proc = make_proc()
        t = proc.process(forward(counterparty="NOBODY"))
        self.assertEqual(t.status, Status.REJECTED)
        self.assertIn("not approved", t.reject_reason)

    def test_illegal_transition_blocked(self):
        proc = make_proc()
        t = proc.book(forward())
        with self.assertRaises(ProcessingError):
            proc.confirm(t.trade_id)  # NEW -> CONFIRMED not allowed

    def test_cannot_settle_before_maturity(self):
        proc = make_proc()
        t = proc.process(forward())
        with self.assertRaises(ProcessingError):
            proc.settle(t.trade_id)

    def test_put_call_parity(self):
        s, k, t, r, v = 100, 100, 1.0, 0.05, 0.2
        c = black_scholes(s, k, t, r, v, OptionType.CALL)
        p = black_scholes(s, k, t, r, v, OptionType.PUT)
        self.assertAlmostEqual(c - p, s - k * 2.718281828459045 ** (-r * t), places=6)

    def test_buy_and_sell_values_offset(self):
        md = make_proc().md
        buy, sell = forward(), forward(direction=Direction.SELL)
        self.assertAlmostEqual(present_value(buy, md), -present_value(sell, md))


if __name__ == "__main__":
    unittest.main()
