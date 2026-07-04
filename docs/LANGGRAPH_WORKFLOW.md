# LangGraph Workflow Design

> State graph orchestrating 7 agents through the 5D business lifecycle.

---

## Why LangGraph

| Requirement | LangGraph Feature |
|-------------|-------------------|
| Multi-agent coordination | State graph with explicit nodes and edges |
| Parallel specialist agents | Fan-out / fan-in pattern |
| Checkpointing | Resume failed runs from last completed node |
| Conditional routing | Re-run only stale agents on feedback |
| Observable progress | Node-level status exposed to API |

**Alternative considered**: Simple sequential chain — rejected because parallel agents reduce latency ~60% and CEO Agent requires barrier synchronization.

---

## State Schema

```python
from typing import TypedDict, Optional, Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # Identifiers
    business_id: str
    agent_run_id: str
    run_type: str  # full_analysis | kpi_reanalysis | copilot_refresh

    # Raw inputs
    raw_onboarding: Optional[dict]

    # Discovery outputs
    business_profile: Optional[dict]
    profile_completeness_score: Optional[int]

    # Specialist outputs (parallel)
    marketing_strategy: Optional[dict]
    campaign_ideas: Optional[list]
    seo_plan: Optional[dict]
    google_ads_suggestions: Optional[list]
    social_media_plan: Optional[dict]
    marketing_budget_allocation: Optional[dict]

    lead_scoring_model: Optional[dict]
    pricing_strategy: Optional[dict]
    sales_funnel: Optional[dict]
    follow_up_strategy: Optional[dict]

    financial_health: Optional[dict]
    roi_analysis: Optional[dict]
    cost_optimization: Optional[list]
    revenue_projection: Optional[dict]

    workflow_improvements: Optional[list]
    automation_suggestions: Optional[list]
    efficiency_metrics: Optional[list]

    # CEO synthesis
    swot_analysis: Optional[dict]
    growth_strategy: Optional[dict]
    business_opportunities: Optional[list]
    competitor_analysis: Optional[list]
    market_analysis: Optional[dict]
    quarterly_goals: Optional[list]
    budget_allocation: Optional[dict]
    priority_tasks: Optional[list]
    business_growth_plan: Optional[dict]

    # Analyst outputs
    dashboard_metrics: Optional[dict]
    risk_alerts: Optional[list]
    trend_analysis: Optional[list]
    forecasts: Optional[list]

    # Control flow
    errors: Annotated[list, add_messages]
    completed_nodes: Annotated[list, add_messages]
    current_node: Optional[str]
    should_rerun: Optional[dict]  # Which agents to re-run on partial update
```

---

## Graph Topology

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  discovery  │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼─────┐ ┌────▼────┐ ┌─────▼─────┐
       │ marketing  │ │  sales  │ │  finance  │
       └──────┬─────┘ └────┬────┘ └─────┬─────┘
              │            │            │
              │     ┌──────▼──────┐     │
              │     │ operations  │     │
              │     └──────┬──────┘     │
              │            │            │
              └────────────┼────────────┘
                           │
                    ┌──────▼──────┐
                    │     ceo     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   analyst   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  persist    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    END      │
                    └─────────────┘
```

---

## Node Definitions

### `discovery`

- **Agent**: Discovery Agent
- **Precondition**: `raw_onboarding` exists OR profile loaded from DB
- **Postcondition**: `business_profile` populated
- **On error**: Set run status `failed`; do not proceed
- **Skip condition**: Profile exists and `run_type != full_analysis`

### `marketing`, `sales`, `finance`, `operations`

- **Execution**: Parallel (LangGraph `Send` API or fan-out node)
- **Precondition**: `business_profile` exists
- **Postcondition**: Respective output keys populated
- **On error**: Log to `errors[]`; continue with partial results (CEO handles gaps)
- **Timeout**: 45 seconds per agent

### `ceo`

- **Agent**: CEO Agent
- **Precondition**: All parallel nodes completed (success or partial)
- **Barrier**: Waits for marketing + sales + finance + operations
- **Postcondition**: Full strategy document in state
- **On error**: Run status `partial`; save whatever specialists produced

### `analyst`

- **Agent**: Data Analyst Agent
- **Precondition**: CEO output exists; loads KPI snapshots from DB
- **Postcondition**: Dashboard scores and comparisons populated
- **Skip condition**: No KPI data → generate profile-based estimates with low confidence flag

### `persist`

- **Not an LLM agent** — service node
- Writes all outputs to PostgreSQL
- Embeds chunks into ChromaDB
- Updates `agent_run` status to `completed`
- Creates `recommendations` records from deliverables
- Sets `dashboard_scores.is_current = true`

---

## Workflow Variants

### W1: Full Analysis (Primary)

**Trigger**: `POST /businesses/{id}/analyze` or onboarding complete

```
START → discovery → [marketing, sales, finance, operations] → ceo → analyst → persist → END
```

**Duration**: 60–90 seconds

### W2: KPI Reanalysis

**Trigger**: New KPI snapshot with significant deviation OR `POST /performance/analyze`

```
START → analyst → persist → END
```

Loads existing strategy from DB into state. Skips specialist agents.

**Duration**: 15–25 seconds

### W3: Marketing Refresh

**Trigger**: `POST /campaigns/generate`

```
START → marketing → persist_recommendations → END
```

Single-agent sub-graph. Does not re-run CEO.

**Duration**: 15–20 seconds

### W4: Copilot Context Refresh

**Trigger**: After any completed agent run (background)

```
START → embed_outputs → END
```

Re-embeds latest outputs into ChromaDB. No LLM call unless summarization needed.

**Duration**: 5–10 seconds

---

## Conditional Routing

```python
def route_after_discovery(state: AgentState) -> list[str]:
    """Fan-out to parallel specialist agents."""
    if state.get("should_rerun"):
        agents = state["should_rerun"].get("agents", [])
        return agents if agents else ["marketing", "sales", "finance", "operations"]
    return ["marketing", "sales", "finance", "operations"]

def should_skip_discovery(state: AgentState) -> str:
    if state["run_type"] == "kpi_reanalysis":
        return "load_existing"
    if state.get("business_profile") and state["run_type"] != "full_analysis":
        return "skip"
    return "run"
```

---

## Checkpointing

LangGraph checkpointer backed by PostgreSQL table `graph_checkpoints`:

| Column | Type | Description |
|--------|------|-------------|
| `thread_id` | VARCHAR | Maps to `agent_run_id` |
| `checkpoint_id` | VARCHAR | Node checkpoint |
| `state_snapshot` | JSONB | Serialized AgentState |
| `created_at` | TIMESTAMPTZ | |

**Benefit**: If Render restarts mid-run, resume from last completed node instead of restarting entire pipeline.

---

## Error Handling Strategy

```
Agent Node
    │
    ├── Success → validate JSON → merge into state → mark node complete
    │
    ├── JSON parse fail → retry with repair prompt (max 1)
    │       │
    │       └── Still fail → log error, set agent output to null
    │
    └── Timeout → log error, set agent output to null

CEO Agent receives null outputs → notes gaps in executive_summary
Analyst Agent with null strategy → uses profile-only analysis
```

---

## Progress Reporting

Each node emits progress event:

```python
async def on_node_start(state: AgentState, node_name: str):
    await update_agent_run(
        run_id=state["agent_run_id"],
        current_node=node_name,
        status="running"
    )
    await ws_broadcast(state["agent_run_id"], {
        "event": "node_started",
        "node": node_name
    })
```

Frontend polls `GET /agent-runs/{id}` or listens on WebSocket.

---

## LLM Configuration Per Agent

| Agent | Model | Temperature | Max Tokens |
|-------|-------|-------------|------------|
| Discovery | gemini-1.5-flash | 0.1 | 4096 |
| Marketing | gemini-1.5-pro | 0.4 | 8192 |
| Sales | gemini-1.5-pro | 0.3 | 4096 |
| Finance | gemini-1.5-pro | 0.2 | 4096 |
| Operations | gemini-1.5-flash | 0.3 | 4096 |
| CEO | gemini-1.5-pro | 0.3 | 8192 |
| Analyst | gemini-1.5-pro | 0.2 | 4096 |
| Copilot | gemini-1.5-flash | 0.5 | 2048 |

**Rationale**: Flash for structured extraction (Discovery, Ops); Pro for creative strategy (Marketing, CEO).

---

## Feedback Loop Integration

```
KPI Snapshot Created
        │
        ▼
Analytics Service checks variance
        │
        ├── variance < 10% → no action
        │
        └── variance >= 10% → create feedback_event
                    │
                    ▼
            Trigger W2 (KPI Reanalysis)
                    │
                    ▼
            Analyst updates scores + risk_alerts
                    │
                    ▼
            Dashboard reflects new alerts
                    │
                    └── If critical → flag strategy as stale
                              → suggest POST /analyze to user
```

---

## File Location (Implementation Reference)

```
backend/
  langgraph/
    __init__.py
    state.py              # AgentState TypedDict
    graph.py              # Graph construction
    nodes/
      discovery.py
      marketing.py
      sales.py
      finance.py
      operations.py
      ceo.py
      analyst.py
      persist.py
    routing.py            # Conditional edge functions
    checkpointer.py       # PostgreSQL checkpointer config
```

---

## Testing Strategy

| Test Type | Scope |
|-----------|-------|
| Unit | Each node with mock LLM returning fixed JSON |
| Integration | Full graph with mock Gemini client |
| E2E | POST /analyze → poll → verify DB records |
| Snapshot | Compare agent outputs against golden fixtures |

Use `langgraph.checkpoint.memory.MemorySaver` for unit tests; PostgreSQL checkpointer for integration.
