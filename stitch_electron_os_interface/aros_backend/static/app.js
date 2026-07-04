let token = null;
let cachedProducts = [];
let cachedPareto = null;
let wizardGroups = []; // [{ id, name, barcodes: [] }]
let currentCurrency = "$";
let currentLocation = "main"; // "main" | "all" | a Tamil Nadu store_id
let currentNewsLocation = "main";

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
}

document.querySelectorAll(".nav-link").forEach((el) => {
  el.addEventListener("click", (e) => {
    e.preventDefault();
    if (el.dataset.view === "wizard") {
      openWizard();
    } else if (el.dataset.view === "news") {
      showNews();
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

async function showInsights() {
  currentLocation = "main";
  currentCurrency = "$";
  const locationSelect = document.getElementById("location-select");
  if (locationSelect) locationSelect.value = "main";

  const [products, categories, { pareto, trend_shifts }] = await Promise.all([
    api("/api/products"),
    api("/api/categories"),
    api("/api/insights"),
  ]);
  cachedProducts = products;
  cachedPareto = pareto;

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
  const { stats, pareto, trend_shifts } = await api(`/api/location-insights?location=${encodeURIComponent(location)}`);
  cachedPareto = pareto;

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

// ---------- theme toggle ----------

const themeToggle = document.getElementById("theme-toggle");
const htmlElement = document.documentElement;
themeToggle.addEventListener("change", () => {
  htmlElement.classList.toggle("light", themeToggle.checked);
  htmlElement.classList.toggle("dark", !themeToggle.checked);
  applyTheme(themeToggle.checked ? "light" : "dark");
});

boot();
