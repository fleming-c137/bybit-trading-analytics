/* Bybit Trading Analytics: dashboard client.
   Every number comes from /api/report (Python). This file only lays it out. */

const API = "/api/report";
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches || new URLSearchParams(location.search).has("still");

/* ------------------------------------------------------------- icons */
const ICONS = {
  overview: '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
  edge: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
  symbols: '<circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/>',
  timing: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  risk: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="M12 8v4"/><path d="M12 16h.01"/>',
  market: '<path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/>',
  trades: '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/><path d="M12 3v18"/>',
  owner: '<circle cx="12" cy="8" r="5"/><path d="M20 21a8 8 0 0 0-16 0"/>',
  demo: '<path d="M10 2v7.31"/><path d="M14 9.3V2"/><path d="M8.5 2h7"/><path d="M14 9.3a6.5 6.5 0 1 1-4 0"/><path d="M5.52 16h12.96"/>',
  api: '<circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6"/><path d="m15.5 7.5 3 3L22 7l-3-3"/>',
  csv: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M17 8l-5-5-5 5"/><path d="M12 3v12"/>',
  local: '<path d="M22 12H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/><path d="M6 16h.01"/><path d="M10 16h.01"/>',
  chev: '<path d="m6 9 6 6 6-6"/>',
  alert: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
  check: '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
  up: '<path d="M7 17 17 7"/><path d="M7 7h10v10"/>',
  down: '<path d="m7 7 10 10"/><path d="M17 7v10H7"/>',
  filter: '<path d="M22 3H2l8 9.46V19l4 2v-8.54z"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/><path d="M12 15V3"/>',
  calendar: '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
  clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  database: '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/>',
  eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  eyeOff: '<path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.4 10.4 0 0 1 12 5c6.5 0 10 7 10 7a13.2 13.2 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.5 13.5 0 0 0 2 12s3.5 7 10 7a9.7 9.7 0 0 0 5.39-1.61"/><path d="M2 2l20 20"/>',
};
const icon = (name, cls = "i") => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ""}</svg>`;

/* ------------------------------------------------------------ format */
const MINUS = "−";
const nfCache = {};
const nf = (d) => (nfCache[d] ??= new Intl.NumberFormat("en-US", { minimumFractionDigits: d, maximumFractionDigits: d }));
const isNum = (v) => typeof v === "number" && Number.isFinite(v);
const fmt = {
  num(v, d = 2, sign = false) {
    if (!isNum(v)) return "–";
    const s = nf(d).format(Math.abs(v));
    return (v < 0 ? MINUS : sign && v > 0 ? "+" : "") + s;
  },
  money(v, d = 2) { return fmt.num(v, d, true); },
  pct(v, d = 0, sign = false) { return isNum(v) ? fmt.num(v * 100, d, sign) + "%" : "–"; },
  int(v) { return isNum(v) ? nf(0).format(v) : "–"; },
  compact(v) {
    if (!isNum(v)) return "";
    if (v === 0) return "0";
    const a = Math.abs(v);
    const s = a >= 1e6 ? nf(1).format(a / 1e6) + "M" : a >= 1e4 ? nf(0).format(a / 1e3) + "k" : a >= 1e3 ? nf(1).format(a / 1e3) + "k" : a >= 10 ? nf(0).format(a) : nf(a >= 1 ? 1 : 2).format(a);
    return (v < 0 ? MINUS : "") + s;
  },
  dur(min) {
    if (!isNum(min)) return "–";
    if (min < 1) return "<1m";
    if (min < 60) return `${nf(0).format(min)}m`;
    if (min < 1440) return `${nf(1).format(min / 60)}h`;
    return `${nf(1).format(min / 1440)}d`;
  },
  date(ms, opts = { month: "short", day: "numeric", year: "numeric" }) {
    return isNum(ms) ? new Date(ms).toLocaleDateString("en-US", { ...opts, timeZone: "UTC" }) : "–";
  },
  dateTime(ms) {
    return isNum(ms) ? new Date(ms).toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "UTC" }) : "–";
  },
  iso(ms) { return isNum(ms) ? new Date(ms).toISOString().slice(0, 10) : ""; },
};

/* ------------------------------------------------------------- state */
const PAGES = [
  { id: "overview", label: "Overview", sub: "Is the account profitable after all costs, and why?" },
  { id: "edge", label: "Trade quality", sub: "Is there an edge per trade, and does holding time matter?" },
  { id: "symbols", label: "Symbols", sub: "Which markets create value and which destroy it?" },
  { id: "timing", label: "Timing & behaviour", sub: "When do results change, and is there tilt or overtrading?" },
  { id: "risk", label: "Risk", sub: "How deep and how long are the drawdowns?" },
  { id: "market", label: "Market context", sub: "Is the PnL just following Bitcoin?" },
  { id: "trades", label: "Trades", sub: "Every round trip reconstructed from the transaction log" },
];
const SOURCE_INFO = {
  owner: { label: "Published account", detail: "Real account snapshot" },
  demo: { label: "Demo account", detail: "Synthetic data" },
  local: { label: "This machine", detail: "Synced SQLite database" },
  api: { label: "Your API key", detail: "Read-only, nothing stored" },
  csv: { label: "Upload CSV export", detail: "Bybit transaction log" },
};
const state = {
  sources: null, source: null, page: "overview", report: null, dataset: null, reqId: 0,
  f: { currency: null, start: null, end: null, symbols: [], tilt: 15 },
  ui: { tradeSort: { key: "close_time", dir: "desc" }, tradePage: 0, tradeQuery: "", tradeOutcome: "all",
        symSort: { key: "net_pnl", dir: "asc" } },
};

/* ------------------------------------------------------------ charts */
const T = {
  text1: "#f2efe9", text2: "rgba(242,239,233,0.76)", text3: "rgba(242,239,233,0.56)",
  grid: "rgba(255,255,255,0.07)", axis: "rgba(255,255,255,0.16)",
  gain: "#3987e5", loss: "#e66767", mid: "#383835", accent: "#9085e9", font: "Inter, system-ui, sans-serif",
};
const charts = new Map();
const pending = new Map();

function tooltipBase(extra = {}) {
  return {
    backgroundColor: "rgba(14,20,34,0.94)", borderColor: "rgba(255,255,255,0.14)", borderWidth: 1,
    padding: [8, 12], textStyle: { color: T.text1, fontSize: 12, fontFamily: T.font },
    extraCssText: "border-radius:10px;box-shadow:0 10px 28px rgba(0,0,0,.4);", confine: true, ...extra,
  };
}
function baseOption(opt) {
  return {
    animation: !reduceMotion, animationDuration: 450, animationEasing: "cubicOut",
    textStyle: { fontFamily: T.font, color: T.text2 },
    grid: { left: 6, right: 14, top: 14, bottom: 6, containLabel: true },
    ...opt,
    tooltip: tooltipBase(opt.tooltip || {}),
  };
}
const valueAxis = (formatter = fmt.compact, extra = {}) => ({
  type: "value", axisLabel: { color: T.text3, formatter, fontSize: 11 }, splitLine: { lineStyle: { color: T.grid } },
  axisLine: { show: false }, axisTick: { show: false }, ...extra,
});
const catAxis = (data, extra = {}) => ({
  type: "category", data, axisLine: { lineStyle: { color: T.axis } }, axisTick: { show: false },
  axisLabel: { color: T.text3, fontSize: 11 }, ...extra,
});
const timeAxis = (extra = {}) => ({
  type: "time", axisLine: { lineStyle: { color: T.axis } }, axisTick: { show: false }, splitLine: { show: false },
  axisLabel: { color: T.text3, fontSize: 11, hideOverlap: true }, ...extra,
});
const signColor = (v) => (v >= 0 ? T.gain : T.loss);
const signBar = (v, horizontal = false) => ({
  value: v,
  itemStyle: { color: signColor(v), borderRadius: horizontal ? (v >= 0 ? [0, 4, 4, 0] : [4, 0, 0, 4]) : (v >= 0 ? [4, 4, 0, 0] : [0, 0, 4, 4]) },
});
const zeroLine = { silent: true, symbol: "none", label: { show: false }, lineStyle: { color: "rgba(255,255,255,0.28)", type: "solid", width: 1 }, data: [{ yAxis: 0 }] };
const ttRow = (label, value) => `<div style="display:flex;justify-content:space-between;gap:18px"><span style="color:${T.text3}">${esc(label)}</span><b style="font-weight:600">${value}</b></div>`;
const ttHead = (t) => `<div style="margin-bottom:4px;font-weight:600">${esc(t)}</div>`;

function chartBox(id, cls = "", label = "") {
  return `<div class="chart ${cls}" id="${id}" role="img" aria-label="${esc(label)}"></div>`;
}
function queueChart(id, option) { pending.set(id, option); }
function mountVisibleCharts() {
  for (const [id, option] of pending) {
    const el = document.getElementById(id);
    if (!el) { pending.delete(id); continue; }
    if (el.closest("details:not([open])")) continue;
    const chart = echarts.init(el, null, { renderer: "canvas" });
    chart.setOption(baseOption(option));
    charts.set(id, chart);
    pending.delete(id);
  }
}
function disposeCharts() {
  for (const c of charts.values()) c.dispose();
  charts.clear();
  pending.clear();
}
let resizeTimer;
new ResizeObserver(() => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => charts.forEach((c) => c.resize()), 120);
}).observe(document.getElementById("view"));

/* chart builders */
function cumPnlChart(daily, ccy) {
  const data = daily.map((d) => [d.date, d.cum_pnl]);
  return {
    xAxis: timeAxis(), yAxis: valueAxis(),
    tooltip: { trigger: "axis", formatter: (p) => {
      const d = daily[p[0].dataIndex];
      return ttHead(fmt.date(d.date)) + ttRow("Cumulative PnL", `${fmt.money(d.cum_pnl)} ${ccy}`) + ttRow("That day", fmt.money(d.pnl)) + ttRow("Fills", fmt.int(d.fills));
    } },
    series: [{
      type: "line", data, showSymbol: false, lineStyle: { width: 2, color: T.gain }, itemStyle: { color: T.gain },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: "rgba(57,135,229,0.30)" }, { offset: 1, color: "rgba(57,135,229,0.02)" }]) },
      markLine: zeroLine,
    }],
  };
}
function drawdownChart(daily, ccy) {
  return {
    xAxis: timeAxis(), yAxis: valueAxis(),
    tooltip: { trigger: "axis", formatter: (p) => {
      const d = daily[p[0].dataIndex];
      return ttHead(fmt.date(d.date)) + ttRow("Below peak", `${fmt.money(d.drawdown_usdt)} ${ccy}`) + ttRow("Cumulative PnL", fmt.money(d.cum_pnl));
    } },
    series: [{
      type: "line", data: daily.map((d) => [d.date, d.drawdown_usdt]), showSymbol: false,
      lineStyle: { width: 2, color: T.loss }, itemStyle: { color: T.loss },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: "rgba(230,103,103,0.04)" }, { offset: 1, color: "rgba(230,103,103,0.32)" }]) },
    }],
  };
}
function dailyPnlChart(daily, ccy) {
  return {
    xAxis: timeAxis(), yAxis: valueAxis(),
    dataZoom: [{ type: "inside" }, { type: "slider", height: 18, bottom: 4, borderColor: "transparent", backgroundColor: "rgba(255,255,255,0.04)",
      fillerColor: "rgba(122,160,255,0.18)", handleStyle: { color: "#c9d6ff", borderColor: "transparent" }, moveHandleStyle: { color: "rgba(255,255,255,.2)" },
      textStyle: { color: T.text3 }, dataBackground: { lineStyle: { color: "rgba(255,255,255,.2)" }, areaStyle: { color: "rgba(255,255,255,.06)" } } }],
    grid: { left: 6, right: 14, top: 14, bottom: 34, containLabel: true },
    tooltip: { trigger: "axis", formatter: (p) => {
      const d = daily[p[0].dataIndex];
      return ttHead(fmt.date(d.date)) + ttRow("Net PnL", `${fmt.money(d.pnl)} ${ccy}`) + ttRow("Gross", fmt.money(d.gross)) + ttRow("Fees", fmt.money(d.fees)) + ttRow("Funding", fmt.money(d.funding, 3));
    } },
    series: [{ type: "bar", barMaxWidth: 10, data: daily.map((d) => ({ value: [d.date, d.pnl], itemStyle: { color: signColor(d.pnl), borderRadius: d.pnl >= 0 ? [3, 3, 0, 0] : [0, 0, 3, 3] } })) }],
  };
}
function waterfallChart(rows, ccy) {
  let run = 0;
  const items = rows.map((r, i) => {
    const short = { "Gross trading PnL": "Gross", "Trading fees": "Fees", Funding: "Funding", "Net PnL": "Net" }[r.component] || r.component;
    if (r.measure === "total") return { i, lo: Math.min(0, r.value), hi: Math.max(0, r.value), v: r.value, total: true, name: short, full: r.component };
    const lo = Math.min(run, run + r.value), hi = Math.max(run, run + r.value);
    run += r.value;
    return { i, lo, hi, v: r.value, total: false, name: short, full: r.component };
  });
  return {
    xAxis: catAxis(items.map((d) => d.name), { axisLabel: { color: T.text3, fontSize: 11, interval: 0, width: 80, overflow: "break" } }),
    yAxis: valueAxis(),
    grid: { left: 6, right: 10, top: 28, bottom: 6, containLabel: true },
    tooltip: { trigger: "item", formatter: (p) => ttHead(items[p.dataIndex].full) + ttRow("Amount", `${fmt.money(items[p.dataIndex].v)} ${ccy}`) },
    series: [{
      type: "custom", encode: { x: 0, y: [1, 2] },
      data: items.map((d) => [d.i, d.lo, d.hi, d.v, d.total ? 1 : 0]),
      renderItem: (params, api) => {
        const idx = api.value(0), lo = api.value(1), hi = api.value(2), v = api.value(3);
        const top = api.coord([idx, hi]), bot = api.coord([idx, lo]);
        const w = api.size([1, 0])[0] * 0.56;
        const h = Math.max(2, bot[1] - top[1]);
        return {
          type: "group", children: [
            { type: "rect", shape: { x: top[0] - w / 2, y: top[1], width: w, height: h, r: 4 }, style: { fill: signColor(v), opacity: api.value(4) ? 1 : 0.88 } },
            { type: "text", style: { text: fmt.compact(v), x: top[0], y: top[1] - 6, align: "center", verticalAlign: "bottom", fill: T.text1, font: `600 12px ${T.font}` } },
          ],
        };
      },
    }],
  };
}
function bucketChart(rows, key, valKey = "net_pnl", { ccy = "", horizontal = false, labelFmt = (x) => x, valueFmt = fmt.money } = {}) {
  const cats = rows.map((r) => labelFmt(r[key]));
  const tip = (p) => {
    const r = rows[p.dataIndex];
    let h = ttHead(cats[p.dataIndex]) + ttRow(valKey === "avg_pnl" ? "Avg PnL" : "Net PnL", `${valueFmt(r[valKey])} ${ccy}`);
    if (isNum(r.trades)) h += ttRow("Trades", fmt.int(r.trades));
    if (isNum(r.days)) h += ttRow("Days", fmt.int(r.days));
    if (isNum(r.win_rate)) h += ttRow("Win rate", fmt.pct(r.win_rate));
    if (isNum(r.avg_pnl) && valKey !== "avg_pnl") h += ttRow("Avg per trade", fmt.money(r.avg_pnl, 3));
    return h;
  };
  const data = rows.map((r) => signBar(r[valKey], horizontal));
  return horizontal ? {
    xAxis: valueAxis(), yAxis: catAxis(cats, { inverse: true, axisLabel: { color: T.text2, fontSize: 11 } }),
    tooltip: { trigger: "item", formatter: tip },
    series: [{ type: "bar", data, barMaxWidth: 16, barCategoryGap: "28%" }],
  } : {
    xAxis: catAxis(cats), yAxis: valueAxis(), tooltip: { trigger: "item", formatter: tip },
    series: [{ type: "bar", data, barMaxWidth: 34, barCategoryGap: "30%", markLine: zeroLine }],
  };
}
function winRateChart(rows, key, breakeven, labelFmt = (x) => x) {
  const cats = rows.map((r) => labelFmt(r[key]));
  const be = isNum(breakeven) ? breakeven : null;
  return {
    xAxis: catAxis(cats), yAxis: valueAxis((v) => `${Math.round(v * 100)}%`, { max: (e) => Math.min(1, Math.max(e.max, be ?? 0) + 0.08), min: 0 }),
    grid: { left: 6, right: 14, top: 18, bottom: 6, containLabel: true },
    tooltip: { trigger: "item", formatter: (p) => {
      const r = rows[p.dataIndex];
      return ttHead(cats[p.dataIndex]) + ttRow("Win rate", fmt.pct(r.win_rate)) + (be != null ? ttRow("Break-even", fmt.pct(be)) : "") + ttRow("Trades", fmt.int(r.trades));
    } },
    series: [{
      type: "bar", barMaxWidth: 34, barCategoryGap: "30%",
      data: rows.map((r) => ({ value: r.win_rate, itemStyle: { color: be != null && r.win_rate >= be ? T.gain : be != null ? T.loss : T.accent, borderRadius: [4, 4, 0, 0] } })),
      markLine: be == null ? undefined : { silent: true, symbol: "none", lineStyle: { color: T.text1, type: "dashed", width: 1.5 },
        label: { formatter: `Break-even ${fmt.pct(be)}`, color: T.text1, fontSize: 11, position: "insideEndTop" }, data: [{ yAxis: be }] },
    }],
  };
}
function histogramChart(values, ccy) {
  const v = values.filter(isNum).sort((a, b) => a - b);
  if (!v.length) return null;
  const q = (p) => v[Math.min(v.length - 1, Math.max(0, Math.floor(p * (v.length - 1))))];
  let lo = q(0.01), hi = q(0.99);
  if (lo === hi) { lo -= 1; hi += 1; }
  const n = 32, w = (hi - lo) / n;
  const bins = Array.from({ length: n }, (_, i) => ({ a: lo + i * w, b: lo + (i + 1) * w, c: 0 }));
  let under = 0, over = 0;
  for (const x of v) {
    if (x < lo) { under++; bins[0].c++; continue; }
    if (x > hi) { over++; bins[n - 1].c++; continue; }
    bins[Math.min(n - 1, Math.floor((x - lo) / w))].c++;
  }
  return {
    xAxis: catAxis(bins.map((b) => fmt.compact((b.a + b.b) / 2)), { axisLabel: { color: T.text3, fontSize: 11, hideOverlap: true } }),
    yAxis: valueAxis(fmt.int),
    tooltip: { trigger: "item", formatter: (p) => {
      const b = bins[p.dataIndex];
      return ttHead(`${fmt.money(b.a)} to ${fmt.money(b.b)} ${ccy}`) + ttRow("Trades", fmt.int(b.c)) +
        (p.dataIndex === 0 && under ? ttRow("Includes larger losses", fmt.int(under)) : "") + (p.dataIndex === n - 1 && over ? ttRow("Includes larger wins", fmt.int(over)) : "");
    } },
    series: [{ type: "bar", barCategoryGap: "8%", data: bins.map((b) => ({ value: b.c, itemStyle: { color: (b.a + b.b) / 2 >= 0 ? T.gain : T.loss, borderRadius: [3, 3, 0, 0] } })) }],
  };
}
function scatterChart(points, { xName, yName, xFmt = fmt.compact, xLog = false, tip, ccy = "" }) {
  const win = points.filter((p) => p[1] > 0), lose = points.filter((p) => p[1] <= 0);
  const large = points.length > 2000;
  const s = (name, data, color) => ({ name, type: "scatter", data, symbolSize: large ? 5 : 8, large, itemStyle: { color, opacity: 0.72, borderColor: "rgba(10,14,24,.9)", borderWidth: large ? 0 : 1 } });
  return {
    legend: { top: 0, right: 0, textStyle: { color: T.text2, fontSize: 12 }, itemWidth: 10, itemHeight: 10, icon: "circle" },
    grid: { left: 22, right: 16, top: 30, bottom: 22, containLabel: true },
    xAxis: { ...valueAxis(xFmt), type: xLog ? "log" : "value", name: xName, nameLocation: "middle", nameGap: 26, nameTextStyle: { color: T.text3, fontSize: 11 }, splitLine: { show: false }, axisLine: { lineStyle: { color: T.axis } } },
    yAxis: { ...valueAxis(), name: yName, nameLocation: "middle", nameGap: 44, nameTextStyle: { color: T.text3, fontSize: 11 } },
    tooltip: { trigger: "item", formatter: tip || ((p) => ttRow(xName, xFmt(p.value[0])) + ttRow(yName, `${fmt.money(p.value[1])} ${ccy}`)) },
    series: [s("Winners", win, T.gain), s("Losers", lose, T.loss)],
  };
}
function heatmapChart(rows, ccy) {
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const hours = Array.from({ length: 24 }, (_, h) => String(h).padStart(2, "0"));
  const map = new Map(rows.map((r) => [`${r.weekday}|${r.hour}`, r]));
  const data = [];
  let m = 0;
  days.forEach((d, y) => hours.forEach((_, x) => {
    const r = map.get(`${d}|${x}`);
    if (r) { data.push([x, y, r.net_pnl]); m = Math.max(m, Math.abs(r.net_pnl)); } else data.push([x, y, null]);
  }));
  // Scale to the 90th percentile so one outlier hour doesn't wash every other cell to grey.
  const mags = data.map((d) => Math.abs(d[2] ?? 0)).filter((x) => x > 0).sort((a, b) => a - b);
  m = mags.length ? mags[Math.floor(0.9 * (mags.length - 1))] : 1;
  return {
    grid: { left: 6, right: 10, top: 6, bottom: 56, containLabel: true },
    xAxis: catAxis(hours, { splitArea: { show: false }, name: "Hour opened (UTC)", nameLocation: "middle", nameGap: 26, nameTextStyle: { color: T.text3, fontSize: 11 } }),
    yAxis: catAxis(days, { inverse: true, axisLine: { show: false } }),
    visualMap: { min: -m, max: m, calculable: false, orient: "horizontal", left: "center", bottom: 0, itemWidth: 12, itemHeight: 180,
      text: [`Gain ${fmt.compact(m)}+`, `Loss ${fmt.compact(-m)}+`], textStyle: { color: T.text2, fontSize: 11 }, inRange: { color: [T.loss, T.mid, T.gain] }, formatter: (v) => fmt.compact(v) },
    tooltip: { trigger: "item", formatter: (p) => {
      const r = map.get(`${days[p.value[1]]}|${p.value[0]}`);
      if (!r) return ttHead(`${days[p.value[1]]} ${hours[p.value[0]]}:00`) + "No trades";
      return ttHead(`${days[p.value[1]]} ${hours[p.value[0]]}:00 UTC`) + ttRow("Net PnL", `${fmt.money(r.net_pnl)} ${ccy}`) + ttRow("Trades", fmt.int(r.trades)) + ttRow("Win rate", fmt.pct(r.win_rate));
    } },
    series: [{ type: "heatmap", data, itemStyle: { borderColor: "rgba(8,12,22,0.9)", borderWidth: 2, borderRadius: 3 }, emphasis: { itemStyle: { borderColor: T.text1, borderWidth: 1 } } }],
  };
}
function lineChart(points, color, name, valueFmt = fmt.compact) {
  return {
    xAxis: timeAxis(), yAxis: valueAxis(valueFmt, { scale: true }),
    tooltip: { trigger: "axis", formatter: (p) => ttHead(fmt.date(p[0].value[0])) + ttRow(name, fmt.num(p[0].value[1], 0)) },
    series: [{ type: "line", data: points, showSymbol: false, lineStyle: { width: 2, color }, itemStyle: { color } }],
  };
}

/* -------------------------------------------------------- components */
function kpi(label, value, { unit = "", foot = "", tone = null, meter = null } = {}) {
  const tag = tone ? `<span class="tag ${tone.dir > 0 ? "pos" : "neg"}">${icon(tone.dir > 0 ? "up" : "down")}${esc(tone.text)}</span>` : "";
  const m = meter ? `<div class="meter" aria-hidden="true"><span style="width:${Math.max(0, Math.min(100, meter.value * 100))}%;background:${meter.value >= meter.target ? T.gain : T.loss}"></span><i style="left:calc(${Math.max(0, Math.min(100, meter.target * 100))}% - 1px)"></i></div>` : "";
  return `<article class="kpi glass"><div class="kpi-label">${esc(label)}${unit ? `<span class="unit">${esc(unit)}</span>` : ""}</div>
    <div class="kpi-value">${value}</div>${m}<div class="kpi-foot">${tag}${foot ? `<span>${foot}</span>` : ""}</div></article>`;
}
function card(title, sub, body, span = "s12", head = "") {
  return `<section class="card glass ${span}"><div class="card-head"><div><h3 class="card-title">${esc(title)}</h3>${sub ? `<p class="card-sub">${sub}</p>` : ""}</div>${head}</div>${body}</section>`;
}
function accordion(title, sub, body, { open = false } = {}) {
  return `<details class="acc glass"${open ? " open" : ""}><summary><span class="acc-title">${esc(title)}</span>${sub ? `<span class="acc-sub">${esc(sub)}</span>` : ""}${icon("chev", "i chev")}</summary><div class="acc-body">${body}</div></details>`;
}
function emptyState(title, text, ico = "info") {
  return `<div class="empty glass">${icon(ico)}<h2>${esc(title)}</h2><p>${text}</p></div>`;
}
function table(columns, rows, { sort = null, sortId = "", maxRows = Infinity } = {}) {
  const head = columns.map((c) => {
    const aria = sort && sort.key === c.key ? ` aria-sort="${sort.dir === "asc" ? "ascending" : "descending"}"` : "";
    const inner = sortId ? `<button type="button" data-sort="${sortId}" data-key="${c.key}">${esc(c.label)}</button>` : esc(c.label);
    return `<th scope="col" class="${c.num ? "num" : ""}"${aria}>${inner}</th>`;
  }).join("");
  const body = rows.slice(0, maxRows).map((r) => `<tr>${columns.map((c) => `<td class="${c.num ? "num" : ""}">${c.fmt ? c.fmt(r[c.key], r) : esc(r[c.key])}</td>`).join("")}</tr>`).join("");
  return `<div class="table-wrap"><table class="t"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}
const signed = (d = 2) => (v) => `<span class="dot ${v >= 0 ? "pos" : "neg"}" aria-hidden="true"></span>${fmt.money(v, d)}`;
const rowsOf = (t) => (t?.rows || []).map((r) => Object.fromEntries(t.columns.map((c, i) => [c, r[i]])));
function sortRows(rows, { key, dir }) {
  const m = dir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const x = a[key], y = b[key];
    if (x == null) return 1;
    if (y == null) return -1;
    return (typeof x === "string" ? x.localeCompare(y) : x - y) * m;
  });
}

/* ------------------------------------------------------------- pages */
function pageOverview(r) {
  const s = r.summary, v = r.verdict, ccy = s.currency, be = s.breakeven_win_rate;
  const verdict = `<section class="verdict glass ${v.tone}" aria-labelledby="vt">
    <div class="verdict-icon">${icon(v.tone === "positive" ? "check" : "alert")}</div>
    <div><h2 id="vt">${esc(v.title)}</h2><p>${esc(v.text)}</p></div>
    <div class="verdict-stats">
      <div class="vstat"><span>Before costs</span><b>${fmt.money(s.gross_pnl)}</b></div>
      <div class="vstat"><span>Fees</span><b>${fmt.money(s.fees)}</b></div>
      <div class="vstat"><span>Funding</span><b>${fmt.money(s.funding)}</b></div>
      <div class="vstat"><span>Net result</span><b>${fmt.money(s.net_pnl)}</b></div>
    </div></section>`;
  const kpis = `<div class="kpis">
    ${kpi("Net PnL", fmt.money(s.net_pnl), { unit: ccy, foot: `${fmt.int(s.trades)} closed trades` })}
    ${kpi("Return on deposits", fmt.pct(s.return_on_deposits, 1, true), { foot: `${fmt.num(s.deposits)} ${ccy} deposited` })}
    ${kpi("Win rate", fmt.pct(s.win_rate), { meter: isNum(be) ? { value: s.win_rate, target: be } : null,
        tone: isNum(be) ? { dir: s.win_rate >= be ? 1 : -1, text: `${fmt.pct(be)} needed` } : null })}
    ${kpi("Profit factor", fmt.num(s.profit_factor), { tone: isNum(s.profit_factor) ? { dir: s.profit_factor >= 1 ? 1 : -1, text: s.profit_factor >= 1 ? "Wins exceed losses" : "Losses exceed wins" } : null })}
    ${kpi("Expectancy per trade", fmt.money(s.expectancy, 3), { unit: ccy, foot: `Payoff ratio ${fmt.num(s.payoff_ratio)}` })}
    ${kpi("Max drawdown", fmt.money(s.max_drawdown_usdt), { unit: ccy, foot: `${fmt.int(s.max_drawdown_days)} days under water` })}
  </div>`;
  const all = r.insights.slice(1).filter((t) => !t.startsWith("At this payoff ratio"));
  const top = all.slice(0, 5), rest = all.slice(5);
  const li = (t, i) => `<li><span class="n">${String(i + 1).padStart(2, "0")}</span><span>${esc(t)}</span></li>`;
  const findings = card("Key findings", "Computed from the data, ordered by importance", `<ol class="findings">${top.map(li).join("")}</ol>` +
    (rest.length ? `<details class="inline-acc"><summary>Show ${rest.length} more findings</summary><ol class="findings">${rest.map((t, i) => li(t, i + top.length)).join("")}</ol></details>` : ""));

  queueChart("c-cum", cumPnlChart(r.daily, ccy));
  queueChart("c-wf", waterfallChart(r.waterfall, ccy));
  queueChart("c-daily", dailyPnlChart(r.daily, ccy));

  return verdict + kpis +
    card("Cumulative PnL", `Trading result over time, deposits and withdrawals excluded (${esc(ccy)})`, chartBox("c-cum", "tall", "Cumulative PnL line chart"), "s8") +
    card("Where the money went", "Gross trading result, then costs", chartBox("c-wf", "tall", "PnL waterfall: gross, fees, funding, net"), "s4") +
    findings +
    accordion("Daily PnL", "Each day's result; drag the slider to zoom", chartBox("c-daily", "", "Daily PnL bar chart")) +
    accordion("Deposits, costs and volume", "Account flows behind the numbers", `<div class="stat-grid">
      ${[["Deposited", fmt.num(s.deposits)], ["Withdrawn", fmt.num(-s.withdrawals)], ["Fees paid", fmt.num(-s.fees)],
         ["Funding", fmt.money(s.funding, 3)], ["Volume traded", fmt.num(s.volume, 0)], ["Effective fee rate", fmt.pct(s.effective_fee_rate, 3)],
         ["Fees share of total loss", fmt.pct(s.fee_drag)], ["Time-weighted return", fmt.pct(s.twr, 1, true)], ["Active days", `${fmt.int(s.active_days)} of ${fmt.int(s.days)}`],
         ["Trades per active day", fmt.num(s.trades_per_active_day, 1)], ["Open positions", fmt.int(s.open_positions)], ["Final balance", fmt.num(s.final_balance)]]
        .map(([k, v]) => `<div class="stat"><span>${esc(k)}</span><b>${v}</b></div>`).join("")}</div>
      <p class="note">Amounts in ${esc(ccy)}. Time-weighted return chains every event, so deposits don't inflate it; on an account that is topped up repeatedly it can approach ${MINUS}100%.</p>`);
}

function pageEdge(r) {
  const s = r.summary, ccy = s.currency, be = s.breakeven_win_rate;
  const kpis = `<div class="kpis">
    ${kpi("Average win", fmt.money(s.avg_win, 3), { unit: ccy })}
    ${kpi("Average loss", fmt.money(s.avg_loss, 3), { unit: ccy })}
    ${kpi("Payoff ratio", fmt.num(s.payoff_ratio), { foot: "Average win / average loss" })}
    ${kpi("Break-even win rate", fmt.pct(be), { tone: isNum(be) ? { dir: s.win_rate >= be ? 1 : -1, text: `Actual ${fmt.pct(s.win_rate)}` } : null })}
    ${kpi("Longest losing streak", fmt.int(s.max_loss_streak), { foot: `Longest winning streak ${fmt.int(s.max_win_streak)}` })}
    ${kpi("Median hold", fmt.dur(s.median_hold_min), { foot: "Per closed trade" })}
  </div>`;
  const dur = r.by_duration;
  queueChart("c-holdwin", winRateChart(dur, "hold", be));
  queueChart("c-holdnet", bucketChart(dur, "hold", "net_pnl", { ccy }));
  const tradeRows = rowsOf(r.trades);
  const hist = histogramChart(tradeRows.map((t) => t.net_pnl), ccy);
  if (hist) queueChart("c-hist", hist);

  const dir = Object.fromEntries(r.by_direction.map((d) => [d.direction, d]));
  const col = (name) => {
    const d = dir[name];
    if (!d) return `<div class="compare-col"><h4>${name}</h4><p class="note">No ${name.toLowerCase()} trades</p></div>`;
    return `<div class="compare-col"><h4>${name}s</h4><dl>
      <dt>Net PnL</dt><dd>${signed()(d.net_pnl)}</dd><dt>Trades</dt><dd>${fmt.int(d.trades)}</dd>
      <dt>Win rate</dt><dd>${fmt.pct(d.win_rate)}</dd><dt>Avg per trade</dt><dd>${fmt.money(d.avg_pnl, 3)}</dd>
      <dt>Fees</dt><dd>${fmt.money(d.fees)}</dd></dl></div>`;
  };
  const better = dir.Long && dir.Short ? (dir.Long.net_pnl >= dir.Short.net_pnl ? "Long" : "Short") : null;
  const dirNote = better ? `<p class="note">${better}s ${dir[better].net_pnl > 0 ? "made more" : "lost less"} in this period.</p>` : "";

  if (r.by_size.length) queueChart("c-size", bucketChart(r.by_size, "size_bucket", "net_pnl", { ccy }));
  const pts = tradeRows.filter((t) => isNum(t.duration_min) && t.duration_min > 0).map((t) => [t.duration_min, t.net_pnl, t.symbol]);
  queueChart("c-scatter", scatterChart(pts, { xName: "Holding time (minutes, log scale)", yName: `Net PnL (${ccy})`, xLog: true, xFmt: (v) => fmt.dur(v), ccy,
    tip: (p) => ttHead(p.value[2]) + ttRow("Held", fmt.dur(p.value[0])) + ttRow("Net PnL", `${fmt.money(p.value[1], 3)} ${ccy}`) }));
  const wl = r.hold_winners_losers;

  return kpis +
    card("Win rate by holding time", "Bars above the dashed line beat the break-even win rate", chartBox("c-holdwin", "", "Win rate by holding time"), "s6") +
    card("Net PnL by holding time", `Which holding periods made or lost money (${esc(ccy)})`, chartBox("c-holdnet", "", "Net PnL by holding time"), "s6") +
    card("Distribution of trade results", `Net PnL per trade; outer 1% folded into the end bars (${esc(ccy)})`, hist ? chartBox("c-hist", "", "Histogram of trade PnL") : "<p class='note'>No trades</p>", "s7") +
    card("Longs vs shorts", "Directional bias", `<div class="compare">${col("Long")}${col("Short")}</div>${dirNote}`, "s5") +
    accordion("Do winners and losers get held differently?", "Median and mean holding time", table(
      [{ key: "outcome", label: "Outcome" }, { key: "count", label: "Trades", num: true, fmt: fmt.int }, { key: "median", label: "Median hold", num: true, fmt: fmt.dur }, { key: "mean", label: "Mean hold", num: true, fmt: fmt.dur }], wl)) +
    accordion("Does position size help or hurt?", "Entry notional split into quintiles", r.by_size.length ? chartBox("c-size", "", "Net PnL by position size quintile") : "<p class='note'>Not enough trades.</p>") +
    accordion("Every trade: holding time vs result", `${fmt.int(pts.length)} trades`, chartBox("c-scatter", "tall", "Scatter of holding time against trade PnL"));
}

function pageSymbols(r) {
  const s = r.summary, ccy = s.currency, sym = r.by_symbol, conc = r.loss_concentration;
  const sorted = [...sym].sort((a, b) => b.net_pnl - a.net_pnl);
  const best = sorted[0], worst = sorted[sorted.length - 1];
  const kpis = `<div class="kpis">
    ${kpi("Symbols traded", fmt.int(sym.length))}
    ${kpi("Net profitable", `${fmt.int(conc.winning_symbols)}`, { foot: `of ${fmt.int(sym.length)} symbols` })}
    ${kpi("Top 5 share of losses", fmt.pct(conc.share), { foot: "Loss concentration" })}
    ${kpi("Best symbol", esc(best?.symbol ?? "–"), { foot: best ? `${fmt.money(best.net_pnl)} ${ccy}` : "" })}
    ${kpi("Worst symbol", esc(worst?.symbol ?? "–"), { foot: worst ? `${fmt.money(worst.net_pnl)} ${ccy}` : "" })}
  </div>`;
  const winners = sorted.filter((x) => x.net_pnl > 0).slice(0, 8);
  const losers = sorted.filter((x) => x.net_pnl < 0).slice(-8);
  const extremes = [...winners, ...losers];
  queueChart("c-sym", bucketChart(extremes, "symbol", "net_pnl", { ccy, horizontal: true }));
  const tl = r.top_losers;
  queueChart("c-share", {
    xAxis: valueAxis((v) => `${Math.round(v * 100)}%`), yAxis: catAxis(tl.map((d) => d.symbol), { inverse: true, axisLabel: { color: T.text2, fontSize: 11 } }),
    grid: { left: 6, right: 44, top: 6, bottom: 6, containLabel: true },
    tooltip: { trigger: "item", formatter: (p) => { const d = tl[p.dataIndex]; return ttHead(d.symbol) + ttRow("Share of losses", fmt.pct(d.share, 1)) + ttRow("Net PnL", `${fmt.money(d.net_pnl)} ${ccy}`) + ttRow("Trades", fmt.int(d.trades)); } },
    series: [{ type: "bar", data: tl.map((d) => ({ value: d.share, itemStyle: { color: T.loss, borderRadius: [0, 4, 4, 0] } })), barMaxWidth: 14,
      label: { show: true, position: "right", color: T.text2, fontSize: 11, formatter: (p) => fmt.pct(p.value) } }],
  });
  const pts = sym.map((d) => [d.trades, d.net_pnl, d.symbol]);
  queueChart("c-symscatter", scatterChart(pts, { xName: "Trades (log scale)", yName: `Net PnL (${ccy})`, xLog: true, xFmt: fmt.int, ccy,
    tip: (p) => ttHead(p.value[2]) + ttRow("Trades", fmt.int(p.value[0])) + ttRow("Net PnL", `${fmt.money(p.value[1])} ${ccy}`) }));
  const cols = [
    { key: "symbol", label: "Symbol" }, { key: "trades", label: "Trades", num: true, fmt: fmt.int },
    { key: "net_pnl", label: "Net PnL", num: true, fmt: signed() }, { key: "avg_pnl", label: "Avg / trade", num: true, fmt: (v) => fmt.money(v, 3) },
    { key: "win_rate", label: "Win rate", num: true, fmt: (v) => fmt.pct(v) }, { key: "fees", label: "Fees", num: true, fmt: (v) => fmt.money(v) },
    { key: "volume", label: "Volume", num: true, fmt: (v) => fmt.num(v, 0) }, { key: "liquidations", label: "Liquidations", num: true, fmt: fmt.int },
    { key: "median_hold_min", label: "Median hold", num: true, fmt: fmt.dur },
  ];
  return kpis +
    card("Biggest winners and losers", `Top ${winners.length} and bottom ${losers.length} symbols by net PnL (${esc(ccy)})`, chartBox("c-sym", "tall", "Horizontal bars of best and worst symbols"), "s7") +
    card("Where the losses concentrate", "Share of all losing-symbol PnL", chartBox("c-share", "tall", "Share of losses by symbol"), "s5") +
    accordion("Does trading a symbol more often help?", "Trades vs net PnL per symbol", chartBox("c-symscatter", "tall", "Scatter of trade count against PnL per symbol")) +
    accordion("All symbols", `${fmt.int(sym.length)} symbols, sortable`, `<div id="symTable">${table(cols, sortRows(sym, state.ui.symSort), { sort: state.ui.symSort, sortId: "sym" })}</div>`);
}

function pageTiming(r) {
  const s = r.summary, ccy = s.currency, be = s.breakeven_win_rate, ot = r.overtrading;
  queueChart("c-heat", heatmapChart(r.by_hour_weekday, ccy));
  const tiltOrder = (c) => (c.startsWith("≤") && c.includes("loss") ? 0 : c.startsWith("≤") ? 1 : 2);
  const tilt = [...r.tilt].sort((a, b) => tiltOrder(a.context) - tiltOrder(b.context));
  queueChart("c-tilt", bucketChart(tilt, "context", "avg_pnl", { ccy, valueFmt: (v) => fmt.money(v, 3) }));
  queueChart("c-ot", bucketChart(ot.buckets, "trade_bucket", "avg_pnl", { ccy, labelFmt: (x) => `${x} trades` }));
  queueChart("c-hour", bucketChart(r.by_hour, "hour", "net_pnl", { ccy, labelFmt: (h) => String(h).padStart(2, "0") }));
  queueChart("c-otscatter", scatterChart(ot.days.map((d) => [d.trades, d.pnl, d.date]), { xName: "Trades closed that day", yName: `Daily PnL (${ccy})`, xFmt: fmt.int, ccy,
    tip: (p) => ttHead(fmt.date(p.value[2])) + ttRow("Trades", fmt.int(p.value[0])) + ttRow("PnL", `${fmt.money(p.value[1])} ${ccy}`) }));
  const w = state.f.tilt;
  const seg = `<div class="mini-seg" role="group" aria-label="Minutes after previous trade">${[5, 15, 30, 60].map((m) => `<button class="btn" type="button" data-tilt="${m}" aria-pressed="${m === w}">${m}m</button>`).join("")}</div>`;
  const corr = ot.corr;
  const corrText = isNum(corr) ? `Correlation between trades per day and daily PnL: <b>${fmt.num(corr, 2, true)}</b>${corr < -0.3 ? ", so busier days are worse days." : "."}` : "";
  const tiltCols = [{ key: "context", label: "Context" }, { key: "trades", label: "Trades", num: true, fmt: fmt.int }, { key: "avg_pnl", label: "Avg / trade", num: true, fmt: (v) => fmt.money(v, 3) },
    { key: "win_rate", label: "Win rate", num: true, fmt: (v) => fmt.pct(v) }, { key: "net_pnl", label: "Net PnL", num: true, fmt: signed() }];
  return card("When trades are opened", `Net PnL by weekday and hour opened, UTC (${esc(ccy)}). Blue is gain, red is loss.`, chartBox("c-heat", "tall", "Heatmap of PnL by weekday and hour"), "s12") +
    card("Tilt check: trading right after a loss", `Average PnL per trade, by what happened just before`, chartBox("c-tilt", "", "Average PnL by context after previous trade"), "s6", seg) +
    card("Overtrading: busy days vs results", corrText || "Average daily PnL by trades that day", chartBox("c-ot", "", "Average daily PnL by trades per day"), "s6") +
    accordion("Net PnL by hour opened", "UTC, all weekdays combined", chartBox("c-hour", "", "Net PnL by hour")) +
    accordion("Every active day: trades vs PnL", `${fmt.int(ot.days.length)} days`, chartBox("c-otscatter", "tall", "Scatter of trades per day against daily PnL")) +
    accordion("Tilt check detail", `Window: ${w} minutes after the previous trade closed`, table(tiltCols, tilt) + (isNum(be) ? `<p class="note">Break-even win rate at the overall payoff ratio: ${fmt.pct(be)}.</p>` : ""));
}

function pageRisk(r) {
  const s = r.summary, ccy = s.currency, be = s.breakeven_win_rate;
  const kpis = `<div class="kpis">
    ${kpi("Max drawdown", fmt.money(s.max_drawdown_usdt), { unit: ccy, foot: "Largest fall from peak cumulative PnL" })}
    ${kpi("Longest drawdown", `${fmt.int(s.max_drawdown_days)} days`, { foot: "Below a previous peak" })}
    ${kpi("Worst day", fmt.money(s.worst_day), { unit: ccy, foot: `Best day ${fmt.money(s.best_day)}` })}
    ${kpi("Liquidations", fmt.int(s.liquidations), { foot: `Cost ${fmt.money(s.liquidation_pnl)} ${ccy}` })}
    ${kpi("Green days", fmt.pct(s.green_day_rate), { foot: "Of active days" })}
    ${kpi("Sharpe ratio", fmt.num(s.sharpe_daily_ann), { foot: "Daily returns, annualised" })}
  </div>`;
  queueChart("c-dd", drawdownChart(r.daily, ccy));
  const lev = r.by_leverage;
  if (lev.length) {
    queueChart("c-lev", bucketChart(lev, "lev_bucket", "net_pnl", { ccy }));
    queueChart("c-levwin", winRateChart(lev, "lev_bucket", be));
  }
  const liq = rowsOf(r.liquidations);
  const liqCols = [{ key: "symbol", label: "Symbol" }, { key: "direction", label: "Side" }, { key: "open_time", label: "Opened", fmt: fmt.dateTime },
    { key: "duration_min", label: "Held", num: true, fmt: fmt.dur }, { key: "entry_notional", label: "Notional", num: true, fmt: (v) => fmt.num(v) },
    { key: "net_pnl", label: "Net PnL", num: true, fmt: signed() }];
  return kpis +
    card("Drawdown", `Distance below the previous peak of cumulative PnL (${esc(ccy)})`, chartBox("c-dd", "tall", "Drawdown area chart"), lev.length ? "s8" : "s12") +
    (lev.length ? card("Leverage", "Net PnL by leverage used (closed-PnL API)", chartBox("c-lev", "tall", "Net PnL by leverage bucket"), "s4") : "") +
    accordion("Liquidated positions", liq.length ? `${fmt.int(liq.length)} positions, ${liq.length > 200 ? "worst 200 shown" : "worst first"}` : "None in this period",
      liq.length ? table(liqCols, liq, { maxRows: 200 }) : "<p class='note'>No liquidations in this period.</p>") +
    (lev.length ? accordion("Win rate by leverage", "Against the break-even win rate", chartBox("c-levwin", "", "Win rate by leverage")) :
      accordion("Leverage", "Needs API data", "<p class='note'>Leverage comes from the closed-PnL endpoint, which CSV exports don't include.</p>"));
}

function pageMarket(r) {
  const m = r.market, ccy = r.summary.currency;
  if (!m.available) return emptyState("No market data for this period", "BTC daily candles are fetched from Bybit's public API. They appear after a sync, or once the server can reach Bybit.");
  const kpis = `<div class="kpis">
    ${kpi("Correlation with BTC", fmt.num(m.corr, 2, true), { foot: "Daily PnL vs BTC daily return" })}
    ${kpi("Avg PnL on BTC up days", fmt.money(m.up_avg), { unit: ccy })}
    ${kpi("Avg PnL on BTC down days", fmt.money(m.down_avg), { unit: ccy })}
  </div>`;
  const pts = m.days.filter((d) => isNum(d.btc_return)).map((d) => [d.btc_return, d.pnl, d.date]);
  queueChart("c-mscatter", scatterChart(pts, { xName: "BTC daily return", yName: `Daily PnL (${ccy})`, xFmt: (v) => fmt.pct(v, 0), ccy,
    tip: (p) => ttHead(fmt.date(p.value[2])) + ttRow("BTC", fmt.pct(p.value[0], 1, true)) + ttRow("Your PnL", `${fmt.money(p.value[1])} ${ccy}`) }));
  queueChart("c-move", bucketChart(m.by_move, "btc_move", "avg_pnl", { ccy, labelFmt: (x) => x.replace("..", " to ") }));
  queueChart("c-vol", bucketChart(m.by_vol, "btc_vol", "avg_pnl", { ccy }));
  queueChart("c-btc", lineChart(m.days.map((d) => [d.date, d.close]), T.accent, "BTC close"));
  queueChart("c-mpnl", dailyPnlChart(m.days.map((d) => ({ ...d, gross: null, fees: null, funding: null })), ccy));
  return kpis +
    card("Your daily PnL vs Bitcoin's move", "Each dot is an active trading day", chartBox("c-mscatter", "tall", "Scatter of BTC return against daily PnL"), "s7") +
    card("Average day by BTC move", `Average daily PnL (${esc(ccy)})`, chartBox("c-move", "tall", "Average PnL by BTC daily move"), "s5") +
    accordion("Average day by BTC volatility", "BTC intraday range, split in thirds", chartBox("c-vol", "", "Average PnL by BTC volatility")) +
    accordion("BTC price and your daily PnL", "Same dates, two separate scales", chartBox("c-btc", "short", "BTC closing price") + chartBox("c-mpnl", "short", "Daily PnL on active days"));
}

const TRADE_COLS = [
  { key: "close_time", label: "Closed", fmt: fmt.dateTime }, { key: "symbol", label: "Symbol" }, { key: "direction", label: "Side" },
  { key: "duration_min", label: "Held", num: true, fmt: fmt.dur }, { key: "entry_notional", label: "Notional", num: true, fmt: (v) => fmt.num(v) },
  { key: "avg_entry", label: "Entry", num: true, fmt: (v) => fmt.num(v, v < 1 ? 5 : 2) }, { key: "avg_exit", label: "Exit", num: true, fmt: (v) => fmt.num(v, v < 1 ? 5 : 2) },
  { key: "gross_pnl", label: "Gross", num: true, fmt: (v) => fmt.money(v, 3) }, { key: "fees", label: "Fees", num: true, fmt: (v) => fmt.money(v, 3) },
  { key: "net_pnl", label: "Net PnL", num: true, fmt: signed(3) },
  { key: "liquidated", label: "Note", fmt: (v, r) => [v ? "Liquidated" : "", r.partial ? "Opened before data" : ""].filter(Boolean).join(", ") },
];
function filteredTrades(r) {
  const q = state.ui.tradeQuery.trim().toUpperCase(), o = state.ui.tradeOutcome;
  let rows = rowsOf(r.trades);
  if (q) rows = rows.filter((t) => t.symbol.includes(q));
  if (o === "win") rows = rows.filter((t) => t.net_pnl > 0);
  if (o === "loss") rows = rows.filter((t) => t.net_pnl <= 0);
  if (o === "liq") rows = rows.filter((t) => t.liquidated);
  return sortRows(rows, state.ui.tradeSort);
}
function tradesTable(r) {
  const rows = filteredTrades(r), per = 25;
  const pages = Math.max(1, Math.ceil(rows.length / per));
  state.ui.tradePage = Math.min(state.ui.tradePage, pages - 1);
  const p = state.ui.tradePage;
  return table(TRADE_COLS, rows.slice(p * per, (p + 1) * per), { sort: state.ui.tradeSort, sortId: "trades" }) +
    `<div class="pager"><span>${fmt.int(rows.length)} trades</span><span class="mini-seg">
      <button class="btn" type="button" data-pg="-1" ${p === 0 ? "disabled" : ""}>Previous</button>
      <span style="align-self:center;padding:0 8px">Page ${p + 1} of ${pages}</span>
      <button class="btn" type="button" data-pg="1" ${p >= pages - 1 ? "disabled" : ""}>Next</button></span></div>`;
}
function pageTrades(r) {
  const o = state.ui.tradeOutcome;
  const outcomes = [["all", "All"], ["win", "Winners"], ["loss", "Losers"], ["liq", "Liquidated"]];
  const toolbar = `<div class="toolbar">
    <label class="sr-only" for="tq">Filter by symbol</label><input class="input" id="tq" type="search" placeholder="Filter by symbol" value="${esc(state.ui.tradeQuery)}">
    <span class="mini-seg" role="group" aria-label="Outcome">${outcomes.map(([k, l]) => `<button class="btn" type="button" data-outcome="${k}" aria-pressed="${k === o}">${l}</button>`).join("")}</span>
    <button class="btn" type="button" id="dlTrades" style="margin-left:auto">${icon("download")}Download CSV</button></div>`;
  return card("Round-trip trades", "Flat, position, flat. Fees and funding are attributed to the position open at the time.", toolbar + `<div id="tradeTable">${tradesTable(r)}</div>`) +
    accordion("How the numbers are built", "Methodology", `<div class="findings" style="gap:6px">
      <p class="note" style="font-size:13px;color:var(--text-2)">Net PnL is the sum of every wallet change except transfers, deposits and conversions. Round-trip PnL reconciles to it exactly.</p>
      <p class="note" style="font-size:13px;color:var(--text-2)">A trade is rebuilt from fills using the signed position size after each fill. Fills in the same second on the same side count as one order. Position flips close one trade and open the next.</p>
      <p class="note" style="font-size:13px;color:var(--text-2)">Positions already open when the data starts count toward PnL, not toward holding-time or size statistics. Drawdown is measured in ${esc(r.summary.currency)}, not percent, because deposits distort percentages.</p></div>`);
}

const PAGE_RENDER = { overview: pageOverview, edge: pageEdge, symbols: pageSymbols, timing: pageTiming, risk: pageRisk, market: pageMarket, trades: pageTrades };

/* ------------------------------------------------------------ render */
const view = $("#view");
function setStatus(msg) { $("#status").textContent = msg; }
function setBusy(on) {
  $("#progress").classList.toggle("on", on);
  view.classList.toggle("busy", on && !!state.report);
  view.setAttribute("aria-busy", on ? "true" : "false");
}
function skeleton() {
  disposeCharts();
  view.innerHTML = `<div class="skel s12" style="height:96px"></div><div class="kpis">${'<div class="skel" style="height:104px"></div>'.repeat(6)}</div>
    <div class="skel s8" style="height:420px"></div><div class="skel s4" style="height:420px"></div>`;
}
function renderPages() {
  $("#pages").innerHTML = PAGES.map((p) => `<button class="pane-btn" type="button" data-page="${p.id}" ${p.id === state.page ? 'aria-current="page"' : ""}>${icon(p.id)}<span class="txt">${esc(p.label)}</span></button>`).join("");
}
function renderSources() {
  const src = state.sources || {};
  const order = ["owner", "local", "demo", "api", "csv"].filter((k) => src[k]);
  $("#sources").innerHTML = order.map((k) => {
    const info = { ...SOURCE_INFO[k] };
    if (k === "owner" && src.owner_meta?.label) info.label = src.owner_meta.label;
    if (k === "owner" && src.owner_meta?.published_at) info.detail = `Snapshot, ${fmt.date(Date.parse(src.owner_meta.published_at))}`;
    if (k === "api" && state.source === "api" && state.report) info.detail = state.report.meta.source.detail || info.detail;
    if (k === "csv" && state.source === "csv" && state.report) info.detail = state.report.meta.source.detail || info.detail;
    return `<button class="pane-btn" type="button" data-source="${k}" aria-pressed="${state.source === k}">${icon(k)}<span class="txt">${esc(info.label)}<small>${esc(info.detail)}</small></span></button>`;
  }).join("");
}
function renderFilters() {
  const r = state.report, meta = r?.meta;
  const presets = [["all", "All"], [90, "90D"], [30, "30D"], [7, "7D"]];
  const active = activePreset();
  $("#presets").innerHTML = presets.map(([k, l]) => `<button class="pane-btn" type="button" data-preset="${k}" aria-pressed="${active === String(k)}" ${meta ? "" : "disabled"}>${l}</button>`).join("");
  const from = $("#from"), to = $("#to");
  if (meta) {
    const lo = fmt.iso(meta.data_start), hi = fmt.iso(meta.data_end);
    for (const el of [from, to]) { el.min = lo; el.max = hi; el.disabled = false; }
    from.value = state.f.start || lo;
    to.value = state.f.end || hi;
  } else { from.disabled = to.disabled = true; }
  const n = state.f.symbols.length;
  $("#symBtn").innerHTML = `${icon("filter")}<span class="txt">${n ? `${n} symbol${n > 1 ? "s" : ""} selected` : "All symbols"}<small>${meta ? `${fmt.int(meta.symbols.length)} traded` : ""}</small></span>`;
  $("#symBtn").setAttribute("aria-pressed", n ? "true" : "false");
  renderSymbolList();
  const ccys = meta?.currencies || [];
  $("#ccyGroup").hidden = ccys.length < 2;
  $("#currency").innerHTML = ccys.map((c) => `<option ${c === meta.currency ? "selected" : ""}>${esc(c)}</option>`).join("");
}
function renderSymbolList() {
  const meta = state.report?.meta;
  if (!meta) return;
  const q = $("#symSearch").value.trim().toUpperCase();
  const sel = new Set(state.f.symbols);
  const list = meta.symbols.filter((s) => !q || s.includes(q));
  $("#symList").innerHTML = list.slice(0, 300).map((s) => `<label><input type="checkbox" value="${esc(s)}" ${sel.has(s) ? "checked" : ""}>${esc(s)}</label>`).join("") ||
    `<p class="note">No symbols match.</p>`;
  $("#symCount").textContent = sel.size ? `${sel.size} selected` : "Showing all";
}
function activePreset() {
  const meta = state.report?.meta;
  if (!state.f.start && !state.f.end) return "all";
  if (!meta || state.f.end) return null;
  for (const d of [90, 30, 7]) if (state.f.start === fmt.iso(meta.data_end - (d - 1) * 864e5)) return String(d);
  return null;
}
function renderHeader() {
  const page = PAGES.find((p) => p.id === state.page);
  $("#pageTitle").textContent = page.label;
  const r = state.report;
  if (!r) { $("#pageSub").textContent = page.sub; $("#chips").innerHTML = ""; return; }
  $("#pageSub").textContent = page.sub;
  const s = r.summary, src = r.meta.source || {};
  const chips = [`<span class="chip">${icon(src.kind === "demo" ? "demo" : src.kind || "database")}<b>${esc(src.label || "Data")}</b></span>`];
  if (!r.empty) {
    chips.push(`<span class="chip">${icon("calendar")}${fmt.date(s.start)} to ${fmt.date(s.end)}</span>`);
    chips.push(`<span class="chip">${fmt.int(s.trades)} trades, ${fmt.int(s.symbols_traded)} symbols</span>`);
  }
  if (r.meta.filters.symbols.length) chips.push(`<span class="chip">${icon("filter")}${r.meta.filters.symbols.length} symbols</span>`);
  if (src.kind === "demo") chips.push(`<span class="chip">${icon("info")}Synthetic, not a real account</span>`);
  $("#chips").innerHTML = chips.join("");
}
function renderView() {
  disposeCharts();
  const r = state.report;
  if (!r) return;
  if (r.empty) {
    view.innerHTML = emptyState("No closed trades in this selection", "Widen the period or clear the symbol filter.", "filter");
    return;
  }
  view.innerHTML = PAGE_RENDER[state.page](r);
  requestAnimationFrame(mountVisibleCharts);
}
function render() { renderPages(); renderSources(); renderFilters(); renderHeader(); renderView(); }

/* -------------------------------------------------------------- data */
function filterParams() {
  const f = state.f, o = {};
  if (f.currency) o.currency = f.currency;
  if (f.start) o.start = f.start;
  if (f.end) o.end = f.end;
  if (f.symbols.length) o.symbols = f.symbols.join(",");
  if (f.tilt !== 15) o.tilt = String(f.tilt);
  return o;
}
async function request(body) {
  const id = ++state.reqId;
  setBusy(true);
  try {
    let res;
    if (body) res = await fetch(API, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    else res = await fetch(`${API}?${new URLSearchParams({ source: state.source, ...filterParams() })}`);
    let data;
    try { data = await res.json(); } catch { throw new Error(`The server returned HTTP ${res.status}.`); }
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    if (id !== state.reqId) return null;
    return data;
  } finally {
    if (id === state.reqId) setBusy(false);
  }
}
async function load() {
  if (!state.report) skeleton();
  setStatus("Loading report");
  try {
    const body = ["api", "csv"].includes(state.source) ? { source: "dataset", dataset: state.dataset, filters: filterParams() } : null;
    const data = await request(body);
    if (!data) return;
    state.report = data.report;
    state.f.currency = data.report.meta.currency;
    render();
    setStatus(`${PAGES.find((p) => p.id === state.page).label} updated`);
  } catch (e) {
    showError(e.message);
  }
}
function showError(msg) {
  setStatus(msg);
  if (!state.report) {
    disposeCharts();
    view.innerHTML = `<div class="error-box glass" role="alert">${icon("alert")}<div><b>Couldn't load the report</b><p class="note" style="font-size:13px">${esc(msg)}</p>
      <button class="btn" type="button" id="retry" style="margin-top:8px">Try again</button></div></div>`;
  } else toast(msg);
}
let toastTimer;
function toast(msg) {
  let el = $("#toast");
  if (!el) { el = document.createElement("div"); el.id = "toast"; el.className = "toast glass"; el.setAttribute("role", "status"); document.body.append(el); }
  el.textContent = msg;
  el.classList.add("on");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("on"), 5000);
}
function resetFilters() { state.f = { currency: null, start: null, end: null, symbols: [], tilt: 15 }; state.ui.tradePage = 0; }
function selectSource(k) {
  if (k === "api") { openApiDialog(); return; }
  if (k === "csv") { $("#csvInput").click(); return; }
  if (k === state.source) return;
  state.source = k; state.dataset = null; state.report = null;
  resetFilters(); writeHash(); renderSources(); load();
}

/* ---------------------------------------------------------- dialogs */
const dlg = $("#apiDialog");
function openApiDialog() { $("#apiError").textContent = ""; dlg.showModal(); $("#apiKey").focus(); }
function clearApiForm() { $("#apiKey").value = ""; $("#apiSecret").value = ""; }
$("#apiCancel").addEventListener("click", () => { clearApiForm(); dlg.close(); });
dlg.addEventListener("close", clearApiForm);
$("#pwToggle").addEventListener("click", (e) => {
  const inp = $("#apiSecret"), show = inp.type === "password";
  inp.type = show ? "text" : "password";
  e.currentTarget.setAttribute("aria-pressed", String(show));
  e.currentTarget.setAttribute("aria-label", show ? "Hide secret" : "Show secret");
  e.currentTarget.innerHTML = icon(show ? "eyeOff" : "eye");
});
$("#apiForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = $("#apiSubmit");
  const credentials = { api_key: $("#apiKey").value.trim(), api_secret: $("#apiSecret").value.trim(),
    days: Number($("#apiDays").value), testnet: $("#apiTestnet").checked };
  if (!credentials.api_key || !credentials.api_secret) { $("#apiError").textContent = "Enter both the key and the secret."; return; }
  btn.disabled = true; btn.textContent = "Fetching from Bybit";
  $("#apiError").textContent = "";
  try {
    resetFilters();
    const data = await request({ source: "api", credentials, filters: {} });
    if (!data) return;
    state.source = "api"; state.dataset = data.dataset; state.report = data.report; state.f.currency = data.report.meta.currency;
    dlg.close(); writeHash(); render();
  } catch (err) {
    $("#apiError").textContent = err.message;
  } finally {
    credentials.api_key = credentials.api_secret = "";
    btn.disabled = false; btn.textContent = "Fetch and analyse";
  }
});
$("#csvInput").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  e.target.value = "";
  if (!file) return;
  if (file.size > 4e6) { toast("That file is over 4 MB. Run the project locally for large exports."); return; }
  try {
    const csv = await file.text();
    resetFilters();
    const data = await request({ source: "csv", csv, filters: {} });
    if (!data) return;
    state.source = "csv"; state.dataset = data.dataset; state.report = data.report; state.f.currency = data.report.meta.currency;
    writeHash(); render();
  } catch (err) { showError(err.message); }
});

/* ----------------------------------------------------------- events */
function writeHash() {
  const p = new URLSearchParams({ page: state.page });
  if (state.source && !["api", "csv"].includes(state.source)) p.set("source", state.source);
  history.replaceState(null, "", `#${p}`);
}
function readHash() {
  const p = new URLSearchParams(location.hash.slice(1));
  if (PAGES.some((x) => x.id === p.get("page"))) state.page = p.get("page");
  return p.get("source");
}
function goPage(id) {
  state.page = id; writeHash(); renderPages(); renderHeader(); renderView(); closePane();
  window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
  $("#main").focus({ preventScroll: true });
}
let filterTimer;
function filtersChanged(delay = 0) {
  clearTimeout(filterTimer);
  state.ui.tradePage = 0;
  filterTimer = setTimeout(load, delay);
}

document.addEventListener("click", (e) => {
  const t = e.target.closest("button");
  if (!t) return;
  if (t.dataset.page) goPage(t.dataset.page);
  else if (t.dataset.source) { selectSource(t.dataset.source); closePane(); }
  else if (t.dataset.preset) {
    const meta = state.report?.meta;
    if (!meta) return;
    const k = t.dataset.preset;
    state.f.start = k === "all" ? null : fmt.iso(meta.data_end - (Number(k) - 1) * 864e5);
    state.f.end = null;
    renderFilters(); filtersChanged();
  } else if (t.dataset.tilt) { state.f.tilt = Number(t.dataset.tilt); filtersChanged(); }
  else if (t.dataset.outcome) { state.ui.tradeOutcome = t.dataset.outcome; state.ui.tradePage = 0; renderView(); }
  else if (t.dataset.pg) { state.ui.tradePage += Number(t.dataset.pg); $("#tradeTable").innerHTML = tradesTable(state.report); }
  else if (t.dataset.sort) {
    const key = t.dataset.key, which = t.dataset.sort === "trades" ? "tradeSort" : "symSort";
    const cur = state.ui[which];
    state.ui[which] = { key, dir: cur.key === key && cur.dir === "desc" ? "asc" : "desc" };
    if (which === "tradeSort") { state.ui.tradePage = 0; $("#tradeTable").innerHTML = tradesTable(state.report); }
    else renderView();
  } else if (t.id === "retry") load();
  else if (t.id === "dlTrades") downloadTrades();
  else if (t.id === "symBtn") {
    const panel = $("#symPanel"), open = panel.hidden;
    panel.hidden = !open; t.setAttribute("aria-expanded", String(open));
    if (open) $("#symSearch").focus();
  } else if (t.id === "symClear") { state.f.symbols = []; renderFilters(); filtersChanged(); }
  else if (t.id === "menuBtn") openPane();
});
document.addEventListener("toggle", (e) => { if (e.target.matches?.("details") && e.target.open) requestAnimationFrame(mountVisibleCharts); }, true);
$("#symList").addEventListener("change", (e) => {
  const v = e.target.value, sel = new Set(state.f.symbols);
  e.target.checked ? sel.add(v) : sel.delete(v);
  state.f.symbols = [...sel].sort();
  const n = state.f.symbols.length;
  $("#symBtn .txt").firstChild.textContent = n ? `${n} symbol${n > 1 ? "s" : ""} selected` : "All symbols";
  $("#symCount").textContent = n ? `${n} selected` : "Showing all";
  filtersChanged(700);
});
$("#symSearch").addEventListener("input", renderSymbolList);
for (const id of ["from", "to"]) {
  $(`#${id}`).addEventListener("change", (e) => {
    const meta = state.report?.meta;
    const v = e.target.value || null;
    if (id === "from") state.f.start = meta && v === fmt.iso(meta.data_start) ? null : v;
    else state.f.end = meta && v === fmt.iso(meta.data_end) ? null : v;
    renderFilters(); filtersChanged();
  });
}
$("#currency").addEventListener("change", (e) => { state.f.currency = e.target.value; state.f.symbols = []; filtersChanged(); });
view.addEventListener("input", (e) => {
  if (e.target.id === "tq") {
    state.ui.tradeQuery = e.target.value; state.ui.tradePage = 0;
    $("#tradeTable").innerHTML = tradesTable(state.report);
  }
});
function downloadTrades() {
  const rows = filteredTrades(state.report), cols = state.report.trades.columns;
  const cell = (v) => (v == null ? "" : typeof v === "string" && /[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v);
  const iso = (k, v) => (["open_time", "close_time"].includes(k) && isNum(v) ? new Date(v).toISOString() : v);
  const csv = [cols.join(","), ...rows.map((r) => cols.map((c) => cell(iso(c, r[c]))).join(","))].join("\n");
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(new Blob([csv], { type: "text/csv" })), download: "round_trips.csv" });
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
function openPane() { $("#pane").classList.add("open"); $("#scrim").classList.add("on"); $("#menuBtn").setAttribute("aria-expanded", "true"); }
function closePane() { $("#pane").classList.remove("open"); $("#scrim").classList.remove("on"); $("#menuBtn").setAttribute("aria-expanded", "false"); }
$("#scrim").addEventListener("click", closePane);
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closePane(); });

window.addEventListener("hashchange", () => {
  const p = new URLSearchParams(location.hash.slice(1));
  const page = p.get("page"), src = p.get("source");
  if (src && src !== state.source && state.sources?.[src] && !["api", "csv"].includes(src)) {
    if (page && PAGES.some((x) => x.id === page)) state.page = page;
    selectSource(src);
  } else if (page && page !== state.page && PAGES.some((x) => x.id === page)) goPage(page);
});

/* ------------------------------------------------------------- boot */
async function boot() {
  const wanted = readHash();
  renderPages(); renderHeader(); skeleton();
  try {
    const res = await fetch(`${API}?action=sources`);
    state.sources = await res.json();
    if (!res.ok) throw new Error(state.sources.error || `HTTP ${res.status}`);
  } catch (e) {
    state.sources = { demo: true, api: true, csv: true, default: "demo" };
  }
  state.source = wanted && state.sources[wanted] && !["api", "csv"].includes(wanted) ? wanted : state.sources.default;
  writeHash(); renderSources(); renderFilters();
  load();
}
boot();
