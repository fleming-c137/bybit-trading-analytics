"""Synthetic but realistic account history, so the project runs without API keys
(and so screenshots in the public repo never expose real account data)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from .transform import TX_COLUMNS, CLOSED_PNL_COLUMNS

SYMBOLS = {  # symbol: (start price, daily vol, trading weight)
    "BTCUSDT": (95_000, 0.025, 6), "ETHUSDT": (3_400, 0.035, 5), "SOLUSDT": (190, 0.05, 5),
    "DOGEUSDT": (0.32, 0.06, 4), "XRPUSDT": (2.3, 0.05, 3), "PEPEUSDT": (0.000018, 0.08, 6),
    "WIFUSDT": (2.1, 0.09, 4), "SUIUSDT": (4.2, 0.07, 3), "ARBUSDT": (0.75, 0.06, 2),
    "LINKUSDT": (22, 0.045, 2), "AVAXUSDT": (38, 0.055, 2), "TIAUSDT": (6.5, 0.08, 2),
}
TAKER, MAKER = 0.00055, 0.0002


def generate(days: int = 75, seed: int = 7, end: datetime | None = None):
    """Return (transactions, closed_pnl, btc_klines) in canonical form."""
    rng = np.random.default_rng(seed)
    end = (end or datetime.now(timezone.utc)).replace(microsecond=0)
    start = end - timedelta(days=days)
    names = list(SYMBOLS)
    weights = np.array([SYMBOLS[s][2] for s in names], float)
    weights /= weights.sum()

    rows: list[dict] = []
    closed: list[dict] = []
    balance = 0.0
    seq = 0

    def emit(t, type_, symbol="", side="", qty=0.0, size=0.0, price=0.0, cash_flow=0.0, fee=0.0, funding=0.0):
        nonlocal balance, seq
        change = cash_flow + fee + funding if not type_.startswith("TRANSFER") else cash_flow
        balance += change
        seq += 1
        rows.append(dict(
            id=f"demo-{seq:07d}", time=t, category="linear" if symbol else "", symbol=symbol, currency="USDT",
            type=type_, side=side, qty=qty, size=size, price=price,
            cash_flow=0.0 if type_.startswith("TRANSFER") else cash_flow, fee=fee, funding=funding,
            change=change, cash_balance=balance, order_id="", trade_id="", source="demo",
        ))

    emit(start, "TRANSFER_IN", cash_flow=500.0)
    t = start + timedelta(minutes=30)
    last_loss_close = None
    while t < end - timedelta(hours=1):
        if balance < 40:
            emit(t, "TRANSFER_IN", cash_flow=float(rng.choice([100, 150, 200])))
        if rng.random() < 0.01 and balance > 600:
            emit(t, "TRANSFER_OUT", cash_flow=-100.0)

        sym = rng.choice(names, p=weights)
        p0, vol, _ = SYMBOLS[sym]
        drift_days = (t - start).total_seconds() / 86400
        price = p0 * np.exp(rng.normal(0, vol) * np.sqrt(max(drift_days, 1)) * 0.3)
        direction = 1 if rng.random() < 0.62 else -1
        leverage = float(rng.choice([5, 10, 10, 20, 25, 50], p=[.15, .3, .2, .2, .1, .05]))
        tilt = last_loss_close is not None and (t - last_loss_close) < timedelta(minutes=15)
        notional = min(balance * leverage * rng.uniform(0.15, 0.6) * (1.4 if tilt else 1.0), balance * leverage * 0.9)
        qty_total = max(round(notional / price, 6), 1e-6)

        hold_min = float(np.exp(rng.normal(2.3, 1.4)))
        # Edge model: slightly negative overall, worse when tilted, better on longer holds.
        edge = -0.0008 - (0.0015 if tilt else 0) + (0.002 if hold_min > 240 else 0)
        move = rng.normal(edge, vol * np.sqrt(hold_min / 1440) * 0.8)
        liq_move = -1 / leverage * 0.9
        liquidated = move * 1 < liq_move
        if liquidated:
            move = liq_move
        exit_price = price * (1 + direction * move)

        # Entry fills
        n_in = int(rng.integers(1, 4))
        parts = rng.dirichlet(np.ones(n_in)) * qty_total
        size = 0.0
        side_in = "Buy" if direction > 0 else "Sell"
        maker = rng.random() < 0.25
        for q in parts:
            size += direction * q
            emit(t, "TRADE", sym, side_in, q, size, price, 0.0, -q * price * (MAKER if maker else TAKER))
        open_fee = -sum(r["fee"] for r in rows[-n_in:])
        open_t = t

        # Funding every 8h while open
        close_t = t + timedelta(minutes=hold_min)
        f = (open_t.replace(minute=0, second=0) + timedelta(hours=1))
        while f < close_t:
            if f.hour % 8 == 0:
                rate = rng.normal(0.0001, 0.0001)
                emit(f, "SETTLEMENT", sym, side_in, 0.0, size, 0.0, 0.0, 0.0, -direction * abs(size) * price * rate)
            f += timedelta(hours=1)

        # Exit fills
        n_out = 1 if liquidated else int(rng.integers(1, 3))
        parts = rng.dirichlet(np.ones(n_out)) * qty_total
        side_out = "Sell" if direction > 0 else "Buy"
        realised = 0.0
        close_fee = 0.0
        for i, q in enumerate(parts):
            size -= direction * q
            if i == n_out - 1:
                size = 0.0
            cf = direction * q * (exit_price - price)
            fee = -q * exit_price * (TAKER if not liquidated else TAKER * 1.5)
            realised += cf
            close_fee -= fee
            emit(close_t, "LIQUIDATION" if liquidated else "TRADE", sym, side_out, q, size, exit_price, cf, fee)
        closed.append(dict(
            order_id=f"demo-ord-{len(closed):06d}", symbol=sym, position_side="Long" if direction > 0 else "Short",
            qty=qty_total, avg_entry_price=price, avg_exit_price=exit_price, entry_value=qty_total * price,
            exit_value=qty_total * exit_price, closed_pnl=realised - open_fee - close_fee, open_fee=open_fee,
            close_fee=close_fee, leverage=leverage, fill_count=n_in + n_out,
            exec_type="BustTrade" if liquidated else "Trade", time=close_t,
        ))
        last_loss_close = close_t if realised - open_fee - close_fee < 0 else None

        # Gap to next trade: bursts on some days, quiet on others.
        busy = rng.random() < 0.35
        gap = rng.exponential(25 if busy else 300)
        if rng.random() < 0.08:
            gap += rng.uniform(12, 48) * 60  # days off
        t = close_t + timedelta(minutes=gap)

    tx = pd.DataFrame(rows, columns=TX_COLUMNS)
    tx["time"] = pd.to_datetime(tx["time"], utc=True)
    tx = tx.sort_values(["time", "id"]).reset_index(drop=True)
    # Recompute running balance in time order (funding rows were emitted out of order).
    tx["cash_balance"] = tx["change"].cumsum()

    cp = pd.DataFrame(closed, columns=CLOSED_PNL_COLUMNS)
    cp["time"] = pd.to_datetime(cp["time"], utc=True)

    dates = pd.date_range(start.date() - timedelta(days=30), end.date(), freq="D", tz="UTC")
    btc = 95_000 * np.exp(np.cumsum(rng.normal(0.0005, 0.025, len(dates))))
    opens = np.r_[btc[0], btc[:-1]]
    kl = pd.DataFrame({
        "symbol": "BTCUSDT", "time": dates, "open": opens, "close": btc,
        "high": np.maximum(opens, btc) * (1 + rng.uniform(0, 0.02, len(dates))),
        "low": np.minimum(opens, btc) * (1 - rng.uniform(0, 0.02, len(dates))),
        "volume": rng.uniform(5e4, 2e5, len(dates)),
    })
    return tx, cp, kl
