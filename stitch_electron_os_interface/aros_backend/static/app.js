let token = null;
let cachedProducts = [];
let cachedPareto = null;
let wizardGroups = []; // [{ id, name, barcodes: [] }]
let currentCurrency = "$";
let currentLocation = "main"; // "main" | "all" | a Tamil Nadu store_id
let currentNewsLocation = "main";
let currentReportLocation = "main";
let currentReportId = null;
let currentChatBase = null; // "/api/reports/<id>" or "/api/plans/<id>" - see the LLM chat modal section
let currentPlanId = null;
let planStarted = false;
let planIntakeStep = 0;
let planAnswers = { location: "main", goal: null, timeframe: null, budget: null };

// ---------- theme tokens ----------
// Applied via style.setProperty rather than a stylesheet rule - a bare
// `html { --c-x: ... }` rule as the first rule in the inline <style> block
// was observed to be silently dropped from the parsed CSSOM in this
// Electron/Chromium build, leaving every bg-*/text-*/border-* utility that
// references these variables resolving to nothing. Setting them imperatively
// on document.documentElement sidesteps that entirely.

const THEMES = {
  dark: {
    "--c-deep-obsidian": "#0A0A0C",
    "--c-slate-gray": "#1A1A1E",
    "--c-on-surface": "#e5e1e4",
    "--c-on-surface-variant": "#b9cacb",
    "--c-outline-variant": "#3b494b",
    "--c-surface-variant": "#353437",
    "--c-electric-blue": "#00F0FF",
    "--c-data-positive": "#00FF41",
    "--c-data-negative": "#FF3131",
  },
  light: {
    "--c-deep-obsidian": "#F8F9FA",
    "--c-slate-gray": "#FFFFFF",
    "--c-on-surface": "#1A1A1E",
    "--c-on-surface-variant": "#5B6770",
    "--c-outline-variant": "#E2E5E7",
    "--c-surface-variant": "#EEF0F1",
    "--c-electric-blue": "#006970",
    "--c-data-positive": "#0A7A2F",
    "--c-data-negative": "#B00020",
  },
};

function applyTheme(mode) {
  const vars = THEMES[mode];
  for (const [key, value] of Object.entries(vars)) {
    document.documentElement.style.setProperty(key, value);
  }
}

applyTheme("dark");

// ---------- low-level API helper ----------

async function api(path, options = {}) {
  const headers = options.headers || {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (options.body) headers["Content-Type"] = "application/json";
  const res = await fetch(path, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

// ---------- view switching ----------

function showAuthMode(mode) {
  document.querySelectorAll("[data-auth-mode]").forEach((el) => {
    el.classList.toggle("hidden", el.dataset.authMode !== mode);
  });
}

function showView(view) {
  document.querySelectorAll("main [data-view]").forEach((el) => {
    el.classList.toggle("active", el.dataset.view === view);
  });
  document.querySelectorAll(".nav-link").forEach((el) => {
    const active = el.dataset.view === view;
    el.classList.toggle("text-electric-blue", active);
    el.classList.toggle("font-bold", active);
    el.classList.toggle("border-r-2", active);
    el.classList.toggle("border-electric-blue", active);
    el.classList.toggle("text-on-surface-variant", !active);
  });
  // The Reports and Plan tabs both have their own right-aligned header
  // controls (history dropdowns, buttons) in the same corner - the fixed
  // one would otherwise sit on top of them and intercept clicks, so hide
  // the redundant fixed one on those tabs.
  const fixedGenerateBtn = document.getElementById("generate-report-btn");
  if (fixedGenerateBtn) fixedGenerateBtn.style.display = view === "reports" || view === "plan" ? "none" : "flex";
}

document.querySelectorAll(".nav-link").forEach((el) => {
  el.addEventListener("click", (e) => {
    e.preventDefault();
    if (el.dataset.view === "wizard") {
      openWizard();
    } else if (el.dataset.view === "news") {
      showNews();
    } else if (el.dataset.view === "reports") {
      showReports();
    } else if (el.dataset.view === "plan") {
      showPlan();
    } else {
      showView(el.dataset.view);
    }
  });
});

// ---------- boot / auth ----------

async function boot() {
  const status = await api("/api/auth/status");
  showAuthMode(status.has_user ? "login" : "setup");
}

async function doSetup() {
  const errorEl = document.getElementById("setup-error");
  errorEl.textContent = "";
  try {
    const username = document.getElementById("setup-username").value;
    const password = document.getElementById("setup-password").value;
    const result = await api("/api/auth/setup", { method: "POST", body: JSON.stringify({ username, password }) });
    token = result.token;
    await afterLogin(username);
  } catch (e) {
    errorEl.textContent = e.message;
  }
}

async function doLogin() {
  const errorEl = document.getElementById("login-error");
  errorEl.textContent = "";
  try {
    const username = document.getElementById("login-username").value;
    const password = document.getElementById("login-password").value;
    const result = await api("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
    token = result.token;
    await afterLogin(username);
  } catch (e) {
    errorEl.textContent = e.message;
  }
}

function logout() {
  token = null;
  document.getElementById("app-shell").classList.add("hidden");
  document.getElementById("auth-screen").classList.add("active");
  document.getElementById("auth-screen").classList.remove("hidden");
  document.getElementById("login-username").value = "";
  document.getElementById("login-password").value = "";
  showAuthMode("login");
}

async function afterLogin(username) {
  document.getElementById("auth-screen").classList.add("hidden");
  document.getElementById("auth-screen").classList.remove("active");
  document.getElementById("app-shell").classList.remove("hidden");
  document.getElementById("current-username").textContent = username;

  try {
    await api("/api/categories");
    await showInsights();
  } catch (e) {
    await openWizard();
  }
  populateLocationSelector();
}

// ---------- category wizard (real product <-> category reassignment) ----------

function newGroupId() {
  return "g" + Math.random().toString(36).slice(2, 9);
}

async function openWizard() {
  const [products, existing] = await Promise.all([
    api("/api/products"),
    api("/api/categories").catch(() => null),
  ]);
  cachedProducts = products;

  let assignments;
  if (existing && existing.assignments && Object.keys(existing.assignments).length) {
    assignments = { ...existing.assignments };
  } else {
    assignments = (await api("/api/categories/template")).assignments;
  }

  // Products added to pos_system.db after categories were last saved have no
  // assignment yet — surface them in an "Uncategorized" group instead of
  // silently dropping them from the wizard (and from by-category insights).
  products.forEach((p) => {
    if (!(p.barcode in assignments)) assignments[p.barcode] = "Uncategorized";
  });

  const byCategory = {};
  for (const [barcode, category] of Object.entries(assignments)) {
    byCategory[category] = byCategory[category] || [];
    byCategory[category].push(barcode);
  }

  wizardGroups = Object.entries(byCategory).map(([name, barcodes]) => ({
    id: newGroupId(),
    name,
    barcodes,
  }));

  renderWizard();
  showView("wizard");
}

function productName(barcode) {
  const p = cachedProducts.find((p) => p.barcode === barcode);
  return p ? p.name : barcode;
}

function renderWizard() {
  const container = document.getElementById("wizard-groups");
  container.innerHTML = "";

  wizardGroups.forEach((group) => {
    const card = document.createElement("div");
    card.className = "glass-panel rounded-lg p-4";
    card.innerHTML = `
      <input class="field-input rounded px-3 py-1.5 text-sm font-bold w-full max-w-xs mb-3" data-group-id="${group.id}" type="text" value="${group.name}">
      <div class="space-y-1" data-group-rows="${group.id}"></div>
    `;
    container.appendChild(card);

    const rowsEl = card.querySelector(`[data-group-rows="${group.id}"]`);
    group.barcodes.forEach((barcode) => {
      const row = document.createElement("div");
      row.className = "flex items-center justify-between py-1.5 border-t border-outline-variant/50 first:border-t-0";
      const select = document.createElement("select");
      select.className = "field-input rounded px-2 py-1 text-xs";
      select.dataset.barcode = barcode;
      wizardGroups.forEach((g) => {
        const opt = document.createElement("option");
        opt.value = g.id;
        opt.textContent = g.name;
        if (g.id === group.id) opt.selected = true;
        select.appendChild(opt);
      });
      const newOpt = document.createElement("option");
      newOpt.value = "__new__";
      newOpt.textContent = "+ New category…";
      select.appendChild(newOpt);
      select.addEventListener("change", () => moveProduct(barcode, group.id, select));

      row.innerHTML = `<span class="text-sm">${productName(barcode)}</span>`;
      row.appendChild(select);
      rowsEl.appendChild(row);
    });
  });

  container.querySelectorAll("input[data-group-id]").forEach((input) => {
    input.addEventListener("change", () => {
      const group = wizardGroups.find((g) => g.id === input.dataset.groupId);
      if (group && input.value.trim()) group.name = input.value.trim();
      renderWizard();
    });
  });
}

function moveProduct(barcode, fromGroupId, selectEl) {
  let targetGroupId = selectEl.value;

  if (targetGroupId === "__new__") {
    const name = prompt("New category name:");
    if (!name || !name.trim()) {
      renderWizard();
      return;
    }
    const group = { id: newGroupId(), name: name.trim(), barcodes: [] };
    wizardGroups.push(group);
    targetGroupId = group.id;
  }

  const from = wizardGroups.find((g) => g.id === fromGroupId);
  const to = wizardGroups.find((g) => g.id === targetGroupId);
  from.barcodes = from.barcodes.filter((b) => b !== barcode);
  to.barcodes.push(barcode);

  renderWizard();
}

async function saveCategories() {
  const errorEl = document.getElementById("wizard-error");
  errorEl.textContent = "";
  try {
    const assignments = {};
    wizardGroups.forEach((group) => {
      group.barcodes.forEach((barcode) => {
        assignments[barcode] = group.name;
      });
    });
    if (!Object.keys(assignments).length) throw new Error("No products assigned to any category.");
    await api("/api/categories", { method: "POST", body: JSON.stringify({ assignments }) });
    await showInsights();
  } catch (e) {
    errorEl.textContent = e.message;
  }
}

// ---------- insights dashboard ----------

function pill(topPerformer) {
  return topPerformer
    ? '<span class="px-2 py-0.5 bg-data-positive/10 text-data-positive text-[10px] font-bold rounded">TOP PERFORMER</span>'
    : "";
}

function delta(pctChange) {
  const up = pctChange >= 0;
  const cls = up ? "text-data-positive" : "text-data-negative";
  const arrow = up ? "▲" : "▼";
  return `<span class="${cls}">${arrow} ${Math.abs(pctChange)}%</span>`;
}

function renderCategoryParetoTable(rows) {
  document.getElementById("pareto-category-table").innerHTML = rows
    .map(
      (r) => `<tr class="border-t border-outline-variant/50">
        <td class="px-4 py-2">${r.name}</td>
        <td class="px-4 py-2 text-right">${currentCurrency}${r.revenue.toFixed(2)}</td>
        <td class="px-4 py-2 text-right">${r.cumulative_pct}%</td>
      </tr>`
    )
    .join("");
}

function renderProductTable() {
  const filter = document.getElementById("product-filter").value.trim().toLowerCase();
  const rows = cachedPareto.by_product.filter((r) => r.name.toLowerCase().includes(filter));
  document.getElementById("pareto-product-table").innerHTML = rows
    .map(
      (r) => `<tr class="border-t border-outline-variant/50">
        <td class="px-4 py-2">${r.name}</td>
        <td class="px-4 py-2 text-right">${currentCurrency}${r.revenue.toFixed(2)}</td>
        <td class="px-4 py-2 text-right">${r.cumulative_pct}%</td>
        <td class="px-4 py-2 text-center">${pill(r.top_performer)}</td>
      </tr>`
    )
    .join("");
}

function renderTrendTable(tableId, rows) {
  document.getElementById(tableId).innerHTML = rows
    .map(
      (r) => `<tr class="border-t border-outline-variant/50">
        <td class="px-4 py-2">${r.name}</td>
        <td class="px-4 py-2 text-right">${currentCurrency}${r.baseline_avg_daily_revenue.toFixed(2)}</td>
        <td class="px-4 py-2 text-right">${currentCurrency}${r.recent_avg_daily_revenue.toFixed(2)}</td>
        <td class="px-4 py-2 text-right">${delta(r.pct_change)}</td>
      </tr>`
    )
    .join("");
}

// ---------- business scorecard ----------
// Business Health / Growth / Revenue Opportunity / Customer Health / Risk
// Alerts are classical (report_analysis.py, computed instantly alongside
// the rest of Insights - no LLM). Lead Score / Market Readiness / AI
// Recommendations / Executive Summary are the scorecard_advisor agent
// (agents.py), on demand via GENERATE AI INSIGHTS since they're a real
// local-model call, not something to fire silently on every page load.

function scoreColor(score) {
  if (score === null || score === undefined) return "text-on-surface-variant";
  if (score >= 75) return "text-data-positive";
  if (score >= 50) return "text-electric-blue";
  if (score >= 25) return "text-on-surface";
  return "text-data-negative";
}

function renderScorecard(scorecard, currency) {
  const { business_health, growth, revenue_opportunity, customer_health, risk_alerts } = scorecard;

  const scoreTile = (label, scoreObj, extra) => `
    <div class="glass-panel p-4 rounded-lg">
      <span class="font-label-caps text-[10px] text-on-surface-variant block mb-1">${label}</span>
      <h3 class="text-2xl font-black ${scoreColor(scoreObj.score)}">${scoreObj.score === null ? "—" : scoreObj.score}</h3>
      <span class="text-[10px] text-on-surface-variant capitalize">${escapeHtml(scoreObj.level)}</span>
      ${extra ? `<p class="text-[10px] text-on-surface-variant mt-1">${extra}</p>` : ""}
    </div>
  `;

  document.getElementById("scorecard-tiles").innerHTML =
    scoreTile("BUSINESS HEALTH", business_health) +
    scoreTile("GROWTH SCORE", growth, growth.tracked ? `${growth.trending_up}/${growth.tracked} trending up` : "") +
    `<div class="glass-panel p-4 rounded-lg">
      <span class="font-label-caps text-[10px] text-on-surface-variant block mb-1">REVENUE OPPORTUNITY</span>
      <h3 class="text-2xl font-black text-electric-blue">${currency}${revenue_opportunity.estimated_monthly_value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</h3>
      <span class="text-[10px] text-on-surface-variant">/mo from ${revenue_opportunity.products_affected} restocked item(s)</span>
    </div>` +
    scoreTile(
      "CUSTOMER HEALTH",
      customer_health,
      customer_health.visit_frequency_trend !== "n/a" ? `${customer_health.avg_daily_transactions} avg daily visits (${customer_health.visit_frequency_trend})` : ""
    );

  document.getElementById("scorecard-alerts").innerHTML = risk_alerts
    .map((a) => {
      const style =
        a.severity === "high"
          ? "border-data-negative/40 text-data-negative"
          : a.severity === "medium"
          ? "border-secondary/40 text-secondary"
          : "border-outline-variant text-on-surface-variant";
      const icon = a.severity === "high" ? "warning" : a.severity === "medium" ? "info" : "check_circle";
      return `<div class="glass-panel border ${style} rounded-lg px-4 py-2 flex items-center space-x-2 text-xs">
        <span class="material-symbols-outlined text-sm">${icon}</span>
        <span>${escapeHtml(a.text)}</span>
      </div>`;
    })
    .join("");

  // Clear stale AI content from whatever location/report was showing before.
  document.getElementById("ai-scorecard-content").innerHTML = "";
  document.getElementById("ai-scorecard-status").classList.add("hidden");
}

async function generateAiScorecard() {
  const btn = document.getElementById("ai-scorecard-btn");
  const statusEl = document.getElementById("ai-scorecard-status");
  const contentEl = document.getElementById("ai-scorecard-content");
  btn.disabled = true;
  statusEl.classList.remove("hidden", "text-data-negative");
  statusEl.textContent = "Asking the local LLM for Lead Score, Market Readiness, Recommendations, and an Executive Summary… (can take ~30-60s)";
  contentEl.innerHTML = "";

  try {
    const sections = await api(`/api/scorecard/ai?location=${encodeURIComponent(currentLocation)}`, { method: "POST" });
    statusEl.classList.add("hidden");
    contentEl.innerHTML = `
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div class="glass-panel rounded-lg p-4">
          <h4 class="font-label-caps text-[10px] text-secondary mb-2">LEAD SCORE (AI ESTIMATE)</h4>
          <p class="text-sm text-on-surface whitespace-pre-wrap leading-relaxed">${escapeHtml(sections["Lead Score"])}</p>
        </div>
        <div class="glass-panel rounded-lg p-4">
          <h4 class="font-label-caps text-[10px] text-secondary mb-2">MARKET READINESS (AI ESTIMATE)</h4>
          <p class="text-sm text-on-surface whitespace-pre-wrap leading-relaxed">${escapeHtml(sections["Market Readiness"])}</p>
        </div>
      </div>
      <div class="glass-panel rounded-lg p-4 mb-4">
        <h4 class="font-label-caps text-[10px] text-electric-blue mb-2">AI RECOMMENDATIONS</h4>
        <p class="text-sm text-on-surface whitespace-pre-wrap leading-relaxed">${escapeHtml(sections["AI Recommendations"])}</p>
      </div>
      <div class="glass-panel rounded-lg p-4">
        <h4 class="font-label-caps text-[10px] text-electric-blue mb-2">EXECUTIVE SUMMARY</h4>
        <p class="text-sm text-on-surface whitespace-pre-wrap leading-relaxed">${escapeHtml(sections["Executive Summary"])}</p>
      </div>
    `;
  } catch (e) {
    statusEl.classList.add("text-data-negative");
    statusEl.textContent = e.message;
  } finally {
    btn.disabled = false;
  }
}

async function showInsights() {
  currentLocation = "main";
  currentCurrency = "$";
  const locationSelect = document.getElementById("location-select");
  if (locationSelect) locationSelect.value = "main";

  const [products, categories, { pareto, trend_shifts, scorecard }] = await Promise.all([
    api("/api/products"),
    api("/api/categories"),
    api("/api/insights"),
  ]);
  cachedProducts = products;
  cachedPareto = pareto;
  renderScorecard(scorecard, "$");

  const totalRevenue = pareto.by_product.reduce((sum, r) => sum + r.revenue, 0);
  document.getElementById("kpi-revenue").textContent = `$${totalRevenue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  document.getElementById("kpi-products").textContent = products.length;
  document.getElementById("kpi-stockouts").textContent = products.filter((p) => p.stock === 0).length;
  document.getElementById("kpi-categories").textContent = new Set(Object.values(categories.assignments)).size;

  const uncategorizedCount = products.filter((p) => !(p.barcode in categories.assignments)).length;
  const warningEl = document.getElementById("uncategorized-warning");
  if (uncategorizedCount > 0) {
    const plural = uncategorizedCount > 1;
    document.getElementById("uncategorized-warning-text").textContent =
      `⚠ ${uncategorizedCount} product${plural ? "s" : ""} ${plural ? "have" : "has"} no category assigned — excluded from the by-category breakdown below.`;
    warningEl.classList.remove("hidden");
  } else {
    warningEl.classList.add("hidden");
  }

  renderCategoryParetoTable(pareto.by_category);
  document.getElementById("product-filter").value = "";
  renderProductTable();

  document.getElementById("trend-category-heading").textContent = `Trend Shifts — by Category (last ${trend_shifts.recent_window_days}d vs. baseline)`;
  document.getElementById("trend-product-heading").textContent = `Trend Shifts — by Product (last ${trend_shifts.recent_window_days}d vs. baseline)`;
  renderTrendTable("trend-category-table", trend_shifts.by_category);
  renderTrendTable("trend-product-table", trend_shifts.by_product);

  showView("insights");
}

async function refreshInsights() {
  const btn = document.getElementById("refresh-insights-btn");
  const label = btn.querySelector("span:last-child");
  const originalText = label.textContent;
  btn.disabled = true;
  btn.classList.add("opacity-50", "cursor-not-allowed");
  label.textContent = "REFRESHING…";
  try {
    if (currentLocation === "main") {
      await showInsights();
    } else {
      await showLocationInsights(currentLocation);
    }
  } catch (e) {
    label.textContent = "REFRESH FAILED";
  } finally {
    btn.disabled = false;
    btn.classList.remove("opacity-50", "cursor-not-allowed");
    setTimeout(() => { label.textContent = originalText; }, 1000);
  }
}

// ---------- Tamil Nadu multi-shop locations ----------
// Populated from pos-system/tamil_nadu_local_simulator.py's data (via
// HQ_Retail_OS/central_hq.db).

// Shared by the Insights and News location dropdowns. "Main Store" is always
// offered; the Tamil Nadu options only appear once the simulator has
// actually been run at least once.
async function populateLocationOptions(select, selectedValue, { hideIfNoLocations = false } = {}) {
  let locations = [];
  try {
    locations = await api("/api/locations");
  } catch (e) {
    locations = [];
  }

  if (hideIfNoLocations && !locations.length) {
    select.classList.add("hidden");
    return;
  }

  select.innerHTML = "";
  select.appendChild(new Option("Main Store (USD)", "main"));
  if (locations.length) {
    select.appendChild(new Option("All Tamil Nadu Locations (₹)", "all"));
    locations.forEach((loc) => {
      select.appendChild(new Option(`${loc.label} (₹)`, loc.store_id));
    });
  }
  select.value = selectedValue;
  select.classList.remove("hidden");
}

async function populateLocationSelector() {
  await populateLocationOptions(document.getElementById("location-select"), currentLocation, { hideIfNoLocations: true });
}

async function onLocationChange() {
  const value = document.getElementById("location-select").value;
  if (value === "main") {
    await showInsights();
  } else {
    currentLocation = value;
    currentCurrency = "₹";
    await showLocationInsights(value);
  }
}

async function showLocationInsights(location) {
  const { stats, pareto, trend_shifts, scorecard } = await api(`/api/location-insights?location=${encodeURIComponent(location)}`);
  cachedPareto = pareto;
  renderScorecard(scorecard, "₹");

  document.getElementById("kpi-revenue").textContent = `₹${stats.revenue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  document.getElementById("kpi-products").textContent = stats.products_tracked;
  document.getElementById("kpi-stockouts").textContent = stats.stockouts;
  document.getElementById("kpi-categories").textContent = pareto.by_category.length;

  // The uncategorized-product warning only applies to the main store's
  // user-editable categories - Tamil Nadu categories are derived automatically.
  document.getElementById("uncategorized-warning").classList.add("hidden");

  renderCategoryParetoTable(pareto.by_category);
  document.getElementById("product-filter").value = "";
  renderProductTable();

  document.getElementById("trend-category-heading").textContent = `Trend Shifts — by Category (last ${trend_shifts.recent_window_days}d vs. baseline)`;
  document.getElementById("trend-product-heading").textContent = `Trend Shifts — by Product (last ${trend_shifts.recent_window_days}d vs. baseline)`;
  renderTrendTable("trend-category-table", trend_shifts.by_category);
  renderTrendTable("trend-product-table", trend_shifts.by_product);

  showView("insights");
}

// ---------- news ----------
// Free, no-key Google News RSS (see aros_backend/news.py), filtered by the
// same location set as Insights.

function formatPublished(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function renderNewsCards(articles) {
  const container = document.getElementById("news-cards");
  const emptyState = document.getElementById("news-empty-state");
  if (!articles.length) {
    container.innerHTML = "";
    emptyState.classList.remove("hidden");
    return;
  }
  emptyState.classList.add("hidden");
  container.innerHTML = articles
    .map(
      (a) => `
      <a class="glass-panel p-4 rounded-lg border border-outline-variant hover:border-electric-blue/50 transition-colors cursor-pointer group block" href="${escapeHtml(a.link)}" rel="noopener noreferrer" target="_blank">
        <div class="flex justify-between items-start mb-2 gap-2">
          <span class="text-[10px] font-label-caps text-electric-blue">${escapeHtml((a.source || "NEWS").toUpperCase())}</span>
          <span class="text-[10px] text-on-surface-variant whitespace-nowrap">${formatPublished(a.published)}</span>
        </div>
        <h4 class="font-bold text-on-surface group-hover:text-electric-blue transition-colors text-sm leading-snug">${escapeHtml(a.title)}</h4>
      </a>`
    )
    .join("");
}

async function loadNews(location) {
  const label = document.getElementById("news-query-label");
  label.textContent = "Loading…";
  try {
    const { query, articles } = await api(`/api/news?location=${encodeURIComponent(location)}`);
    label.textContent = `Showing results for "${query}"`;
    renderNewsCards(articles);
  } catch (e) {
    label.textContent = "Couldn't load news — check your internet connection.";
    renderNewsCards([]);
  }
}

async function showNews() {
  await populateLocationOptions(document.getElementById("news-location-select"), currentNewsLocation);
  await loadNews(currentNewsLocation);
  showView("news");
}

async function onNewsLocationChange() {
  currentNewsLocation = document.getElementById("news-location-select").value;
  await loadNews(currentNewsLocation);
}

async function refreshNews() {
  const btn = document.getElementById("refresh-news-btn");
  const label = btn.querySelector("span:last-child");
  const originalText = label.textContent;
  btn.disabled = true;
  btn.classList.add("opacity-50", "cursor-not-allowed");
  label.textContent = "REFRESHING…";
  try {
    await loadNews(currentNewsLocation);
  } catch (e) {
    label.textContent = "REFRESH FAILED";
  } finally {
    btn.disabled = false;
    btn.classList.remove("opacity-50", "cursor-not-allowed");
    setTimeout(() => { label.textContent = originalText; }, 1000);
  }
}

// ---------- insights reports ----------
// Classical (non-LLM) analysis, generated on demand and saved to a file by
// the backend (aros_backend/reports.py). The "Full Report Text" block is
// exactly the payload sent to the local LLM - see sendReportToLLM() below.

function renderReportSection(section) {
  const { title, currency, analysis } = section;
  const s = analysis.summary;

  if (s.transactions === 0) {
    return `
      <div class="glass-panel rounded-lg p-6 mb-6">
        <h3 class="text-lg font-bold mb-2">${escapeHtml(title)}</h3>
        <p class="text-sm text-on-surface-variant">No sales data available for this section.</p>
      </div>`;
  }

  const trend = analysis.trend;
  const conc = analysis.concentration;
  const trendColor = trend.direction === "growing" ? "text-data-positive" : trend.direction === "declining" ? "text-data-negative" : "text-on-surface";

  const categoryRows = analysis.pareto.by_category
    .map(
      (r) => `<tr class="border-t border-outline-variant/50">
        <td class="px-4 py-2">${escapeHtml(r.name)}</td>
        <td class="px-4 py-2 text-right">${currency}${r.revenue.toFixed(2)}</td>
        <td class="px-4 py-2 text-right">${r.cumulative_pct}%</td>
        <td class="px-4 py-2 text-center">${pill(r.top_performer)}</td>
      </tr>`
    )
    .join("");

  const moverRows = analysis.trend_shifts.by_product
    .slice(0, 5)
    .map(
      (m) => `<tr class="border-t border-outline-variant/50">
        <td class="px-4 py-2">${escapeHtml(m.name)}</td>
        <td class="px-4 py-2 text-right">${delta(m.pct_change)}</td>
      </tr>`
    )
    .join("");

  const seasonalityRows = analysis.seasonality
    .map(
      (d) => `<tr class="border-t border-outline-variant/50">
        <td class="px-4 py-2">${d.weekday}</td>
        <td class="px-4 py-2 text-right">${currency}${d.avg_revenue.toFixed(2)}</td>
      </tr>`
    )
    .join("");

  const stockoutsText = analysis.stockouts.length ? escapeHtml(analysis.stockouts.join(", ")) : "None";

  return `
    <div class="glass-panel rounded-lg p-6 mb-6">
      <h3 class="text-lg font-bold mb-4">${escapeHtml(title)}</h3>

      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-surface-variant/20 rounded p-3">
          <span class="font-label-caps text-[10px] text-on-surface-variant block mb-1">REVENUE</span>
          <span class="text-lg font-black">${currency}${s.revenue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
        </div>
        <div class="bg-surface-variant/20 rounded p-3">
          <span class="font-label-caps text-[10px] text-on-surface-variant block mb-1">TRANSACTIONS</span>
          <span class="text-lg font-black">${s.transactions}</span>
        </div>
        <div class="bg-surface-variant/20 rounded p-3">
          <span class="font-label-caps text-[10px] text-on-surface-variant block mb-1">PRODUCTS TRACKED</span>
          <span class="text-lg font-black">${s.products_tracked}</span>
        </div>
        <div class="bg-surface-variant/20 rounded p-3">
          <span class="font-label-caps text-[10px] text-on-surface-variant block mb-1">STOCKOUTS</span>
          <span class="text-lg font-black text-data-negative">${s.stockouts}</span>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6 text-sm">
        <div class="border border-outline-variant rounded p-3">
          <span class="font-label-caps text-[10px] text-on-surface-variant block mb-1">REVENUE TREND (LEAST SQUARES)</span>
          <span class="font-bold ${trendColor}">${trend.direction}</span>
          <span class="text-on-surface-variant"> (${currency}${trend.slope_per_day.toFixed(2)}/day, R²=${trend.r_squared})</span>
        </div>
        <div class="border border-outline-variant rounded p-3">
          <span class="font-label-caps text-[10px] text-on-surface-variant block mb-1">REVENUE CONCENTRATION (HHI)</span>
          <span class="font-bold">Category:</span> ${conc.by_category.level} (${conc.by_category.hhi}) ·
          <span class="font-bold">Product:</span> ${conc.by_product.level} (${conc.by_product.hhi})
        </div>
      </div>

      ${categoryRows ? `
      <h4 class="font-bold text-sm mb-2">Pareto (80/20) — by Category</h4>
      <table class="w-full text-left font-data-code text-xs mb-6">
        <thead class="bg-surface-variant/30 text-on-surface-variant uppercase text-[10px]">
          <tr><th class="px-4 py-2">Category</th><th class="px-4 py-2 text-right">Revenue</th><th class="px-4 py-2 text-right">Cum. %</th><th class="px-4 py-2 text-center">Status</th></tr>
        </thead>
        <tbody>${categoryRows}</tbody>
      </table>` : ""}

      ${moverRows ? `
      <h4 class="font-bold text-sm mb-2">Biggest Week-over-Week Movers</h4>
      <table class="w-full text-left font-data-code text-xs mb-6"><tbody>${moverRows}</tbody></table>` : ""}

      ${seasonalityRows ? `
      <h4 class="font-bold text-sm mb-2">Day-of-Week Seasonality</h4>
      <table class="w-full text-left font-data-code text-xs mb-4"><tbody>${seasonalityRows}</tbody></table>` : ""}

      <p class="text-xs text-on-surface-variant"><span class="font-bold text-on-surface">Out of stock:</span> ${stockoutsText}</p>
    </div>
  `;
}

function renderReport(report) {
  currentReportId = report.id;
  document.getElementById("report-empty-state").classList.add("hidden");
  const generatedAt = new Date(report.generated_at).toLocaleString();
  const locationLabel = report.location_label || "Main Store (USD)";

  const sectionsHtml = report.sections.length
    ? report.sections.map(renderReportSection).join("")
    : `<div class="glass-panel rounded-lg p-6 text-sm text-on-surface-variant">No sales data was available for ${escapeHtml(locationLabel)} when this report was generated.</div>`;

  document.getElementById("report-content").innerHTML = `
    <p class="text-xs text-on-surface-variant mb-4">
      <span class="font-label-caps text-electric-blue">${escapeHtml(locationLabel)}</span> ·
      Generated ${generatedAt} — ${escapeHtml(report.method)}
    </p>
    ${sectionsHtml}
    <div class="glass-panel rounded-lg p-6">
      <h3 class="text-sm font-bold mb-3">Full Report Text</h3>
      <p class="text-xs text-on-surface-variant mb-3">This is exactly what gets forwarded to the local LLM for deeper, qualitative analysis.</p>
      <pre class="font-data-code text-xs whitespace-pre-wrap bg-deep-obsidian text-on-surface rounded p-4 max-h-72 overflow-y-auto border border-outline-variant">${escapeHtml(report.narrative)}</pre>
      <div class="flex flex-wrap items-center gap-4 mt-4">
        <button class="flex items-center space-x-2 border border-electric-blue text-electric-blue font-bold px-4 py-2 rounded transition-transform active:scale-95 hover:bg-electric-blue hover:text-deep-obsidian" id="send-to-llm-btn" onclick="sendReportToLLM()">
          <span class="material-symbols-outlined text-sm">psychology</span>
          <span class="font-label-caps text-[10px]">SEND TO LLM →</span>
        </button>
        <button class="flex items-center space-x-2 border border-secondary text-secondary font-bold px-4 py-2 rounded transition-transform active:scale-95 hover:bg-secondary hover:text-deep-obsidian" id="correlate-news-btn" onclick="correlateWithNews()">
          <span class="material-symbols-outlined text-sm">newspaper</span>
          <span class="font-label-caps text-[10px]">CORRELATE WITH NEWS →</span>
        </button>
        <span class="text-xs text-on-surface-variant" id="send-to-llm-status"></span>
      </div>
    </div>
  `;
}

async function loadReportHistory(selectedId) {
  const select = document.getElementById("report-history-select");
  try {
    const list = await api("/api/reports");
    if (!list.length) {
      select.classList.add("hidden");
      return [];
    }
    select.innerHTML = "";
    list.forEach((r) => {
      select.appendChild(new Option(`${new Date(r.generated_at).toLocaleString()} — ${r.location_label}`, r.id));
    });
    select.value = selectedId || list[0].id;
    select.classList.remove("hidden");
    return list;
  } catch (e) {
    select.classList.add("hidden");
    return [];
  }
}

async function showReports() {
  await populateLocationOptions(document.getElementById("report-location-select"), currentReportLocation);
  const list = await loadReportHistory(currentReportId);
  if (!list.length) {
    document.getElementById("report-empty-state").classList.remove("hidden");
    document.getElementById("report-content").innerHTML = "";
  } else {
    const idToLoad = document.getElementById("report-history-select").value;
    renderReport(await api(`/api/reports/${encodeURIComponent(idToLoad)}`));
  }
  showView("reports");
}

async function onReportHistoryChange() {
  const id = document.getElementById("report-history-select").value;
  renderReport(await api(`/api/reports/${encodeURIComponent(id)}`));
}

function onReportLocationChange() {
  currentReportLocation = document.getElementById("report-location-select").value;
}

async function generateReport() {
  const buttons = [document.getElementById("generate-report-btn"), document.getElementById("generate-report-btn-inline")].filter(Boolean);
  const originalLabels = buttons.map((b) => b.querySelector("span:last-child").textContent);
  buttons.forEach((b) => {
    b.disabled = true;
    b.classList.add("opacity-50", "cursor-not-allowed");
    b.querySelector("span:last-child").textContent = "ANALYZING…";
  });
  try {
    const report = await api(`/api/reports/generate?location=${encodeURIComponent(currentReportLocation)}`, { method: "POST" });
    await loadReportHistory(report.id);
    renderReport(report);
    showView("reports");
  } catch (e) {
    alert(`Couldn't generate report: ${e.message}`);
  } finally {
    buttons.forEach((b, i) => {
      b.disabled = false;
      b.classList.remove("opacity-50", "cursor-not-allowed");
      b.querySelector("span:last-child").textContent = originalLabels[i];
    });
  }
}

async function sendReportToLLM() {
  const btn = document.getElementById("send-to-llm-btn");
  const statusEl = document.getElementById("send-to-llm-status");
  btn.disabled = true;
  statusEl.textContent = "Asking the local LLM… (can take a while the first time a model loads)";
  try {
    const { explanation } = await api(`/api/reports/${encodeURIComponent(currentReportId)}/send-to-llm`, { method: "POST" });
    statusEl.textContent = "";
    currentChatBase = `/api/reports/${encodeURIComponent(currentReportId)}`;
    document.getElementById("chat-messages").innerHTML = "";
    appendChatBubble("assistant", explanation);
    openChatModal();
  } catch (e) {
    statusEl.textContent = e.message;
  } finally {
    btn.disabled = false;
  }
}

async function correlateWithNews() {
  const btn = document.getElementById("correlate-news-btn");
  const statusEl = document.getElementById("send-to-llm-status");
  btn.disabled = true;
  statusEl.textContent = "Fetching local news and asking the local LLM to correlate it… (can take a while)";
  try {
    const { explanation } = await api(`/api/reports/${encodeURIComponent(currentReportId)}/correlate-news`, { method: "POST" });
    statusEl.textContent = "";
    currentChatBase = `/api/reports/${encodeURIComponent(currentReportId)}`;
    document.getElementById("chat-messages").innerHTML = "";
    appendChatBubble("assistant", explanation);
    openChatModal();
  } catch (e) {
    statusEl.textContent = e.message;
  } finally {
    btn.disabled = false;
  }
}

// ---------- LLM chat modal ----------
// Generic - used by both per-report chat (chat_store.py, keyed by report_id)
// and per-plan chat (keyed by plan_id). currentChatBase holds whichever
// "/api/reports/<id>" or "/api/plans/<id>" is currently active; sendChatMessage()
// just POSTs to `${currentChatBase}/chat` and doesn't need to know which.

function appendChatBubble(role, content) {
  const container = document.getElementById("chat-messages");
  const isUser = role === "user";
  const bubble = document.createElement("div");
  bubble.className = `flex ${isUser ? "justify-end" : "justify-start"}`;
  bubble.innerHTML = `<div class="max-w-[85%] rounded-lg px-3 py-2 text-sm ${isUser ? "bg-electric-blue text-deep-obsidian" : "bg-surface-variant/40 text-on-surface"}">${escapeHtml(content).replace(/\n/g, "<br>")}</div>`;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
  return bubble;
}

function openChatModal() {
  // Toggled via inline style rather than a "hidden"/"flex" class pair -
  // Tailwind utility classes of equal specificity break ties by stylesheet
  // order, not DOM order, which isn't worth relying on for a show/hide flag.
  document.getElementById("chat-modal").style.display = "flex";
  const input = document.getElementById("chat-input");
  input.value = "";
  input.focus();
}

function closeChatModal() {
  document.getElementById("chat-modal").style.display = "none";
}

async function sendChatMessage() {
  const input = document.getElementById("chat-input");
  const message = input.value.trim();
  if (!message) return;
  input.value = "";

  appendChatBubble("user", message);
  const sendBtn = document.getElementById("chat-send-btn");
  sendBtn.disabled = true;
  const thinkingBubble = appendChatBubble("assistant", "…thinking…");

  try {
    const { reply } = await api(`${currentChatBase}/chat`, {
      method: "POST",
      body: JSON.stringify({ message }),
    });
    thinkingBubble.remove();
    appendChatBubble("assistant", reply);
  } catch (e) {
    thinkingBubble.remove();
    appendChatBubble("assistant", `⚠ ${e.message}`);
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

// ---------- business plan (guided intake -> 6-engine pipeline) ----------
// See aros_backend/plans.py + agents.py. The intake below asks its questions
// as chat bubbles, but answers come from structured controls (buttons/number
// input), not from parsing free text - reliable data in, still conversational.

const PLAN_STEPS = [
  {
    key: "goal",
    question: "What's your main goal right now?",
    options: [
      "Increase overall sales",
      "Rebalance product mix (focus on best/worst sellers)",
      "Expand to a new location",
    ],
    customPlaceholder: "Describe your goal…",
  },
  {
    key: "timeframe",
    question: "What timeframe are you thinking?",
    options: ["1 month", "3 months", "6 months", "1 year"],
    customPlaceholder: "e.g. 45 days, 2 years…",
  },
  {
    key: "budget",
    question: "What's your budget for this?",
    isNumber: true,
  },
];

const ENGINE_STEPS = [
  { key: "strategy_engine", label: "Strategy Engine", icon: "insights" },
  { key: "marketing_engine", label: "Marketing Engine", icon: "campaign" },
  { key: "leadgen_engine", label: "Lead Gen Engine", icon: "person_add" },
  { key: "sales_engine", label: "Sale Engine", icon: "point_of_sale" },
  { key: "analytics_engine", label: "Analytics Engine", icon: "monitoring" },
  { key: "customer_success_engine", label: "Customer Success Engine", icon: "support_agent" },
];

function planBubble(text, isUser) {
  const container = document.getElementById("plan-intake-messages");
  const div = document.createElement("div");
  div.className = `flex ${isUser ? "justify-end" : "justify-start"}`;
  div.innerHTML = `<div class="max-w-[85%] rounded-lg px-3 py-2 text-sm ${isUser ? "bg-electric-blue text-deep-obsidian" : "bg-surface-variant/40 text-on-surface"}">${escapeHtml(text)}</div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

async function showPlan() {
  await populateLocationOptions(document.getElementById("plan-location-select"), planAnswers.location);
  await loadPlanHistory(currentPlanId);
  if (!planStarted) startNewPlan();
  showView("plan");
}

function onPlanLocationChange() {
  planAnswers.location = document.getElementById("plan-location-select").value;
}

function startNewPlan() {
  planStarted = true;
  currentPlanId = null;
  planIntakeStep = 0;
  planAnswers = { location: document.getElementById("plan-location-select").value, goal: null, timeframe: null, budget: null };
  document.getElementById("plan-history-select").value = "";
  document.getElementById("plan-intake-messages").innerHTML = "";
  document.getElementById("plan-intake-controls").innerHTML = "";
  document.getElementById("plan-intake").classList.remove("hidden");
  document.getElementById("plan-pipeline").classList.add("hidden");
  askCurrentPlanStep();
}

function askCurrentPlanStep() {
  if (planIntakeStep >= PLAN_STEPS.length) {
    finalizePlanIntake();
    return;
  }
  const step = PLAN_STEPS[planIntakeStep];
  planBubble(step.question, false);
  renderPlanStepControls(step);
}

function renderPlanStepControls(step) {
  const controls = document.getElementById("plan-intake-controls");
  controls.innerHTML = "";

  if (step.isNumber) {
    const currency = planAnswers.location === "main" ? "$" : "₹";
    const row = document.createElement("div");
    row.className = "flex items-center gap-2";
    row.innerHTML = `
      <span class="text-lg font-bold">${currency}</span>
      <input class="field-input rounded px-3 py-2 text-sm w-40" id="plan-number-input" min="0" step="1" type="number" placeholder="Amount">
      <button class="bg-electric-blue text-deep-obsidian font-bold px-4 py-2 rounded transition-transform active:scale-95" id="plan-number-submit">OK</button>
    `;
    controls.appendChild(row);
    const submit = () => {
      const value = parseFloat(document.getElementById("plan-number-input").value);
      if (isNaN(value) || value < 0) return;
      submitPlanStepValue(value, `${currency}${value.toLocaleString()}`);
    };
    document.getElementById("plan-number-submit").addEventListener("click", submit);
    document.getElementById("plan-number-input").addEventListener("keydown", (e) => { if (e.key === "Enter") submit(); });
    document.getElementById("plan-number-input").focus();
    return;
  }

  const optionsRow = document.createElement("div");
  optionsRow.className = "flex flex-wrap gap-2";
  step.options.forEach((opt) => {
    const btn = document.createElement("button");
    btn.className = "border border-outline-variant hover:border-electric-blue hover:text-electric-blue rounded px-3 py-2 text-sm transition-colors";
    btn.textContent = opt;
    btn.addEventListener("click", () => submitPlanStepValue(opt, opt));
    optionsRow.appendChild(btn);
  });
  const customBtn = document.createElement("button");
  customBtn.className = "border border-outline-variant hover:border-electric-blue hover:text-electric-blue rounded px-3 py-2 text-sm transition-colors";
  customBtn.textContent = "Something else…";
  optionsRow.appendChild(customBtn);
  controls.appendChild(optionsRow);

  const customRow = document.createElement("div");
  customRow.className = "hidden mt-2 flex gap-2";
  customRow.id = "plan-custom-row";
  customRow.innerHTML = `
    <input class="field-input rounded px-3 py-2 text-sm flex-1" id="plan-custom-input" placeholder="${escapeHtml(step.customPlaceholder || "")}" type="text">
    <button class="bg-electric-blue text-deep-obsidian font-bold px-4 py-2 rounded transition-transform active:scale-95" id="plan-custom-submit">OK</button>
  `;
  controls.appendChild(customRow);

  customBtn.addEventListener("click", () => {
    customRow.classList.remove("hidden");
    document.getElementById("plan-custom-input").focus();
  });
  const submitCustom = () => {
    const val = document.getElementById("plan-custom-input").value.trim();
    if (val) submitPlanStepValue(val, val);
  };
  document.getElementById("plan-custom-submit").addEventListener("click", submitCustom);
  document.getElementById("plan-custom-input").addEventListener("keydown", (e) => { if (e.key === "Enter") submitCustom(); });
}

function submitPlanStepValue(value, displayText) {
  const step = PLAN_STEPS[planIntakeStep];
  planAnswers[step.key] = value;
  planBubble(displayText, true);
  document.getElementById("plan-intake-controls").innerHTML = "";
  planIntakeStep++;
  askCurrentPlanStep();
}

async function finalizePlanIntake() {
  planBubble("Great — creating your plan now…", false);
  try {
    const plan = await api("/api/plans", {
      method: "POST",
      body: JSON.stringify(planAnswers),
    });
    currentPlanId = plan.id;
    await loadPlanHistory(plan.id);
    showPlanPipeline(plan);
    await runEnginePipeline(plan.id, ENGINE_STEPS);
  } catch (e) {
    planBubble(`⚠ Couldn't create the plan: ${e.message}`, false);
  }
}

function showPlanPipeline(plan) {
  document.getElementById("plan-intake").classList.add("hidden");
  document.getElementById("plan-pipeline").classList.remove("hidden");

  document.getElementById("plan-summary-card").innerHTML = `
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div><span class="font-label-caps text-[10px] text-on-surface-variant block mb-1">GOAL</span><span class="text-sm font-bold">${escapeHtml(plan.goal)}</span></div>
      <div><span class="font-label-caps text-[10px] text-on-surface-variant block mb-1">TIMEFRAME</span><span class="text-sm font-bold">${escapeHtml(plan.timeframe)}</span></div>
      <div><span class="font-label-caps text-[10px] text-on-surface-variant block mb-1">BUDGET</span><span class="text-sm font-bold">${plan.currency}${Number(plan.budget).toLocaleString()}</span></div>
      <div><span class="font-label-caps text-[10px] text-on-surface-variant block mb-1">LOCATION</span><span class="text-sm font-bold text-electric-blue">${escapeHtml(plan.location_label)}</span></div>
    </div>
  `;

  document.getElementById("plan-engine-progress").innerHTML = ENGINE_STEPS
    .map(
      (eng) => `
      <div class="flex items-center space-x-3 text-sm" id="progress-row-${eng.key}">
        <span class="material-symbols-outlined text-on-surface-variant" id="progress-icon-${eng.key}">radio_button_unchecked</span>
        <span class="text-on-surface-variant" id="progress-label-${eng.key}">${escapeHtml(eng.label)}</span>
      </div>`
    )
    .join("");
  document.getElementById("plan-engine-sections").innerHTML = "";
  document.getElementById("plan-chat-entry").classList.add("hidden");
}

function setEngineProgress(key, status) {
  const icon = document.getElementById(`progress-icon-${key}`);
  const label = document.getElementById(`progress-label-${key}`);
  if (!icon) return;
  icon.classList.remove("animate-spin", "text-electric-blue", "text-data-positive", "text-data-negative", "text-on-surface-variant");
  if (status === "running") {
    icon.textContent = "sync";
    icon.classList.add("text-electric-blue", "animate-spin");
    label.classList.remove("text-on-surface-variant");
  } else if (status === "done") {
    icon.textContent = "check_circle";
    icon.classList.add("text-data-positive");
  } else if (status === "failed") {
    icon.textContent = "error";
    icon.classList.add("text-data-negative");
  } else {
    icon.textContent = "radio_button_unchecked";
    icon.classList.add("text-on-surface-variant");
  }
}

function renderPlanRealData(realData) {
  if (realData.type === "analytics") {
    const section = realData.section;
    if (!section) {
      return `<div class="text-xs text-data-negative mb-3">No sales data available for this location.</div>`;
    }
    const rows = section.analysis.pareto.by_category
      .map(
        (r) => `<tr class="border-t border-outline-variant/50">
          <td class="px-3 py-1.5">${escapeHtml(r.name)}</td>
          <td class="px-3 py-1.5 text-right">${section.currency}${r.revenue.toFixed(2)}</td>
          <td class="px-3 py-1.5 text-right">${r.cumulative_pct}%</td>
        </tr>`
      )
      .join("");
    return `
      <div class="bg-surface-variant/20 rounded p-4 mb-4">
        <p class="font-label-caps text-[10px] text-electric-blue mb-2">REAL DATA (not AI-generated)</p>
        <table class="w-full text-left font-data-code text-xs">
          <thead class="text-on-surface-variant uppercase text-[10px]"><tr><th class="px-3 py-1">Category</th><th class="px-3 py-1 text-right">Revenue</th><th class="px-3 py-1 text-right">Cum. %</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  }

  if (realData.type === "customer_activity") {
    if (!realData.available) {
      return `<div class="bg-surface-variant/20 rounded p-4 mb-4 text-xs text-on-surface-variant"><strong class="text-on-surface">Real data:</strong> ${escapeHtml(realData.reason)}</div>`;
    }
    const warning = realData.has_named_customers
      ? ""
      : `<p class="text-xs text-data-negative mb-2">⚠ Every transaction below is logged under a generic "Guest" customer — there's no loyalty/customer-ID system in place yet.</p>`;
    const rows = realData.recent_transactions
      .slice(0, 8)
      .map(
        (t) => `<tr class="border-t border-outline-variant/50">
          <td class="px-3 py-1.5">${new Date(t.timestamp).toLocaleString()}</td>
          <td class="px-3 py-1.5">${escapeHtml(t.customer_name)}</td>
          <td class="px-3 py-1.5 text-right">${t.item_count}</td>
          <td class="px-3 py-1.5 text-right">$${t.total_amount.toFixed(2)}</td>
        </tr>`
      )
      .join("");
    return `
      <div class="bg-surface-variant/20 rounded p-4 mb-4">
        <p class="font-label-caps text-[10px] text-electric-blue mb-2">REAL DATA (not AI-generated) — recent transaction activity</p>
        ${warning}
        <table class="w-full text-left font-data-code text-xs">
          <thead class="text-on-surface-variant uppercase text-[10px]"><tr><th class="px-3 py-1">When</th><th class="px-3 py-1">Customer</th><th class="px-3 py-1 text-right">Items</th><th class="px-3 py-1 text-right">Total</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  }

  return "";
}

function renderEngineSection(engine, entry) {
  const container = document.getElementById("plan-engine-sections");
  const realDataHtml = entry.real_data ? renderPlanRealData(entry.real_data) : "";
  const card = document.createElement("div");
  card.className = "glass-panel rounded-lg p-6 mb-4";
  card.innerHTML = `
    <h3 class="text-lg font-bold mb-3 flex items-center space-x-2">
      <span class="material-symbols-outlined text-electric-blue">${engine.icon}</span>
      <span>${escapeHtml(engine.label)}</span>
    </h3>
    ${realDataHtml}
    <p class="text-sm text-on-surface whitespace-pre-wrap leading-relaxed">${escapeHtml(entry.narrative)}</p>
  `;
  container.appendChild(card);
}

async function runEnginePipeline(planId, stepsToRun) {
  for (const engine of stepsToRun) {
    setEngineProgress(engine.key, "running");
    try {
      const entry = await api(`/api/plans/${encodeURIComponent(planId)}/run/${engine.key}`, { method: "POST" });
      setEngineProgress(engine.key, "done");
      renderEngineSection(engine, entry);
    } catch (e) {
      setEngineProgress(engine.key, "failed");
      const container = document.getElementById("plan-engine-sections");
      const errDiv = document.createElement("div");
      errDiv.className = "glass-panel rounded-lg p-4 mb-4 border border-data-negative/40 text-sm text-data-negative";
      errDiv.textContent = `Couldn't run ${engine.label}: ${e.message}`;
      container.appendChild(errDiv);
      return;
    }
  }
  document.getElementById("plan-chat-entry").classList.remove("hidden");
}

async function loadPlanHistory(selectedId) {
  const select = document.getElementById("plan-history-select");
  try {
    const list = await api("/api/plans");
    if (!list.length) {
      select.classList.add("hidden");
      return [];
    }
    select.innerHTML = "";
    select.appendChild(new Option("— Start a new plan —", ""));
    list.forEach((p) => {
      select.appendChild(new Option(`${new Date(p.created_at).toLocaleString()} — ${p.goal} (${p.engines_completed}/${p.engines_total})`, p.id));
    });
    select.value = selectedId || "";
    select.classList.remove("hidden");
    return list;
  } catch (e) {
    select.classList.add("hidden");
    return [];
  }
}

async function onPlanHistoryChange() {
  const id = document.getElementById("plan-history-select").value;
  if (!id) {
    startNewPlan();
    return;
  }
  planStarted = true;
  const plan = await api(`/api/plans/${encodeURIComponent(id)}`);
  currentPlanId = plan.id;
  showPlanPipeline(plan);

  const remaining = [];
  for (const engine of ENGINE_STEPS) {
    const entry = plan.engines[engine.key];
    if (entry) {
      setEngineProgress(engine.key, "done");
      renderEngineSection(engine, entry);
    } else {
      remaining.push(engine);
    }
  }

  if (remaining.length === 0) {
    document.getElementById("plan-chat-entry").classList.remove("hidden");
  } else {
    await runEnginePipeline(plan.id, remaining);
  }
}

function openPlanChat() {
  currentChatBase = `/api/plans/${encodeURIComponent(currentPlanId)}`;
  document.getElementById("chat-messages").innerHTML = "";
  appendChatBubble("assistant", "Got it — I've reviewed your full plan. What would you like to know?");
  openChatModal();
}

// ---------- theme toggle ----------

const themeToggle = document.getElementById("theme-toggle");
const htmlElement = document.documentElement;
themeToggle.addEventListener("change", () => {
  htmlElement.classList.toggle("light", themeToggle.checked);
  htmlElement.classList.toggle("dark", !themeToggle.checked);
  applyTheme(themeToggle.checked ? "light" : "dark");
});

boot();
