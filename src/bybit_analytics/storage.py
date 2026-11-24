"""SQLite persistence. Upserts make repeated syncs idempotent."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pandas as pd

from .transform import CLOSED_PNL_COLUMNS, TX_COLUMNS

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY, time INTEGER NOT NULL, category TEXT, symbol TEXT, currency TEXT,
    type TEXT, side TEXT, qty REAL, size REAL, price REAL, cash_flow REAL, fee REAL,
    funding REAL, change REAL, cash_balance REAL, order_id TEXT, trade_id TEXT, source TEXT
);
CREATE INDEX IF NOT EXISTS ix_tx_time ON transactions(time);
CREATE TABLE IF NOT EXISTS closed_pnl (
    order_id TEXT PRIMARY KEY, symbol TEXT, position_side TEXT, qty REAL, avg_entry_price REAL,
    avg_exit_price REAL, entry_value REAL, exit_value REAL, closed_pnl REAL, open_fee REAL,
    close_fee REAL, leverage REAL, fill_count REAL, exec_type TEXT, time INTEGER
);
CREATE TABLE IF NOT EXISTS klines (
    symbol TEXT, time INTEGER, open REAL, high REAL, low REAL, close REAL, volume REAL,
    PRIMARY KEY (symbol, time)
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""


class Store:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.path)
        try:
            yield con
            con.commit()
        finally:
            con.close()

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _to_db(df: pd.DataFrame, time_cols=("time",)) -> pd.DataFrame:
        out = df.copy()
        for c in time_cols:
            out[c] = pd.to_datetime(out[c], utc=True).dt.as_unit("ms").astype("int64")
        return out

    @staticmethod
    def _from_db(df: pd.DataFrame, time_cols=("time",)) -> pd.DataFrame:
        for c in time_cols:
            df[c] = pd.to_datetime(df[c], unit="ms", utc=True)
        return df

    def _upsert(self, table: str, df: pd.DataFrame, columns: list[str]) -> int:
        if df.empty:
            return 0
        rows = self._to_db(df[columns]).astype(object).where(df[columns].notna(), None)
        placeholders = ",".join("?" * len(columns))
        with self.connect() as con:
            con.executemany(
                f"INSERT OR REPLACE INTO {table} ({','.join(columns)}) VALUES ({placeholders})",
                rows.itertuples(index=False, name=None),
            )
        return len(df)

    def _load(self, query: str, columns: list[str]) -> pd.DataFrame:
        with self.connect() as con:
            df = pd.read_sql_query(query, con)
        if df.empty:
            return pd.DataFrame(columns=columns)
        return self._from_db(df)

    # ------------------------------------------------------------ public API
    def upsert_transactions(self, df: pd.DataFrame) -> int:
        return self._upsert("transactions", df, TX_COLUMNS)

    def load_transactions(self) -> pd.DataFrame:
        df = self._load("SELECT * FROM transactions ORDER BY time, id", TX_COLUMNS)
        for c in ["category", "symbol", "currency", "side", "order_id", "trade_id"]:
            df[c] = df[c].fillna("")
        return df

    def upsert_closed_pnl(self, df: pd.DataFrame) -> int:
        return self._upsert("closed_pnl", df, CLOSED_PNL_COLUMNS)

    def load_closed_pnl(self) -> pd.DataFrame:
        return self._load("SELECT * FROM closed_pnl ORDER BY time", CLOSED_PNL_COLUMNS)

    def upsert_klines(self, df: pd.DataFrame) -> int:
        return self._upsert("klines", df, ["symbol", "time", "open", "high", "low", "close", "volume"])

    def load_klines(self, symbol: str = "BTCUSDT") -> pd.DataFrame:
        with self.connect() as con:
            df = pd.read_sql_query("SELECT * FROM klines WHERE symbol = ? ORDER BY time", con, params=(symbol,))
        return self._from_db(df) if not df.empty else df

    def latest_time(self, table: str, source: str | None = None) -> pd.Timestamp | None:
        sql = f"SELECT MAX(time) FROM {table}" + (" WHERE source = ?" if source else "")
        with self.connect() as con:
            (value,) = con.execute(sql, (source,) if source else ()).fetchone()
        return pd.to_datetime(value, unit="ms", utc=True) if value else None

    def set_meta(self, key: str, value) -> None:
        with self.connect() as con:
            con.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (key, json.dumps(value)))

    def get_meta(self, key: str, default=None):
        with self.connect() as con:
            row = con.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def clear(self) -> None:
        with self.connect() as con:
            for table in ["transactions", "closed_pnl", "klines", "meta"]:
                con.execute(f"DELETE FROM {table}")
