"""Simple reporting: blotter, exposure by counterparty, status summary."""
from collections import Counter, defaultdict

from .models import Status
from .processor import DerivativesProcessor


def blotter(proc: DerivativesProcessor) -> str:
    lines = [f"{'ID':<4}{'Counterparty':<14}{'Product':<9}{'Dir':<5}{'Underlying':<11}"
             f"{'Notional':>14}{'Status':>11}{'MTM':>16}"]
    lines.append("-" * len(lines[0]))
    for t in proc.repo.list():
        live = t.status in (Status.VALIDATED, Status.CONFIRMED)
        mtm = f"{proc.value(t.trade_id):,.2f}" if live else "-"
        lines.append(f"{t.trade_id:<4}{t.counterparty:<14}{t.product.value:<9}{t.direction.value:<5}"
                     f"{t.underlying:<11}{t.notional:>14,.0f}{t.status.value:>11}{mtm:>16}")
    return "\n".join(lines)


def exposure_by_counterparty(proc: DerivativesProcessor) -> dict:
    exposure = defaultdict(float)
    for t in proc.repo.list():
        if t.status in (Status.VALIDATED, Status.CONFIRMED):
            exposure[t.counterparty] += proc.value(t.trade_id)
    return dict(exposure)


def status_summary(proc: DerivativesProcessor) -> dict:
    return dict(Counter(t.status.value for t in proc.repo.list()))
