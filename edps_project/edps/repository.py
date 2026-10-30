"""SQLite persistence for trades and the audit trail."""
import sqlite3
from datetime import date, datetime
from typing import List, Optional

from .models import Direction, OptionType, Product, Status, Trade

SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
    counterparty TEXT NOT NULL,
    product TEXT NOT NULL,
    direction TEXT NOT NULL,
    underlying TEXT NOT NULL,
    notional REAL NOT NULL,
    trade_date TEXT NOT NULL,
    maturity_date TEXT NOT NULL,
    strike REAL NOT NULL,
    option_type TEXT,
    status TEXT NOT NULL,
    reject_reason TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER NOT NULL,
    ts TEXT NOT NULL,
    event TEXT NOT NULL,
    detail TEXT DEFAULT ''
);
"""


class TradeRepository:
    def __init__(self, path: str = ":memory:"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def add(self, t: Trade) -> Trade:
        cur = self.conn.execute(
            """INSERT INTO trades (counterparty, product, direction, underlying, notional,
               trade_date, maturity_date, strike, option_type, status, reject_reason)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (t.counterparty, t.product.value, t.direction.value, t.underlying, t.notional,
             t.trade_date.isoformat(), t.maturity_date.isoformat(), t.strike,
             t.option_type.value if t.option_type else None, t.status.value, t.reject_reason),
        )
        self.conn.commit()
        t.trade_id = cur.lastrowid
        return t

    def update_status(self, trade_id: int, status: Status, reason: str = "") -> None:
        self.conn.execute("UPDATE trades SET status=?, reject_reason=? WHERE trade_id=?",
                          (status.value, reason, trade_id))
        self.conn.commit()

    def get(self, trade_id: int) -> Optional[Trade]:
        row = self.conn.execute("SELECT * FROM trades WHERE trade_id=?", (trade_id,)).fetchone()
        return self._to_trade(row) if row else None

    def list(self, status: Optional[Status] = None) -> List[Trade]:
        if status:
            rows = self.conn.execute("SELECT * FROM trades WHERE status=? ORDER BY trade_id",
                                     (status.value,)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM trades ORDER BY trade_id").fetchall()
        return [self._to_trade(r) for r in rows]

    def log(self, trade_id: int, event: str, detail: str = "") -> None:
        self.conn.execute("INSERT INTO audit (trade_id, ts, event, detail) VALUES (?,?,?,?)",
                          (trade_id, datetime.now().isoformat(timespec="seconds"), event, detail))
        self.conn.commit()

    def audit_trail(self, trade_id: int) -> List[sqlite3.Row]:
        return self.conn.execute("SELECT ts, event, detail FROM audit WHERE trade_id=? ORDER BY id",
                                 (trade_id,)).fetchall()

    @staticmethod
    def _to_trade(r: sqlite3.Row) -> Trade:
        return Trade(
            trade_id=r["trade_id"], counterparty=r["counterparty"],
            product=Product(r["product"]), direction=Direction(r["direction"]),
            underlying=r["underlying"], notional=r["notional"],
            trade_date=date.fromisoformat(r["trade_date"]),
            maturity_date=date.fromisoformat(r["maturity_date"]),
            strike=r["strike"],
            option_type=OptionType(r["option_type"]) if r["option_type"] else None,
            status=Status(r["status"]), reject_reason=r["reject_reason"] or "",
        )
