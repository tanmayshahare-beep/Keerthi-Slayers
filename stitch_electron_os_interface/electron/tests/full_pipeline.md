# Manually verifying the Ollama-dependent features

`smoke.mjs` (`npm test`) covers the golden path that doesn't need a local
model running. The features below make a real call to Ollama, take real
time (10-90s each), and are exercised by hand rather than in the committed
suite - automating them would mean either bundling a model download into CI
or mocking the LLM, and a mocked LLM response wouldn't tell you anything
real about prompt quality or grounding. This is the checklist used to
verify them during development; repeat it after touching `agents.py`,
`ollama_client.py`, `plans.py`, `reports.py`, or `ai_scorecards.py`.

Prerequisite: Ollama running with the default model pulled
(`ollama pull llama3`, or whatever `AROS_OLLAMA_MODEL` points at).

1. **Report chat** (Reports tab): generate a report, click **SEND TO LLM**,
   confirm the explanation references real numbers from the report (not
   generic filler), then ask a follow-up question in the chat and confirm
   it stays grounded in the report's own data.
2. **News correlation** (Reports tab): click **CORRELATE WITH NEWS** on a
   report, confirm it either finds a plausible connection to real fetched
   headlines or says plainly that it didn't - not a forced correlation.
3. **Plan pipeline** (Plan tab): complete the guided intake, let all six
   engines run. Confirm: each engine's own budget allocation (shown in the
   summary card) matches what it references in its own text; later engines
   reference earlier ones by name (e.g. Marketing citing the Strategy
   Engine's positioning); Analytics and Customer Success show a "REAL DATA"
   section grounded in the same numbers Insights shows; Customer Success
   correctly surfaces the "Guest"-only data limitation for locations where
   it applies.
4. **AI Scorecard** (Insights tab): click **GENERATE AI INSIGHTS**, confirm
   Lead Score and Market Readiness are explicitly labeled as estimates, the
   Executive Summary references the real Business Health/Growth numbers
   above it, and reloading the page (or switching location and back) shows
   the cached result immediately instead of re-running.
5. **PDF export** (any of the three tabs above): click **EXPORT PDF**,
   confirm the saved file has no sidebar/buttons/dropdowns in it and the
   dark theme rendered rather than a blank/white page.

Across all of the above: switch locations (Main Store vs. a Tamil Nadu
city vs. All Tamil Nadu Locations) and confirm the numbers and currency
symbol actually change - a stale/cached value from the wrong location is
the most common regression in this part of the app.
