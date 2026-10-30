"""Demo run of the Enterprise Derivatives Processing System."""
from datetime import date

from edps.models import Direction, OptionType, Product, Trade
from edps.pricing import MarketData
from edps.processor import DerivativesProcessor
from edps.repository import TradeRepository
from edps.reports import blotter, exposure_by_counterparty, status_summary


def main():
    md = MarketData(
        valuation_date=date(2026, 10, 30),
        risk_free_rate=0.05,
        spots={"EURUSD": 1.09, "GOLD": 2650.0},
        vols={"EURUSD": 0.08, "GOLD": 0.18},
        float_rates={"SOFR": 0.043},
    )
    proc = DerivativesProcessor(TradeRepository(), md, {"ALPHA BANK", "BETA FUND", "GAMMA CORP"})

    trades = [
        Trade("ALPHA BANK", Product.FORWARD, Direction.BUY, "EURUSD", 5_000_000,
              date(2026, 9, 1), date(2027, 3, 1), 1.07),
        Trade("BETA FUND", Product.OPTION, Direction.BUY, "GOLD", 1_000,
              date(2026, 10, 1), date(2027, 1, 29), 2700.0, OptionType.CALL),
        Trade("GAMMA CORP", Product.SWAP, Direction.SELL, "SOFR", 20_000_000,
              date(2026, 6, 1), date(2029, 6, 1), 0.04),
        Trade("ALPHA BANK", Product.FORWARD, Direction.SELL, "GOLD", 500,
              date(2026, 4, 30), date(2026, 10, 30), 2600.0),   # matures today
        Trade("SHADY LTD", Product.FORWARD, Direction.BUY, "EURUSD", 1_000_000,
              date(2026, 10, 1), date(2027, 1, 1), 1.08),       # unapproved -> rejected
    ]
    for t in trades:
        proc.process(t)

    print("=== Blotter (after booking) ===")
    print(blotter(proc))

    print("\n=== End-of-day settlement ===")
    for trade_id, amount in proc.settle_matured().items():
        print(f"Trade {trade_id} settled, cash amount {amount:,.2f}")

    print("\n=== Exposure by counterparty (MTM) ===")
    for cp, mtm in exposure_by_counterparty(proc).items():
        print(f"{cp:<12}{mtm:>16,.2f}")

    print("\n=== Status summary ===", status_summary(proc))

    print("\n=== Audit trail for trade 5 ===")
    for row in proc.repo.audit_trail(5):
        print(row["ts"], row["event"], row["detail"])


if __name__ == "__main__":
    main()
