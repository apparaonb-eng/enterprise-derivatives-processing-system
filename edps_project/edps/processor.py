"""Trade lifecycle workflow: book -> validate -> confirm -> settle."""
from .models import Status, Trade
from .pricing import MarketData, present_value, settlement_amount
from .repository import TradeRepository
from .validation import validate_trade


class ProcessingError(Exception):
    pass


class DerivativesProcessor:
    def __init__(self, repo: TradeRepository, market_data: MarketData, approved_counterparties):
        self.repo = repo
        self.md = market_data
        self.approved = set(approved_counterparties)

    # ---- lifecycle steps -------------------------------------------------
    def book(self, trade: Trade) -> Trade:
        trade.status = Status.NEW
        self.repo.add(trade)
        self.repo.log(trade.trade_id, "BOOKED", f"{trade.product.value} {trade.direction.value}")
        return trade

    def validate(self, trade_id: int) -> Trade:
        trade = self._get(trade_id)
        errors = validate_trade(trade, self.md, self.approved)
        if errors:
            reason = "; ".join(errors)
            self._move(trade, Status.REJECTED, reason)
            self.repo.log(trade_id, "REJECTED", reason)
        else:
            self._move(trade, Status.VALIDATED)
            self.repo.log(trade_id, "VALIDATED")
        return trade

    def confirm(self, trade_id: int) -> Trade:
        trade = self._get(trade_id)
        self._move(trade, Status.CONFIRMED)
        self.repo.log(trade_id, "CONFIRMED", "Confirmation matched with counterparty")
        return trade

    def settle(self, trade_id: int) -> float:
        trade = self._get(trade_id)
        if trade.maturity_date > self.md.valuation_date:
            raise ProcessingError(f"Trade {trade_id} has not matured yet ({trade.maturity_date})")
        amount = settlement_amount(trade, self.md)
        self._move(trade, Status.SETTLED)
        self.repo.log(trade_id, "SETTLED", f"cash amount {amount:,.2f}")
        return amount

    def cancel(self, trade_id: int) -> Trade:
        trade = self._get(trade_id)
        self._move(trade, Status.CANCELLED)
        self.repo.log(trade_id, "CANCELLED")
        return trade

    # ---- convenience -----------------------------------------------------
    def process(self, trade: Trade) -> Trade:
        """Straight-through processing: book, validate and confirm."""
        self.book(trade)
        trade = self.validate(trade.trade_id)
        if trade.status == Status.VALIDATED:
            trade = self.confirm(trade.trade_id)
        return trade

    def value(self, trade_id: int) -> float:
        return present_value(self._get(trade_id), self.md)

    def settle_matured(self) -> dict:
        """End-of-day batch: settle every confirmed trade that has matured."""
        results = {}
        for t in self.repo.list(Status.CONFIRMED):
            if t.maturity_date <= self.md.valuation_date:
                results[t.trade_id] = self.settle(t.trade_id)
        return results

    # ---- internals -------------------------------------------------------
    def _get(self, trade_id: int) -> Trade:
        trade = self.repo.get(trade_id)
        if not trade:
            raise ProcessingError(f"Trade {trade_id} not found")
        return trade

    def _move(self, trade: Trade, new_status: Status, reason: str = "") -> None:
        if not trade.can_move_to(new_status):
            raise ProcessingError(
                f"Trade {trade.trade_id}: illegal transition {trade.status.value} -> {new_status.value}")
        self.repo.update_status(trade.trade_id, new_status, reason)
        trade.status, trade.reject_reason = new_status, reason
