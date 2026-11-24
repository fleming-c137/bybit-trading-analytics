"""Performance metrics and the analytical questions behind the dashboard.

Every function takes the canonical transaction frame (``tx``) and/or the
round-trip frame from :func:`bybit_analytics.trades.build_round_trips` and
returns a tidy DataFrame or dict, so the same logic feeds the dashboard,
the notebook and the tests.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .transform import FUNDING_TYPES, is_flow_type

DURATION_BINS = [0, 1, 5, 15, 60, 240, 1440, np.inf]
DURATION_LABELS = ["<1m", "1-5m", "5-15m", "15-60m", "1-4h", "4-24h", ">1d"]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# ------------------------------------------------------------------ helpers
def closed(rounds: pd.DataFrame) -> pd.DataFrame:
    return rounds[~rounds["is_open"].astype(bool)]


def _safe_div(a, b):
    return a / b if b else np.nan


def trade_stats(pnl: pd.Series) -> dict:
    """Edge metrics for a series of per-trade net PnL."""
    pnl = pnl.dropna()
    wins, losses = pnl[pnl > 0], pnl[pnl < 0]
    avg_win = wins.mean() if len(wins) else 0.0
    avg_loss = losses.mean() if len(losses) else 0.0
    return {
        "trades": int(len(pnl)),
        "net_pnl": float(pnl.sum()),
        "win_rate": _safe_div(len(wins), len(pnl)),
        "avg_win": float(avg_win),
        "avg_loss": float(avg_loss),
        "payoff_ratio": _safe_div(avg_win, abs(avg_loss)),
        "profit_factor": _safe_div(wins.sum(), abs(losses.sum())),
        "expectancy": float(pnl.mean()) if len(pnl) else np.nan,
        "best": float(pnl.max()) if len(pnl) else np.nan,
        "worst": float(pnl.min()) if len(pnl) else np.nan,
    }


def _group_stats(df: pd.DataFrame, by, extra: dict | None = None) -> pd.DataFrame:
    g = df.groupby(by, observed=True)
    out = g.agg(
        trades=("net_pnl", "size"),
        net_pnl=("net_pnl", "sum"),
        avg_pnl=("net_pnl", "mean"),
        win_rate=("net_pnl", lambda s: (s > 0).mean()),
        gross_pnl=("gross_pnl", "sum"),
        fees=("fees", "sum"),
        funding=("funding", "sum"),
        **(extra or {}),
    )
    return out.reset_index()


def streaks(pnl: pd.Series) -> dict:
    sign = np.sign(pnl.to_numpy())
    best_w = best_l = cur = 0
    prev = 0
    for s in sign:
        cur = cur + 1 if s == prev and s != 0 else (1 if s != 0 else 0)
        prev = s
        if s > 0:
            best_w = max(best_w, cur)
        elif s < 0:
            best_l = max(best_l, cur)
    return {"max_win_streak": best_w, "max_loss_streak": best_l}


# --------------------------------------------------------- account level
def daily_series(tx: pd.DataFrame) -> pd.DataFrame:
    """Daily PnL decomposition, flows, balance and a deposit-adjusted return index."""
    df = tx.copy()
    df["date"] = df["time"].dt.tz_convert("UTC").dt.floor("D")
    flow = is_flow_type(df["type"])
    df["pnl"] = np.where(flow, 0.0, df["change"])
    df["flow"] = np.where(flow, df["change"], 0.0)
    df["trade_fill"] = (~flow & ~df["type"].isin(FUNDING_TYPES)).astype(int)
    # Time-weighted return, chained event by event so deposits/withdrawals don't distort it.
    before = df["cash_balance"] - df["change"]
    r = np.where(~flow & (before > 1e-6), df["change"] / before.where(before > 1e-6, 1.0), 0.0)
    df["log_r"] = np.log1p(np.clip(r, -0.999999, None))

    days = df.groupby("date").agg(
        pnl=("pnl", "sum"), gross=("cash_flow", "sum"), fees=("fee", "sum"),
        funding=("funding", "sum"), flows=("flow", "sum"), fills=("trade_fill", "sum"),
        balance=("cash_balance", "last"), log_r=("log_r", "sum"),
    )
    full = pd.date_range(days.index.min(), days.index.max(), freq="D")
    days = days.reindex(full)
    days.index.name = "date"
    for c in ["pnl", "gross", "fees", "funding", "flows", "fills", "log_r"]:
        days[c] = days[c].fillna(0.0)
    days["balance"] = days["balance"].ffill()
    days["active"] = days["fills"] > 0

    days["return"] = np.expm1(days["log_r"])
    days["equity_index"] = np.exp(days["log_r"].cumsum())
    days["cum_pnl"] = days["pnl"].cumsum()
    days["cum_flows"] = days["flows"].cumsum()
    days["drawdown_usdt"] = days["cum_pnl"] - days["cum_pnl"].cummax().clip(lower=0)
    days["drawdown_pct"] = np.expm1(days["log_r"].cumsum() - days["log_r"].cumsum().cummax().clip(lower=0))
    return days.drop(columns="log_r").reset_index()


def max_drawdown_duration(days: pd.DataFrame) -> int:
    """Longest run of days spent below a previous cumulative-PnL peak."""
    under = (days["drawdown_usdt"] < -1e-9).astype(int).to_numpy()
    best = cur = 0
    for u in under:
        cur = cur + 1 if u else 0
        best = max(best, cur)
    return best


def account_summary(tx: pd.DataFrame, rounds: pd.DataFrame) -> dict:
    flow = is_flow_type(tx["type"])
    flows = tx.loc[flow, "change"]
    pnl_rows = tx.loc[~flow]
    c = closed(rounds)
    days = daily_series(tx)
    gross = float(pnl_rows["cash_flow"].sum())
    fees = float(pnl_rows["fee"].sum())
    funding = float(pnl_rows["funding"].sum())
    net = float(pnl_rows["change"].sum())
    deposits = float(flows[flows > 0].sum())
    withdrawals = float(flows[flows < 0].sum())
    liq = c[c["liquidated"].astype(bool)]
    daily_ret = days.loc[days["active"], "return"]
    losses_total = c.loc[c["net_pnl"] < 0, "net_pnl"].sum()
    fills = pnl_rows[pnl_rows["qty"] > 0]
    volume = float((fills["qty"] * fills["price"]).sum())

    summary = {
        "start": tx["time"].min(), "end": tx["time"].max(),
        "days": int(len(days)), "active_days": int(days["active"].sum()),
        "net_pnl": net, "gross_pnl": gross, "fees": fees, "funding": funding,
        "deposits": deposits, "withdrawals": withdrawals, "net_deposits": deposits + withdrawals,
        "return_on_deposits": _safe_div(net, deposits),
        "twr": float(days["equity_index"].iloc[-1] - 1),
        "fee_drag": _safe_div(abs(fees), abs(gross) + abs(fees)),
        "volume": volume,
        "effective_fee_rate": _safe_div(-fees, volume),
        "max_drawdown_usdt": float(days["drawdown_usdt"].min()),
        "max_drawdown_pct": float(days["drawdown_pct"].min()),
        "max_drawdown_days": max_drawdown_duration(days),
        "best_day": float(days["pnl"].max()), "worst_day": float(days["pnl"].min()),
        "green_day_rate": _safe_div((days.loc[days["active"], "pnl"] > 0).sum(), days["active"].sum()),
        "sharpe_daily_ann": _safe_div(daily_ret.mean(), daily_ret.std()) * np.sqrt(365) if len(daily_ret) > 2 else np.nan,
        "liquidations": int(len(liq)), "liquidation_pnl": float(liq["net_pnl"].sum()),
        "liquidation_share_of_losses": _safe_div(liq["net_pnl"].clip(upper=0).sum(), losses_total),
        "symbols_traded": int(c["symbol"].nunique()),
        "trades_per_active_day": _safe_div(len(c), days["active"].sum()),
        "median_hold_min": float(c["duration_min"].median()) if len(c) else np.nan,
        "open_positions": int(rounds["is_open"].sum()),
        "final_balance": float(tx["cash_balance"].iloc[-1]),
    }
    summary.update(trade_stats(c["net_pnl"]))
    summary.update(streaks(c.sort_values("close_time")["net_pnl"]))
    return summary


def pnl_waterfall(summary: dict) -> pd.DataFrame:
    return pd.DataFrame({
        "component": ["Gross trading PnL", "Trading fees", "Funding", "Net PnL"],
        "value": [summary["gross_pnl"], summary["fees"], summary["funding"], summary["net_pnl"]],
        "measure": ["relative", "relative", "relative", "total"],
    })


# ---------------------------------------------------------- the questions
def by_symbol(rounds: pd.DataFrame) -> pd.DataFrame:
    c = closed(rounds)
    out = _group_stats(c, "symbol", {
        "volume": ("entry_notional", "sum"),
        "liquidations": ("liquidated", "sum"),
        "median_hold_min": ("duration_min", "median"),
    })
    return out.sort_values("net_pnl").reset_index(drop=True)


def loss_concentration(sym: pd.DataFrame, top_n: int = 5) -> dict:
    losers = sym[sym["net_pnl"] < 0].sort_values("net_pnl")
    total_loss = losers["net_pnl"].sum()
    return {
        "top_n": top_n,
        "share": _safe_div(losers.head(top_n)["net_pnl"].sum(), total_loss),
        "symbols": losers.head(top_n)["symbol"].tolist(),
        "losing_symbols": int(len(losers)),
        "winning_symbols": int((sym["net_pnl"] > 0).sum()),
    }


def by_direction(rounds: pd.DataFrame) -> pd.DataFrame:
    return _group_stats(closed(rounds), "direction", {"volume": ("entry_notional", "sum")})


def by_hour_weekday(rounds: pd.DataFrame) -> pd.DataFrame:
    c = closed(rounds).copy()
    t = c["open_time"].dt.tz_convert("UTC")
    c["hour"] = t.dt.hour
    c["weekday"] = pd.Categorical(t.dt.dayofweek.map(dict(enumerate(WEEKDAYS))), WEEKDAYS, ordered=True)
    return _group_stats(c[~c["partial"]], ["weekday", "hour"])


def by_hour(rounds: pd.DataFrame) -> pd.DataFrame:
    c = closed(rounds)
    c = c[~c["partial"]].assign(hour=lambda d: d["open_time"].dt.tz_convert("UTC").dt.hour)
    return _group_stats(c, "hour")


def by_duration(rounds: pd.DataFrame) -> pd.DataFrame:
    c = closed(rounds).dropna(subset=["duration_min"]).copy()
    c["hold"] = pd.cut(c["duration_min"], DURATION_BINS, labels=DURATION_LABELS, right=False)
    return _group_stats(c, "hold")


def winners_vs_losers_hold(rounds: pd.DataFrame) -> pd.DataFrame:
    c = closed(rounds).dropna(subset=["duration_min"])
    c = c.assign(outcome=np.where(c["net_pnl"] > 0, "Winners", "Losers"))
    return c.groupby("outcome")["duration_min"].agg(["count", "median", "mean"]).reset_index()


def by_size(rounds: pd.DataFrame, q: int = 5) -> pd.DataFrame:
    c = closed(rounds)
    c = c[~c["partial"] & (c["entry_notional"] > 0)].copy()
    if len(c) < q:
        return pd.DataFrame()
    c["size_bucket"] = pd.qcut(c["entry_notional"], q, duplicates="drop")
    out = _group_stats(c, "size_bucket", {"avg_notional": ("entry_notional", "mean")})
    out["size_bucket"] = [f"Q{i + 1} (~{n:,.0f})" for i, n in enumerate(out["avg_notional"])]
    return out


def after_loss_behaviour(rounds: pd.DataFrame, window_min: float = 15) -> pd.DataFrame:
    """Tilt check: how do trades opened shortly after a losing trade perform?"""
    c = closed(rounds).sort_values("open_time").reset_index(drop=True)
    if c.empty:
        return pd.DataFrame()
    closes = c.sort_values("close_time")[["close_time", "net_pnl"]].rename(
        columns={"close_time": "prev_close", "net_pnl": "prev_pnl"})
    m = pd.merge_asof(c, closes, left_on="open_time", right_on="prev_close",
                      direction="backward", allow_exact_matches=False)
    gap = (m["open_time"] - m["prev_close"]).dt.total_seconds() / 60
    quick = gap <= window_min
    m["context"] = np.select(
        [m["prev_pnl"].isna(), quick & (m["prev_pnl"] < 0), quick & (m["prev_pnl"] > 0)],
        ["First trade", f"≤{window_min:g}m after a loss", f"≤{window_min:g}m after a win"],
        default=f">{window_min:g}m since last trade",
    )
    return _group_stats(m[m["context"] != "First trade"], "context")


def overtrading(tx: pd.DataFrame, rounds: pd.DataFrame) -> pd.DataFrame:
    """Daily trade count vs. daily net PnL."""
    c = closed(rounds)
    days = daily_series(tx).set_index("date")
    counts = c.groupby(c["close_time"].dt.tz_convert("UTC").dt.floor("D")).size()
    days["trades"] = counts.reindex(days.index).fillna(0)
    days = days[days["active"]].reset_index()
    days["trade_bucket"] = pd.cut(days["trades"], [0, 3, 7, 15, 30, np.inf],
                                  labels=["1-3", "4-7", "8-15", "16-30", "30+"], right=True)
    return days


def market_context(days: pd.DataFrame, klines: pd.DataFrame) -> pd.DataFrame:
    """Join daily PnL with BTC daily return and intraday range."""
    if klines is None or klines.empty:
        return pd.DataFrame()
    k = klines.copy()
    k["date"] = k["time"].dt.tz_convert("UTC").dt.floor("D")
    k["btc_return"] = k["close"].pct_change()
    k["btc_range"] = (k["high"] - k["low"]) / k["open"]
    m = days.merge(k[["date", "close", "btc_return", "btc_range"]], on="date", how="inner")
    m = m[m["active"]].copy()
    if len(m) < 3:
        return m
    m["btc_move"] = pd.cut(m["btc_return"], [-np.inf, -0.03, -0.01, 0.01, 0.03, np.inf],
                           labels=["< -3%", "-3..-1%", "flat ±1%", "+1..+3%", "> +3%"])
    m["btc_vol"] = pd.qcut(m["btc_range"], 3, labels=["Low vol", "Mid vol", "High vol"], duplicates="drop")
    return m


def by_leverage(closed_pnl: pd.DataFrame) -> pd.DataFrame:
    if closed_pnl is None or closed_pnl.empty:
        return pd.DataFrame()
    c = closed_pnl.copy()
    c["lev_bucket"] = pd.cut(c["leverage"], [0, 3, 5, 10, 20, 50, np.inf],
                             labels=["≤3x", "3-5x", "5-10x", "10-20x", "20-50x", ">50x"], right=True)
    return c.groupby("lev_bucket", observed=True).agg(
        trades=("closed_pnl", "size"), net_pnl=("closed_pnl", "sum"),
        avg_pnl=("closed_pnl", "mean"), win_rate=("closed_pnl", lambda s: (s > 0).mean()),
    ).reset_index()


# ------------------------------------------------------------- insights
def insights(tx: pd.DataFrame, rounds: pd.DataFrame, klines: pd.DataFrame | None = None) -> list[str]:
    """Plain-English findings, computed -- not hand-written."""
    s = account_summary(tx, rounds)
    out: list[str] = []
    out.append(
        f"Net result {s['net_pnl']:+,.2f} USDT over {s['days']} days on {s['deposits']:,.2f} USDT deposited "
        f"({s['return_on_deposits']:+.1%} of deposits)."
    )
    if s["gross_pnl"] > 0 > s["net_pnl"]:
        out.append(f"Gross trading was profitable (+{s['gross_pnl']:,.2f}) but fees ({s['fees']:,.2f}) turned it into a loss.")
    elif s["gross_pnl"] < 0:
        out.append(
            f"Losses come from trading itself ({s['gross_pnl']:,.2f} gross); fees added another {s['fees']:,.2f} "
            f"({abs(s['fees']) / (abs(s['gross_pnl']) + abs(s['fees'])):.0%} of the total damage)."
        )
    out.append(
        f"Win rate {s['win_rate']:.0%} with payoff ratio {s['payoff_ratio']:.2f} → expectancy "
        f"{s['expectancy']:+.3f} USDT per trade (profit factor {s['profit_factor']:.2f})."
    )
    breakeven = 1 / (1 + s["payoff_ratio"]) if s["payoff_ratio"] == s["payoff_ratio"] else np.nan
    if breakeven == breakeven:
        out.append(f"At this payoff ratio you need a {breakeven:.0%} win rate just to break even.")

    sym = by_symbol(rounds)
    conc = loss_concentration(sym, 3)
    if conc["symbols"]:
        out.append(
            f"{conc['share']:.0%} of all losses came from just 3 symbols: {', '.join(conc['symbols'])}. "
            f"{conc['winning_symbols']} of {len(sym)} symbols were net profitable."
        )
    d = by_direction(rounds).set_index("direction")
    if {"Long", "Short"} <= set(d.index):
        better = d["net_pnl"].idxmax()
        verdict = f"{better}s work better" if d["net_pnl"].max() > 0 else f"{better}s lose less"
        out.append(
            f"Longs: {d.loc['Long', 'net_pnl']:+,.2f} ({d.loc['Long', 'win_rate']:.0%} win, n={d.loc['Long', 'trades']}) vs "
            f"Shorts: {d.loc['Short', 'net_pnl']:+,.2f} ({d.loc['Short', 'win_rate']:.0%} win, n={d.loc['Short', 'trades']}) "
            f"— {verdict}."
        )
    wl = winners_vs_losers_hold(rounds).set_index("outcome")
    if {"Winners", "Losers"} <= set(wl.index):
        ratio = wl.loc["Losers", "median"] / max(wl.loc["Winners", "median"], 1e-9)
        if ratio > 1.2:
            out.append(f"Losing trades are held {ratio:.1f}x longer than winners (median) — a classic 'let losers run' pattern.")
        elif ratio < 0.8:
            out.append(f"Winners are held {1 / ratio:.1f}x longer than losers — good: losses are being cut quickly.")
    tilt = after_loss_behaviour(rounds).set_index("context")
    after_loss = [i for i in tilt.index if "after a loss" in i]
    calm = [i for i in tilt.index if i.startswith(">")]
    if after_loss and calm:
        a, b = tilt.loc[after_loss[0]], tilt.loc[calm[0]]
        out.append(
            f"Trades opened {after_loss[0]} average {a['avg_pnl']:+.3f} USDT ({a['win_rate']:.0%} win, n={int(a['trades'])}) "
            f"vs {b['avg_pnl']:+.3f} ({b['win_rate']:.0%} win) after a pause."
        )
    dur = by_duration(rounds)
    if len(dur) >= 3:
        best = dur.loc[dur["avg_pnl"].idxmax()]
        out.append(
            f"Holding time matters: trades held {best['hold']} were the best bucket "
            f"({best['avg_pnl']:+.3f} USDT/trade, {best['win_rate']:.0%} win); "
            f"{(dur['net_pnl'] < 0).sum()} of {len(dur)} holding-time buckets lost money."
        )
    size = by_size(rounds)
    if len(size) >= 3:
        top, bottom = size.iloc[-1], size.iloc[0]
        out.append(
            f"Largest positions (avg {top['avg_notional']:,.0f} USDT) returned {top['net_pnl']:+,.2f} in total vs "
            f"{bottom['net_pnl']:+,.2f} for the smallest (avg {bottom['avg_notional']:,.0f})."
        )
    ot = overtrading(tx, rounds)
    if len(ot) >= 5:
        corr = ot["trades"].corr(ot["pnl"])
        out.append(f"Correlation between number of trades in a day and that day's PnL: {corr:+.2f}"
                   + (" — busier days are worse days." if corr < -0.3 else "."))
    if s["effective_fee_rate"] == s["effective_fee_rate"]:
        out.append(
            f"Effective fee rate {s['effective_fee_rate']:.3%} of traded volume "
            f"({s['volume']:,.0f} USDT traded) — Bybit's taker fee is ~0.055%, maker ~0.02%."
        )
    if s["liquidations"]:
        out.append(
            f"{s['liquidations']} liquidation{'s' if s['liquidations'] != 1 else ''} cost {s['liquidation_pnl']:,.2f} USDT "
            f"({s['liquidation_share_of_losses']:.0%} of all losing-trade PnL)."
        )
    hrs = by_hour(rounds)
    if len(hrs) >= 4:
        worst = hrs.nsmallest(1, "net_pnl").iloc[0]
        best = hrs.nlargest(1, "net_pnl").iloc[0]
        out.append(
            f"Best hour to open trades: {int(best['hour']):02d}:00 UTC ({best['net_pnl']:+,.2f}); "
            f"worst: {int(worst['hour']):02d}:00 UTC ({worst['net_pnl']:+,.2f})."
        )
    if klines is not None and not klines.empty:
        mc = market_context(daily_series(tx), klines)
        if len(mc) >= 10:
            corr = mc["pnl"].corr(mc["btc_return"])
            out.append(f"Correlation between your daily PnL and BTC's daily return: {corr:+.2f}.")
    return out
