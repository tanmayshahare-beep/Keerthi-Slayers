# Multi-Agent Architecture

> Seven specialized agents orchestrated by LangGraph, synthesized by the CEO Agent.

---

## Agent Architecture Overview

```
                    ┌─────────────────────┐
                    │   Discovery Agent   │
                    │   (Entry Node)      │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
     ┌────────────┐   ┌────────────┐   ┌────────────┐
     │ Marketing  │   │   Sales    │   │  Finance   │
     │   Agent    │   │   Agent    │   │   Agent    │
     └─────┬──────┘   └─────┬──────┘   └─────┬──────┘
           │                │                │
           └────────────────┼────────────────┘
                            │
                     ┌──────▼──────┐
                     │ Operations  │
                     │   Agent     │
                     └──────┬──────┘
                            │
                     ┌──────▼──────┐
                     │  CEO Agent  │
                     │ (Synthesis) │
                     └──────┬──────┘
                            │
                     ┌──────▼──────┐
                     │    Data     │
                     │  Analyst    │
                     │   Agent     │
                     └─────────────┘
```

**Execution model**: Discovery runs first. Marketing, Sales, Finance, and Operations run **in parallel** (LangGraph fan-out). CEO Agent waits for all four. Data Analyst runs after CEO (uses strategy + any existing KPIs).

---

## Shared Agent Contract

Every agent implements:

```python
class BaseAgent(Protocol):
    role: str
    inputs: list[str]      # State keys required
    outputs: list[str]     # State keys produced

    async def run(self, state: AgentState) -> AgentState: ...
```

**AgentState** (LangGraph TypedDict) holds all cross-agent data. Each agent reads required inputs, calls Gemini with structured prompt, validates JSON output against Pydantic schema, writes outputs back to state.

---

## Agent 1: Discovery Agent

| Attribute | Value |
|-----------|-------|
| **Role** | Collect, validate, and structure raw onboarding data into a canonical Business Profile |
| **Phase** | Discover (5D) |
| **LangGraph Node** | `discovery` (entry) |

### Inputs

| Key | Source |
|-----|--------|
| `raw_onboarding` | API request body from onboarding wizard |
| `business_id` | Route parameter |

### Outputs

| Key | Description |
|-----|-------------|
| `business_profile` | Structured profile (see schema below) |
| `profile_completeness_score` | 0–100 indicating data quality |

### System Prompt (Summary)

```
You are the Discovery Agent for a Business Growth Operating System.
Your role is to organize raw business onboarding data into a structured,
complete Business Profile. Fill reasonable gaps with industry benchmarks
ONLY when marked as estimates. Never invent specific financial figures.
Flag missing critical fields. Output valid JSON only.
```

### Expected Response Format

```json
{
  "company_name": "string",
  "industry": "string",
  "business_size": "solo|small|medium|large",
  "employee_count": 0,
  "products": ["string"],
  "services": ["string"],
  "annual_revenue": { "amount": 0, "currency": "USD", "is_estimate": false },
  "annual_expenses": { "amount": 0, "currency": "USD", "is_estimate": false },
  "current_marketing": ["string"],
  "sales_channels": ["string"],
  "target_customers": { "demographics": "string", "segments": ["string"] },
  "competitors": [{ "name": "string", "notes": "string" }],
  "website": "string|null",
  "social_media": [{ "platform": "string", "handle": "string" }],
  "existing_problems": ["string"],
  "goals": [{ "description": "string", "timeframe": "string", "priority": "high|medium|low" }],
  "data_gaps": ["string"],
  "completeness_score": 85
}
```

---

## Agent 2: Marketing Agent

| Attribute | Value |
|-----------|-------|
| **Role** | Create comprehensive marketing strategy and campaign recommendations |
| **Phase** | Design + Deliver |
| **LangGraph Node** | `marketing` (parallel) |

### Inputs

- `business_profile`
- `market_context` (optional, from prior runs)

### Outputs

- `marketing_strategy`
- `campaign_ideas`
- `seo_plan`
- `google_ads_suggestions`
- `social_media_plan`
- `marketing_budget_allocation`

### System Prompt (Summary)

```
You are the Marketing Agent. Analyze the business profile and produce
actionable marketing strategy. Include specific campaign ideas with
channels, budgets, and KPIs. SEO recommendations must be prioritized.
Social media plan must include posting frequency and content themes.
Output valid JSON matching the schema.
```

### Expected Response Format

```json
{
  "strategy_summary": "string",
  "campaign_ideas": [{
    "name": "string",
    "objective": "string",
    "channels": ["string"],
    "estimated_budget": 0,
    "duration_weeks": 4,
    "expected_kpis": [{ "metric": "string", "target": "string" }]
  }],
  "seo_plan": {
    "priority_keywords": ["string"],
    "on_page_actions": ["string"],
    "content_strategy": "string",
    "timeline_months": 3
  },
  "google_ads_suggestions": [{
    "campaign_type": "string",
    "target_keywords": ["string"],
    "daily_budget": 0,
    "expected_cpc": 0
  }],
  "social_media_plan": {
    "platforms": [{ "platform": "string", "frequency": "string", "content_themes": ["string"] }]
  },
  "budget_allocation": {
    "total_monthly": 0,
    "breakdown": [{ "category": "string", "amount": 0, "percentage": 0 }]
  }
}
```

---

## Agent 3: Sales Agent

| Attribute | Value |
|-----------|-------|
| **Role** | Optimize sales funnel, pricing, and lead management |
| **Phase** | Design + Deliver |
| **LangGraph Node** | `sales` (parallel) |

### Inputs

- `business_profile`
- `marketing_strategy` (optional cross-reference)

### Outputs

- `lead_scoring_model`
- `pricing_strategy`
- `sales_funnel_improvements`
- `follow_up_strategy`

### System Prompt (Summary)

```
You are the Sales Agent. Design lead scoring criteria, pricing strategy,
and sales funnel improvements based on the business profile. Recommendations
must be specific and measurable. Consider the target customer segments.
Output valid JSON only.
```

### Expected Response Format

```json
{
  "lead_scoring_model": {
    "criteria": [{ "factor": "string", "weight": 0, "description": "string" }],
    "score_bands": [{ "range": "0-30", "label": "Cold", "action": "string" }]
  },
  "pricing_strategy": {
    "current_assessment": "string",
    "recommendations": [{ "product_or_service": "string", "suggested_price": 0, "rationale": "string" }],
    "pricing_model": "string"
  },
  "sales_funnel": {
    "stages": [{ "name": "string", "current_conversion": "string", "improvement": "string" }],
    "bottlenecks": ["string"],
    "improvements": [{ "action": "string", "expected_impact": "string", "priority": "high|medium|low" }]
  },
  "follow_up_strategy": {
    "sequences": [{ "trigger": "string", "channels": ["string"], "timing": "string", "template_summary": "string" }]
  }
}
```

---

## Agent 4: Finance Agent

| Attribute | Value |
|-----------|-------|
| **Role** | Analyze financial health, ROI, and projections |
| **Phase** | Design + Develop |
| **LangGraph Node** | `finance` (parallel) |

### Inputs

- `business_profile`
- `marketing_budget_allocation` (if available from parallel run, use profile estimates otherwise)

### Outputs

- `financial_health`
- `roi_analysis`
- `cost_optimization`
- `revenue_projection`

### System Prompt (Summary)

```
You are the Finance Agent. Analyze revenue, expenses, and marketing spend.
Calculate ROI projections, identify cost optimization opportunities, and
forecast revenue for the next 3-6 months. Flag financial risks clearly.
Use conservative assumptions. Output valid JSON only.
```

### Expected Response Format

```json
{
  "financial_health": {
    "score": 0,
    "profit_margin": 0,
    "cash_flow_status": "healthy|constrained|critical",
    "key_risks": ["string"]
  },
  "roi_analysis": {
    "marketing_roi_estimate": 0,
    "breakdown_by_channel": [{ "channel": "string", "estimated_roi": 0 }]
  },
  "cost_optimization": [{
    "area": "string",
    "current_cost": 0,
    "potential_savings": 0,
    "recommendation": "string"
  }],
  "revenue_projection": {
    "months": [{ "month": "string", "projected_revenue": 0, "confidence": "high|medium|low" }]
  }
}
```

---

## Agent 5: Operations Agent

| Attribute | Value |
|-----------|-------|
| **Role** | Improve internal workflows, automation, and efficiency |
| **Phase** | Design + Deliver |
| **LangGraph Node** | `operations` (parallel) |

### Inputs

- `business_profile`

### Outputs

- `workflow_improvements`
- `automation_suggestions`
- `efficiency_metrics`

### System Prompt (Summary)

```
You are the Operations Agent. Identify workflow bottlenecks, suggest
automation opportunities, and define efficiency metrics appropriate
for the business size and industry. Be practical — recommend tools
and processes achievable for an SMB. Output valid JSON only.
```

### Expected Response Format

```json
{
  "workflow_improvements": [{
    "process": "string",
    "current_state": "string",
    "proposed_state": "string",
    "impact": "string",
    "effort": "low|medium|high"
  }],
  "automation_suggestions": [{
    "task": "string",
    "tool_suggestion": "string",
    "time_saved_hours_per_week": 0,
    "implementation_steps": ["string"]
  }],
  "efficiency_metrics": [{
    "metric": "string",
    "current_baseline": "string",
    "target": "string",
    "measurement_method": "string"
  }]
}
```

---

## Agent 6: CEO Agent

| Attribute | Value |
|-----------|-------|
| **Role** | Synthesize all specialist outputs; resolve conflicts; prioritize; produce unified Growth Plan |
| **Phase** | Design (primary) |
| **LangGraph Node** | `ceo` (barrier after parallel agents) |

### Inputs

- `business_profile`
- `marketing_strategy`, `campaign_ideas`, `marketing_budget_allocation`
- `lead_scoring_model`, `pricing_strategy`, `sales_funnel`
- `financial_health`, `roi_analysis`, `revenue_projection`
- `workflow_improvements`, `automation_suggestions`

### Outputs

- `swot_analysis`
- `growth_strategy`
- `business_opportunities`
- `competitor_analysis`
- `market_analysis`
- `quarterly_goals`
- `budget_allocation`
- `priority_tasks`
- `business_growth_plan` (executive summary document)

### System Prompt (Summary)

```
You are the CEO Agent — the executive synthesizer. You receive outputs
from Marketing, Sales, Finance, and Operations agents. Your job:
1. Resolve conflicting recommendations (e.g., budget vs. growth ambition)
2. Prioritize actions by impact and feasibility
3. Produce SWOT, market analysis, competitor analysis
4. Set quarterly goals aligned with business objectives
5. Allocate budget across functions
6. Output a unified Business Growth Plan

Be decisive. Every priority task must have an owner suggestion, deadline,
and success metric. Output valid JSON only.
```

### Expected Response Format

```json
{
  "swot_analysis": {
    "strengths": ["string"],
    "weaknesses": ["string"],
    "opportunities": ["string"],
    "threats": ["string"]
  },
  "growth_strategy": {
    "vision": "string",
    "strategic_pillars": [{ "pillar": "string", "description": "string" }],
    "12_month_targets": [{ "metric": "string", "target": "string" }]
  },
  "business_opportunities": [{
    "opportunity": "string",
    "market_size_estimate": "string",
    "effort_required": "low|medium|high",
    "priority": 1
  }],
  "competitor_analysis": [{
    "competitor": "string",
    "strengths": ["string"],
    "weaknesses": ["string"],
    "differentiation_strategy": "string"
  }],
  "market_analysis": {
    "market_size": "string",
    "growth_rate": "string",
    "trends": ["string"],
    "target_segment_insights": "string"
  },
  "quarterly_goals": [{
    "quarter": "Q1",
    "goals": [{ "goal": "string", "metric": "string", "target": "string" }]
  }],
  "budget_allocation": {
    "total_quarterly": 0,
    "categories": [{ "category": "string", "amount": 0, "percentage": 0, "rationale": "string" }]
  },
  "priority_tasks": [{
    "id": "string",
    "title": "string",
    "description": "string",
    "owner_role": "string",
    "deadline": "string",
    "priority": 1,
    "source_agent": "marketing|sales|finance|operations",
    "success_metric": "string"
  }],
  "executive_summary": "string (2-3 paragraphs)",
  "conflicts_resolved": [{ "conflict": "string", "resolution": "string" }]
}
```

---

## Agent 7: Data Analyst Agent

| Attribute | Value |
|-----------|-------|
| **Role** | Compute dashboard metrics, trend analysis, forecasts; compare expected vs actual |
| **Phase** | Develop + Dominate |
| **LangGraph Node** | `analyst` (terminal) |

### Inputs

- `business_profile`
- `business_growth_plan`
- `priority_tasks`
- `kpi_snapshots` (historical from DB)
- `expected_performance` (derived from growth plan targets)

### Outputs

- `dashboard_metrics`
- `business_health_score`
- `growth_score`
- `revenue_opportunity`
- `lead_score`
- `customer_health`
- `market_readiness`
- `risk_alerts`
- `trend_analysis`
- `forecasts`

### System Prompt (Summary)

```
You are the Data Analyst Agent. Compute executive dashboard scores (0-100)
based on business profile, strategy targets, and actual KPI data.
Compare expected vs actual performance. Identify trends and risks.
When KPI data is sparse, use profile-based estimates and flag confidence.
Output valid JSON only.
```

### Expected Response Format

```json
{
  "scores": {
    "business_health_score": 0,
    "growth_score": 0,
    "revenue_opportunity": 0,
    "lead_score": 0,
    "customer_health": 0,
    "market_readiness": 0
  },
  "expected_vs_actual": [{
    "metric": "string",
    "expected": 0,
    "actual": 0,
    "variance_percent": 0,
    "status": "on_track|at_risk|off_track"
  }],
  "trend_analysis": [{
    "metric": "string",
    "direction": "up|down|flat",
    "insight": "string"
  }],
  "forecasts": [{
    "metric": "string",
    "period": "string",
    "predicted_value": 0,
    "confidence": "high|medium|low"
  }],
  "risk_alerts": [{
    "severity": "critical|warning|info",
    "title": "string",
    "description": "string",
    "recommended_action": "string"
  }],
  "ai_recommendations": [{
    "title": "string",
    "rationale": "string",
    "priority": "high|medium|low",
    "linked_task_id": "string|null"
  }]
}
```

---

## AI Copilot Architecture

The Copilot is **not** a separate LangGraph agent. It is a **RAG-powered chat service** that queries:

1. **ChromaDB** — embedded agent outputs, executive summaries, recommendations
2. **PostgreSQL** — structured business profile, latest KPIs, scores

### Copilot Flow

```
User question
     │
     ▼
Intent classification (simple keyword + LLM)
     │
     ├── Structured query path → SQL for KPIs/scores
     │
     └── Semantic query path → ChromaDB retrieval
              │
              ▼
     Context assembly (top-k chunks + structured data)
              │
              ▼
     Gemini completion with business context
              │
              ▼
     Response with source citations
```

### Supported Intents

| Intent | Example | Data Sources |
|--------|---------|--------------|
| `diagnose` | "Why is revenue decreasing?" | KPI snapshots, analyst trends |
| `recommend` | "How can I increase sales?" | Sales agent output, CEO priorities |
| `generate` | "Generate a marketing campaign" | Marketing agent + profile |
| `analyze` | "Analyze my business" | Full profile + latest growth plan |
| `risk` | "Show biggest risks" | Analyst risk alerts |
| `forecast` | "Predict next month's revenue" | Finance projections + KPI trends |

---

## Conflict Resolution Rules (CEO Agent)

| Conflict Type | Resolution Policy |
|---------------|-------------------|
| Budget overrun (Marketing vs Finance) | Finance caps win; Marketing reprioritizes channels |
| Aggressive pricing vs margin (Sales vs Finance) | CEO selects based on `business_size` and cash flow status |
| Automation vs headcount (Ops vs Finance) | Prefer automation when `employee_count` < 20 |
| Conflicting quarterly targets | CEO ranks by stated business goals priority |

---

## Embedding Strategy for ChromaDB

Each agent output is chunked and embedded after validation:

| Collection | Contents |
|------------|----------|
| `business_profiles` | Full profile JSON + natural language summary |
| `strategies` | CEO output: SWOT, growth plan, goals |
| `recommendations` | Marketing, Sales, Ops deliverables |
| `analytics` | Analyst reports, risk alerts |
| `copilot_history` | Past Q&A for continuity |

Metadata on each chunk: `business_id`, `agent_name`, `created_at`, `run_id`.
