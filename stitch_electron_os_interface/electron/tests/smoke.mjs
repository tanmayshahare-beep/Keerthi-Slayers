// AROS smoke test - launches the real Electron app (not a mock, not a unit
// test of an internal function) and drives it through the golden path that
// doesn't need Ollama running: account setup, category wizard, Insights
// (real KPIs + classical Business Scorecard), Reports tab, and Plan tab
// intake. It intentionally stops short of anything that calls the local
// LLM (report chat, AI scorecard, the 6-engine plan pipeline) so this can
// run in a dev machine or CI without a model pulled - see
// tests/full_pipeline.md in this same folder for how to exercise those by
// hand when Ollama is available.
//
// DESTRUCTIVE: wipes aros_backend/aros_app.db, reports/, plans/, and
// ai_scorecards/ before and after running, since account setup fails
// against an existing user. Never run this against real data - only a dev
// checkout with pos_system.db already seeded.
//
// Run with: npm test (from stitch_electron_os_interface/electron)

import { _electron as electron } from "playwright-core";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ELECTRON_DIR = path.resolve(__dirname, "..");
const BACKEND_DIR = path.resolve(ELECTRON_DIR, "..", "aros_backend");
const electronBin = path.join(ELECTRON_DIR, "node_modules", "electron", "dist", "electron.exe");

let passed = 0;
let failed = 0;

function check(label, condition) {
  if (condition) {
    console.log(`  PASS - ${label}`);
    passed++;
  } else {
    console.log(`  FAIL - ${label}`);
    failed++;
  }
}

function wipeState() {
  for (const rel of ["aros_app.db", "reports", "plans", "ai_scorecards", "__pycache__"]) {
    fs.rmSync(path.join(BACKEND_DIR, rel), { recursive: true, force: true });
  }
}

async function main() {
  if (!fs.existsSync(electronBin)) {
    console.error(`Electron binary not found at ${electronBin} - run "npm install" first.`);
    process.exit(1);
  }

  wipeState();

  const app = await electron.launch({ executablePath: electronBin, args: [ELECTRON_DIR], timeout: 30000 });
  const page = await app.firstWindow({ timeout: 20000 });
  const pageErrors = [];
  page.on("pageerror", (err) => pageErrors.push(err.message));

  try {
    console.log("Auth setup...");
    await page.waitForLoadState("domcontentloaded");
    await page.waitForFunction(
      () => document.querySelector('[data-auth-mode="setup"]') && !document.querySelector('[data-auth-mode="setup"]').classList.contains("hidden"),
      { timeout: 15000 }
    );
    check("setup screen shown on first launch", true);

    await page.fill("#setup-username", "smoketest");
    await page.fill("#setup-password", "smoketest123");
    await page.click('button:has-text("CREATE ACCOUNT")');
    await page.waitForFunction(() => document.querySelector('main [data-view="wizard"]').classList.contains("active"), { timeout: 15000 });
    check("wizard shown after account creation", true);

    console.log("Category wizard...");
    const groupCount = await page.evaluate(() => document.querySelectorAll("#wizard-groups > div").length);
    check("wizard shows suggested category groups", groupCount > 0);

    await page.click('button:has-text("CONFIRM CATEGORIES")');
    await page.waitForFunction(() => document.querySelector('main [data-view="insights"]').classList.contains("active"), { timeout: 15000 });
    check("lands on Insights after confirming categories", true);

    console.log("Insights + Business Scorecard (real classical data)...");
    await page.waitForFunction(() => document.getElementById("kpi-revenue").textContent !== "—", { timeout: 10000 });
    const revenue = await page.evaluate(() => document.getElementById("kpi-revenue").textContent);
    check(`KPI revenue shows a real figure (got "${revenue}")`, /\$[\d,]+\.\d{2}/.test(revenue));

    const scorecardTileCount = await page.evaluate(() => document.getElementById("scorecard-tiles").children.length);
    check("Business Scorecard renders 4 tiles", scorecardTileCount === 4);

    const alertCount = await page.evaluate(() => document.getElementById("scorecard-alerts").children.length);
    check("Risk Alerts section renders at least one alert", alertCount >= 1);

    console.log("Reports tab...");
    await page.click('.nav-link[data-view="reports"]');
    await page.waitForFunction(() => document.querySelector('main [data-view="reports"]').classList.contains("active"), { timeout: 10000 });
    check("Reports view loads without crashing", true);

    console.log("Plan tab intake...");
    await page.click('.nav-link[data-view="plan"]');
    await page.waitForFunction(() => document.querySelector('main [data-view="plan"]').classList.contains("active"), { timeout: 10000 });
    await page.waitForFunction(() => document.getElementById("plan-intake-messages").children.length > 0, { timeout: 10000 });
    check("Plan tab starts the guided intake with a question", true);

    const goalOptionCount = await page.evaluate(() => document.querySelectorAll("#plan-intake-controls button").length);
    check("Plan intake offers goal option buttons", goalOptionCount > 0);

    check("no uncaught page errors during the run", pageErrors.length === 0);
    if (pageErrors.length) pageErrors.forEach((e) => console.log(`  (page error: ${e})`));
  } finally {
    await app.close();
    wipeState();
  }

  console.log(`\n${passed} passed, ${failed} failed`);
  process.exit(failed > 0 ? 1 : 0);
}

main().catch((e) => {
  console.error("Smoke test crashed:", e.message);
  wipeState();
  process.exit(1);
});
