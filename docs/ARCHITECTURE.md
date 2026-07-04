# System Architecture — Business Growth OS

> Phase 1 deliverable. No implementation code — design only.

---

## 1. Problem Analysis

### 1.1 Core Problem

Small and mid-size business owners lack access to an executive team. They must simultaneously understand their market, design strategy, execute marketing and sales, measure results, and adapt — often without dedicated analysts, CMOs, or CFOs.

Existing tools solve **fragments** of this problem:

| Tool Type | What It Does | What It Misses |
|-----------|--------------|----------------|
| CRM | Tracks contacts and deals | No strategy generation or cross-functional analysis |
| Chatbot | Answers questions | No persistent business model, no structured lifecycle |
| Analytics dashboards | Shows metrics | No recommendations, no causal reasoning |
| Marketing automation | Executes campaigns | No upstream strategy or financial context |

**Our system** closes the loop: it **understands** the business, **generates** strategy, **recommends** actions, **measures** outcomes, and **learns** from feedback — continuously.

### 1.2 System Goals

1. **Holistic understanding** — Single structured Business Profile from onboarding
2. **Multi-domain intelligence** — Marketing, Sales, Finance, Operations analyzed in parallel
3. **Executive synthesis** — CEO Agent resolves conflicts and prioritizes
4. **Actionable output** — Not reports alone; concrete campaigns, funnels, budgets
5. **Closed-loop learning** — Develop phase feeds back into Design and Deliver
6. **Accessible interface** — Dashboard for scores; Copilot for natural-language queries

### 1.3 Non-Goals (Hackathon Scope)

- Real ad platform integration (Google Ads API) — mock/simulate for demo
- Real payment processing or accounting sync — manual KPI entry + CSV import
- Multi-tenant enterprise SSO — Supabase auth with email/password
- Custom LLM fine-tuning — prompt engineering + RAG only

### 1.4 Key Constraints

- **Latency**: Agent pipeline may take 30–90 seconds; use async jobs + polling/WebSocket
- **Cost**: Gemini API calls batched; cache agent outputs in PostgreSQL
- **Consistency**: Structured JSON outputs from all agents via Pydantic validation
- **Traceability**: Every recommendation links to the agent run that produced it

---

## 2. Module Breakdown

The system decomposes into **8 logical modules**, each mapped to the 5D framework.

```
┌─────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Onboarding  │  │  Dashboard   │  │     AI Copilot       │  │
│  │  (Discover)  │  │  (Dominate)  │  │  (Cross-cutting)     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                         API GATEWAY                              │
│              FastAPI — REST /api/v1 + WebSocket                  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATION LAYER                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              LangGraph Workflow Engine                    │   │
│  │   Discovery → Specialists (parallel) → CEO → Analyst    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                         AGENT LAYER                              │
│  Discovery │ Marketing │ Sales │ Finance │ Ops │ CEO │ Analyst  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                        SERVICE LAYER                             │
│  Profile │ Strategy │ Campaign │ Analytics │ Scoring │ Copilot  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                       KNOWLEDGE LAYER                            │
│  ┌────────────────────┐    ┌─────────────────────────────┐    │
│  │  PostgreSQL (Supabase)│    │  ChromaDB (Vector Store)    │    │
│  │  Structured data      │    │  Embeddings + RAG context   │    │
│  └────────────────────┘    └─────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Module Definitions

| # | Module | 5D Phase | Responsibility |
|---|--------|----------|----------------|
| M1 | **Business Discovery** | Discover | Multi-step onboarding wizard; validates and persists Business Profile |
| M2 | **Strategy Engine** | Design | Triggers Design-phase agents; stores SWOT, goals, budget allocation |
| M3 | **Action Generator** | Deliver | Produces campaigns, SEO plans, funnel improvements, pricing suggestions |
| M4 | **Analytics Engine** | Develop | KPI ingestion, expected vs actual comparison, trend detection |
| M5 | **Dashboard & Scoring** | Dominate | Computes health scores; renders executive summary and risk alerts |
| M6 | **AI Copilot** | Cross-cutting | NL interface over business data + agent outputs via RAG |
| M7 | **Agent Orchestrator** | Cross-cutting | LangGraph state machine; manages agent execution and dependencies |
| M8 | **Auth & Tenant** | Foundation | User auth, business ownership, row-level security |

---

## 3. Overall Software Architecture

### 3.1 Architecture Style

**Clean Architecture** with **hexagonal boundaries**:

```
┌──────────────────────────────────────────────┐
│  Adapters (In)  │  API routes, WebSocket     │
├──────────────────────────────────────────────┤
│  Application    │  Services, use cases       │
├──────────────────────────────────────────────┤
│  Domain         │  Models, business rules    │
├──────────────────────────────────────────────┤
│  Adapters (Out) │  DB repos, LLM, ChromaDB   │
└──────────────────────────────────────────────┘
```

**Rationale**: Agents and API routes depend on domain interfaces, not concrete DB/LLM implementations. Enables testing agents with mock repositories and swapping Gemini for another LLM later.

### 3.2 Deployment Architecture

```
                    ┌─────────────┐
                    │   Vercel    │
                    │  (Next.js)  │
                    └──────┬──────┘
                           │ HTTPS
                    ┌──────▼──────┐
                    │   Render    │
                    │  (FastAPI)  │
                    └──┬───────┬──┘
                       │       │
              ┌────────▼──┐ ┌──▼──────────┐
              │ Supabase  │ │  ChromaDB   │
              │ PostgreSQL│ │  (embedded  │
              │           │ │  or hosted) │
              └───────────┘ └─────────────┘
                       │
              ┌────────▼──────────┐
              │  Google Gemini   │
              │  API             │
              └─────────────────┘
```

**Decision**: ChromaDB runs **embedded in the FastAPI process** on Render for hackathon simplicity. Persistent volume mounted for durability. Can migrate to Chroma Cloud post-hackathon.

### 3.3 Frontend Architecture

- **Next.js App Router** with route groups: `(auth)`, `(dashboard)`, `(onboarding)`
- **Server Components** for dashboard data fetching (SSR with caching)
- **Client Components** for interactive charts (Recharts), Copilot chat, onboarding forms
- **API client layer** (`services/`) — typed fetch wrappers, no direct DB access from frontend
- **State**: React Context for auth; TanStack Query for server state caching

### 3.4 Backend Architecture

- **FastAPI** with async endpoints
- **Dependency injection** for DB sessions, current user, business context
- **Background tasks** via FastAPI `BackgroundTasks` for agent runs (Phase 2); Celery optional for production
- **Pydantic v2** models at API boundary and agent output validation
- **Repository pattern** for PostgreSQL access (SQLAlchemy 2.0 async)

---

## 4. Module Communication

### 4.1 Synchronous Flow (User-Initiated)

```
User → Frontend → REST API → Service Layer → Repository → PostgreSQL
                                    │
                                    └──→ LangGraph → Agents → Gemini
                                              │
                                              └──→ ChromaDB (embeddings)
```

### 4.2 Async Agent Pipeline

Long-running agent workflows use **job-based execution**:

1. `POST /api/v1/businesses/{id}/analyze` → creates `agent_run` record (status: `pending`)
2. Background worker executes LangGraph workflow
3. Frontend polls `GET /api/v1/agent-runs/{run_id}` or subscribes via WebSocket
4. On completion, outputs persisted to PostgreSQL + embedded in ChromaDB
5. Dashboard and Copilot read from stored outputs

### 4.3 Inter-Module Communication Matrix

| From → To | Protocol | Payload |
|-----------|----------|---------|
| Frontend → API | HTTPS REST/WS | JSON (Pydantic-validated) |
| API → Services | In-process call | Domain objects |
| Services → Repositories | In-process call | SQL via SQLAlchemy |
| Services → LangGraph | In-process call | `AgentState` TypedDict |
| LangGraph → Agents | In-process call | Prompt + context |
| Agents → Gemini | HTTPS | Chat completion request |
| Agents → ChromaDB | HTTP/local | Embedding upsert/query |
| Analyst Agent → Strategy Engine | State graph edge | KPI deltas trigger re-analysis flag |
| Copilot → ChromaDB | RAG query | User question + top-k chunks |
| Copilot → PostgreSQL | Structured query | Business profile, latest scores |

### 4.4 Event-Driven Feedback Loop (Develop → Design)

```
Analytics Engine detects KPI deviation
        │
        ▼
Creates `feedback_event` record
        │
        ▼
Data Analyst Agent re-evaluates trends
        │
        ▼
CEO Agent receives updated analyst report
        │
        ▼
Strategy Engine marks recommendations as `stale`
        │
        ▼
User notified via Dashboard risk alerts
```

### 4.5 Data Flow Through 5D Lifecycle

```
DISCOVER          DESIGN              DELIVER
   │                 │                    │
   ▼                 ▼                    ▼
Business Profile → Strategy Doc → Action Items
   │                 │                    │
   └─────────────────┴────────────────────┘
                     │
                     ▼
                  DEVELOP ←── KPI Input (manual/CSV)
                     │
                     ▼
                  DOMINATE
                     │
                     ▼
              Dashboard + Copilot
                     │
                     └──→ Feedback → DESIGN (re-run)
```

---

## 5. Cross-Cutting Concerns

### 5.1 Authentication & Authorization

- Supabase Auth (JWT) → FastAPI validates token on every request
- Row-level security: users access only their `business_id`(s)
- API keys for service-to-service (Render internal) not needed in hackathon

### 5.2 Error Handling

- Structured error responses: `{ "error": { "code", "message", "details" } }`
- Agent failures: partial results saved; CEO Agent notes missing inputs
- LLM JSON parse failures: retry once with repair prompt; else mark run `failed`

### 5.3 Observability

- Structured logging (JSON) with `request_id`, `business_id`, `agent_run_id`
- Agent run timeline stored in DB for demo/debugging
- Health check: `GET /health` (DB + ChromaDB + Gemini connectivity)

### 5.4 Caching Strategy

| Data | Cache | TTL |
|------|-------|-----|
| Business Profile | PostgreSQL (source of truth) | — |
| Agent outputs | PostgreSQL + ChromaDB | Until re-run triggered |
| Dashboard scores | Computed on read; cached in Redis optional | 5 min |
| Copilot RAG chunks | ChromaDB | Persistent |

---

## 6. Technology Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Frontend framework | Next.js 14 | SSR for dashboard, Vercel deployment, React ecosystem |
| Backend framework | FastAPI | Async, Pydantic native, Python AI ecosystem |
| Primary DB | PostgreSQL via Supabase | Relational data, auth built-in, free tier |
| Vector DB | ChromaDB | Lightweight, Python-native, easy RAG setup |
| Agent framework | LangGraph | Explicit state graphs, parallel nodes, checkpointing |
| LLM | Gemini 1.5 Pro/Flash | Cost-effective, long context, JSON mode |
| Charts | Recharts | React-native, composable |
| Deployment | Vercel + Render | Zero-config frontend, simple Python hosting |

---

## Related Documents

- [Multi-Agent Architecture](MULTI_AGENT_ARCHITECTURE.md)
- [Database Schema](DATABASE_SCHEMA.md)
- [API Architecture](API_ARCHITECTURE.md)
- [LangGraph Workflow](LANGGRAPH_WORKFLOW.md)
- [Architecture Diagram](ARCHITECTURE_DIAGRAM.md)
