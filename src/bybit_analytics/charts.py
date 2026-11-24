"""Plotly figures. Layout chrome is left to the host theme (Streamlit light/dark);
only mark colors are fixed here, from a colorblind-validated palette.

Colour jobs
-----------
* polarity (PnL gain/loss): diverging blue (+) / red (-)
* identity (Long/Short, series): categorical slots in fixed order
* magnitude (heatmaps): diverging blue<->gray<->red around zero
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

GAIN = "#2a78d6"
LOSS = "#e34948"
NEUTRAL = "#8a8985"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
DIRECTION_COLORS = {"Long": SERIES[0], "Short": SERIES[1]}
DIVERGING = [[0.0, "#b3261e"], [0.25, "#e34948"], [0.5, "#d9d8d4"], [0.75, "#2a78d6"], [1.0, "#104281"]]


def _layout(fig: go.Figure, title: str | None = None, height: int = 380, **kw) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=15)) if title else None,
        height=height,
        margin=dict(l=8, r=8, t=48 if title else 16, b=8),
        hovermode=kw.pop("hovermode", "closest"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        bargap=0.25,
        **kw,
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridwidth=1, zeroline=True, zerolinewidth=1)
    return fig


def _pnl_colors(values) -> list[str]:
    return [GAIN if v >= 0 else LOSS for v in values]


# --------------------------------------------------------------- overview
def equity_curve(days: pd.DataFrame) -> go.Figure:
    """Cumulative PnL vs cumulative net deposits, same USDT axis."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=days["date"], y=days["cum_flows"], name="Net deposits", mode="lines",
        line=dict(color=NEUTRAL, width=2, dash="dot"),
        hovertemplate="%{x|%b %d}<br>Net deposits %{y:,.2f} USDT<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=days["date"], y=days["balance"], name="Wallet balance", mode="lines",
        line=dict(color=SERIES[0], width=2),
        hovertemplate="%{x|%b %d}<br>Balance %{y:,.2f} USDT<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=days["date"], y=days["cum_pnl"], name="Cumulative PnL", mode="lines",
        line=dict(color=SERIES[1], width=2),
        hovertemplate="%{x|%b %d}<br>Cumulative PnL %{y:+,.2f} USDT<extra></extra>",
    ))
    return _layout(fig, "Equity: what you put in vs. what you made", hovermode="x unified", yaxis_title="USDT")


def daily_pnl(days: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=days["date"], y=days["pnl"], marker_color=_pnl_colors(days["pnl"]), marker_line_width=0,
        customdata=np.c_[days["gross"], days["fees"], days["funding"], days["fills"]],
        hovertemplate=("%{x|%a %b %d}<br><b>Net %{y:+,.2f}</b><br>Gross %{customdata[0]:+,.2f}"
                       "<br>Fees %{customdata[1]:+,.2f}<br>Funding %{customdata[2]:+,.3f}"
                       "<br>Fills %{customdata[3]:.0f}<extra></extra>"),
    ))
    return _layout(fig, "Daily net PnL", yaxis_title="USDT")


def drawdown(days: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Scatter(
        x=days["date"], y=days["drawdown_usdt"], fill="tozeroy", mode="lines",
        line=dict(color=LOSS, width=2), fillcolor="rgba(227,73,72,0.18)",
        hovertemplate="%{x|%b %d}<br>%{y:,.2f} USDT below peak<extra></extra>",
    ))
    return _layout(fig, "Drawdown from peak cumulative PnL", height=280, yaxis_title="USDT")


def waterfall(wf: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Waterfall(
        x=wf["component"], y=wf["value"], measure=wf["measure"],
        text=[f"{v:+,.2f}" for v in wf["value"]], textposition="outside",
        increasing=dict(marker=dict(color=GAIN)), decreasing=dict(marker=dict(color=LOSS)),
        totals=dict(marker=dict(color=NEUTRAL)), connector=dict(line=dict(width=1, color=NEUTRAL)),
        hovertemplate="%{x}: %{y:+,.2f} USDT<extra></extra>",
    ))
    return _layout(fig, "Where the PnL went", yaxis_title="USDT")


# --------------------------------------------------------------- trades
def pnl_distribution(rounds: pd.DataFrame) -> go.Figure:
    c = rounds[~rounds["is_open"]]
    fig = go.Figure()
    for label, sub, color in [("Losers", c[c["net_pnl"] <= 0], LOSS), ("Winners", c[c["net_pnl"] > 0], GAIN)]:
        fig.add_trace(go.Histogram(
            x=sub["net_pnl"], name=label, marker_color=color, nbinsx=60, marker_line_width=0,
            hovertemplate="%{x} USDT<br>%{y} trades<extra></extra>",
        ))
    fig.update_layout(barmode="overlay")
    fig.update_traces(opacity=0.85)
    return _layout(fig, "Distribution of trade results", xaxis_title="Net PnL per trade (USDT)", yaxis_title="Trades")


def trade_scatter(rounds: pd.DataFrame) -> go.Figure:
    c = rounds[~rounds["is_open"]].dropna(subset=["duration_min"])
    fig = go.Figure()
    for direction, sub in c.groupby("direction"):
        fig.add_trace(go.Scatter(
            x=sub["duration_min"], y=sub["net_pnl"], mode="markers", name=direction,
            marker=dict(size=8, color=DIRECTION_COLORS.get(direction, NEUTRAL), opacity=0.7,
                        line=dict(width=1, color="rgba(255,255,255,0.8)"),
                        symbol=np.where(sub["liquidated"], "x", "circle")),
            customdata=np.c_[sub["symbol"], sub["entry_notional"], sub["liquidated"].map({True: "LIQUIDATED", False: ""})],
            hovertemplate=("%{customdata[0]}<br>Held %{x:.1f} min<br>Net %{y:+,.3f} USDT"
                           "<br>Notional %{customdata[1]:,.0f}<br>%{customdata[2]}<extra></extra>"),
        ))
    fig.update_xaxes(type="log")
    return _layout(fig, "Every trade: holding time vs. result (× = liquidation)",
                   xaxis_title="Holding time (minutes, log scale)", yaxis_title="Net PnL (USDT)", height=420)


def bucket_bars(df: pd.DataFrame, x: str, title: str, value: str = "net_pnl", x_title: str | None = None) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=df[x].astype(str), y=df[value], marker_color=_pnl_colors(df[value]), marker_line_width=0,
        customdata=np.c_[df["trades"], df["win_rate"] * 100, df["avg_pnl"]],
        hovertemplate=("%{x}<br><b>%{y:+,.2f} USDT</b><br>%{customdata[0]:.0f} trades · "
                       "%{customdata[1]:.0f}% win<br>avg %{customdata[2]:+,.3f}/trade<extra></extra>"),
    ))
    return _layout(fig, title, xaxis_title=x_title, yaxis_title="Net PnL (USDT)", height=340)


def win_rate_bars(df: pd.DataFrame, x: str, title: str, breakeven: float | None = None) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=df[x].astype(str), y=df["win_rate"] * 100, marker_color=SERIES[0], marker_line_width=0,
        customdata=df["trades"], hovertemplate="%{x}<br>%{y:.0f}% win · %{customdata} trades<extra></extra>",
    ))
    if breakeven is not None and breakeven == breakeven:
        fig.add_hline(y=breakeven * 100, line=dict(color=LOSS, dash="dash", width=1),
                      annotation_text=f"break-even {breakeven:.0%}", annotation_position="top left")
    return _layout(fig, title, yaxis_title="Win rate (%)", height=300, yaxis_range=[0, 100])


# -------------------------------------------------------------- symbols
def symbol_bars(sym: pd.DataFrame, n: int = 12) -> go.Figure:
    worst, best = sym.nsmallest(n, "net_pnl"), sym.nlargest(n, "net_pnl")
    top = pd.concat([worst, best]).drop_duplicates("symbol").sort_values("net_pnl")
    fig = go.Figure(go.Bar(
        y=top["symbol"], x=top["net_pnl"], orientation="h",
        marker_color=_pnl_colors(top["net_pnl"]), marker_line_width=0,
        customdata=np.c_[top["trades"], top["win_rate"] * 100, top["fees"]],
        hovertemplate=("%{y}<br><b>%{x:+,.2f} USDT</b><br>%{customdata[0]:.0f} trades · "
                       "%{customdata[1]:.0f}% win<br>fees %{customdata[2]:,.2f}<extra></extra>"),
    ))
    return _layout(fig, f"Best and worst {n} symbols", xaxis_title="Net PnL (USDT)", height=max(360, 22 * len(top)))


def symbol_scatter(sym: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Scatter(
        x=sym["trades"], y=sym["net_pnl"], mode="markers",
        marker=dict(size=np.clip(np.sqrt(sym["volume"].clip(lower=0)) / 4, 8, 40),
                    color=_pnl_colors(sym["net_pnl"]), opacity=0.75,
                    line=dict(width=1, color="rgba(255,255,255,0.8)")),
        text=sym["symbol"],
        customdata=np.c_[sym["win_rate"] * 100, sym["volume"]],
        hovertemplate=("%{text}<br>%{x} trades · %{customdata[0]:.0f}% win<br>"
                       "<b>%{y:+,.2f} USDT</b><br>volume %{customdata[1]:,.0f}<extra></extra>"),
    ))
    fig.update_xaxes(type="log")
    return _layout(fig, "Do you overtrade the symbols you lose on? (bubble = volume)",
                   xaxis_title="Number of trades (log)", yaxis_title="Net PnL (USDT)", height=420)


def loss_pareto(sym: pd.DataFrame) -> go.Figure:
    losers = sym[sym["net_pnl"] < 0].sort_values("net_pnl").reset_index(drop=True)
    share = losers["net_pnl"].cumsum() / losers["net_pnl"].sum() * 100
    fig = go.Figure(go.Scatter(
        x=np.arange(1, len(losers) + 1), y=share, mode="lines+markers", line=dict(color=LOSS, width=2),
        marker=dict(size=8), text=losers["symbol"],
        hovertemplate="Top %{x} losing symbols (%{text})<br>= %{y:.0f}% of all losses<extra></extra>",
    ))
    fig.add_hline(y=80, line=dict(color=NEUTRAL, dash="dot", width=1), annotation_text="80%")
    return _layout(fig, "Loss concentration (Pareto)", xaxis_title="Number of losing symbols",
                   yaxis_title="Cumulative share of losses (%)", height=340, yaxis_range=[0, 105])


# ----------------------------------------------------------- behaviour
def hour_weekday_heatmap(hw: pd.DataFrame, value: str = "net_pnl") -> go.Figure:
    from .analysis import WEEKDAYS
    grid = hw.pivot_table(index="weekday", columns="hour", values=value, aggfunc="sum", observed=False)
    grid = grid.reindex(index=WEEKDAYS, columns=range(24))
    counts = hw.pivot_table(index="weekday", columns="hour", values="trades", aggfunc="sum", observed=False)
    counts = counts.reindex(index=WEEKDAYS, columns=range(24)).fillna(0)
    lim = np.nanmax(np.abs(grid.to_numpy())) if np.isfinite(grid.to_numpy()).any() else 1
    fig = go.Figure(go.Heatmap(
        z=grid.to_numpy(), x=[f"{h:02d}" for h in range(24)], y=WEEKDAYS,
        colorscale=DIVERGING, zmid=0, zmin=-lim, zmax=lim, xgap=2, ygap=2,
        customdata=counts.to_numpy(), colorbar=dict(title="USDT", thickness=10),
        hovertemplate="%{y} %{x}:00 UTC<br><b>%{z:+,.2f} USDT</b><br>%{customdata:.0f} trades<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed", zeroline=False)
    return _layout(fig, "When do you make / lose money? (trade open time, UTC)", xaxis_title="Hour (UTC)", height=330)


def overtrading_scatter(ot: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Scatter(
        x=ot["trades"], y=ot["pnl"], mode="markers",
        marker=dict(size=10, color=_pnl_colors(ot["pnl"]), opacity=0.8, line=dict(width=1, color="rgba(255,255,255,0.8)")),
        customdata=ot["date"].dt.strftime("%a %b %d"),
        hovertemplate="%{customdata}<br>%{x:.0f} trades<br><b>%{y:+,.2f} USDT</b><extra></extra>",
    ))
    if len(ot) >= 3:
        m, b = np.polyfit(ot["trades"], ot["pnl"], 1)
        xs = np.linspace(ot["trades"].min(), ot["trades"].max(), 20)
        fig.add_trace(go.Scatter(x=xs, y=m * xs + b, mode="lines", line=dict(color=NEUTRAL, width=2, dash="dash"),
                                 hoverinfo="skip", name="trend"))
    fig.update_layout(showlegend=False)
    return _layout(fig, "Overtrading: trades per day vs. that day's PnL",
                   xaxis_title="Trades closed that day", yaxis_title="Daily net PnL (USDT)", height=380)


def direction_bars(d: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=d["direction"], y=d["net_pnl"], marker_color=[DIRECTION_COLORS.get(x, NEUTRAL) for x in d["direction"]],
        marker_line_width=0, text=[f"{v:+,.2f}" for v in d["net_pnl"]], textposition="outside",
        customdata=np.c_[d["trades"], d["win_rate"] * 100],
        hovertemplate="%{x}<br><b>%{y:+,.2f} USDT</b><br>%{customdata[0]:.0f} trades · %{customdata[1]:.0f}% win<extra></extra>",
    ))
    return _layout(fig, "Long vs. short", yaxis_title="Net PnL (USDT)", height=320)


# ------------------------------------------------------------- market
def market_scatter(mc: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Scatter(
        x=mc["btc_return"] * 100, y=mc["pnl"], mode="markers",
        marker=dict(size=10, color=_pnl_colors(mc["pnl"]), opacity=0.8, line=dict(width=1, color="rgba(255,255,255,0.8)")),
        customdata=mc["date"].dt.strftime("%a %b %d"),
        hovertemplate="%{customdata}<br>BTC %{x:+.2f}%<br><b>You %{y:+,.2f} USDT</b><extra></extra>",
    ))
    return _layout(fig, "Your daily PnL vs. BTC's daily move", xaxis_title="BTC daily return (%)",
                   yaxis_title="Your daily net PnL (USDT)", height=380)


def btc_with_pnl(mc: pd.DataFrame) -> go.Figure:
    """BTC price line with your trading days marked (one axis: price)."""
    fig = go.Figure(go.Scatter(
        x=mc["date"], y=mc["close"], mode="lines+markers", line=dict(color=NEUTRAL, width=2),
        marker=dict(size=np.clip(np.abs(mc["pnl"]) * 2, 8, 30), color=_pnl_colors(mc["pnl"]),
                    line=dict(width=1, color="rgba(255,255,255,0.8)")),
        customdata=mc["pnl"],
        hovertemplate="%{x|%b %d}<br>BTC %{y:,.0f}<br><b>You %{customdata:+,.2f} USDT</b><extra></extra>",
    ))
    return _layout(fig, "BTC price, with your daily result as dot size/colour", yaxis_title="BTC (USDT)", height=340)
