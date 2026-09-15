"""Histórico de mercado en SQLite (sin dependencias externas).

Cada rueda se guarda como un snapshot de cotizaciones. Con eso el motor de IA
deja de analizar "una foto del día" y puede calcular tendencia, volatilidad y
momentum por instrumento, además de permitir backtesting del scoring.

Tablas:
    snapshot_runs(rueda PK, captured_at, instruments, total_cash)
    quote_snapshots(symbol, rueda, captured_at, price, var_pct, cash_amount)
        PRIMARY KEY (symbol, rueda)  -> reejecutar el mismo día actualiza, no duplica
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from statistics import pstdev
from typing import Any, Dict, List, Optional

try:
    from src.config import HISTORY_DB, HISTORY_WINDOW
except Exception:  # pragma: no cover - permite importar el módulo aislado
    HISTORY_DB, HISTORY_WINDOW = "market_history.db", 30

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshot_runs (
    rueda        TEXT PRIMARY KEY,
    captured_at  TEXT NOT NULL,
    instruments  INTEGER NOT NULL DEFAULT 0,
    total_cash   REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS quote_snapshots (
    symbol       TEXT NOT NULL,
    rueda        TEXT NOT NULL,
    captured_at  TEXT NOT NULL,
    price        REAL NOT NULL,
    var_pct      REAL NOT NULL DEFAULT 0,
    cash_amount  REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (symbol, rueda)
);
CREATE INDEX IF NOT EXISTS idx_quote_symbol ON quote_snapshots (symbol, rueda);
"""


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class MarketHistory:
    """Acceso al histórico de cotizaciones (SQLite)."""

    def __init__(self, db_path=None, window: Optional[int] = None):
        self.db_path = str(db_path or HISTORY_DB)
        self.window = int(window or HISTORY_WINDOW or 30)

    # ── infraestructura ─────────────────────────────────────────
    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def init_db(self) -> None:
        with self._connect() as connection:
            connection.executescript(SCHEMA)

    # ── escritura ───────────────────────────────────────────────
    def save_snapshot(self, quotes, when: Optional[datetime] = None) -> Dict[str, Any]:
        """Guarda (o actualiza) el snapshot de la rueda. Devuelve un resumen."""
        when = when or datetime.now()
        rueda = when.strftime("%Y-%m-%d")
        captured_at = when.isoformat(timespec="seconds")

        rows, total_cash = [], 0.0
        for quote in quotes or []:
            if not isinstance(quote, dict):
                continue
            symbol = str(quote.get("symbol") or quote.get("simbolo") or "").strip().upper()
            price = _to_float(quote.get("last_price", quote.get("precio_ultimo")), 0.0)
            if not symbol or price <= 0:
                continue
            var_pct = _to_float(quote.get("var_pct", quote.get("relative_variation_pct")), 0.0)
            cash = _to_float(quote.get("cash_amount", quote.get("monto_efectivo")), 0.0)
            total_cash += cash
            rows.append((symbol, rueda, captured_at, price, var_pct, cash))

        self.init_db()
        with self._connect() as connection:
            connection.executemany(
                """INSERT INTO quote_snapshots
                       (symbol, rueda, captured_at, price, var_pct, cash_amount)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(symbol, rueda) DO UPDATE SET
                       captured_at = excluded.captured_at,
                       price = excluded.price,
                       var_pct = excluded.var_pct,
                       cash_amount = excluded.cash_amount""",
                rows,
            )
            connection.execute(
                """INSERT INTO snapshot_runs (rueda, captured_at, instruments, total_cash)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(rueda) DO UPDATE SET
                       captured_at = excluded.captured_at,
                       instruments = excluded.instruments,
                       total_cash = excluded.total_cash""",
                (rueda, captured_at, len(rows), round(total_cash, 2)),
            )

        return {
            "rueda": rueda,
            "captured_at": captured_at,
            "instruments": len(rows),
            "total_cash": round(total_cash, 2),
        }

    # ── lectura ─────────────────────────────────────────────────
    def available_ruedas(self) -> List[str]:
        self.init_db()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT rueda FROM snapshot_runs ORDER BY rueda ASC"
            ).fetchall()
        return [row["rueda"] for row in rows]

    def has_data(self) -> bool:
        return bool(self.available_ruedas())

    def get_price_history(self, symbol: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Serie histórica de un símbolo, de la rueda más antigua a la más reciente."""
        symbol = str(symbol or "").strip().upper()
        limit = int(limit or self.window)
        self.init_db()
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT rueda, price, var_pct, cash_amount
                   FROM quote_snapshots WHERE symbol = ?
                   ORDER BY rueda DESC LIMIT ?""",
                (symbol, limit),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def get_symbol_stats(self, symbol: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """Tendencia %, volatilidad, momentum y número de ruedas de un símbolo."""
        history = self.get_price_history(symbol, limit)
        stats = {
            "symbol": str(symbol or "").strip().upper(),
            "samples": len(history),
            "trend_pct": 0.0,
            "volatility": 0.0,
            "momentum_pct": 0.0,
            "first_price": 0.0,
            "last_price": 0.0,
            "lines": [],
        }
        if not history:
            return stats

        prices = [_to_float(row.get("price")) for row in history if _to_float(row.get("price")) > 0]
        changes = [_to_float(row.get("var_pct")) for row in history]
        if not prices:
            return stats

        stats["first_price"] = prices[0]
        stats["last_price"] = prices[-1]
        if prices[0] > 0:
            stats["trend_pct"] = round((prices[-1] / prices[0] - 1.0) * 100.0, 2)
        if len(changes) >= 2:
            stats["volatility"] = round(pstdev(changes), 2)
        recent = changes[-3:]
        if recent:
            stats["momentum_pct"] = round(sum(recent) / len(recent), 2)
        stats["lines"] = [
            {"rueda": row["rueda"], "price": _to_float(row["price"]), "var_pct": _to_float(row["var_pct"])}
            for row in history
        ]
        return stats

    def get_all_stats(self, limit: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
        """Estadísticas de todos los símbolos con histórico."""
        self.init_db()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT DISTINCT symbol FROM quote_snapshots ORDER BY symbol ASC"
            ).fetchall()
        return {row["symbol"]: self.get_symbol_stats(row["symbol"], limit) for row in rows}

    def market_snapshot(self, rueda: str) -> List[Dict[str, Any]]:
        """Todas las cotizaciones de una rueda concreta (para backtesting)."""
        self.init_db()
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT symbol, price, var_pct, cash_amount
                   FROM quote_snapshots WHERE rueda = ? ORDER BY symbol ASC""",
                (str(rueda),),
            ).fetchall()
        return [dict(row) for row in rows]

    def summary(self) -> Dict[str, Any]:
        """Resumen del histórico disponible (ruedas, símbolos y rango de fechas)."""
        ruedas = self.available_ruedas()
        if not ruedas:
            return {"ruedas": 0, "symbols": 0, "from": None, "to": None}
        self.init_db()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(DISTINCT symbol) AS symbols FROM quote_snapshots"
            ).fetchone()
        return {
            "ruedas": len(ruedas),
            "symbols": int(row["symbols"]) if row else 0,
            "from": ruedas[0],
            "to": ruedas[-1],
        }

