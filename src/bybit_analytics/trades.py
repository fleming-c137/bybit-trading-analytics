"""Reconstruct round-trip trades (open -> flat) from the transaction log.

The transaction log is fill-level: one row per execution, plus funding
settlements. Performance questions ("what is my win rate?", "do I hold losers
too long?") need *positions*: the span from leaving flat to returning to flat.

We walk each symbol's fills in time order and use the post-trade position size
(``size``, signed: short < 0) to detect when a position opens, closes or flips.
Funding settlements are attributed to whichever round was open at that time.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .transform import FUNDING_TYPES, TRADE_TYPES

ROUND_COLUMNS = [
    "round_id", "symbol", "direction", "open_time", "close_time", "duration_min",
    "entry_qty", "entry_notional", "avg_entry", "avg_exit", "max_size", "gross_pnl",
    "fees", "funding", "net_pnl", "return_pct", "liquidated", "n_fills", "partial", "is_open",
]


@dataclass
class _Round:
    symbol: str
    direction: int
    open_time: pd.Timestamp
    partial: bool = False
    entry_qty: float = 0.0
    entry_notional: float = 0.0
    exit_qty: float = 0.0
    exit_notional: float = 0.0
    max_size: float = 0.0
    gross_pnl: float = 0.0
    fees: float = 0.0
    liquidated: bool = False
    n_fills: int = 0
    close_time: pd.Timestamp | None = None
    extra: dict = field(default_factory=dict)

    def add(self, qty, notional, opening, cash_flow, fee, n_fills, liquidated, size):
        if opening:
            self.entry_qty += qty
            self.entry_notional += notional
        else:
            self.exit_qty += qty
            self.exit_notional += notional
        self.gross_pnl += cash_flow
        self.fees += fee
        self.n_fills += n_fills
        self.liquidated |= bool(liquidated)
        self.max_size = max(self.max_size, abs(size))


def _fill_events(tx: pd.DataFrame) -> pd.DataFrame:
    """Collapse fills sharing (symbol, time, side) -- i.e. one order's fills -- into events."""
    trades = tx[tx["type"].isin(TRADE_TYPES) & (tx["symbol"] != "") & (tx["side"] != "")].copy()
    if trades.empty:
        return trades
    trades["notional"] = trades["qty"] * trades["price"]
    trades["is_liq"] = trades["type"].eq("LIQUIDATION")
    signed_sizes = (tx["size"] < 0).any()
    trades["_order"] = np.arange(len(trades))

    ev = trades.groupby(["symbol", "time", "side"], sort=False).agg(
        qty=("qty", "sum"), notional=("notional", "sum"), cash_flow=("cash_flow", "sum"),
        fee=("fee", "sum"), size_max=("size", "max"), size_min=("size", "min"),
        size_last=("size", "last"), liquidated=("is_liq", "any"), n_fills=("qty", "size"),
        _order=("_order", "min"),
    ).reset_index()
    if signed_sizes:
        # Within one order the position moves monotonically, so the final size
        # is the extreme in the order's direction (row order within a second is unreliable).
        ev["size"] = np.where(ev["side"].eq("Buy"), ev["size_max"], ev["size_min"])
    else:
        ev["size"] = ev["size_last"]
    ev["price"] = np.where(ev["qty"] > 0, ev["notional"] / ev["qty"].replace(0, np.nan), np.nan)
    return ev.sort_values(["symbol", "time", "_order"]).reset_index(drop=True)


def _signed_from_unsigned(ev: pd.DataFrame) -> pd.Series:
    """Infer position sign when the source reports unsigned sizes."""
    out = np.zeros(len(ev))
    direction = 0
    prev_symbol = None
    prev_abs = 0.0
    for i, row in enumerate(ev.itertuples(index=False)):
        if row.symbol != prev_symbol:
            direction, prev_abs, prev_symbol = 0, 0.0, row.symbol
        side = 1 if row.side == "Buy" else -1
        size = abs(row.size)
        if direction == 0 or prev_abs == 0:
            direction = side
        elif side != direction and row.qty > prev_abs + 1e-12:
            direction = side  # flipped through zero
        out[i] = direction * size
        prev_abs = size
        if size == 0:
            direction = 0
    return pd.Series(out, index=ev.index)


def build_round_trips(tx: pd.DataFrame) -> pd.DataFrame:
    ev = _fill_events(tx)
    if ev.empty:
        return pd.DataFrame(columns=ROUND_COLUMNS)
    if not (tx["size"] < 0).any():
        ev["size"] = _signed_from_unsigned(ev)

    data_start = tx["time"].min()
    rounds: list[_Round] = []
    for symbol, grp in ev.groupby("symbol", sort=False):
        cur: _Round | None = None
        for row in grp.itertuples(index=False):
            side = 1 if row.side == "Buy" else -1
            size = float(row.size)
            tol = 1e-9 * max(1.0, row.qty)
            new_dir = int(np.sign(size)) if abs(size) > tol else 0

            if cur is None:
                prev = size - side * row.qty
                if abs(prev) > tol:  # position already open before our data starts
                    cur = _Round(symbol, int(np.sign(prev)), data_start, partial=True)
                    cur.max_size = abs(prev)
                elif new_dir != 0:
                    cur = _Round(symbol, new_dir, row.time)
                else:
                    continue

            opening = side == cur.direction
            flipped = new_dir != 0 and new_dir != cur.direction
            if flipped:
                close_qty = max(row.qty - abs(size), 0.0)
                frac = close_qty / row.qty if row.qty else 1.0
                cur.add(close_qty, row.notional * frac, False, row.cash_flow, row.fee * frac,
                        row.n_fills, row.liquidated, 0.0)
                cur.close_time = row.time
                rounds.append(cur)
                cur = _Round(symbol, new_dir, row.time)
                cur.add(abs(size), row.notional * (1 - frac), True, 0.0, row.fee * (1 - frac), 0, False, size)
                continue

            cur.add(row.qty, row.notional, opening, row.cash_flow, row.fee, row.n_fills, row.liquidated, size)
            if new_dir == 0:
                cur.close_time = row.time
                rounds.append(cur)
                cur = None
        if cur is not None:
            rounds.append(cur)  # still open at end of data

    df = pd.DataFrame([{
        "symbol": r.symbol,
        "direction": "Long" if r.direction > 0 else "Short",
        "open_time": r.open_time,
        "close_time": r.close_time,
        "entry_qty": r.entry_qty,
        "entry_notional": r.entry_notional,
        "avg_entry": r.entry_notional / r.entry_qty if r.entry_qty else np.nan,
        "avg_exit": r.exit_notional / r.exit_qty if r.exit_qty else np.nan,
        "max_size": r.max_size,
        "gross_pnl": r.gross_pnl,
        "fees": r.fees,
        "liquidated": r.liquidated,
        "n_fills": r.n_fills,
        "partial": r.partial,
        "is_open": r.close_time is None,
    } for r in rounds])

    df["funding"] = _attribute_funding(df, tx)
    df["net_pnl"] = df["gross_pnl"] + df["fees"] + df["funding"]
    df["duration_min"] = (df["close_time"] - df["open_time"]).dt.total_seconds() / 60
    df.loc[df["partial"], "duration_min"] = np.nan
    notional = df["entry_notional"].where(~df["partial"] & (df["entry_notional"] > 0))
    df["return_pct"] = df["net_pnl"] / notional * 100
    df = df.sort_values("open_time").reset_index(drop=True)
    df["round_id"] = np.arange(1, len(df) + 1)
    return df[ROUND_COLUMNS]


def _attribute_funding(rounds: pd.DataFrame, tx: pd.DataFrame) -> pd.Series:
    funding = tx[tx["type"].isin(FUNDING_TYPES)]
    out = pd.Series(0.0, index=rounds.index)
    if funding.empty or rounds.empty:
        return out
    naive = lambda s: s.dt.tz_convert(None).to_numpy()  # noqa: E731
    far_future = pd.Timestamp("2262-01-01", tz="UTC")
    for symbol, idx in rounds.groupby("symbol").groups.items():
        f = funding[funding["symbol"] == symbol]
        if f.empty:
            continue
        r = rounds.loc[idx]
        opens = naive(r["open_time"])
        closes = naive(r["close_time"].fillna(far_future))
        for t, amount in zip(naive(f["time"]), f["funding"].to_numpy()):
            hit = np.flatnonzero((opens <= t) & (t <= closes))
            if hit.size:
                out.loc[idx[hit[-1]]] += amount
    return out
