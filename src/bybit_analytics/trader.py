"""Trader-facing views: sessions, weekdays, asset classes, recent results, highlights.

These sit on top of :mod:`analysis` and answer questions in a trader's words
("when do I trade best?", "what should I trade?") rather than a statistician's.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import analysis as A
from .assets import CLASS_ORDER, asset_class

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SESSIONS = [  # (name, start hour UTC, end hour UTC)
    ("Asia", 0, 8), ("London", 8, 13), ("New York", 13, 21), ("Late US", 21, 24),
]
HOLD_LABELS = {"<1m": "Under 1 min", "1-5m": "1-5 min", "5-15m": "5-15 min", "15-60m": "15-60 min",
               "1-4h": "1-4 hours", "4-24h": "4-24 hours", ">1d": "Over a day"}


def _opened(c: pd.DataFrame) -> pd.Series:
    return c["open_time"].dt.tz_convert("UTC")


def _usable(rounds: pd.DataFrame) -> pd.DataFrame:
    c = A.closed(rounds)
    return c[~c["partial"].astype(bool)]


def by_weekday(rounds: pd.DataFrame) -> pd.DataFrame:
    c = _usable(rounds).copy()
    c["weekday"] = pd.Categorical(_opened(c).dt.day_of_week.map(dict(enumerate(WEEKDAYS))), WEEKDAYS, ordered=True)
    return A._group_stats(c, "weekday")


def session_of(hours: pd.Series) -> pd.Series:
    out = pd.Series("", index=hours.index, dtype=object)
    for name, lo, hi in SESSIONS:
        out[(hours >= lo) & (hours < hi)] = name
    return out


def by_session(rounds: pd.DataFrame) -> pd.DataFrame:
    c = _usable(rounds).copy()
    c["session"] = pd.Categorical(session_of(_opened(c).dt.hour), [s[0] for s in SESSIONS], ordered=True)
    out = A._group_stats(c, "session")
    hours = {name: f"{lo:02d}:00-{hi:02d}:00" for name, lo, hi in SESSIONS}
    out["hours"] = out["session"].astype(str).map(hours)
    return out


def by_hour(rounds: pd.DataFrame) -> pd.DataFrame:
    out = A.by_hour(rounds)
    full = pd.DataFrame({"hour": range(24)})
    return full.merge(out, on="hour", how="left").fillna({"trades": 0, "net_pnl": 0.0})


def by_asset_class(rounds: pd.DataFrame) -> pd.DataFrame:
    c = A.closed(rounds).copy()
    if c.empty:
        return pd.DataFrame()
    c["asset_class"] = c["symbol"].map(asset_class)
    out = A._group_stats(c, "asset_class", {"symbols": ("symbol", "nunique")})
    out["share"] = out["trades"] / out["trades"].sum()
    sym = c.groupby(["asset_class", "symbol"])["net_pnl"].sum().reset_index()
    best = sym.loc[sym.groupby("asset_class")["net_pnl"].idxmax()].set_index("asset_class")
    worst = sym.loc[sym.groupby("asset_class")["net_pnl"].idxmin()].set_index("asset_class")
    out["best_symbol"] = out["asset_class"].map(best["symbol"])
    out["worst_symbol"] = out["asset_class"].map(worst["symbol"])
    order = {k: i for i, k in enumerate(CLASS_ORDER)}
    return out.sort_values("asset_class", key=lambda s: s.map(order)).reset_index(drop=True)


def by_holding_time(rounds: pd.DataFrame) -> pd.DataFrame:
    out = A.by_duration(rounds)
    out["hold"] = out["hold"].astype(str).map(HOLD_LABELS)
    return out


def market_weekdays(klines: pd.DataFrame, start=None, end=None, min_weeks: int = 4) -> dict:
    """How BTC behaves on each weekday: average daily return and share of green days."""
    if klines is None or klines.empty:
        return {"available": False}
    k = klines.sort_values("time").copy()
    k["ret"] = k["close"] / k["open"] - 1
    t = k["time"].dt.tz_convert("UTC")
    if start is not None:
        k, t = k[t >= start], t[t >= start]
    if end is not None:
        k, t = k[t < end], t[t < end]
    weeks = len(k) / 7
    if weeks < min_weeks:
        k = klines.sort_values("time").copy()
        k["ret"] = k["close"] / k["open"] - 1
        t = k["time"].dt.tz_convert("UTC")
        weeks = len(k) / 7
        widened = True
    else:
        widened = False
    if weeks < 2:
        return {"available": False}
    k = k.assign(weekday=pd.Categorical(t.dt.day_of_week.map(dict(enumerate(WEEKDAYS))), WEEKDAYS, ordered=True))
    g = k.groupby("weekday", observed=True)["ret"].agg(avg_return="mean", median_return="median",
                                                       up_share=lambda s: (s > 0).mean(), days="size").reset_index()
    pump = g.loc[g["avg_return"].idxmax()]
    dump = g.loc[g["avg_return"].idxmin()]
    return {
        "available": True, "weeks": int(round(weeks)), "widened": widened,
        "symbol": str(klines["symbol"].iloc[0]) if "symbol" in klines else "BTCUSDT",
        "rows": g, "pump": str(pump["weekday"]), "dump": str(dump["weekday"]),
        "pump_avg": float(pump["avg_return"]), "dump_avg": float(dump["avg_return"]),
        "pump_up": float(pump["up_share"]), "dump_up": float(dump["up_share"]),
    }


def recent(days: pd.DataFrame) -> dict:
    if days.empty:
        return {}
    d = days.set_index("date")["pnl"]
    end = d.index.max()
    return {
        "last_day": end, "today": float(d.iloc[-1]),
        "d7": float(d[d.index > end - pd.Timedelta(days=7)].sum()),
        "d30": float(d[d.index > end - pd.Timedelta(days=30)].sum()),
    }


def _pick(df: pd.DataFrame, label: str, best: bool, fmt=str, min_trades: int = 1) -> dict | None:
    if df is None or df.empty:
        return None
    d = df[df["trades"] >= min_trades]
    if d.empty:
        return None
    r = d.loc[d["net_pnl"].idxmax() if best else d["net_pnl"].idxmin()]
    return {"label": fmt(r[label]), "net_pnl": float(r["net_pnl"]), "trades": int(r["trades"]),
            "win_rate": float(r["win_rate"])}


def best_worst(tables: dict) -> list[dict]:
    """One row per dimension: the best and worst bucket by net PnL."""
    specs = [
        ("Hour of day (UTC)", "hour", tables["hour"], lambda h: f"{int(h):02d}:00", 3),
        ("Day of week", "weekday", tables["weekday"], str, 3),
        ("Session", "session", tables["session"], str, 3),
        ("Asset class", "asset_class", tables["asset_class"], str, 3),
        ("Coin", "symbol", tables["symbol"], str, 1),
        ("Direction", "direction", tables["direction"], str, 1),
        ("Holding time", "hold", tables["hold"], str, 3),
    ]
    rows = []
    for name, key, df, fmt, n in specs:
        b, w = _pick(df, key, True, fmt, n), _pick(df, key, False, fmt, n)
        if b and w and b["label"] != w["label"]:
            rows.append({"dimension": name, "best": b, "worst": w})
    return rows


def _money(v: float, ccy: str) -> str:
    s = f"{v:+,.0f}" if abs(v) >= 100 else f"{v:+,.2f}"
    return f"{s.replace('-', '−')} {ccy}"


def highlights(s: dict, tables: dict, tilt: pd.DataFrame, busy: pd.DataFrame, ccy: str) -> dict:
    """Short plain-English lines: what is working and what is costing money."""
    good, bad = [], []

    def best_of(df, key, fmt=str):
        if df is None or df.empty or "net_pnl" not in df:
            return None
        d = df[df["trades"] >= 3] if "trades" in df else df
        return d.loc[d["net_pnl"].idxmax()] if not d.empty else None

    hold = tables["hold"]
    if hold is not None and not hold.empty:
        winners = hold[hold["net_pnl"] > 0]
        if not winners.empty:
            good.append(f"Trades held {', '.join(winners['hold'].str.lower())} made {_money(winners['net_pnl'].sum(), ccy)}.")
        run = []  # shortest holding times, while they keep losing
        for _, r in hold.iterrows():
            if r["net_pnl"] < 0:
                run.append(r)
            elif run:
                break
        if run:
            loss = sum(r["net_pnl"] for r in run)
            n = sum(r["trades"] for r in run)
            wr = sum(r["win_rate"] * r["trades"] for r in run) / max(n, 1)
            span = (run[-1]["hold"].lower() if len(run) == 1 and run[0] is hold.iloc[0] else f"under {run[-1]['hold'].split('-')[-1].strip().lower()}" if "-" in run[-1]["hold"] else run[-1]["hold"].lower()).replace("under 60 min", "within an hour")
            bad.append(f"Trades closed {span} lost {abs(loss):,.0f} {ccy} ({wr:.0%} win rate).")
    for key, df, fmt, what in [("hour", tables["hour"], lambda h: f"{int(h):02d}:00 UTC", "Best hour"),
                               ("weekday", tables["weekday"], str, "Best day"),
                               ("asset_class", tables["asset_class"], str, "Best asset class")]:
        r = best_of(df, key)
        if r is not None and r["net_pnl"] > 0:
            good.append(f"{what}: {fmt(r[key])}, {_money(r['net_pnl'], ccy)} at a {r['win_rate']:.0%} win rate.")
    d = tables["direction"]
    if d is not None and len(d) == 2:
        top = d.loc[d["net_pnl"].idxmax()]
        if top["net_pnl"] > 0:
            good.append(f"{top['direction']}s are profitable: {_money(top['net_pnl'], ccy)}.")

    # Fees are a cost of trading, not a skill signal; mention them only when they change the outcome.
    gross, fees = s.get("gross_pnl") or 0.0, abs(s.get("fees") or 0.0)
    if gross > 0 and s["net_pnl"] < 0:
        bad.append(f"Your trades made {_money(gross, ccy)} before fees, but fees and funding turned it into "
                   f"{_money(s['net_pnl'], ccy)}. Fewer, larger trades would keep more of it.")
    elif gross > 0 and fees > gross / 3:
        bad.append(f"Fees took {fees / gross:.0%} of your profit before fees ({fees:,.0f} {ccy}).")
    if tilt is not None and not tilt.empty:
        t = tilt.set_index("context")
        after = [i for i in t.index if "after a loss" in i]
        calm = [i for i in t.index if i.startswith(">")]
        if after and calm and t.loc[after[0], "avg_pnl"] < t.loc[calm[0], "avg_pnl"]:
            bad.append(f"Right after a loss you trade worse: {t.loc[after[0], 'win_rate']:.0%} win rate vs "
                       f"{t.loc[calm[0], 'win_rate']:.0%} after a break.")
    if busy is not None and len(busy) >= 2:
        worst = busy.loc[busy["avg_pnl"].idxmin()]
        calmest = busy.iloc[0]
        if worst["avg_pnl"] < 0 and str(worst["trade_bucket"]) != str(calmest["trade_bucket"]):
            bad.append(f"Busy days hurt: days with {worst['trade_bucket']} trades averaged {_money(worst['avg_pnl'], ccy)} a day.")
    ac = tables["asset_class"]
    if ac is not None and not ac.empty:
        w = ac.loc[ac["net_pnl"].idxmin()]
        if w["net_pnl"] < 0:
            bad.append(f"Worst asset class: {w['asset_class']}, down {abs(w['net_pnl']):,.0f} {ccy} over {int(w['trades']):,} trades.")
    if s.get("liquidations"):
        bad.append(f"{s['liquidations']} liquidation{'s' if s['liquidations'] != 1 else ''} cost "
                   f"{abs(s['liquidation_pnl']):,.0f} {ccy}.")
    return {"working": good[:4], "costing": bad[:4]}


def plain_verdict(s: dict, ccy: str) -> dict:
    wr, payoff = s.get("win_rate"), s.get("payoff_ratio")
    if not s.get("trades") or wr is None or wr != wr:
        return {"tone": "neutral", "title": "Not enough closed trades", "text": "Widen the period to see results."}
    need = 1 / (1 + payoff) if payoff and payoff == payoff else None
    per100 = round(wr * 100)
    size = f"Your average win is {payoff:.1f}x your average loss" if payoff and payoff == payoff else ""
    if s["net_pnl"] > 0:
        text = (f"{per100} of every 100 trades win. {size}, so you only need {round(need * 100)} to break even."
                if need else f"{per100} of every 100 trades win.")
        return {"tone": "positive", "title": f"Profitable: {_money(s['net_pnl'], ccy)}", "text": text}
    text = (f"{per100} of every 100 trades win. {size}, so you need {round(need * 100)} to break even."
            if need else f"{per100} of every 100 trades win.")
    return {"tone": "negative", "title": f"Losing money: {_money(s['net_pnl'], ccy)}", "text": text}
