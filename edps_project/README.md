# Enterprise Derivatives Processing System (EDPS)

A simple base project showing the core of a derivatives back-office: trade capture,
validation, valuation, lifecycle workflow, settlement and reporting.

## Structure
- `edps/models.py` – Trade, enums, allowed status transitions
- `edps/pricing.py` – Forward, Black-Scholes option and simple swap valuation, settlement amounts
- `edps/validation.py` – Pre-confirmation business rules
- `edps/repository.py` – SQLite storage + audit trail
- `edps/processor.py` – Workflow: book -> validate -> confirm -> settle (or reject/cancel)
- `edps/reports.py` – Blotter, counterparty exposure, status summary
- `main.py` – Demo run
- `tests/test_edps.py` – Unit tests

## Run
```
python main.py
python -m unittest discover -s tests
```
Requires Python 3.8+ and no third-party packages.

## Ideas to extend
REST API (FastAPI), more products, real market data feeds, netting/collateral, FIX/SWIFT messaging.
