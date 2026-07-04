# API Architecture

> REST API v1 — FastAPI backend. All endpoints prefixed with `/api/v1`.

---

## Design Principles

1. **Resource-oriented URLs** — nouns, not verbs (`/businesses`, not `/createBusiness`)
2. **JSON everywhere** — request/response bodies; `Content-Type: application/json`
3. **Consistent envelope** — success and error shapes standardized
4. **Async long operations** — 202 Accepted + polling for agent runs
5. **Versioned** — `/api/v1` allows future breaking changes in v2
6. **Authenticated by default** — all routes except `/health` and `/auth/*` require JWT

---

## Authentication

### Flow

```
Frontend (Supabase Auth) → JWT access token
     │
     ▼
Authorization: Bearer <token>
     │
     ▼
FastAPI middleware validates JWT via Supabase JWKS
     │
     ▼
Extract user_id → inject into request context
```

### Auth Endpoints

Handled primarily by Supabase client SDK on frontend. Backend validates tokens only.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/auth/me` | Return current user profile |

---

## Response Envelopes

### Success

```json
{
  "data": { },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-07-04T10:00:00Z"
  }
}
```

### Paginated List

```json
{
  "data": [],
  "meta": {
    "total": 100,
    "page": 1,
    "page_size": 20,
    "request_id": "uuid"
  }
}
```

### Error

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable message",
    "details": [{ "field": "email", "issue": "invalid format" }]
  },
  "meta": { "request_id": "uuid" }
}
```

### Error Codes

| Code | HTTP Status | When |
|------|-------------|------|
| `UNAUTHORIZED` | 401 | Missing/invalid token |
| `FORBIDDEN` | 403 | User lacks access to resource |
| `NOT_FOUND` | 404 | Resource doesn't exist |
| `VALIDATION_ERROR` | 422 | Pydantic validation failure |
| `CONFLICT` | 409 | Duplicate or state conflict |
| `AGENT_RUN_FAILED` | 500 | LangGraph workflow failure |
| `RATE_LIMITED` | 429 | Too many LLM requests |

---

## API Endpoints

### Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Service health (DB, ChromaDB, Gemini) |

---

### Businesses

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/businesses` | Yes | Create new business |
| GET | `/api/v1/businesses` | Yes | List user's businesses |
| GET | `/api/v1/businesses/{id}` | Yes | Get business details |
| PATCH | `/api/v1/businesses/{id}` | Yes | Update business metadata |
| DELETE | `/api/v1/businesses/{id}` | Yes | Archive business |

**POST /businesses** request:

```json
{
  "name": "Acme Corp"
}
```

---

### Onboarding (Discover)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/businesses/{id}/onboarding` | Yes | Get onboarding progress |
| PUT | `/api/v1/businesses/{id}/onboarding/step/{n}` | Yes | Save wizard step data |
| POST | `/api/v1/businesses/{id}/onboarding/complete` | Yes | Finalize onboarding, trigger Discovery Agent |

**PUT step request** (step-specific schemas):

```json
{
  "step_data": {
    "industry": "SaaS",
    "business_size": "small",
    "employee_count": 12
  }
}
```

**POST complete** response (202):

```json
{
  "data": {
    "agent_run_id": "uuid",
    "status": "pending",
    "poll_url": "/api/v1/agent-runs/uuid"
  }
}
```

---

### Business Profile

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/businesses/{id}/profile` | Yes | Get structured Business Profile |
| PATCH | `/api/v1/businesses/{id}/profile` | Yes | Update profile fields |

---

### Analysis & Strategy (Design)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/businesses/{id}/analyze` | Yes | Trigger full LangGraph analysis pipeline |
| GET | `/api/v1/businesses/{id}/strategy` | Yes | Get active growth strategy (CEO output) |
| GET | `/api/v1/businesses/{id}/strategy/history` | Yes | List past strategies |

**POST /analyze** triggers: Discovery (if profile stale) → parallel specialists → CEO → Analyst.

Response (202):

```json
{
  "data": {
    "agent_run_id": "uuid",
    "status": "pending",
    "estimated_duration_seconds": 60
  }
}
```

---

### Recommendations (Deliver)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/businesses/{id}/recommendations` | Yes | List recommendations (filterable) |
| GET | `/api/v1/businesses/{id}/recommendations/{rec_id}` | Yes | Get single recommendation |
| PATCH | `/api/v1/businesses/{id}/recommendations/{rec_id}` | Yes | Update status (in_progress, completed) |
| GET | `/api/v1/businesses/{id}/campaigns` | Yes | List marketing campaigns |
| POST | `/api/v1/businesses/{id}/campaigns/generate` | Yes | Generate new campaign via Marketing Agent |

**GET /recommendations** query params:

- `category` — marketing, sales, seo, etc.
- `status` — pending, in_progress, completed
- `priority` — 1, 2, 3

---

### Analytics (Develop)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/businesses/{id}/kpis` | Yes | List KPI definitions |
| POST | `/api/v1/businesses/{id}/kpis` | Yes | Create KPI definition |
| GET | `/api/v1/businesses/{id}/kpis/snapshots` | Yes | Get time-series KPI data |
| POST | `/api/v1/businesses/{id}/kpis/snapshots` | Yes | Record KPI data point |
| POST | `/api/v1/businesses/{id}/kpis/import` | Yes | Bulk CSV import |
| GET | `/api/v1/businesses/{id}/performance` | Yes | Expected vs actual comparisons |
| POST | `/api/v1/businesses/{id}/performance/analyze` | Yes | Trigger Data Analyst re-run |

**POST /kpis/snapshots** request:

```json
{
  "metric_name": "revenue",
  "value": 45000.00,
  "period_start": "2026-06-01",
  "period_end": "2026-06-30"
}
```

---

### Dashboard (Dominate)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/businesses/{id}/dashboard` | Yes | Full dashboard payload |
| GET | `/api/v1/businesses/{id}/dashboard/scores` | Yes | Score cards only |
| GET | `/api/v1/businesses/{id}/dashboard/risks` | Yes | Risk alerts |
| GET | `/api/v1/businesses/{id}/dashboard/summary` | Yes | Executive summary |

**GET /dashboard** response:

```json
{
  "data": {
    "scores": {
      "business_health_score": 72,
      "growth_score": 65,
      "revenue_opportunity": 80,
      "lead_score": 58,
      "customer_health": 70,
      "market_readiness": 75
    },
    "risk_alerts": [],
    "ai_recommendations": [],
    "executive_summary": "...",
    "performance_summary": [],
    "trends": [],
    "last_updated": "2026-07-04T10:00:00Z"
  }
}
```

---

### Agent Runs

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/agent-runs/{run_id}` | Yes | Poll run status |
| GET | `/api/v1/agent-runs/{run_id}/outputs` | Yes | Get all agent outputs for run |
| GET | `/api/v1/businesses/{id}/agent-runs` | Yes | List runs for business |

**GET /agent-runs/{id}** response:

```json
{
  "data": {
    "id": "uuid",
    "status": "running",
    "current_node": "marketing",
    "progress": {
      "completed_nodes": ["discovery"],
      "pending_nodes": ["sales", "finance", "operations", "ceo", "analyst"]
    },
    "started_at": "2026-07-04T10:00:00Z"
  }
}
```

---

### AI Copilot

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/businesses/{id}/copilot/conversations` | Yes | List conversations |
| POST | `/api/v1/businesses/{id}/copilot/conversations` | Yes | Start new conversation |
| GET | `/api/v1/businesses/{id}/copilot/conversations/{conv_id}` | Yes | Get conversation with messages |
| POST | `/api/v1/businesses/{id}/copilot/conversations/{conv_id}/messages` | Yes | Send message, get AI response |
| POST | `/api/v1/businesses/{id}/copilot/quick-ask` | Yes | Single-turn question (no conversation) |

**POST /messages** request:

```json
{
  "content": "Why is revenue decreasing?"
}
```

**POST /messages** response:

```json
{
  "data": {
    "user_message": { "id": "uuid", "content": "..." },
    "assistant_message": {
      "id": "uuid",
      "content": "...",
      "sources": [
        { "type": "kpi_snapshot", "metric": "revenue", "period": "2026-06" },
        { "type": "agent_output", "agent": "finance", "run_id": "uuid" }
      ],
      "intent": "diagnose"
    }
  }
}
```

---

## WebSocket API

For real-time agent run progress and Copilot streaming.

| Path | Purpose |
|------|---------|
| `WS /api/v1/ws/agent-runs/{run_id}` | Stream node completion events |
| `WS /api/v1/ws/copilot/{conv_id}` | Stream Copilot response tokens |

**Agent run event**:

```json
{
  "event": "node_completed",
  "data": {
    "node": "marketing",
    "status": "success",
    "duration_ms": 8500
  }
}
```

---

## Rate Limiting

| Endpoint Group | Limit | Rationale |
|----------------|-------|-----------|
| Copilot messages | 20/min per user | LLM cost control |
| Agent runs | 5/hour per business | Pipeline cost control |
| KPI snapshots | 100/min | Normal CRUD |
| Dashboard reads | 60/min | Cache-friendly |

Return `429` with `Retry-After` header.

---

## CORS Configuration

```python
origins = [
    "http://localhost:3000",       # Local dev
    "https://*.vercel.app",        # Vercel previews
    "https://business-growth-os.vercel.app"  # Production
]
```

---

## API ↔ Module Mapping

| API Group | Backend Module | 5D Phase |
|-----------|----------------|----------|
| `/onboarding`, `/profile` | M1 Business Discovery | Discover |
| `/analyze`, `/strategy` | M2 Strategy Engine | Design |
| `/recommendations`, `/campaigns` | M3 Action Generator | Deliver |
| `/kpis`, `/performance` | M4 Analytics Engine | Develop |
| `/dashboard` | M5 Dashboard & Scoring | Dominate |
| `/copilot` | M6 AI Copilot | Cross-cutting |
| `/agent-runs` | M7 Agent Orchestrator | Cross-cutting |

---

## OpenAPI Documentation

FastAPI auto-generates OpenAPI 3.1 spec at:

- `/docs` — Swagger UI
- `/redoc` — ReDoc
- `/openapi.json` — Raw spec

All Pydantic models include `json_schema_extra` with examples for hackathon demo clarity.
