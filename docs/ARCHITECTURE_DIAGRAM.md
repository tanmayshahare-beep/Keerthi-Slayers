# One-Page Architecture Diagram

> Complete system view: Frontend → Backend → AI Layer → Knowledge Layer → Database → Dashboard

---

## System Architecture (Single View)

```mermaid
flowchart TB
    subgraph DEPLOY["Deployment"]
        VERCEL["Vercel<br/>Next.js Frontend"]
        RENDER["Render<br/>FastAPI Backend"]
    end

    subgraph FRONTEND["Frontend Layer — Next.js + React + TypeScript + Tailwind + Recharts"]
        AUTH_UI["Auth Pages<br/>Login / Signup"]
        ONBOARD["Onboarding Wizard<br/>(Discover)"]
        DASH["Executive Dashboard<br/>(Dominate)"]
        STRAT_UI["Strategy View<br/>(Design)"]
        ACT_UI["Actions View<br/>(Deliver)"]
        ANAL_UI["Analytics View<br/>(Develop)"]
        COPILOT_UI["AI Copilot Chat"]
    end

    subgraph API["API Gateway — FastAPI REST + WebSocket"]
        REST["/api/v1/*<br/>REST Endpoints"]
        WS["WebSocket<br/>Agent Progress + Copilot Stream"]
    end

    subgraph SERVICES["Service Layer"]
        SVC_DISC["Discovery Service"]
        SVC_STRAT["Strategy Service"]
        SVC_ACT["Action Service"]
        SVC_ANAL["Analytics Service"]
        SVC_DASH["Dashboard Service"]
        SVC_COP["Copilot Service"]
    end

    subgraph LANGGRAPH["AI Orchestration — LangGraph"]
        LG["State Graph Engine"]
        LG --> N1["Discovery"]
        LG --> N2["Marketing"]
        LG --> N3["Sales"]
        LG --> N4["Finance"]
        LG --> N5["Operations"]
        N2 & N3 & N4 & N5 --> N6["CEO Agent"]
        N6 --> N7["Data Analyst"]
        N7 --> N8["Persist"]
    end

    subgraph AGENTS["AI Agents — 7 Specialists"]
        A1["Discovery Agent"]
        A2["Marketing Agent"]
        A3["Sales Agent"]
        A4["Finance Agent"]
        A5["Operations Agent"]
        A6["CEO Agent"]
        A7["Data Analyst Agent"]
    end

    subgraph LLM["LLM Provider"]
        GEMINI["Google Gemini API<br/>1.5 Pro + Flash"]
    end

    subgraph KNOWLEDGE["Knowledge Layer"]
        CHROMA["ChromaDB<br/>Vector Store<br/>RAG Embeddings"]
    end

    subgraph DATABASE["Database Layer — Supabase PostgreSQL"]
        PG_USERS["users"]
        PG_BIZ["businesses"]
        PG_PROFILE["business_profiles"]
        PG_RUNS["agent_runs"]
        PG_OUTPUTS["agent_outputs"]
        PG_STRAT["strategies"]
        PG_REC["recommendations"]
        PG_KPI["kpi_snapshots"]
        PG_SCORES["dashboard_scores"]
        PG_COP["copilot_messages"]
    end

    subgraph EXTERNAL["Third-Party Services"]
        SUPA_AUTH["Supabase Auth<br/>JWT / OAuth"]
    end

    VERCEL --- FRONTEND
    AUTH_UI --> SUPA_AUTH
    ONBOARD & DASH & STRAT_UI & ACT_UI & ANAL_UI & COPILOT_UI --> REST
    ONBOARD & DASH & COPILOT_UI --> WS
    FRONTEND --> VERCEL
    REST & WS --> RENDER
    REST --> SERVICES
    WS --> SERVICES
    SVC_DISC & SVC_STRAT --> LG
    SVC_ANAL --> LG
    N1 --> A1
    N2 --> A2
    N3 --> A3
    N4 --> A4
    N5 --> A5
    N6 --> A6
    N7 --> A7
    A1 & A2 & A3 & A4 & A5 & A6 & A7 --> GEMINI
    SVC_COP --> GEMINI
    SVC_COP --> CHROMA
    N8 --> CHROMA
    N8 --> DATABASE
    SERVICES --> DATABASE
    SUPA_AUTH --> PG_USERS
```

---

## Layer Summary

| Layer | Technology | Responsibility |
|-------|------------|----------------|
| **Frontend** | Next.js, React, TypeScript, Tailwind, Recharts | UI for 5D lifecycle + Copilot |
| **API Gateway** | FastAPI, WebSocket | REST endpoints, auth, async jobs |
| **Service Layer** | Python services | Business logic, use cases |
| **AI Orchestration** | LangGraph | Agent pipeline state machine |
| **AI Agents** | 7 specialist agents | Domain-specific LLM reasoning |
| **LLM** | Google Gemini 1.5 Pro/Flash | Language model inference |
| **Knowledge Layer** | ChromaDB | Vector embeddings for RAG |
| **Database** | PostgreSQL (Supabase) | Structured data, auth, RLS |
| **Deployment** | Vercel + Render | Production hosting |

---

## Data Flow (Business Lifecycle)

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant API as FastAPI
    participant LG as LangGraph
    participant Agents as AI Agents
    participant Gemini as Gemini API
    participant PG as PostgreSQL
    participant Chroma as ChromaDB

    User->>FE: Complete Onboarding
    FE->>API: POST /onboarding/complete
    API->>LG: Start workflow (run_id)
    API-->>FE: 202 { agent_run_id }

    LG->>Agents: Discovery Agent
    Agents->>Gemini: Structured prompt
    Gemini-->>Agents: Business Profile JSON
    Agents-->>LG: Update state

    par Parallel Specialists
        LG->>Agents: Marketing Agent
        LG->>Agents: Sales Agent
        LG->>Agents: Finance Agent
        LG->>Agents: Operations Agent
    end
    Agents->>Gemini: Domain prompts
    Gemini-->>Agents: Strategy JSON

    LG->>Agents: CEO Agent (synthesis)
    Agents->>Gemini: Consolidation prompt
    Gemini-->>Agents: Growth Plan JSON

    LG->>Agents: Data Analyst Agent
    Agents->>PG: Load KPI snapshots
    Agents->>Gemini: Analysis prompt
    Gemini-->>Agents: Dashboard scores

    LG->>PG: Persist all outputs
    LG->>Chroma: Embed for RAG

    FE->>API: GET /dashboard
    API->>PG: Load scores + strategy
    API-->>FE: Dashboard payload
    FE-->>User: Executive Dashboard

    User->>FE: Copilot question
    FE->>API: POST /copilot/quick-ask
    API->>Chroma: RAG retrieval
    API->>PG: KPI query
    API->>Gemini: Context + question
    Gemini-->>API: Answer with sources
    API-->>FE: Copilot response
    FE-->>User: AI answer with citations
```

---

## Deployment Architecture

```mermaid
flowchart LR
    USER["User Browser"]

    subgraph VERCEL["Vercel"]
        NEXT["Next.js App<br/>SSR + Static"]
    end

    subgraph RENDER["Render"]
        FAST["FastAPI<br/>Python 3.11"]
        CHROMA_LOCAL["ChromaDB<br/>Embedded + Volume"]
    end

    subgraph SUPABASE["Supabase Cloud"]
        PG["PostgreSQL"]
        AUTH["Auth Service"]
    end

    subgraph GOOGLE["Google Cloud"]
        GEMINI["Gemini API"]
    end

    USER -->|HTTPS| NEXT
    NEXT -->|API calls| FAST
    NEXT -->|Auth| AUTH
    FAST --> PG
    FAST --> CHROMA_LOCAL
    FAST --> GEMINI
    AUTH --> PG
```

---

## Tech Stack Reference

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BUSINESS GROWTH OS                              │
├─────────────────────────────────────────────────────────────────────────┤
│  FRONTEND          │  Next.js 14 · React 18 · TypeScript · Tailwind    │
│                    │  Recharts · TanStack Query · Supabase JS           │
├────────────────────┼────────────────────────────────────────────────────┤
│  BACKEND           │  FastAPI · Python 3.11 · Pydantic v2 · SQLAlchemy │
│                    │  Alembic · WebSocket · BackgroundTasks             │
├────────────────────┼────────────────────────────────────────────────────┤
│  AI LAYER          │  LangGraph · 7 Custom Agents · Prompt Templates   │
│                    │  Google Gemini 1.5 Pro / Flash                     │
├────────────────────┼────────────────────────────────────────────────────┤
│  KNOWLEDGE LAYER   │  ChromaDB (embedded) · RAG · Embedding Service    │
├────────────────────┼────────────────────────────────────────────────────┤
│  DATABASE          │  PostgreSQL (Supabase) · Row-Level Security       │
│                    │  Supabase Auth (JWT)                               │
├────────────────────┼────────────────────────────────────────────────────┤
│  DEPLOYMENT        │  Vercel (frontend) · Render (backend + ChromaDB)  │
├────────────────────┼────────────────────────────────────────────────────┤
│  THIRD-PARTY       │  Google Gemini API · Supabase (Auth + DB)         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5D Framework → System Mapping

| 5D Phase | Frontend Route | API Endpoints | Agents | DB Tables |
|----------|---------------|---------------|--------|-----------|
| **Discover** | `/onboarding/*` | `/onboarding`, `/profile` | Discovery | business_profiles |
| **Design** | `/strategy` | `/analyze`, `/strategy` | Marketing, Sales, Finance, Ops, CEO | strategies, agent_outputs |
| **Deliver** | `/actions` | `/recommendations`, `/campaigns` | Marketing, Sales, Ops | recommendations, campaigns |
| **Develop** | `/analytics` | `/kpis`, `/performance` | Data Analyst | kpi_snapshots, performance_comparisons |
| **Dominate** | `/` (dashboard) | `/dashboard` | Data Analyst | dashboard_scores |
| **Copilot** | `/copilot` | `/copilot/*` | RAG over all outputs | copilot_messages |

---

## Agent Execution Flow

```
User Action                    LangGraph Pipeline                 Output
───────────                    ──────────────────                 ──────

Onboarding Complete ──────►  [Discovery]  ──────────────────►  Business Profile
                                    │
Full Analysis Request ────►  [Marketing ]──┐
                             [Sales     ]──┤
                             [Finance   ]──┼──► [CEO] ──► [Analyst] ──► Dashboard
                             [Operations]──┘
                                    │
KPI Update ───────────────►  [Analyst]  ──────────────────►  Updated Scores
                                    │
Copilot Question ─────────►  RAG Query (ChromaDB + PG) ────►  Contextual Answer
```
