// Review page: reads the latest run bundle and renders Table, Exceptions and NAV trend.
// Every value is clickable and opens its source in the side panel.

const AS_OF_CHOICES = ["2025-12-31", "2025-09-30", "2025-06-30", "2025-03-31"];
const STATUS_SHORT = {
  not_found: "not found", not_verified: "not verified", not_reported: "not reported by fund",
  not_applicable: "not applicable", not_extracted: "not extracted in v1", excluded_by_rule: "excluded",
  fetch_failed: "fetch failed",
};
const EXCEPTION_TITLES = {
  conflict: "Conflicts between filings", missing: "Missing or not verified", lag: "Data lags",
  data_quality: "Filing data quality", client_data: "Apex Ridge data checks (question for the client)",
  check_failed: "Low confidence: review before use", amendment: "Amendments (EDGAR index check)",
  not_comparable: "Not directly comparable", peer_question: "Peer set questions", fetch: "EDGAR errors",
  computed: "Computed values (formula and inputs)", not_like_for_like: "Not like-for-like",
};
const FUND_COLORS = { "Apex Ridge": "#1f4e79", CCLFX: "#0f766e", TAKIX: "#7c3aed", GBDC: "#b45309", KREF: "#6b7280" };

let bundle = null;
let chart = null;

const $ = (sel) => document.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

function fmt(rec) {
  if (rec.value === null || rec.value === undefined) return "—";
  const v = Number(rec.value);
  if (rec.unit === "usd") return "$" + v.toFixed(2);
  if (rec.unit === "pct") return v.toFixed(2) + "%";
  return v.toFixed(2) + "x";
}
const shortDate = (d) => { if (!d) return ""; const [y, m, day] = d.split("-"); return `${+m}/${+day}/${y.slice(2)}`; };
const metricLabel = (key) => (bundle.rows.find(([k]) => k === key) || [key, key])[1];

// ---------- Table ----------
function renderTable() {
  const funds = bundle.funds;
  const nav = bundle.table.nav_per_share;
  let html = "<thead><tr><th>Metric</th>";
  for (const f of funds) {
    const rec = nav[f];
    let sub = f === "Apex Ridge" ? "client data" : rec.period_end ? `as of ${shortDate(rec.period_end)}` : "";
    if (rec.lag_quarters) sub += ` · ${rec.lag_quarters}Q lag`;
    const tag = f === "KREF" ? '<span class="tag" title="Not a like-for-like peer; CIO to decide">peer?</span>' : "";
    html += `<th>${esc(f)}${tag}<span class="sub">${esc(sub)}</span></th>`;
  }
  html += "</tr></thead><tbody>";
  for (const [metric, label] of bundle.rows) {
    html += `<tr><td class="metric">${esc(label)}</td>`;
    for (const f of funds) html += cellHtml(bundle.table[metric][f], metric, f);
    html += "</tr>";
  }
  $("#bench").innerHTML = html + "</tbody>";
  $("#footnotes").innerHTML = (bundle.footnotes || []).map((n) => `<li>${esc(n)}</li>`).join("");
  document.querySelectorAll("#bench td.val").forEach((td) =>
    td.addEventListener("click", () => openPanel(bundle.table[td.dataset.metric][td.dataset.fund], td)));
}

function cellHtml(rec, metric, fund) {
  const cls = fund === "Apex Ridge" ? "val apex" : "val";
  const attrs = `class="${cls}" data-metric="${metric}" data-fund="${esc(fund)}"`;
  const label = rec.label ? `<span class="label">${esc(rec.label)}</span>` : "";
  if (rec.status !== "ok") {
    return `<td ${attrs} title="${esc(rec.reason)}">${label}<span class="gap">${esc(rec.gap)}</span></td>`;
  }
  const dot = rec.confidence ? `<span class="dot ${rec.confidence}" title="${rec.confidence} confidence"></span>` : "";
  const flags = (rec.flags || []).filter((f) => f.startsWith("Superseded")).map((f) => `<span class="flag">${esc(f)}</span>`).join("");
  // A value older than the column's NAV date says so in the cell (e.g. CCLFX returns as of 3/31/25).
  const navDate = bundle.table.nav_per_share[fund]?.period_end;
  const asOf = rec.lag_quarters && rec.period_end !== navDate
    ? `<span class="flag">as of ${shortDate(rec.period_end)} · ${rec.lag_quarters}Q lag</span>` : "";
  return `<td ${attrs}>${label}${fmt(rec)}${dot}${rec.note ? `<span class="note">${esc(rec.note)}</span>` : ""}${asOf}${flags}</td>`;
}

// ---------- Side panel ----------
function highlight(quote, rec) {
  const safe = esc(quote);
  if (rec.value === null) return safe;
  const shown = Number(rec.value).toFixed(2).replace(/^-/, "");
  return safe.split(shown).join(`<mark>${shown}</mark>`);
}

function openPanel(rec, el) {
  document.querySelectorAll("td.selected").forEach((t) => t.classList.remove("selected"));
  if (el) el.classList.add("selected");
  const c = rec.citation;
  let h = `<h2>${esc(rec.fund)} · ${esc(rec.label || metricLabel(rec.metric))}</h2>`;
  h += `<div class="big">${fmt(rec)}</div>`;
  if (rec.period_end) h += `<div class="muted">Period ending ${esc(rec.period_end)}${rec.lag_quarters ? ` · ${rec.lag_quarters} quarter(s) before the as-of date` : ""}</div>`;
  if (rec.status !== "ok") {
    h += `<h4>Why there is no value</h4><p class="reason"><b>${esc(STATUS_SHORT[rec.status] || rec.status)}</b>: ${esc(rec.reason)}</p>`;
  }
  if (rec.confidence) {
    h += `<h4>Confidence</h4><p class="reason"><span class="dot ${rec.confidence}"></span><b>${rec.confidence}</b>: ${esc(rec.confidence_reason)}</p>`;
  } else if (rec.status === "ok") {
    h += `<h4>Confidence</h4><p class="reason">${esc(rec.confidence_reason)}</p>`;
  }
  if (c) {
    h += "<h4>Source</h4><dl>";
    if (c.cik === "client") {
      h += `<dt>Source</dt><dd>Client-provided file ${esc(c.document)}</dd><dt>Row / column</dt><dd>${esc(c.row_label)} / ${esc(c.column_label)}</dd>`;
    } else {
      h += `<dt>Filing</dt><dd><a href="${esc(c.url)}" target="_blank" rel="noopener">${esc(c.form)} · ${esc(c.accession)}</a></dd>`;
      h += `<dt>Filed</dt><dd>${esc(c.filing_date)}</dd>`;
      h += `<dt>Section</dt><dd>${esc(c.section)}</dd>`;
      if (c.row_label) h += `<dt>Row</dt><dd>${esc(c.row_label)}${c.column_label ? ` · column ${esc(c.column_label)}` : ""}</dd>`;
      if (c.fact_id) h += `<dt>XBRL tag</dt><dd>${esc(c.concept)} (element ${esc(c.fact_id)})</dd>`;
      h += `<dt>Document</dt><dd><a href="${esc(c.url)}" target="_blank" rel="noopener">${esc(c.document)}</a></dd>`;
      if (c.find_match) h += `<dt>Find it</dt><dd>Search the page for "${esc(c.row_label)}": it is match ${c.find_match} of ${c.find_total}.</dd>`;
      if (c.column_header) h += `<dt>Column header</dt><dd>${esc(c.column_header.replace(" | ", " "))}</dd>`;
      if (c.sha256) h += `<dt>File hash</dt><dd class="muted">SHA-256 ${esc(c.sha256.slice(0, 16))}… (verified unchanged)</dd>`;
    }
    h += "</dl>";
    if (c.quote) h += `<div class="muted">Source text${c.char_offset != null ? ` (found at character ${c.char_offset})` : ""}:</div><blockquote>${highlight(c.quote, rec)}</blockquote>`;
  }
  if (rec.inputs?.length) {
    h += `<h4>Inputs (each verified in its filing)</h4><ol class="inputs">${rec.inputs.map((x) => {
      const xc = x.citation;
      return `<li><b>${esc(x.value)}</b> · ${esc(xc.row_label || xc.section)}${xc.column_label ? ` · ${esc(xc.column_label)}` : ""}<br>
        <a href="${esc(xc.url)}" target="_blank" rel="noopener">${esc(xc.form)} ${esc(xc.accession)}</a> · ${esc(xc.section)}
        ${xc.find_match ? `<br><span class="muted">Search "${esc(xc.row_label)}": match ${xc.find_match} of ${xc.find_total}</span>` : ""}
        <blockquote>${esc(xc.quote)}</blockquote></li>`;
    }).join("")}</ol>`;
  }
  if (rec.check) h += `<h4>Independent check</h4><p class="reason">${esc(rec.check)}</p>`;
  if (rec.normalizations?.length) h += `<h4>${rec.method === "computed" ? "Calculation" : "Note"}</h4><ul>${rec.normalizations.map((n) => `<li>${esc(n)}</li>`).join("")}</ul>`;
  if (rec.resolution) h += `<h4>How we chose</h4><p class="reason">${esc(rec.resolution)}</p>`;
  const recon = rec.candidates?.find((x) => x.reconciliation && c && x.citation.accession === c.accession);
  if (recon) h += `<h4>Check</h4><p class="reason">${esc(recon.reconciliation)}</p>`;
  if (rec.candidates?.length > 1) {
    h += `<h4>All sources seen for this period</h4><ul>${rec.candidates.map((x) =>
      `<li>${esc(x.value)} · ${esc(x.citation.form)} ${esc(x.citation.accession)} · ${x.verified ? "verified" : "not verified: " + esc(x.verify_reason)}</li>`).join("")}</ul>`;
  }
  $("#panel-body").innerHTML = h;
  $("#panel").hidden = false;
  $("#panel").scrollTop = 0;
  document.body.classList.add("panel-open");
}

// ---------- Exceptions ----------
function renderExceptions() {
  const groups = {};
  for (const issue of bundle.issues) (groups[issue.kind] ||= []).push(issue);
  $("#exc-count").textContent = bundle.issues.length || "";
  let h = "";
  for (const kind of Object.keys(EXCEPTION_TITLES)) {
    if (!groups[kind]) continue;
    h += `<div class="exc-group"><h3>${EXCEPTION_TITLES[kind]} (${groups[kind].length})</h3><ul>`;
    for (const [i, issue] of groups[kind].entries()) {
      const linked = issue.metric && bundle.table[issue.metric]?.[issue.fund];
      h += `<li class="${linked ? "link" : ""}" data-kind="${kind}" data-i="${i}"><span class="fund">${esc(issue.fund)}</span>${esc(issue.message)}</li>`;
    }
    h += "</ul></div>";
  }
  $("#exceptions").innerHTML = h || '<p class="muted">No exceptions.</p>';
  document.querySelectorAll(".exc-group li.link").forEach((li) => li.addEventListener("click", () => {
    const issue = groups[li.dataset.kind][li.dataset.i];
    openPanel(bundle.table[issue.metric][issue.fund]);
  }));
}

// ---------- NAV trend ----------
function renderTrend() {
  const funds = Object.keys(bundle.trend);
  const quarters = bundle.trend[funds[0]].map((p) => p.period_end);
  const datasets = funds.map((f) => ({
    label: f === "KREF" ? "KREF (Book value per share)" : f,
    data: bundle.trend[f].map((p) => (p.status === "ok" ? Number(p.value) : null)),
    borderColor: FUND_COLORS[f], backgroundColor: FUND_COLORS[f],
    borderDash: f === "KREF" ? [5, 4] : [], pointRadius: 5, pointHoverRadius: 7, spanGaps: false, tension: 0,
  }));
  if (chart) chart.destroy();
  chart = new Chart($("#trend-chart"), {
    type: "line",
    data: { labels: quarters.map(shortDate), datasets },
    options: {
      maintainAspectRatio: false, interaction: { mode: "nearest", intersect: true },
      scales: { y: { ticks: { callback: (v) => "$" + v } } },
      plugins: {
        legend: { position: "bottom" },
        tooltip: { callbacks: { label: (ctx) => {
          const p = bundle.trend[funds[ctx.datasetIndex]][ctx.dataIndex];
          return `${ctx.dataset.label}: ${fmt(p)}${p.confidence ? ` (${p.confidence})` : ""}`;
        } } },
      },
      onClick: (_e, els) => { if (els.length) openPanel(bundle.trend[funds[els[0].datasetIndex]][els[0].index]); },
    },
  });
  let h = `<thead><tr><th>Fund</th>${quarters.map((q) => `<th>${shortDate(q)}</th>`).join("")}</tr></thead><tbody>`;
  for (const f of funds) {
    h += `<tr><td>${esc(f === "KREF" ? "KREF (Book value per share)" : f)}</td>`;
    bundle.trend[f].forEach((p, i) => {
      const body = p.status === "ok" ? `${fmt(p)}${p.confidence ? `<span class="dot ${p.confidence}"></span>` : ""}`
        : `<span class="missing">—</span>`;
      h += `<td class="val" data-fund="${esc(f)}" data-i="${i}" title="${esc(p.status === "ok" ? "" : p.reason)}">${body}</td>`;
    });
    h += "</tr>";
  }
  $("#trend-table").innerHTML = h + "</tbody>";
  document.querySelectorAll("#trend-table td.val").forEach((td) =>
    td.addEventListener("click", () => openPanel(bundle.trend[td.dataset.fund][td.dataset.i], td)));
}

// ---------- Run / load ----------
function renderAll() {
  const shown = Object.values(bundle.table).flatMap((r) => Object.values(r))
    .filter((r) => r.status === "ok" && r.method !== "client_csv").length;
  const when = new Date(bundle.created_at).toLocaleString();
  $("#run-info").textContent = `As of ${bundle.as_of} · run ${when} · ${shown} competitor values verified · ${bundle.filings.length} filings read`;
  setAsOf(bundle.as_of);
  renderTable();
  renderExceptions();
  if (!$("#tab-trend").hidden) renderTrend();
}

// Load the latest run, or the latest run for one quarter-end. Returns false if there is none.
async function loadBundle(asOf) {
  const resp = await fetch(asOf ? `/api/bundle?as_of=${asOf}` : "/api/bundle");
  if (!resp.ok) {
    if (!bundle) $("#run-info").textContent = "No run yet. Choose a quarter-end and press Run.";
    return false;
  }
  bundle = await resp.json();
  renderAll();
  return true;
}

// Picking a quarter shows its latest run straight away; if it has never been run, say so.
async function pickQuarter(d) {
  setAsOf(d);
  if (bundle && bundle.as_of === d) return;
  if (await loadBundle(d)) { showStatus(""); return; }
  showStatus(`No run for ${quarterName(d)} yet. Press Run to build it (about 20 seconds).`);
}

// Export the run on screen. The server also keeps a copy in exports/ and says where.
async function exportExcel() {
  if (!bundle) { showStatus("Run the benchmark first.", true); return; }
  showStatus("Building the Excel file…");
  const resp = await fetch(`/api/export.xlsx?as_of=${bundle.as_of}`);
  if (!resp.ok) { showStatus("Export failed: " + ((await resp.json()).detail || resp.status), true); return; }
  const saved = resp.headers.get("X-Saved-Path");
  const name = saved ? saved.split("/").pop() : `peer_benchmark_${bundle.as_of}.xlsx`;
  const url = URL.createObjectURL(await resp.blob());
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
  showStatus(`Downloaded ${name}. A copy is also saved at ${saved}`);
}

function showStatus(text, isError = false) {
  const el = $("#status");
  el.hidden = !text;
  el.textContent = text;
  el.classList.toggle("error", isError);
}

async function startRun() {
  $("#run-btn").disabled = true;
  const resp = await fetch("/api/run", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ as_of: selectedAsOf }),
  });
  if (!resp.ok) {
    showStatus((await resp.json()).detail || "Could not start the run.", true);
    $("#run-btn").disabled = false;
    return;
  }
  const poll = setInterval(async () => {
    const s = await (await fetch("/api/status")).json();
    showStatus(s.error || s.message, Boolean(s.error));
    if (!s.running) {
      clearInterval(poll);
      $("#run-btn").disabled = false;
      if (!s.error) { showStatus(""); await loadBundle(selectedAsOf); }
    }
  }, 1000);
}

function selectTab(name) {
  document.querySelectorAll(".tabs button").forEach((b) => b.setAttribute("aria-selected", b.dataset.tab === name));
  document.querySelectorAll(".tab").forEach((t) => (t.hidden = t.id !== `tab-${name}`));
  if (name === "trend" && bundle) renderTrend();
}

// Quarter-end picker: four small buttons (a native dropdown opened far too large on the analyst's screen).
let selectedAsOf = AS_OF_CHOICES[0];
const quarterName = (d) => { const [y, m] = d.split("-"); return `Q${+m / 3} ${y}`; };
function setAsOf(d) {
  selectedAsOf = d;
  document.querySelectorAll("#as-of button").forEach((b) => b.setAttribute("aria-checked", b.dataset.date === d));
}
$("#as-of").innerHTML = AS_OF_CHOICES.map((d) =>
  `<button type="button" role="radio" data-date="${d}" title="${d}">${quarterName(d)}</button>`).join("");
document.querySelectorAll("#as-of button").forEach((b) => b.addEventListener("click", () => pickQuarter(b.dataset.date)));
$("#export-btn").addEventListener("click", exportExcel);
setAsOf(selectedAsOf);
const closePanel = () => { $("#panel").hidden = true; document.body.classList.remove("panel-open"); };
$("#run-btn").addEventListener("click", startRun);
$("#panel-close").addEventListener("click", closePanel);
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closePanel(); });
document.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => selectTab(b.dataset.tab)));
loadBundle();
