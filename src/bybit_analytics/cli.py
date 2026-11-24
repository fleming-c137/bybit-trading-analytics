"""Command line entry point.

    python -m bybit_analytics sync [--days N]     # pull from the Bybit API
    python -m bybit_analytics import-csv FILE     # load a Bybit CSV export
    python -m bybit_analytics demo                # generate a synthetic demo database
    python -m bybit_analytics report              # print key findings
    python -m bybit_analytics serve               # web dashboard on http://localhost:8000
    python -m bybit_analytics publish             # snapshot for the hosted dashboard
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import PROJECT_ROOT, get_settings
from .storage import Store


def _store(args) -> Store:
    return Store(args.db or get_settings().db_path)


def cmd_sync(args) -> int:
    from .sync import sync_all
    settings = get_settings()
    if args.db:
        settings = settings.__class__(settings.api_key, settings.api_secret, settings.testnet, Path(args.db))
    if not settings.has_credentials:
        print("No API key found. Copy .env.example to .env and add a READ-ONLY Bybit API key.", file=sys.stderr)
        return 1
    sync_all(settings, days=args.days)
    return 0


def cmd_import_csv(args) -> int:
    from .sync import import_csv, sync_market_context
    store = _store(args)
    for path in args.files:
        n = import_csv(path, store)
        print(f"Imported {n} rows from {path}")
    if not args.no_market:
        try:
            print(f"Fetched {sync_market_context(store)} BTC candles for market context")
        except Exception as exc:  # offline is fine
            print(f"Skipped market context ({exc})")
    return 0


def cmd_demo(args) -> int:
    from .demo import generate
    path = Path(args.db) if args.db else PROJECT_ROOT / "data" / "demo.db"
    store = Store(path)
    store.clear()
    tx, cp, kl = generate(days=args.days, seed=args.seed)
    store.upsert_transactions(tx)
    store.upsert_closed_pnl(cp)
    store.upsert_klines(kl)
    store.set_meta("demo", True)
    print(f"Demo database written to {path} ({len(tx)} transactions, {len(cp)} closed positions)")
    return 0


def cmd_report(args) -> int:
    from . import analysis
    from .trades import build_round_trips
    store = _store(args)
    tx = store.load_transactions()
    if tx.empty:
        print("No data yet. Run `sync`, `import-csv` or `demo` first.", file=sys.stderr)
        return 1
    from .transform import main_currency, trading_scope
    tx = trading_scope(tx, args.currency or main_currency(tx))
    rounds = build_round_trips(tx)
    s = analysis.account_summary(tx, rounds)
    print(f"Period: {s['start']:%Y-%m-%d} -> {s['end']:%Y-%m-%d}  |  {s['trades']} closed trades on {s['symbols_traded']} symbols\n")
    for line in analysis.insights(tx, rounds, store.load_klines()):
        print(f"  • {line}")
    if args.export:
        out = Path(args.export)
        out.mkdir(parents=True, exist_ok=True)
        rounds.to_csv(out / "round_trips.csv", index=False)
        analysis.by_symbol(rounds).to_csv(out / "by_symbol.csv", index=False)
        analysis.daily_series(tx).to_csv(out / "daily.csv", index=False)
        print(f"\nExported tables to {out}")
    return 0


def cmd_serve(args) -> int:
    from .server import serve
    serve(args.host, args.port, open_browser=not args.no_browser)
    return 0


def cmd_publish(args) -> int:
    """Write a snapshot of the synced account for the hosted dashboard.

    Your API key is only used locally (by `sync`); the hosted site reads this file.
    """
    from datetime import datetime, timezone

    from .report import Dataset, encode_dataset
    from .webapi import SNAPSHOT_PATH
    store = _store(args)
    tx = store.load_transactions()
    if tx.empty:
        print("Nothing to publish. Run `sync` first.", file=sys.stderr)
        return 1
    tx = tx.assign(order_id="", trade_id="")  # not needed for analysis
    meta = {"kind": "owner", "label": args.label, "detail": "Published snapshot of a real account",
            "published_at": datetime.now(timezone.utc).isoformat(), "last_sync": store.get_meta("last_sync")}
    out = Path(args.out) if args.out else SNAPSHOT_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(encode_dataset(Dataset(tx, store.load_closed_pnl(), store.load_klines(), meta)))
    print(f"Wrote {out} ({out.stat().st_size / 1e6:.1f} MB, {len(tx):,} transactions).")
    print("Anyone can download this file once you push it: it contains every fill, fee, transfer and balance.")
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="bybit-analytics", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", help="SQLite path (default: BYBIT_DB_PATH or data/bybit.db)")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("sync", help="Pull history from the Bybit V5 API")
    p.add_argument("--days", type=int, help="Look-back window (default: resume, or full 2 years on first run)")
    p.set_defaults(func=cmd_sync)

    p = sub.add_parser("import-csv", help="Import Bybit 'Asset Change Details' CSV export(s)")
    p.add_argument("files", nargs="+")
    p.add_argument("--no-market", action="store_true", help="Don't fetch BTC candles")
    p.set_defaults(func=cmd_import_csv)

    p = sub.add_parser("demo", help="Write a synthetic demo database to data/demo.db")
    p.add_argument("--days", type=int, default=75)
    p.add_argument("--seed", type=int, default=7)
    p.set_defaults(func=cmd_demo)

    p = sub.add_parser("report", help="Print key findings")
    p.add_argument("--currency", help="Settlement currency to analyse (default: the one you trade most, e.g. USDT)")
    p.add_argument("--export", metavar="DIR", help="Also write round trips / symbol / daily tables as CSV")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("serve", help="Run the web dashboard locally")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--no-browser", action="store_true")
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("publish", help="Write snapshots/owner.json.gz for the hosted dashboard")
    p.add_argument("--label", default="Published account", help="Name shown in the data-source list")
    p.add_argument("--out", help="Output path (default: snapshots/owner.json.gz)")
    p.set_defaults(func=cmd_publish)

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
