# Team Assignments — 6 Members

> Role-based ownership aligned to architecture modules and development phases.

---

## Team Structure

```
                    ┌─────────────────────┐
                    │    Team Lead /      │
                    │  Full-Stack Architect│
                    └──────────┬──────────┘
                               │
        ┌──────────┬───────────┼───────────┬──────────┐
        │          │           │           │          │
   ┌────▼────┐ ┌───▼───┐ ┌────▼────┐ ┌────▼────┐ ┌───▼───┐
   │Backend  │ │Frontend│ │   AI    │ │  DevOps │ │  QA   │
   │  Lead   │ │  Lead  │ │Engineer │ │ / Infra │ │ / PM  │
   └────┬────┘ └───┬───┘ └────┬────┘ └────┬────┘ └───┬───┘
        │          │           │           │          │
   ┌────▼────┐ ┌───▼───┐      │           │          │
   │Backend  │ │Frontend│      │           │          │
   │  Dev    │ │  Dev   │      │           │          │
   └─────────┘ └────────┘      │           │          │
                               │           │          │
                    All members contribute to integration testing
```

---

## Member 1: Team Lead / Full-Stack Architect

**Name**: _(assign)_  
**Primary focus**: Architecture enforcement, integration, code review

### Responsibilities

| Area | Tasks |
|------|-------|
| Architecture | Maintain design docs; resolve cross-module conflicts |
| Backend | FastAPI app factory, middleware, dependency injection |
| Integration | End-to-end flow testing; API contract enforcement |
| LangGraph | Graph topology review; checkpointing strategy |
| Code review | All PRs require Lead approval |
| Demo | Demo script; presentation narrative |

### Owns (Files/Modules)

- `backend/api/main.py`, `deps.py`, `middleware.py`
- `backend/langgraph/graph.py`, `routing.py`
- `docs/*` (maintains architecture docs)
- Root `README.md`

### Phase Ownership

| Phase | Role |
|-------|------|
| 1 | Author (complete) |
| 2–6 | Integration lead, unblocks blockers |

---

## Member 2: Backend Lead

**Name**: _(assign)_  
**Primary focus**: Database, repositories, core services, auth

### Responsibilities

| Area | Tasks |
|------|-------|
| Database | SQLAlchemy models, Alembic migrations, RLS policies |
| Auth | Supabase JWT validation, user context injection |
| Services | Business, onboarding, profile, analysis services |
| Repositories | All PostgreSQL repository implementations |
| API routes | Businesses, onboarding, profile, agent-runs |

### Owns (Files/Modules)

- `backend/database/*`
- `backend/models/db/*`
- `backend/models/schemas/*`
- `backend/services/business_service.py`, `onboarding_service.py`, `profile_service.py`, `analysis_service.py`
- `backend/api/routes/businesses.py`, `onboarding.py`, `profile.py`, `agent_runs.py`
- `backend/utils/auth.py`

### Phase Ownership

| Phase | Deliverables |
|-------|-------------|
| 2 | DB schema, auth, onboarding API |
| 3 | Agent run tracking, strategy persistence |
| 4 | KPI API, dashboard service |
| 6 | Render deployment config |

---

## Member 3: Backend Developer

**Name**: _(assign)_  
**Primary focus**: Agent outputs persistence, recommendations, analytics, copilot backend

### Responsibilities

| Area | Tasks |
|------|-------|
| Deliver module | Recommendations + campaigns API and services |
| Develop module | KPI snapshots, performance comparison, feedback events |
| Dominate module | Dashboard scores API |
| Copilot | Copilot service, RAG retrieval, conversation API |
| Vector | ChromaDB client, chunker, retriever |
| WebSocket | Agent run progress + copilot streaming |

### Owns (Files/Modules)

- `backend/services/recommendation_service.py`, `analytics_service.py`, `dashboard_service.py`, `copilot_service.py`, `embedding_service.py`
- `backend/api/routes/recommendations.py`, `campaigns.py`, `kpis.py`, `dashboard.py`, `copilot.py`
- `backend/vector/*`
- `backend/api/websocket.py`

### Phase Ownership

| Phase | Deliverables |
|-------|-------------|
| 3 | Recommendations persistence, ChromaDB setup |
| 4 | KPI + dashboard APIs |
| 5 | Copilot backend |

---

## Member 4: AI Engineer

**Name**: _(assign)_  
**Primary focus**: All 7 agents, prompts, LangGraph nodes, LLM integration

### Responsibilities

| Area | Tasks |
|------|-------|
| Agents | Implement all 7 agents with prompt engineering |
| Prompts | Write, test, and iterate prompt templates |
| LangGraph | Implement all graph nodes and routing logic |
| LLM | Gemini client wrapper, JSON validation, retry logic |
| Output schemas | Pydantic models for all agent outputs |
| Testing | Agent unit tests with mock LLM responses |

### Owns (Files/Modules)

- `backend/agents/*`
- `backend/agents/prompts/*`
- `backend/langgraph/nodes/*`
- `backend/langgraph/state.py`
- `backend/models/agents/*`
- `backend/utils/llm.py`, `json_repair.py`

### Phase Ownership

| Phase | Deliverables |
|-------|-------------|
| 2 | Discovery Agent + node |
| 3 | All 7 agents + full graph |
| 4 | Data Analyst Agent + KPI reanalysis workflow |
| 5 | Copilot intent classification + RAG context assembly |

---

## Member 5: Frontend Lead

**Name**: _(assign)_  
**Primary focus**: App shell, dashboard, charts, design system

### Responsibilities

| Area | Tasks |
|------|-------|
| App shell | Layout, sidebar, header, routing, auth pages |
| Dashboard | Score cards, executive summary, risk alerts (Dominate) |
| Charts | Recharts components for KPIs, scores, budget |
| Design system | Base UI components (Button, Card, Input, Badge) |
| API layer | API client, types, TanStack Query setup |
| State | Auth context, business context |

### Owns (Files/Modules)

- `frontend/app/layout.tsx`, `(dashboard)/layout.tsx`
- `frontend/components/ui/*`
- `frontend/components/layout/*`
- `frontend/components/dashboard/*`
- `frontend/components/charts/*`
- `frontend/services/api-client.ts`
- `frontend/types/*`
- `frontend/hooks/useAuth.ts`, `useDashboard.ts`

### Phase Ownership

| Phase | Deliverables |
|-------|-------------|
| 2 | Auth pages, app shell |
| 4 | Dashboard home with scores and charts |
| 6 | Vercel deployment |

---

## Member 6: Frontend Developer / QA

**Name**: _(assign)_  
**Primary focus**: Onboarding, strategy/actions pages, copilot UI, testing

### Responsibilities

| Area | Tasks |
|------|-------|
| Onboarding | 5-step wizard with validation (Discover) |
| Strategy | SWOT, growth plan, goals, tasks pages (Design) |
| Actions | Recommendations list, campaign cards (Deliver) |
| Analytics | KPI input form, trend display (Develop) |
| Copilot | Chat UI, message bubbles, source citations |
| QA | Manual test plans, bug reporting, demo data seeding |
| UX | Loading states, error boundaries, empty states, responsive |

### Owns (Files/Modules)

- `frontend/app/(onboarding)/*`
- `frontend/components/onboarding/*`
- `frontend/components/strategy/*`
- `frontend/components/actions/*`
- `frontend/components/analytics/*`
- `frontend/components/copilot/*`
- `frontend/components/shared/*`
- `frontend/hooks/useAgentRun.ts`, `useCopilot.ts`, `useKpis.ts`

### Phase Ownership

| Phase | Deliverables |
|-------|-------------|
| 2 | Onboarding wizard |
| 3 | Strategy + actions pages |
| 4 | Analytics page |
| 5 | Copilot UI + demo prep |

---

## Collaboration Matrix

| Activity | Lead | Backend Lead | Backend Dev | AI Engineer | FE Lead | FE Dev |
|----------|------|-------------|-------------|-------------|---------|--------|
| Architecture review | **R** | C | C | C | C | I |
| API contract definition | **R** | C | C | I | C | I |
| Agent prompt iteration | C | I | I | **R** | I | I |
| DB schema changes | C | **R** | C | I | I | I |
| UI/UX decisions | C | I | I | I | **R** | C |
| LangGraph workflow | **R** | C | I | **R** | I | I |
| Integration testing | C | C | C | C | C | **R** |
| Deployment | C | **R** | I | I | **R** | I |
| Demo preparation | **R** | C | C | C | C | C |

_R = Responsible, C = Consulted, I = Informed_

---

## Communication Cadence

| Meeting | Frequency | Participants | Purpose |
|---------|-----------|-------------|---------|
| Standup | Daily, 15 min | All | Blockers, progress |
| Architecture sync | Twice weekly | Lead + Backend Lead + AI Engineer | API/agent contracts |
| Frontend sync | Twice weekly | Lead + FE Lead + FE Dev | UI/API alignment |
| Integration test | End of each phase | All | Phase exit criteria verification |
| Demo rehearsal | 2 days before deadline | All | Full walkthrough |

---

## Git Workflow

- **Main branch**: `main` — always deployable
- **Feature branches**: `{member}/{feature}` — e.g., `ai-engineer/discovery-agent`
- **PR rules**: 1 approval required; Lead approves architecture-sensitive changes
- **Commit style**: `feat:`, `fix:`, `docs:`, `refactor:` prefixes

---

## Skill Requirements Summary

| Member | Required Skills |
|--------|----------------|
| Team Lead | System design, FastAPI, LangGraph, code review |
| Backend Lead | Python, SQLAlchemy, PostgreSQL, REST API design |
| Backend Dev | Python, FastAPI, WebSocket, vector DB basics |
| AI Engineer | LLM prompt engineering, LangGraph, Pydantic, JSON schemas |
| Frontend Lead | Next.js, TypeScript, Tailwind, Recharts, state management |
| Frontend Dev | React, forms, UX, manual testing, responsive design |
