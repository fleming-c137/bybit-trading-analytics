"""Normalise Bybit data (API JSON or CSV export) into one canonical schema.

Canonical transaction columns
-----------------------------
id, time (UTC), category, symbol, currency, type, side (Buy/Sell/""), qty,
size (signed position after the event, short < 0), price,
cash_flow (realised PnL from closing), fee (signed: negative = cost),
funding (signed: negative = paid), change (net wallet change),
cash_balance, order_id, trade_id, source

Sign conventions differ between the API (fee/funding positive = expense) and the
CSV export (signed P&L). We sidestep that by deriving fee/funding from the
identity ``change = cash_flow + fee + funding``, which holds in both sources.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

TX_COLUMNS = [
    "id", "time", "category", "symbol", "currency", "type", "side", "qty", "size", "price",
    "cash_flow", "fee", "funding", "change", "cash_balance", "order_id", "trade_id", "source",
]

FUNDING_TYPES = {"SETTLEMENT"}
TRADE_TYPES = {"TRADE", "LIQUIDATION", "DELIVERY", "ADL", "BANKRUPT"}
# Balance changes that are *not* derivatives trading performance: money moving
# in/out, coin conversions, spot buys/sells, earn products.
FLOW_PREFIXES = ("TRANSFER", "DEPOSIT", "WITHDRAW", "CURRENCY_", "CONVERT", "SPOT_",
                 "FLEXIBLE_STAKING", "EARN", "AIRDROP")
DERIVATIVE_CATEGORIES = {"linear", "inverse", ""}


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.replace({"--": np.nan, "": np.nan}), errors="coerce")


def _side(s: pd.Series) -> pd.Series:
    return s.fillna("").astype(str).str.strip().str.capitalize().replace({"--": "", "None": ""})


def _finalise(df: pd.DataFrame) -> pd.DataFrame:
    for col in ["qty", "size", "price", "cash_flow", "change", "cash_balance"]:
        df[col] = df[col].fillna(0.0).astype(float)
    is_funding = df["type"].isin(FUNDING_TYPES)
    is_flow = is_flow_type(df["type"])
    residual = df["change"] - df["cash_flow"]
    df["funding"] = np.where(is_funding, residual, 0.0)
    df["fee"] = np.where(~is_funding & ~is_flow, residual, 0.0)
    # Transfers: the whole change is a flow, not PnL.
    df.loc[is_flow, "cash_flow"] = 0.0
    for col in ["category", "symbol", "currency", "side", "order_id", "trade_id"]:
        df[col] = df[col].fillna("").astype(str)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df[TX_COLUMNS].sort_values(["time", "id"]).reset_index(drop=True)


def is_flow_type(types: pd.Series) -> pd.Series:
    return types.astype(str).str.upper().str.startswith(FLOW_PREFIXES)


def trading_scope(tx: pd.DataFrame, currency: str = "USDT") -> pd.DataFrame:
    """Restrict to one settlement currency and treat spot trades as balance flows.

    A UTA can hold several coins; summing their ``change`` columns would add
    DOGS to USDT. Spot buys/sells swap one asset for another rather than
    realising derivatives PnL, so they are relabelled ``SPOT_TRADE`` (a flow).
    """
    out = tx[tx["currency"] == currency].copy()
    spot = ~out["category"].isin(DERIVATIVE_CATEGORIES)
    out.loc[spot, "type"] = "SPOT_TRADE"
    flow = is_flow_type(out["type"])
    out.loc[flow, ["cash_flow", "fee", "funding"]] = 0.0
    return out.reset_index(drop=True)


def main_currency(tx: pd.DataFrame) -> str:
    counts = tx.loc[tx["type"].isin(TRADE_TYPES), "currency"].value_counts()
    return counts.index[0] if len(counts) else "USDT"


def normalize_api_transactions(rows: list[dict]) -> pd.DataFrame:
    """Rows from /v5/account/transaction-log -> canonical frame."""
    if not rows:
        return pd.DataFrame(columns=TX_COLUMNS)
    raw = pd.DataFrame(rows)
    get = lambda c: raw[c] if c in raw else pd.Series([None] * len(raw))  # noqa: E731
    df = pd.DataFrame({
        "id": get("id").astype(str),
        "time": pd.to_datetime(_num(get("transactionTime")), unit="ms", utc=True),
        "category": get("category"),
        "symbol": get("symbol"),
        "currency": get("currency"),
        "type": get("type").astype(str).str.upper(),
        "side": _side(get("side")),
        "qty": _num(get("qty")).abs(),
        "size": _num(get("size")),
        "price": _num(get("tradePrice")),
        "cash_flow": _num(get("cashFlow")),
        "change": _num(get("change")),
        "cash_balance": _num(get("cashBalance")),
        "order_id": get("orderId"),
        "trade_id": get("tradeId"),
        "source": "api",
    })
    return _finalise(df)


def _row_ids(df: pd.DataFrame) -> pd.Series:
    """Deterministic ids for CSV rows (the export has no id column)."""
    key = df.astype(object).fillna("").astype(str).agg("|".join, axis=1)
    dup = key.groupby(key).cumcount().astype(str)
    return (key + "#" + dup).map(lambda k: "csv-" + hashlib.sha1(k.encode()).hexdigest()[:16])


def normalize_csv(raw: pd.DataFrame) -> pd.DataFrame:
    """Bybit 'Asset Change Details' (UTA) CSV export -> canonical frame."""
    raw = raw.copy()
    raw.columns = [c.strip() for c in raw.columns]
    time_col = next(c for c in raw.columns if c.lower().startswith("time"))
    df = pd.DataFrame({
        "id": _row_ids(raw),
        "time": pd.to_datetime(raw[time_col], utc=True),
        "category": "linear",
        "symbol": raw.get("Contract"),
        "currency": raw.get("Currency"),
        "type": raw["Type"].astype(str).str.upper(),
        "side": _side(raw.get("Direction")),
        "qty": _num(raw.get("Quantity")).abs(),
        "size": _num(raw.get("Position")),
        "price": _num(raw.get("Filled Price")),
        "cash_flow": _num(raw.get("Cash Flow")),
        "change": _num(raw.get("Change")),
        "cash_balance": _num(raw.get("Wallet Balance")),
        "order_id": "",
        "trade_id": "",
        "source": "csv",
    })
    df.loc[is_flow_type(df["type"]), "symbol"] = ""
    return _finalise(df)


# ---------------------------------------------------------------- closed pnl
CLOSED_PNL_COLUMNS = [
    "order_id", "symbol", "position_side", "qty", "avg_entry_price", "avg_exit_price",
    "entry_value", "exit_value", "closed_pnl", "open_fee", "close_fee", "leverage",
    "fill_count", "exec_type", "time",
]


def normalize_closed_pnl(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=CLOSED_PNL_COLUMNS)
    raw = pd.DataFrame(rows)
    df = pd.DataFrame({
        "order_id": raw["orderId"].astype(str),
        "symbol": raw["symbol"],
        # `side` on a closed-pnl record is the side of the *closing* order.
        "position_side": raw["side"].map({"Buy": "Short", "Sell": "Long"}).fillna(""),
        "qty": _num(raw["closedSize"]),
        "avg_entry_price": _num(raw["avgEntryPrice"]),
        "avg_exit_price": _num(raw["avgExitPrice"]),
        "entry_value": _num(raw["cumEntryValue"]),
        "exit_value": _num(raw["cumExitValue"]),
        "closed_pnl": _num(raw["closedPnl"]),
        "open_fee": _num(raw.get("openFee", pd.Series(0, index=raw.index))),
        "close_fee": _num(raw.get("closeFee", pd.Series(0, index=raw.index))),
        "leverage": _num(raw["leverage"]),
        "fill_count": _num(raw.get("fillCount", pd.Series(0, index=raw.index))),
        "exec_type": raw.get("execType", pd.Series("", index=raw.index)).astype(str),
        "time": pd.to_datetime(_num(raw["updatedTime"]), unit="ms", utc=True),
    })
    return df.sort_values("time").reset_index(drop=True)


def normalize_klines(rows: list[list[str]], symbol: str) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["symbol", "time", "open", "high", "low", "close", "volume"])
    df = pd.DataFrame([r[:6] for r in rows], columns=["time", "open", "high", "low", "close", "volume"])
    df["time"] = pd.to_datetime(pd.to_numeric(df["time"]), unit="ms", utc=True)
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c])
    df.insert(0, "symbol", symbol)
    return df.drop_duplicates("time").sort_values("time").reset_index(drop=True)
