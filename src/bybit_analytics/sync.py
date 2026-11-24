"""Pull data from Bybit into the local SQLite store (incremental)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pandas as pd

from .client import MAX_HISTORY_DAYS, BybitClient
from .config import Settings
from .storage import Store
from .transform import normalize_api_transactions, normalize_closed_pnl, normalize_csv, normalize_klines

log = logging.getLogger(__name__)

# Re-fetch a little overlap on incremental syncs; upserts make it harmless.
OVERLAP = timedelta(days=1)
CONTEXT_SYMBOLS = ["BTCUSDT"]


def _start_for(store: Store, table: str, days: int | None, source: str | None = None) -> datetime:
    now = datetime.now(timezone.utc)
    if days is not None:
        return now - timedelta(days=days)
    last = store.latest_time(table, source)
    if last is not None:
        return last.to_pydatetime() - OVERLAP
    return now - timedelta(days=MAX_HISTORY_DAYS - 1)


def sync_all(settings: Settings, days: int | None = None, progress=print) -> dict[str, int]:
    """Fetch transaction log, closed PnL, wallet snapshot and BTC candles.

    ``days`` forces a look-back window; otherwise sync resumes from the last
    stored record (or the full 2-year history on first run).
    """
    client = BybitClient(settings.api_key, settings.api_secret, settings.base_url)
    store = Store(settings.db_path)
    end = datetime.now(timezone.utc)
    counts: dict[str, int] = {}

    start = _start_for(store, "transactions", days, source="api")
    progress(f"Transaction log: {start:%Y-%m-%d} -> {end:%Y-%m-%d} (7-day windows)")
    rows = list(client.transaction_log(start, end))
    counts["transactions"] = store.upsert_transactions(normalize_api_transactions(rows))

    start = _start_for(store, "closed_pnl", days)
    progress(f"Closed PnL: {start:%Y-%m-%d} -> {end:%Y-%m-%d}")
    counts["closed_pnl"] = store.upsert_closed_pnl(normalize_closed_pnl(list(client.closed_pnl(start, end))))

    try:
        wallet = client.wallet_balance()
        store.set_meta("wallet", {
            "totalEquity": wallet.get("totalEquity"),
            "totalWalletBalance": wallet.get("totalWalletBalance"),
            "totalAvailableBalance": wallet.get("totalAvailableBalance"),
            "fetched_at": end.isoformat(),
        })
    except Exception as exc:  # wallet snapshot is nice-to-have
        log.warning("Could not fetch wallet balance: %s", exc)

    counts["klines"] = sync_market_context(store, client)
    store.set_meta("last_sync", end.isoformat())
    progress(f"Done: {counts}")
    return counts


def sync_market_context(store: Store, client: BybitClient | None = None, symbols=CONTEXT_SYMBOLS) -> int:
    """Daily candles for market context. Public endpoint -- no API key needed."""
    client = client or BybitClient()
    tx = store.load_transactions()
    if tx.empty:
        return 0
    start = tx["time"].min().to_pydatetime() - timedelta(days=30)
    end = datetime.now(timezone.utc)
    total = 0
    for symbol in symbols:
        total += store.upsert_klines(normalize_klines(client.klines(symbol, start, end), symbol))
    return total


def import_csv(path, store: Store) -> int:
    """Load a Bybit 'Asset Change Details' CSV export into the store."""
    return store.upsert_transactions(normalize_csv(pd.read_csv(path)))
