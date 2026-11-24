import hashlib
import hmac

import numpy as np
import pandas as pd
import pytest

from bybit_analytics import analysis as A
from bybit_analytics.client import SEVEN_DAYS_MS, sign, time_windows
from bybit_analytics.demo import generate
from bybit_analytics.storage import Store
from bybit_analytics.trades import build_round_trips
from bybit_analytics.transform import normalize_api_transactions, normalize_csv, trading_scope


# ------------------------------------------------------------------ client
def test_signature_matches_hmac_sha256():
    expected = hmac.new(b"secret", b"1700000000000key5000a=1&b=2", hashlib.sha256).hexdigest()
    assert sign("secret", "1700000000000", "key", "5000", "a=1&b=2") == expected


def test_time_windows_cover_range_without_gaps():
    start, end = 0, SEVEN_DAYS_MS * 3 + 123
    windows = list(time_windows(start, end))
    assert windows[0][0] == start and windows[-1][1] == end
    assert all(hi - lo < SEVEN_DAYS_MS for lo, hi in windows)
    assert all(b[0] == a[1] + 1 for a, b in zip(windows, windows[1:]))


# --------------------------------------------------------------- transform
CSV_HEADER = "Uid,Currency,Contract,Type,Direction,Quantity,Position,Filled Price,Funding,Fee Paid,Cash Flow,Change,Wallet Balance,Action,Time(UTC)"
CSV_ROWS = [  # newest first, as Bybit exports
    "1,USDT,ABCUSDT,TRADE,SELL,100,0,1.10,0,-0.06,10,9.94,109.85,CLOSE,2026-01-01 02:00:00",
    "1,USDT,ABCUSDT,SETTLEMENT,BUY,--,100,--,-0.05,0,0,-0.05,99.91,SETTLEMENT,2026-01-01 01:00:00",
    "1,USDT,ABCUSDT,TRADE,BUY,60,100,1.00,0,-0.024,0,-0.024,99.96,OPEN,2026-01-01 00:30:00",
    "1,USDT,ABCUSDT,TRADE,BUY,40,40,1.00,0,-0.016,0,-0.016,99.984,OPEN,2026-01-01 00:30:00",
    "1,USDT,,TRANSFER_IN,--,0,0,0,0,0,100,100,100,--,2026-01-01 00:00:00",
]


@pytest.fixture
def csv_tx(tmp_path):
    p = tmp_path / "export.csv"
    p.write_text("\n".join([CSV_HEADER, *CSV_ROWS]))
    return normalize_csv(pd.read_csv(p))


def test_csv_normalisation(csv_tx):
    assert list(csv_tx["type"]) == ["TRANSFER_IN", "TRADE", "TRADE", "SETTLEMENT", "TRADE"]
    pnl = csv_tx[csv_tx["type"] != "TRANSFER_IN"]
    assert np.allclose(pnl["cash_flow"] + pnl["fee"] + pnl["funding"], pnl["change"])
    assert csv_tx["id"].is_unique


def test_api_normalisation_sign_agnostic():
    rows = [
        {"id": "1", "transactionTime": "1700000000000", "symbol": "BTCUSDT", "category": "linear", "currency": "USDT",
         "type": "TRADE", "side": "Buy", "qty": "0.01", "size": "0.01", "tradePrice": "30000", "cashFlow": "0",
         "fee": "0.165", "funding": "", "change": "-0.165", "cashBalance": "99.835"},
        {"id": "2", "transactionTime": "1700000100000", "symbol": "BTCUSDT", "category": "linear", "currency": "USDT",
         "type": "SETTLEMENT", "side": "Buy", "qty": "0", "size": "0.01", "tradePrice": "", "cashFlow": "0",
         "fee": "0", "funding": "0.03", "change": "-0.03", "cashBalance": "99.805"},
    ]
    tx = normalize_api_transactions(rows)
    assert tx.loc[0, "fee"] == pytest.approx(-0.165)
    assert tx.loc[1, "funding"] == pytest.approx(-0.03)


# -------------------------------------------------------------- round trips
def test_round_trip_reconstruction(csv_tx):
    r = build_round_trips(csv_tx)
    assert len(r) == 1
    t = r.iloc[0]
    assert t["direction"] == "Long" and not t["partial"] and not t["is_open"]
    assert t["entry_qty"] == pytest.approx(100)
    assert t["avg_entry"] == pytest.approx(1.0) and t["avg_exit"] == pytest.approx(1.1)
    assert t["gross_pnl"] == pytest.approx(10)
    assert t["fees"] == pytest.approx(-0.1)
    assert t["funding"] == pytest.approx(-0.05)
    assert t["net_pnl"] == pytest.approx(9.85)
    assert t["duration_min"] == pytest.approx(90)


def _tx(rows):
    df = pd.DataFrame(rows, columns=["time", "side", "qty", "size", "price", "cash_flow", "fee"])
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df["change"] = df["cash_flow"] + df["fee"]
    df = df.assign(id=[str(i) for i in range(len(df))], category="linear", symbol="XUSDT", currency="USDT",
                   type="TRADE", funding=0.0, cash_balance=100.0, order_id="", trade_id="", source="test")
    return df


def test_flip_long_to_short_splits_into_two_rounds():
    tx = _tx([
        ("2026-01-01 00:00", "Buy", 10, 10, 1.0, 0.0, -0.01),
        ("2026-01-01 00:10", "Sell", 15, -5, 1.2, 2.0, -0.015),
        ("2026-01-01 00:20", "Buy", 5, 0, 1.0, 1.0, -0.005),
    ])
    r = build_round_trips(tx)
    assert list(r["direction"]) == ["Long", "Short"]
    assert r.loc[0, "gross_pnl"] == pytest.approx(2.0)
    assert r.loc[1, "entry_qty"] == pytest.approx(5)
    assert r["net_pnl"].sum() == pytest.approx(3.0 - 0.03)


def test_position_open_before_data_is_flagged_partial():
    tx = _tx([("2026-01-01 00:00", "Sell", 10, 0, 1.0, 1.0, -0.01)])
    r = build_round_trips(tx)
    assert len(r) == 1 and bool(r.loc[0, "partial"]) and np.isnan(r.loc[0, "duration_min"])


def test_unsigned_sizes_are_inferred():
    tx = _tx([
        ("2026-01-01 00:00", "Sell", 10, 10, 1.0, 0.0, -0.01),  # unsigned short
        ("2026-01-01 00:10", "Buy", 10, 0, 0.9, 1.0, -0.01),
    ])
    r = build_round_trips(tx)
    assert list(r["direction"]) == ["Short"] and r.loc[0, "gross_pnl"] == pytest.approx(1.0)


# -------------------------------------------------------- analysis on demo
@pytest.fixture(scope="module")
def demo():
    tx, cp, kl = generate(days=40, seed=1)
    return tx, build_round_trips(tx), cp, kl


def test_round_trips_reconcile_with_account(demo):
    tx, rounds, _, _ = demo
    s = A.account_summary(tx, rounds)
    assert rounds["net_pnl"].sum() == pytest.approx(s["net_pnl"], abs=1e-6)
    assert s["gross_pnl"] + s["fees"] + s["funding"] == pytest.approx(s["net_pnl"], abs=1e-6)


def test_trade_stats_basic():
    s = A.trade_stats(pd.Series([2.0, -1.0, -1.0, 4.0]))
    assert s["win_rate"] == 0.5 and s["profit_factor"] == 3.0 and s["payoff_ratio"] == 3.0
    assert A.streaks(pd.Series([1, -1, -1, -1, 2, 3]))["max_loss_streak"] == 3


def test_every_analysis_runs(demo):
    tx, rounds, cp, kl = demo
    days = A.daily_series(tx)
    assert days["date"].is_monotonic_increasing and days["drawdown_usdt"].max() <= 1e-9
    for frame in [A.by_symbol(rounds), A.by_direction(rounds), A.by_hour_weekday(rounds), A.by_duration(rounds),
                  A.by_size(rounds), A.after_loss_behaviour(rounds), A.overtrading(tx, rounds),
                  A.market_context(days, kl), A.by_leverage(cp)]:
        assert not frame.empty
    assert len(A.insights(tx, rounds, kl)) >= 5


def test_store_roundtrip(tmp_path, demo):
    tx, _, cp, kl = demo
    store = Store(tmp_path / "t.db")
    store.upsert_transactions(tx)
    store.upsert_transactions(tx)  # idempotent
    back = store.load_transactions()
    assert len(back) == len(tx)
    assert back["change"].sum() == pytest.approx(tx["change"].sum())
    assert (back["time"].reset_index(drop=True) == tx["time"].dt.floor("ms").reset_index(drop=True)).all()
    store.upsert_klines(kl)
    k = store.load_klines()
    assert len(k) == len(kl) and k["time"].iloc[-1] == kl["time"].iloc[-1]


def test_trading_scope_excludes_other_coins_and_spot():
    base = dict(category="linear", symbol="XUSDT", side="Buy", qty=0.0, size=0.0, price=0.0, cash_flow=0.0,
                fee=0.0, funding=0.0, cash_balance=0.0, order_id="", trade_id="", source="t")
    tx = pd.DataFrame([
        {**base, "id": "1", "time": "2026-01-01", "currency": "USDT", "type": "TRANSFER_IN", "change": 100.0},
        {**base, "id": "2", "time": "2026-01-02", "currency": "DOGS", "type": "TRANSFER_IN", "change": 60000.0},
        {**base, "id": "3", "time": "2026-01-03", "currency": "USDT", "type": "TRADE", "category": "spot",
         "change": -50.0, "fee": -0.05},
        {**base, "id": "4", "time": "2026-01-04", "currency": "USDT", "type": "CURRENCY_BUY", "change": 13.0},
    ])
    tx["time"] = pd.to_datetime(tx["time"], utc=True)
    scoped = trading_scope(tx, "USDT")
    assert set(scoped["currency"]) == {"USDT"}
    assert scoped.loc[scoped["id"] == "3", "type"].item() == "SPOT_TRADE"
    s = A.account_summary(scoped, build_round_trips(scoped))
    assert s["net_pnl"] == 0 and s["deposits"] == pytest.approx(113.0)


# ------------------------------------------------------------ web report
from bybit_analytics import webapi  # noqa: E402
from bybit_analytics.report import Dataset, build_report, decode_dataset, encode_dataset, prepare  # noqa: E402


@pytest.fixture(scope="module")
def demo_ds():
    tx, cp, kl = generate(days=40, seed=3)
    return Dataset(tx, cp, kl, {"kind": "demo"})


def test_dataset_roundtrip_preserves_analysis(demo_ds):
    back = decode_dataset(encode_dataset(demo_ds))
    assert len(back.tx) == len(demo_ds.tx)
    assert back.tx["time"].dt.tz is not None
    assert (back.tx["category"] == demo_ds.tx["category"]).all()  # empty strings stay strings
    a = build_report(prepare(demo_ds))["summary"]
    b = build_report(prepare(back))["summary"]
    for k in ["net_pnl", "trades", "win_rate", "max_drawdown_usdt"]:
        assert a[k] == pytest.approx(b[k])


def test_report_filters_and_empty_selection(demo_ds):
    p = prepare(demo_ds)
    full = build_report(p)
    assert not full["empty"] and full["verdict"]["tone"] in {"positive", "negative"}
    assert full["summary"]["trades"] == len(full["trades"]["rows"])
    one = full["meta"]["symbols"][0]
    sub = build_report(p, symbols=[one])
    assert set(r[0] for r in sub["trades"]["rows"]) == {one}
    assert build_report(p, start="2001-01-01", end="2001-01-02")["empty"] is True
    with pytest.raises(Exception):
        build_report(p, start="not a date")


def test_handle_csv_then_dataset(monkeypatch):
    monkeypatch.setattr(webapi, "_klines_for", lambda tx, client=None: pd.DataFrame())
    csv = "\n".join([CSV_HEADER, *CSV_ROWS])
    status, body, _ = webapi.handle({"source": "csv", "csv": csv})
    assert status == 200 and body["report"]["summary"]["trades"] == 1
    status, body2, _ = webapi.handle({"source": "dataset", "dataset": body["dataset"]})
    assert status == 200 and body2["report"]["summary"]["net_pnl"] == pytest.approx(body["report"]["summary"]["net_pnl"])
    assert "dataset" not in body2


def test_handle_rejects_bad_input():
    assert webapi.handle({"source": "api", "credentials": {}})[0] == 400
    assert webapi.handle({"source": "local"}, allow_local=False)[0] == 404
    assert webapi.handle({"source": "nope"})[0] == 400
    assert webapi.handle({"source": "dataset", "dataset": "garbage"})[0] == 400
