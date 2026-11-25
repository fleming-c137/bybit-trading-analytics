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
  assets: '<circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/>',
  habits: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
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
  { id: "overview", label: "Overview", sub: "Am I making money, and what is driving it?" },
  { id: "timing", label: "When to trade", sub: "Your best hours, days and sessions, and how the market moves each weekday" },
  { id: "assets", label: "What to trade", sub: "Which asset classes and coins make money, and which you trade most" },
  { id: "habits", label: "Habits", sub: "Holding time, trading after losses and busy days" },
  { id: "trades", label: "Trade log", sub: "Every trade, rebuilt from your transaction history" },
]
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
        symSort: { key: "net_pnl", dir: "desc" }, localTime: false },
};

/* ------------------------------------------------------------ charts */
const T = {
  text1: "#f4f2ee", text2: "rgba(244,242,238,0.8)", text3: "rgba(244,242,238,0.62)",
  grid: "rgba(255,255,255,0.09)", axis: "rgba(255,255,255,0.22)",
  gain: "#199e70", loss: "#e66767", mid: "#383835", accent: "#f07a35", font: "Inter, system-ui, sans-serif",
};
const charts = new Map();
const pending = new Map();

function tooltipBase(extra = {}) {
  return {
    backgroundColor: "rgba(28,29,34,0.88)", borderColor: "rgba(255,255,255,0.22)", borderWidth: 1,
    padding: [8, 12], textStyle: { color: T.text1, fontSize: 12, fontFamily: T.font },
    extraCssText: "border-radius:10px;box-shadow:0 10px 28px rgba(0,0,0,.4);backdrop-filter:blur(12px);", confine: true, ...extra,
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
  // Few categories: show every label (wrapped) instead of letting ECharts skip some.
  axisLabel: { color: T.text3, fontSize: 11, ...(data.length <= 12 ? { interval: 0, width: 86, overflow: "break", lineHeight: 14 } : {}) },
  ...extra,
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
const zeroLine = { silent: true, symbol: "none", label: { show: false }, lineStyle: { color: "rgba(255,255,255,0.32)", type: "solid", width: 1 }, data: [{ yAxis: 0 }] };
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
      type: "line", data, showSymbol: false, lineStyle: { width: 2, color: T.accent }, itemStyle: { color: T.accent },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: "rgba(240,122,53,0.32)" }, { offset: 1, color: "rgba(240,122,53,0.02)" }]) },
      markLine: zeroLine,
    }],
  };
}
function dailyPnlChart(daily, ccy) {
  return {
    xAxis: timeAxis(), yAxis: valueAxis(),
    dataZoom: [{ type: "inside" }, { type: "slider", height: 18, bottom: 4, borderColor: "transparent", backgroundColor: "rgba(255,255,255,0.05)",
      fillerColor: "rgba(240,122,53,0.22)", handleStyle: { color: "#f07a35", borderColor: "transparent" }, moveHandleStyle: { color: "rgba(255,255,255,.22)" },
      textStyle: { color: T.text3 }, dataBackground: { lineStyle: { color: "rgba(255,255,255,.25)" }, areaStyle: { color: "rgba(255,255,255,.06)" } } }],
    grid: { left: 6, right: 14, top: 14, bottom: 34, containLabel: true },
    tooltip: { trigger: "axis", formatter: (p) => {
      const d = daily[p[0].dataIndex];
      return ttHead(fmt.date(d.date)) + ttRow("Net PnL", `${fmt.money(d.pnl)} ${ccy}`) + ttRow("Gross", fmt.money(d.gross)) + ttRow("Fees", fmt.money(d.fees)) + ttRow("Funding", fmt.money(d.funding, 3));
    } },
    series: [{ type: "bar", barMaxWidth: 10, data: daily.map((d) => ({ value: [d.date, d.pnl], itemStyle: { color: signColor(d.pnl), borderRadius: d.pnl >= 0 ? [3, 3, 0, 0] : [0, 0, 3, 3] } })) }],
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
    series: [{ type: "heatmap", data, itemStyle: { borderColor: "rgba(20,21,25,0.6)", borderWidth: 2, borderRadius: 3 }, emphasis: { itemStyle: { borderColor: T.text1, borderWidth: 1 } } }],
  };
}
function kpi(label, value, { unit = "", foot = "", tone = null, meter = null, text = false } = {}) {
  const tag = tone ? `<span class="tag ${tone.dir > 0 ? "pos" : "neg"}">${icon(tone.dir > 0 ? "up" : "down")}${esc(tone.text)}</span>` : "";
  const m = meter ? `<div class="meter" aria-hidden="true"><span style="width:${Math.max(0, Math.min(100, meter.value * 100))}%;background:${meter.value >= meter.target ? T.gain : T.loss}"></span><i style="left:calc(${Math.max(0, Math.min(100, meter.target * 100))}% - 1px)"></i></div>` : "";
  return `<article class="kpi glass"><div class="kpi-label">${esc(label)}${unit ? `<span class="unit">${esc(unit)}</span>` : ""}</div>
    <div class="kpi-value${text ? " txt" : ""}">${value}</div>${m}<div class="kpi-foot">${tag}${foot ? `<span>${foot}</span>` : ""}</div></article>`;
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
const pnlClass = (v) => (v >= 0 ? "pos" : "neg");
const money0 = (v) => (isNum(v) && Math.abs(v) >= 100 ? fmt.money(v, 0) : fmt.money(v));
function bwRow(r, dim) { return (r.best_worst || []).find((x) => x.dimension === dim); }
function bwTile(label, entry, kind, ccy) {
  if (!entry) return kpi(label, "–");
  const e = entry[kind];
  return kpi(label, esc(e.label), { text: true, foot: `<span class="dot ${pnlClass(e.net_pnl)}" aria-hidden="true"></span>${money0(e.net_pnl)} ${esc(ccy)} &middot; ${fmt.pct(e.win_rate)} win` });
}
function verdictBlock(r) {
  const v = r.verdict, rc = r.recent || {}, ccy = r.summary.currency;
  const stat = (label, val) => `<div class="vstat"><span>${label}</span><b><span class="dot ${pnlClass(val)}" aria-hidden="true"></span>${money0(val)}</b></div>`;
  return `<section class="verdict glass ${v.tone}" aria-labelledby="vt">
    <div class="verdict-icon">${icon(v.tone === "positive" ? "check" : "alert")}</div>
    <div><h2 id="vt">${esc(v.title)}</h2><p>${esc(v.text)}</p></div>
    <div class="verdict-stats" aria-label="Recent results in ${esc(ccy)}">
      ${stat(`Last day (${fmt.date(rc.last_day, { month: "short", day: "numeric" })})`, rc.today)}${stat("Last 7 days", rc.d7)}${stat("Last 30 days", rc.d30)}
    </div></section>`;
}
function rankList(rows, ccy, { key = "symbol", n = 5 } = {}) {
  const max = Math.max(...rows.map((d) => Math.abs(d.net_pnl)), 1e-9);
  return `<ol class="rank">${rows.slice(0, n).map((d, i) => `<li><span class="rank-n">${i + 1}</span><span class="rank-name">${esc(d[key])}</span>
    <span class="rank-bar"><i class="${pnlClass(d.net_pnl)}" style="width:${(Math.abs(d.net_pnl) / max) * 100}%"></i></span>
    <span class="rank-val">${money0(d.net_pnl)}</span><span class="rank-sub">${fmt.int(d.trades)} trades, ${fmt.pct(d.win_rate)} win</span></li>`).join("")}</ol>`;
}

function pageOverview(r) {
  const s = r.summary, ccy = s.currency, be = s.breakeven_win_rate, h = r.highlights || { working: [], costing: [] };
  const kpis = `<div class="kpis">
    ${kpi("Win rate", fmt.pct(s.win_rate), { meter: isNum(be) ? { value: s.win_rate, target: be } : null,
        foot: `${fmt.int(s.wins)} wins, ${fmt.int(s.losses)} losses${isNum(be) ? ` &middot; need ${fmt.pct(be)}` : ""}` })}
    ${kpi("Average win / loss", `${fmt.money(s.avg_win)} <span class="kpi-sep">/</span> ${fmt.money(s.avg_loss)}`, { unit: ccy,
        foot: isNum(s.payoff_ratio) ? `Wins are ${fmt.num(s.payoff_ratio, 1)}x the size of losses` : "" })}
    ${kpi("Trades", fmt.int(s.trades), { foot: `${fmt.num(s.trades_per_active_day, 1)} per trading day &middot; ${fmt.int(s.symbols_traded)} coins` })}
    ${kpi("Fees paid", fmt.num(-s.fees, 0), { unit: ccy, foot: s.net_pnl < 0 && s.fees < 0 ? `${fmt.pct(Math.min(1, -s.fees / Math.abs(s.net_pnl)))} of your net loss` : "" })}
    ${kpi("Biggest drop", fmt.money(s.max_drawdown_usdt, 0), { unit: ccy, foot: "From your best point to your worst" })}
  </div>`;
  const list = (items, kind) => items.length ? `<ul class="hl ${kind}">${items.map((t) => `<li>${icon(kind === "good" ? "check" : "alert")}<span>${esc(t)}</span></li>`).join("")}</ul>` : `<p class="note">Nothing stands out yet.</p>`;
  const hl = `<section class="card glass s4"><h3 class="card-title">What's working</h3>${list(h.working, "good")}
    <h3 class="card-title" style="margin-top:14px">What's costing you</h3>${list(h.costing, "bad")}</section>`;
  const bw = r.best_worst || [];
  const cell = (e) => `<b>${esc(e.label)}</b><span class="bw-v"><span class="dot ${pnlClass(e.net_pnl)}" aria-hidden="true"></span>${money0(e.net_pnl)}</span><span class="bw-s">${fmt.pct(e.win_rate)} win &middot; ${fmt.int(e.trades)} trades</span>`;
  const bwTable = `<div class="bw" role="table" aria-label="Best and worst by category">
    <div class="bw-row bw-head" role="row"><span role="columnheader"></span><span role="columnheader">Best</span><span role="columnheader">Worst</span></div>
    ${bw.map((x) => `<div class="bw-row" role="row"><span class="bw-dim" role="rowheader">${esc(x.dimension)}</span><span class="bw-cell" role="cell">${cell(x.best)}</span><span class="bw-cell" role="cell">${cell(x.worst)}</span></div>`).join("")}</div>`;
  queueChart("c-cum", cumPnlChart(r.daily, ccy));
  queueChart("c-daily", dailyPnlChart(r.daily, ccy));
  return verdictBlock(r) + kpis +
    card("Your PnL over time", `Running total after fees, deposits excluded (${esc(ccy)})`, chartBox("c-cum", "tall", "Cumulative PnL line chart"), "s8") + hl +
    card("Best and worst", "Where you made and lost the most, by net PnL", bwTable) +
    accordion("Daily results", "Each day's PnL; drag the slider to zoom", chartBox("c-daily", "", "Daily PnL bar chart"));
}

function localOffsetHours() { return -new Date().getTimezoneOffset() / 60; }
function hourRows(rows) {
  const off = localOffsetHours();
  if (!state.ui.localTime || !Number.isInteger(off) || off === 0) return rows;
  return [...rows].map((r) => ({ ...r, hour: (r.hour + off + 24) % 24 })).sort((a, b) => a.hour - b.hour);
}
function pageTiming(r) {
  const ccy = r.summary.currency, be = r.summary.breakeven_win_rate, m = r.market_weekdays || {};
  const hour = bwRow(r, "Hour of day (UTC)"), day = bwRow(r, "Day of week"), ses = bwRow(r, "Session");
  const kpis = `<div class="kpis">${bwTile("Best hour (UTC)", hour, "best", ccy)}${bwTile("Worst hour (UTC)", hour, "worst", ccy)}
    ${bwTile("Best day", day, "best", ccy)}${bwTile("Worst day", day, "worst", ccy)}${bwTile("Best session", ses, "best", ccy)}</div>`;
  const off = localOffsetHours(), canLocal = Number.isInteger(off) && off !== 0;
  const tz = canLocal ? `<div class="mini-seg" role="group" aria-label="Time zone"><button class="btn" type="button" data-tz="utc" aria-pressed="${!state.ui.localTime}">UTC</button>
    <button class="btn" type="button" data-tz="local" aria-pressed="${!!state.ui.localTime}">Your time (UTC${off > 0 ? "+" : ""}${off})</button></div>` : "";
  const hrs = hourRows(r.by_hour).filter((d) => d.trades > 0);
  queueChart("c-hour", bucketChart(hrs, "hour", "net_pnl", { ccy, labelFmt: (h) => String(h).padStart(2, "0") }));
  queueChart("c-wd", bucketChart(r.by_weekday, "weekday", "net_pnl", { ccy, labelFmt: (d) => d.slice(0, 3) }));
  let market = `<p class="note">BTC candles aren't available for this data source.</p>`;
  if (m.available) {
    queueChart("c-mkt", {
      xAxis: catAxis(m.rows.map((d) => d.weekday.slice(0, 3))), yAxis: valueAxis((v) => fmt.pct(v, 1)),
      tooltip: { trigger: "item", formatter: (p) => { const d = m.rows[p.dataIndex]; return ttHead(`${d.weekday}, ${m.symbol.replace("USDT", "")}`) + ttRow("Average move", fmt.pct(d.avg_return, 2, true)) + ttRow("Green days", fmt.pct(d.up_share)) + ttRow("Days measured", fmt.int(d.days)); } },
      series: [{ type: "bar", barMaxWidth: 34, data: m.rows.map((d) => signBar(d.avg_return)), markLine: zeroLine }],
    });
    market = chartBox("c-mkt", "", "Average BTC daily move by weekday");
  }
  const mSub = m.available ? `Bitcoin's average daily move${m.widened ? " over all available history" : ` over ${m.weeks} weeks`}. Pumps most on <b>${esc(m.pump)}</b> (${fmt.pct(m.pump_avg, 2, true)}, ${fmt.pct(m.pump_up)} green), dumps most on <b>${esc(m.dump)}</b> (${fmt.pct(m.dump_avg, 2, true)}).` : "";
  const sessions = `<div class="sessions">${r.by_session.map((x) => `<div class="session ${pnlClass(x.net_pnl)}"><div class="row-between"><b>${esc(x.session)}</b><span class="note">${esc(x.hours)} UTC</span></div>
    <div class="session-v">${money0(x.net_pnl)} <small>${esc(ccy)}</small></div><div class="note">${fmt.pct(x.win_rate)} win &middot; ${fmt.int(x.trades)} trades</div></div>`).join("")}</div>`;
  queueChart("c-heat", heatmapChart(r.by_hour_weekday, ccy));
  return kpis +
    card("Your results by hour", `Net PnL of trades opened in each hour (${esc(ccy)}). Hover for win rate.`, chartBox("c-hour", "", "Net PnL by hour opened"), "s12", tz) +
    card("Your results by day", `Net PnL of trades opened on each weekday (${esc(ccy)})`, chartBox("c-wd", "", "Net PnL by weekday"), "s6") +
    card("When the market pumps and dumps", mSub, market, "s6") +
    card("Trading sessions", "Asia, London and New York, by when the trade was opened", sessions) +
    accordion("Day and hour combined", "Every weekday and hour on one grid, UTC", chartBox("c-heat", "tall", "Heatmap of PnL by weekday and hour")) +
    (isNum(be) ? "" : "");
}

function pageAssets(r) {
  const ccy = r.summary.currency, ac = r.by_asset_class || [], sym = r.by_symbol || [];
  const most = [...ac].sort((a, b) => b.trades - a.trades)[0];
  const cls = bwRow(r, "Asset class"), coin = bwRow(r, "Coin");
  const kpis = `<div class="kpis">
    ${kpi("Most traded", esc(most?.asset_class ?? "–"), { text: true, foot: most ? `${fmt.pct(most.share)} of your trades` : "" })}
    ${bwTile("Best asset class", cls, "best", ccy)}${bwTile("Worst asset class", cls, "worst", ccy)}
    ${bwTile("Best coin", coin, "best", ccy)}${bwTile("Worst coin", coin, "worst", ccy)}</div>`;
  const byPnl = [...ac].sort((a, b) => b.net_pnl - a.net_pnl);
  queueChart("c-acpnl", bucketChart(byPnl, "asset_class", "net_pnl", { ccy, horizontal: true }));
  const byCount = [...ac].sort((a, b) => b.trades - a.trades);
  queueChart("c-account", {
    xAxis: valueAxis((v) => `${Math.round(v * 100)}%`), yAxis: catAxis(byCount.map((d) => d.asset_class), { inverse: true, axisLabel: { color: T.text2, fontSize: 11 } }),
    grid: { left: 6, right: 48, top: 6, bottom: 6, containLabel: true },
    tooltip: { trigger: "item", formatter: (p) => { const d = byCount[p.dataIndex]; return ttHead(d.asset_class) + ttRow("Share of trades", fmt.pct(d.share, 1)) + ttRow("Trades", fmt.int(d.trades)) + ttRow("Coins", fmt.int(d.symbols)); } },
    series: [{ type: "bar", barMaxWidth: 16, data: byCount.map((d) => ({ value: d.share, itemStyle: { color: T.accent, borderRadius: [0, 4, 4, 0] } })),
      label: { show: true, position: "right", color: T.text2, fontSize: 11, formatter: (p) => fmt.pct(p.value) } }],
  });
  const classCols = [
    { key: "asset_class", label: "Asset class" }, { key: "trades", label: "Trades", num: true, fmt: fmt.int },
    { key: "win_rate", label: "Win rate", num: true, fmt: (v) => fmt.pct(v) }, { key: "net_pnl", label: "Net PnL", num: true, fmt: signed(0) },
    { key: "best_symbol", label: "Best coin" }, { key: "worst_symbol", label: "Worst coin", fmt: (v, r) => (v === r.best_symbol ? "–" : esc(v)) },
  ];
  const sorted = [...sym].sort((a, b) => b.net_pnl - a.net_pnl);
  const top = sorted.filter((d) => d.net_pnl > 0), bottom = sorted.filter((d) => d.net_pnl < 0).reverse();
  const dir = Object.fromEntries((r.by_direction || []).map((d) => [d.direction, d]));
  const side = (name) => { const d = dir[name]; return d ? `<div class="session ${pnlClass(d.net_pnl)}"><b>${name}s</b><div class="session-v">${money0(d.net_pnl)} <small>${esc(ccy)}</small></div><div class="note">${fmt.pct(d.win_rate)} win &middot; ${fmt.int(d.trades)} trades</div></div>` : ""; };
  const symCols = [
    { key: "symbol", label: "Coin" }, { key: "trades", label: "Trades", num: true, fmt: fmt.int },
    { key: "net_pnl", label: "Net PnL", num: true, fmt: signed() }, { key: "win_rate", label: "Win rate", num: true, fmt: (v) => fmt.pct(v) },
    { key: "fees", label: "Fees", num: true, fmt: (v) => fmt.money(v) }, { key: "median_hold_min", label: "Typical hold", num: true, fmt: fmt.dur },
  ];
  return kpis +
    card("Profit by asset class", `Net PnL after fees (${esc(ccy)})`, chartBox("c-acpnl", "", "Net PnL by asset class"), "s6") +
    card("What you trade most", "Share of your trades in each asset class", chartBox("c-account", "", "Share of trades by asset class"), "s6") +
    card("Asset classes at a glance", "", table(classCols, byPnl)) +
    card("Top coins", "Most profitable", top.length ? rankList(top, ccy) : `<p class="note">No profitable coins in this period.</p>`, "s6") +
    card("Bottom coins", "Biggest losses", bottom.length ? rankList(bottom, ccy) : `<p class="note">No losing coins in this period.</p>`, "s6") +
    card("Longs vs shorts", "", `<div class="sessions two">${side("Long")}${side("Short")}</div>`) +
    accordion("Every coin", `${fmt.int(sym.length)} coins, click a column to sort`, `<div id="symTable">${table(symCols, sortRows(sym, state.ui.symSort), { sort: state.ui.symSort, sortId: "sym" })}</div>`);
}

function pageHabits(r) {
  const s = r.summary, ccy = s.currency, be = s.breakeven_win_rate, h = r.highlights || { costing: [] };
  const hold = r.by_holding_time || [];
  const holdLine = h.costing.find((t) => t.startsWith("Trades closed")) || (r.highlights.working || []).find((t) => t.startsWith("Trades held")) || "";
  queueChart("c-holdnet", bucketChart(hold, "hold", "net_pnl", { ccy }));
  queueChart("c-holdwin", winRateChart(hold, "hold", be));
  const tiltOrder = (c) => (c.startsWith("≤") && c.includes("loss") ? 0 : c.startsWith("≤") ? 1 : 2);
  const tilt = [...(r.tilt || [])].sort((a, b) => tiltOrder(a.context) - tiltOrder(b.context));
  const tiltLabel = (c) => c.replace(/^≤(\d+)m after a loss$/, "Within $1 min of a loss").replace(/^≤(\d+)m after a win$/, "Within $1 min of a win").replace(/^>(\d+)m since last trade$/, "After a break");
  const tiltRows = tilt.map((t) => ({ ...t, context: tiltLabel(t.context) }));
  queueChart("c-tilt", winRateChart(tiltRows, "context", be));
  const busy = r.busy_days || [];
  queueChart("c-busy", bucketChart(busy, "trade_bucket", "avg_pnl", { ccy, labelFmt: (x) => `${x} trades` }));
  const w = state.f.tilt;
  const seg = `<div class="mini-seg" role="group" aria-label="Minutes after previous trade">${[5, 15, 30, 60].map((m) => `<button class="btn" type="button" data-tilt="${m}" aria-pressed="${m === w}">${m}m</button>`).join("")}</div>`;
  const lev = r.by_leverage || [];
  if (lev.length) queueChart("c-lev", bucketChart(lev, "lev_bucket", "net_pnl", { ccy }));
  const typical = fmt.dur(s.median_hold_min);
  const kpis = `<div class="kpis">
    ${kpi("Typical hold", typical, { foot: "Half your trades close faster" })}
    ${kpi("Trades per day", fmt.num(s.trades_per_active_day, 1), { foot: "On days you trade" })}
    ${kpi("Longest losing streak", fmt.int(s.max_loss_streak), { foot: `Longest winning streak ${fmt.int(s.max_win_streak)}` })}
    ${kpi("Liquidations", fmt.int(s.liquidations), { foot: s.liquidations ? `Cost ${fmt.num(-s.liquidation_pnl, 0)} ${esc(ccy)}` : "None" })}
  </div>`;
  return kpis +
    card("How long you hold", esc(holdLine) || `Net PnL by holding time (${esc(ccy)})`, chartBox("c-holdnet", "", "Net PnL by holding time"), "s6") +
    card("Win rate by holding time", "Bars above the dashed line win often enough to make money", chartBox("c-holdwin", "", "Win rate by holding time"), "s6") +
    card("Trading right after a loss", "Win rate of trades opened soon after the previous one closed", chartBox("c-tilt", "", "Win rate after a loss, after a win and after a break"), "s6", seg) +
    card("Busy days", "Average result of a day, by how many trades you made", chartBox("c-busy", "", "Average daily PnL by trades per day"), "s6") +
    (lev.length ? accordion("Leverage", "Net PnL by the leverage you used", chartBox("c-lev", "", "Net PnL by leverage")) : "");
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

const PAGE_RENDER = { overview: pageOverview, timing: pageTiming, assets: pageAssets, habits: pageHabits, trades: pageTrades };

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
  } else if (t.dataset.tz) { state.ui.localTime = t.dataset.tz === "local"; renderView(); }
  else if (t.dataset.tilt) { state.f.tilt = Number(t.dataset.tilt); filtersChanged(); }
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
