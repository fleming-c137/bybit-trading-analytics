"""Streamlit dashboard.  Run:  streamlit run dashboard/app.py"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bybit_analytics import analysis as A  # noqa: E402
from bybit_analytics import charts as C  # noqa: E402
from bybit_analytics.config import get_settings  # noqa: E402
from bybit_analytics.storage import Store  # noqa: E402
from bybit_analytics.trades import build_round_trips  # noqa: E402
from bybit_analytics.transform import main_currency, normalize_csv, trading_scope  # noqa: E402

st.set_page_config(page_title="Bybit Trading Analytics", page_icon="📈", layout="wide")

settings = get_settings()
DEMO_DB = ROOT / "data" / "demo.db"


# ------------------------------------------------------------------ data
@st.cache_data(show_spinner=False)
def load_db(path: str, _mtime: float):
    store = Store(path)
    return store.load_transactions(), store.load_closed_pnl(), store.load_klines(), store.get_meta("wallet"), store.get_meta("last_sync")


@st.cache_data(show_spinner=False)
def load_csv(file) -> pd.DataFrame:
    return normalize_csv(pd.read_csv(file))


@st.cache_data(show_spinner=False)
def rounds_for(tx: pd.DataFrame) -> pd.DataFrame:
    return build_round_trips(tx)


def ensure_demo() -> None:
    if not DEMO_DB.exists():
        from bybit_analytics.demo import generate
        store = Store(DEMO_DB)
        tx, cp, kl = generate()
        store.upsert_transactions(tx)
        store.upsert_closed_pnl(cp)
        store.upsert_klines(kl)


with st.sidebar:
    st.header("Data source")
    has_db = settings.db_path.exists()
    options = (["Bybit API (synced)"] if has_db or settings.has_credentials else []) + ["Upload CSV export", "Demo data"]
    source = st.radio("Source", options, label_visibility="collapsed")

    tx = cp = kl = None
    wallet = last_sync = None
    if source == "Bybit API (synced)":
        if settings.has_credentials and st.button("🔄 Sync from Bybit now", use_container_width=True):
            from bybit_analytics.sync import sync_all
            with st.status("Syncing…", expanded=True) as status:
                sync_all(settings, progress=st.write)
                status.update(label="Sync complete", state="complete")
            st.cache_data.clear()
        if settings.db_path.exists():
            tx, cp, kl, wallet, last_sync = load_db(str(settings.db_path), settings.db_path.stat().st_mtime)
        if last_sync:
            st.caption(f"Last sync: {pd.Timestamp(last_sync):%Y-%m-%d %H:%M} UTC")
        if not settings.has_credentials:
            st.caption("No API key in .env — showing previously synced data.")
    elif source == "Upload CSV export":
        up = st.file_uploader("Bybit → Orders → Unified Trading Account → Transaction log → Export", type="csv")
        if up is not None:
            tx = load_csv(up)
            cp, kl = pd.DataFrame(), pd.DataFrame()
    else:
        ensure_demo()
        tx, cp, kl, wallet, last_sync = load_db(str(DEMO_DB), DEMO_DB.stat().st_mtime)
        st.caption("Synthetic data — no real account.")

if tx is None or tx.empty:
    st.title("📈 Bybit Trading Analytics")
    st.info("Pick a data source in the sidebar. Run `python -m bybit_analytics sync` after adding a read-only "
            "API key to `.env`, upload a CSV export, or explore the demo data.")
    st.stop()

# ---------------------------------------------------------------- filters
currencies = sorted(tx["currency"].replace("", pd.NA).dropna().unique())
default_ccy = main_currency(tx)
with st.sidebar:
    st.header("Filters")
    currency = st.selectbox("Settlement currency", currencies, index=currencies.index(default_ccy),
                            help="Coins can't be added together, so the analysis runs on one currency at a time. "
                                 "Spot trades and conversions count as balance movements, not trading PnL.")
tx = trading_scope(tx, currency)
all_rounds = rounds_for(tx)
min_d, max_d = tx["time"].min().date(), tx["time"].max().date()
with st.sidebar:
    date_range = st.date_input("Date range (UTC)", (min_d, max_d), min_value=min_d, max_value=max_d)
    symbols = sorted(all_rounds["symbol"].unique())
    picked = st.multiselect("Symbols", symbols, placeholder="All symbols")
    st.divider()
    st.caption("All times UTC. PnL in USDT. A *trade* is a round trip: flat → position → flat.")

if isinstance(date_range, tuple) and len(date_range) == 2:
    lo = pd.Timestamp(date_range[0], tz="UTC")
    hi = pd.Timestamp(date_range[1], tz="UTC") + pd.Timedelta(days=1)
    tx_f = tx[(tx["time"] >= lo) & (tx["time"] < hi)]
    rounds = all_rounds[(all_rounds["open_time"] >= lo) & (all_rounds["open_time"] < hi)]
else:
    tx_f, rounds = tx, all_rounds
if picked:
    flows = A.is_flow_type(tx_f["type"])
    tx_f = tx_f[flows | tx_f["symbol"].isin(picked)]
    rounds = rounds[rounds["symbol"].isin(picked)]
if tx_f.empty or A.closed(rounds).empty:
    st.warning("No closed trades in this selection.")
    st.stop()

summary = A.account_summary(tx_f, rounds)
days = A.daily_series(tx_f)
breakeven = 1 / (1 + summary["payoff_ratio"]) if summary["payoff_ratio"] == summary["payoff_ratio"] else None


def kpi(col, label, value, help=None, delta=None):
    col.metric(label, value, delta=delta, help=help, delta_color="off")


# ----------------------------------------------------------------- header
st.title("📈 Bybit Trading Analytics")
st.caption(f"{summary['start']:%b %d, %Y} → {summary['end']:%b %d, %Y} · {summary['trades']} closed trades · "
           f"{summary['symbols_traded']} symbols · {summary['active_days']} active of {summary['days']} days")

c = st.columns(6)
kpi(c[0], "Net PnL", f"{summary['net_pnl']:+,.2f}", "Wallet change excluding transfers (USDT)")
kpi(c[1], "Return on deposits", f"{summary['return_on_deposits']:+.1%}", "Net PnL ÷ total deposited")
kpi(c[2], "Win rate", f"{summary['win_rate']:.0%}",
    f"Break-even win rate at your payoff ratio: {breakeven:.0%}" if breakeven else None,
    delta=f"break-even {breakeven:.0%}" if breakeven else None)
kpi(c[3], "Profit factor", f"{summary['profit_factor']:.2f}", "Gross wins ÷ gross losses (>1 = profitable)")
kpi(c[4], "Expectancy / trade", f"{summary['expectancy']:+.3f}", "Average net PnL per closed trade")
kpi(c[5], "Max drawdown", f"{summary['max_drawdown_usdt']:,.2f}", "Largest fall from peak cumulative PnL (USDT)")

tabs = st.tabs(["Overview", "Trade quality", "Symbols", "Timing & behaviour", "Risk", "Market context", "Data"])

# ---------------------------------------------------------------- overview
with tabs[0]:
    st.subheader("Key findings")
    for line in A.insights(tx_f, rounds, kl):
        st.markdown(f"- {line}")
    left, right = st.columns([3, 2])
    left.plotly_chart(C.equity_curve(days), use_container_width=True)
    right.plotly_chart(C.waterfall(A.pnl_waterfall(summary)), use_container_width=True)
    st.plotly_chart(C.daily_pnl(days), use_container_width=True)
    c = st.columns(4)
    kpi(c[0], "Deposited", f"{summary['deposits']:,.2f}")
    kpi(c[1], "Withdrawn", f"{-summary['withdrawals']:,.2f}")
    kpi(c[2], "Fees paid", f"{-summary['fees']:,.2f}", f"Effective rate {summary['effective_fee_rate']:.3%} of volume")
    kpi(c[3], "Funding", f"{summary['funding']:+,.3f}")

# ----------------------------------------------------------- trade quality
with tabs[1]:
    st.markdown("**Is there an edge?** Win rate alone means nothing — it must be read against the payoff ratio.")
    c = st.columns(5)
    kpi(c[0], "Avg win", f"{summary['avg_win']:+,.3f}")
    kpi(c[1], "Avg loss", f"{summary['avg_loss']:+,.3f}")
    kpi(c[2], "Payoff ratio", f"{summary['payoff_ratio']:.2f}", "Avg win ÷ |avg loss|")
    kpi(c[3], "Longest losing streak", f"{summary['max_loss_streak']}")
    kpi(c[4], "Median hold", f"{summary['median_hold_min']:.1f} min")
    left, right = st.columns(2)
    left.plotly_chart(C.pnl_distribution(rounds), use_container_width=True)
    right.plotly_chart(C.direction_bars(A.by_direction(rounds)), use_container_width=True)
    st.plotly_chart(C.trade_scatter(rounds), use_container_width=True)
    dur = A.by_duration(rounds)
    left, right = st.columns(2)
    left.plotly_chart(C.bucket_bars(dur, "hold", "Net PnL by holding time", x_title="Holding time"), use_container_width=True)
    right.plotly_chart(C.win_rate_bars(dur, "hold", "Win rate by holding time", breakeven), use_container_width=True)
    st.caption("Median holding time of winners vs losers (minutes)")
    st.dataframe(A.winners_vs_losers_hold(rounds).round(1), hide_index=True)
    size = A.by_size(rounds)
    if not size.empty:
        st.plotly_chart(C.bucket_bars(size, "size_bucket", "Does position size help or hurt? (entry notional quintiles)",
                                      x_title="Position size quintile (avg USDT notional)"), use_container_width=True)

# ---------------------------------------------------------------- symbols
with tabs[2]:
    sym = A.by_symbol(rounds)
    conc = A.loss_concentration(sym, 5)
    c = st.columns(3)
    kpi(c[0], "Symbols traded", f"{len(sym)}")
    kpi(c[1], "Net profitable symbols", f"{conc['winning_symbols']}")
    kpi(c[2], "Top-5 share of losses", f"{conc['share']:.0%}" if conc["share"] == conc["share"] else "–")
    left, right = st.columns([3, 2])
    left.plotly_chart(C.symbol_bars(sym), use_container_width=True)
    right.plotly_chart(C.loss_pareto(sym), use_container_width=True)
    right.plotly_chart(C.symbol_scatter(sym), use_container_width=True)
    st.dataframe(
        sym.sort_values("net_pnl"), hide_index=True, use_container_width=True,
        column_config={
            "win_rate": st.column_config.ProgressColumn("win rate", format="percent", min_value=0, max_value=1),
            "net_pnl": st.column_config.NumberColumn("net PnL", format="%+.2f"),
            "avg_pnl": st.column_config.NumberColumn("avg PnL", format="%+.3f"),
            "volume": st.column_config.NumberColumn("volume", format="%.0f"),
        },
    )

# ------------------------------------------------------- timing/behaviour
with tabs[3]:
    st.plotly_chart(C.hour_weekday_heatmap(A.by_hour_weekday(rounds)), use_container_width=True)
    left, right = st.columns(2)
    hrs = A.by_hour(rounds)
    left.plotly_chart(C.bucket_bars(hrs, "hour", "Net PnL by hour opened (UTC)", x_title="Hour (UTC)"), use_container_width=True)
    ot = A.overtrading(tx_f, rounds)
    right.plotly_chart(C.overtrading_scatter(ot), use_container_width=True)

    st.subheader("Tilt check: what happens right after a loss?")
    window = st.slider("“Right after” means within … minutes of the previous trade closing", 1, 120, 15)
    tilt = A.after_loss_behaviour(rounds, window)
    left, right = st.columns(2)
    left.plotly_chart(C.bucket_bars(tilt, "context", "Net PnL by context"), use_container_width=True)
    right.plotly_chart(C.win_rate_bars(tilt, "context", "Win rate by context", breakeven), use_container_width=True)
    if not ot.empty:
        ob = ot.groupby("trade_bucket", observed=True)["pnl"].agg(days="size", avg_daily_pnl="mean", total="sum").reset_index()
        st.caption("Daily PnL by number of trades that day")
        st.dataframe(ob.round(2), hide_index=True)

# -------------------------------------------------------------------- risk
with tabs[4]:
    c = st.columns(5)
    kpi(c[0], "Max drawdown", f"{summary['max_drawdown_usdt']:,.2f}")
    kpi(c[1], "Days under water", f"{summary['max_drawdown_days']}")
    kpi(c[2], "Worst day", f"{summary['worst_day']:+,.2f}")
    kpi(c[3], "Liquidations", f"{summary['liquidations']}", f"Cost {summary['liquidation_pnl']:,.2f} USDT")
    kpi(c[4], "Green days", f"{summary['green_day_rate']:.0%}")
    st.plotly_chart(C.drawdown(days), use_container_width=True)
    liq = A.closed(rounds)[A.closed(rounds)["liquidated"]]
    if not liq.empty:
        st.caption("Liquidated positions")
        st.dataframe(liq[["symbol", "direction", "open_time", "close_time", "duration_min", "entry_notional", "net_pnl"]]
                     .sort_values("net_pnl"), hide_index=True, use_container_width=True)
    lev = A.by_leverage(cp)
    if not lev.empty:
        left, right = st.columns(2)
        left.plotly_chart(C.bucket_bars(lev.assign(gross_pnl=0, fees=0, funding=0), "lev_bucket",
                                        "Net PnL by leverage", x_title="Leverage"), use_container_width=True)
        right.plotly_chart(C.win_rate_bars(lev, "lev_bucket", "Win rate by leverage", breakeven), use_container_width=True)
    else:
        st.caption("Leverage analysis needs closed-PnL data from the API (not included in CSV exports).")

# ------------------------------------------------------------------ market
with tabs[5]:
    mc = A.market_context(days, kl) if kl is not None and not kl.empty else pd.DataFrame()
    if mc.empty or len(mc) < 3:
        st.info("Market context needs BTC daily candles — they're fetched automatically on `sync` / `import-csv` "
                "(public endpoint, no key needed).")
    else:
        corr = mc["pnl"].corr(mc["btc_return"])
        c = st.columns(3)
        kpi(c[0], "Correlation with BTC daily return", f"{corr:+.2f}")
        kpi(c[1], "Avg PnL on BTC up days", f"{mc.loc[mc['btc_return'] > 0, 'pnl'].mean():+,.2f}")
        kpi(c[2], "Avg PnL on BTC down days", f"{mc.loc[mc['btc_return'] <= 0, 'pnl'].mean():+,.2f}")
        left, right = st.columns(2)
        left.plotly_chart(C.market_scatter(mc), use_container_width=True)
        right.plotly_chart(C.btc_with_pnl(mc), use_container_width=True)
        for col, title in [("btc_move", "BTC daily move"), ("btc_vol", "BTC intraday volatility")]:
            if col in mc:
                g = mc.groupby(col, observed=True)["pnl"].agg(days="size", avg_pnl="mean", total="sum").reset_index()
                st.caption(f"Your daily PnL by {title}")
                st.dataframe(g.round(2), hide_index=True)

# -------------------------------------------------------------------- data
with tabs[6]:
    st.caption("Round-trip trades reconstructed from the transaction log")
    st.dataframe(rounds, hide_index=True, use_container_width=True)
    st.download_button("Download trades CSV", rounds.to_csv(index=False), "round_trips.csv", "text/csv")
    with st.expander("Raw transaction log"):
        st.dataframe(tx_f, hide_index=True, use_container_width=True)
    if wallet:
        st.caption(f"Wallet snapshot: total equity {float(wallet.get('totalEquity') or 0):,.2f} USD")
