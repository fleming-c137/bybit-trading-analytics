"""Turn a dataset into the JSON report the web dashboard renders.

The dashboard never computes metrics itself: every number on screen comes from
:mod:`bybit_analytics.analysis` via :func:`build_report`. Datasets can be
serialised (:func:`encode_dataset`) so a visitor's freshly fetched data can be
re-filtered without fetching it from Bybit again.
"""

from __future__ import annotations

import base64
import gzip
import io
import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import analysis as A
from .trades import build_round_trips
from .transform import CLOSED_PNL_COLUMNS, TX_COLUMNS, is_flow_type, main_currency, trading_scope

KLINE_COLUMNS = ["symbol", "time", "open", "high", "low", "close", "volume"]
FRAMES = {  # name: (columns, time columns, text columns)
    "tx": (TX_COLUMNS, ["time"], ["id", "category", "symbol", "currency", "type", "side",
                                  "order_id", "trade_id", "source"]),
    "closed_pnl": (CLOSED_PNL_COLUMNS, ["time"], ["order_id", "symbol", "position_side", "exec_type"]),
    "klines": (KLINE_COLUMNS, ["time"], ["symbol"]),
}
TRADE_FIELDS = ["symbol", "direction", "open_time", "close_time", "duration_min", "entry_notional",
                "avg_entry", "avg_exit", "gross_pnl", "fees", "funding", "net_pnl", "return_pct",
                "liquidated", "partial"]


class ReportError(ValueError):
    """The request can't produce a report (bad filter, no data...)."""


@dataclass
class Dataset:
    tx: pd.DataFrame
    closed_pnl: pd.DataFrame
    klines: pd.DataFrame
    meta: dict = field(default_factory=dict)


@dataclass
class Prepared:
    """A dataset scoped to one settlement currency, with round trips built once."""
    dataset: Dataset
    currency: str
    currencies: list[str]
    tx: pd.DataFrame
    rounds: pd.DataFrame


# ------------------------------------------------------------ serialisation
def _frame_to_csv(df: pd.DataFrame, columns, time_cols) -> str:
    out = df.reindex(columns=columns).copy()
    for c in time_cols:
        out[c] = pd.to_datetime(out[c], utc=True).dt.as_unit("ms").astype("int64")
    return out.to_csv(index=False)


def _frame_from_csv(text: str, columns, time_cols, text_cols) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    df = df.reindex(columns=columns, fill_value="")
    for c in columns:
        if c in time_cols:
            df[c] = pd.to_datetime(pd.to_numeric(df[c]), unit="ms", utc=True)
        elif c not in text_cols:
            df[c] = pd.to_numeric(df[c].replace("", np.nan), errors="coerce")
    return df


def encode_dataset(ds: Dataset) -> bytes:
    payload = {"meta": ds.meta}
    for name, (cols, tcols, _) in FRAMES.items():
        payload[name] = _frame_to_csv(getattr(ds, name), cols, tcols)
    return gzip.compress(json.dumps(payload).encode(), compresslevel=6)


def decode_dataset(blob: bytes) -> Dataset:
    try:
        payload = json.loads(gzip.decompress(blob))
    except (OSError, ValueError) as exc:
        raise ReportError("The dataset could not be read.") from exc
    frames = {name: _frame_from_csv(payload.get(name, ""), *spec) if payload.get(name)
              else pd.DataFrame(columns=spec[0]) for name, spec in FRAMES.items()}
    return Dataset(frames["tx"], frames["closed_pnl"], frames["klines"], payload.get("meta", {}))


def dataset_to_b64(ds: Dataset) -> str:
    return base64.b64encode(encode_dataset(ds)).decode()


def dataset_from_b64(text: str) -> Dataset:
    try:
        return decode_dataset(base64.b64decode(text))
    except (ValueError, TypeError) as exc:
        raise ReportError("The dataset could not be read.") from exc


# ------------------------------------------------------------- JSON helpers
def _clean(v):
    if isinstance(v, pd.Timestamp):
        return int(v.value // 1_000_000)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return None if not math.isfinite(float(v)) else round(float(v), 6)
    if isinstance(v, np.bool_):
        return bool(v)
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, _Raw):
        return v
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    return v


def _tidy(df: pd.DataFrame, columns: list[str] | None, digits: int) -> pd.DataFrame:
    out = (df[columns] if columns else df).copy()
    for c in out.columns:
        if isinstance(out[c].dtype, pd.CategoricalDtype):
            out[c] = out[c].astype(str)
        elif pd.api.types.is_datetime64_any_dtype(out[c]):
            ms = out[c].dt.as_unit("ms").astype("int64")
            out[c] = ms.where(out[c].notna(), None).astype(object)
        elif pd.api.types.is_float_dtype(out[c]):
            out[c] = out[c].round(digits)
    return out


class _Raw(list):
    """Already JSON-safe; _clean leaves it alone."""


def _records(df: pd.DataFrame, columns: list[str] | None = None, digits: int = 6) -> list[dict]:
    if df is None or df.empty:
        return _Raw()
    return _Raw(json.loads(_tidy(df, columns, digits).to_json(orient="records")))


def _table(df: pd.DataFrame, columns: list[str], digits: int = 4) -> dict:
    """Compact column/rows form for long tables (trades)."""
    if df is None or df.empty:
        return {"columns": columns, "rows": _Raw()}
    rows = json.loads(_tidy(df, columns, digits).to_json(orient="values"))
    return {"columns": columns, "rows": _Raw(rows)}


# ------------------------------------------------------------------ report
def prepare(ds: Dataset, currency: str | None = None) -> Prepared:
    raw = ds.tx
    if raw is None or raw.empty:
        raise ReportError("This data source has no transactions yet.")
    currencies = sorted(c for c in raw["currency"].dropna().unique() if c)
    if currency not in currencies:
        currency = main_currency(raw)
    tx = trading_scope(raw, currency)
    return Prepared(ds, currency, currencies, tx, build_round_trips(tx))


def _day(value: str | None, name: str) -> pd.Timestamp | None:
    if not value:
        return None
    try:
        ts = pd.Timestamp(value)
    except (ValueError, TypeError) as exc:
        raise ReportError(f"'{name}' must be a date like 2026-01-31.") from exc
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def _verdict(s: dict, breakeven: float | None) -> dict:
    wr, exp = s.get("win_rate"), s.get("expectancy")
    if wr is None or exp is None or not math.isfinite(exp):
        return {"tone": "neutral", "title": "Not enough closed trades", "text": "Widen the period to see the edge."}
    be = f"{breakeven:.0%}" if breakeven is not None and math.isfinite(breakeven) else "n/a"
    payoff = s.get("payoff_ratio")
    payoff_txt = f"{payoff:.2f}" if payoff is not None and math.isfinite(payoff) else "n/a"
    if exp > 0 and (s.get("profit_factor") or 0) > 1:
        return {"tone": "positive", "title": "Positive edge in this period",
                "text": f"A {wr:.0%} win rate at a {payoff_txt} payoff ratio clears the {be} break-even rate. "
                        f"Each trade made {exp:+.2f} {s['currency']} on average after costs."}
    cost = ""
    if s["gross_pnl"] > 0 > s["net_pnl"]:
        cost = " Trading was profitable before costs; fees turned it into a loss."
    return {"tone": "negative", "title": "No edge in this period",
            "text": f"A {wr:.0%} win rate is below the {be} needed at a {payoff_txt} payoff ratio. "
                    f"Each trade lost {abs(exp):.2f} {s['currency']} on average after costs.{cost}"}


def build_report(p: Prepared, start: str | None = None, end: str | None = None,
                 symbols: list[str] | None = None, tilt_window: float = 15) -> dict:
    tx, rounds, ds = p.tx, p.rounds, p.dataset
    lo, hi = _day(start, "start"), _day(end, "end")
    if hi is not None:
        hi = hi + pd.Timedelta(days=1)
    if lo is not None:
        tx = tx[tx["time"] >= lo]
        rounds = rounds[rounds["open_time"] >= lo]
    if hi is not None:
        tx = tx[tx["time"] < hi]
        rounds = rounds[rounds["open_time"] < hi]
    symbols_all = sorted(p.rounds["symbol"].dropna().unique().tolist())
    picked = [s for s in (symbols or []) if s in symbols_all]
    if picked:
        tx = tx[is_flow_type(tx["type"]) | tx["symbol"].isin(picked)]
        rounds = rounds[rounds["symbol"].isin(picked)]

    meta = {
        "source": ds.meta, "currency": p.currency, "currencies": p.currencies,
        "data_start": p.tx["time"].min(), "data_end": p.tx["time"].max(),
        "symbols": symbols_all,
        "filters": {"start": start, "end": end, "symbols": picked, "tilt_window": tilt_window},
        "generated_at": pd.Timestamp(datetime.now(timezone.utc)),
    }
    if tx.empty or A.closed(rounds).empty:
        return _clean({"meta": meta, "empty": True})

    s = A.account_summary(tx, rounds)
    s["currency"] = p.currency
    payoff = s["payoff_ratio"]
    breakeven = 1 / (1 + payoff) if payoff == payoff and payoff is not None else None
    s["breakeven_win_rate"] = breakeven
    days = A.daily_series(tx)
    c = A.closed(rounds)

    sym = A.by_symbol(rounds)
    conc = A.loss_concentration(sym, 5)
    losers = sym[sym["net_pnl"] < 0].sort_values("net_pnl")
    total_loss = losers["net_pnl"].sum()
    losers = losers.assign(share=losers["net_pnl"] / total_loss if total_loss else np.nan)

    ot = A.overtrading(tx, rounds)
    ot_buckets = (ot.groupby("trade_bucket", observed=True)["pnl"]
                  .agg(days="size", avg_pnl="mean", total="sum").reset_index()) if not ot.empty else pd.DataFrame()

    kl = ds.klines
    market: dict = {"available": False}
    if kl is not None and not kl.empty:
        mc = A.market_context(days, kl)
        if len(mc) >= 3:
            market = {
                "available": True,
                "corr": mc["pnl"].corr(mc["btc_return"]),
                "up_avg": mc.loc[mc["btc_return"] > 0, "pnl"].mean(),
                "down_avg": mc.loc[mc["btc_return"] <= 0, "pnl"].mean(),
                "days": _records(mc, ["date", "pnl", "btc_return", "btc_range", "close"]),
                "by_move": _records(mc.groupby("btc_move", observed=True)["pnl"]
                                    .agg(days="size", avg_pnl="mean", total="sum").reset_index())
                if "btc_move" in mc else [],
                "by_vol": _records(mc.groupby("btc_vol", observed=True)["pnl"]
                                   .agg(days="size", avg_pnl="mean", total="sum").reset_index())
                if "btc_vol" in mc else [],
            }

    cp = ds.closed_pnl
    if cp is not None and not cp.empty:
        cp = cp[cp["symbol"].isin(picked)] if picked else cp
        cp = cp[cp["time"] >= lo] if lo is not None else cp
        cp = cp[cp["time"] < hi] if hi is not None else cp

    report = {
        "meta": meta,
        "empty": False,
        "summary": s,
        "verdict": _verdict(s, breakeven),
        "insights": A.insights(tx, rounds, kl),
        "daily": _records(days, ["date", "pnl", "gross", "fees", "funding", "flows", "fills", "balance",
                                 "cum_pnl", "drawdown_usdt", "equity_index", "active"]),
        "waterfall": _records(A.pnl_waterfall(s)),
        "by_symbol": _records(sym),
        "loss_concentration": conc,
        "top_losers": _records(losers.head(12), ["symbol", "net_pnl", "share", "trades"]),
        "by_direction": _records(A.by_direction(rounds)),
        "by_duration": _records(A.by_duration(rounds)),
        "hold_winners_losers": _records(A.winners_vs_losers_hold(rounds)),
        "by_size": _records(A.by_size(rounds)),
        "by_hour": _records(A.by_hour(rounds)),
        "by_hour_weekday": _records(A.by_hour_weekday(rounds)),
        "tilt": _records(A.after_loss_behaviour(rounds, tilt_window)),
        "overtrading": {
            "corr": ot["trades"].corr(ot["pnl"]) if len(ot) >= 5 else None,
            "days": _records(ot, ["date", "trades", "pnl"]) if not ot.empty else [],
            "buckets": _records(ot_buckets),
        },
        "market": market,
        "by_leverage": _records(A.by_leverage(cp)),
        "liquidations": _table(c[c["liquidated"].astype(bool)].sort_values("net_pnl"), TRADE_FIELDS),
        "trades": _table(c.sort_values("close_time"), TRADE_FIELDS),
    }
    return _clean(report)
