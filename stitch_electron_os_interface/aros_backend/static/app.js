let token = null;
let cachedProducts = [];
let cachedPareto = null;
let wizardGroups = []; // [{ id, name, barcodes: [] }]

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
    assignments = existing.assignments;
  } else {
    assignments = (await api("/api/categories/template")).assignments;
  }

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
        <td class="px-4 py-2 text-right">$${r.revenue.toFixed(2)}</td>
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
        <td class="px-4 py-2 text-right">$${r.revenue.toFixed(2)}</td>
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
        <td class="px-4 py-2 text-right">$${r.baseline_avg_daily_revenue.toFixed(2)}</td>
        <td class="px-4 py-2 text-right">$${r.recent_avg_daily_revenue.toFixed(2)}</td>
        <td class="px-4 py-2 text-right">${delta(r.pct_change)}</td>
      </tr>`
    )
    .join("");
}

async function showInsights() {
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

  renderCategoryParetoTable(pareto.by_category);
  document.getElementById("product-filter").value = "";
  renderProductTable();

  document.getElementById("trend-category-heading").textContent = `Trend Shifts — by Category (last ${trend_shifts.recent_window_days}d vs. baseline)`;
  document.getElementById("trend-product-heading").textContent = `Trend Shifts — by Product (last ${trend_shifts.recent_window_days}d vs. baseline)`;
  renderTrendTable("trend-category-table", trend_shifts.by_category);
  renderTrendTable("trend-product-table", trend_shifts.by_product);

  showView("insights");
}

// ---------- theme toggle ----------

const themeToggle = document.getElementById("theme-toggle");
const htmlElement = document.documentElement;
themeToggle.addEventListener("change", () => {
  htmlElement.classList.toggle("light", themeToggle.checked);
  htmlElement.classList.toggle("dark", !themeToggle.checked);
});

boot();
