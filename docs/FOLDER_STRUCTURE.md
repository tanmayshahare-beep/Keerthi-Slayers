# Project Folder Structure

> Complete directory layout for frontend, backend, and documentation.

---

## Root

```
business-growth-os/
├── frontend/                 # Next.js application
├── backend/                  # FastAPI + LangGraph + agents
├── docs/                     # Architecture & design documents
├── .github/
│   └── workflows/
│       ├── frontend-ci.yml
│       └── backend-ci.yml
├── .gitignore
└── README.md
```

---

## Backend

```
backend/
├── agents/
│   ├── __init__.py
│   ├── base.py                    # BaseAgent protocol, shared utilities
│   ├── discovery_agent.py
│   ├── marketing_agent.py
│   ├── sales_agent.py
│   ├── finance_agent.py
│   ├── operations_agent.py
│   ├── ceo_agent.py
│   ├── analyst_agent.py
│   └── prompts/
│       ├── discovery.py           # System + user prompt templates
│       ├── marketing.py
│       ├── sales.py
│       ├── finance.py
│       ├── operations.py
│       ├── ceo.py
│       └── analyst.py
│
├── api/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app factory
│   ├── deps.py                    # Dependency injection (auth, db, business)
│   ├── middleware.py              # CORS, request ID, error handling
│   ├── websocket.py               # WS handlers for agent runs + copilot
│   └── routes/
│       ├── __init__.py
│       ├── health.py
│       ├── auth.py
│       ├── businesses.py
│       ├── onboarding.py
│       ├── profile.py
│       ├── analysis.py
│       ├── strategy.py
│       ├── recommendations.py
│       ├── campaigns.py
│       ├── kpis.py
│       ├── dashboard.py
│       ├── agent_runs.py
│       └── copilot.py
│
├── database/
│   ├── __init__.py
│   ├── connection.py              # Async SQLAlchemy engine + session
│   ├── migrations/                # Alembic migrations
│   │   ├── env.py
│   │   └── versions/
│   └── repositories/
│       ├── __init__.py
│       ├── business_repo.py
│       ├── profile_repo.py
│       ├── agent_run_repo.py
│       ├── strategy_repo.py
│       ├── recommendation_repo.py
│       ├── kpi_repo.py
│       ├── dashboard_repo.py
│       └── copilot_repo.py
│
├── models/
│   ├── __init__.py
│   ├── domain/                    # Domain entities (pure Python)
│   │   ├── business.py
│   │   ├── profile.py
│   │   ├── strategy.py
│   │   └── kpi.py
│   ├── schemas/                   # Pydantic request/response schemas
│   │   ├── business.py
│   │   ├── onboarding.py
│   │   ├── profile.py
│   │   ├── strategy.py
│   │   ├── recommendation.py
│   │   ├── kpi.py
│   │   ├── dashboard.py
│   │   ├── agent_run.py
│   │   └── copilot.py
│   ├── agents/                    # Agent output Pydantic models
│   │   ├── discovery_output.py
│   │   ├── marketing_output.py
│   │   ├── sales_output.py
│   │   ├── finance_output.py
│   │   ├── operations_output.py
│   │   ├── ceo_output.py
│   │   └── analyst_output.py
│   └── db/                        # SQLAlchemy ORM models
│       ├── __init__.py
│       ├── user.py
│       ├── business.py
│       ├── profile.py
│       ├── agent_run.py
│       ├── strategy.py
│       ├── recommendation.py
│       ├── kpi.py
│       ├── dashboard.py
│       └── copilot.py
│
├── services/
│   ├── __init__.py
│   ├── business_service.py
│   ├── onboarding_service.py
│   ├── profile_service.py
│   ├── analysis_service.py        # Triggers LangGraph workflows
│   ├── strategy_service.py
│   ├── recommendation_service.py
│   ├── analytics_service.py       # KPI ingestion + variance detection
│   ├── dashboard_service.py
│   ├── copilot_service.py         # RAG + intent classification
│   └── embedding_service.py       # ChromaDB upsert/query
│
├── langgraph/
│   ├── __init__.py
│   ├── state.py                   # AgentState TypedDict
│   ├── graph.py                   # Graph builder
│   ├── routing.py                 # Conditional edges
│   ├── checkpointer.py
│   └── nodes/
│       ├── __init__.py
│       ├── discovery.py
│       ├── marketing.py
│       ├── sales.py
│       ├── finance.py
│       ├── operations.py
│       ├── ceo.py
│       ├── analyst.py
│       └── persist.py
│
├── vector/
│   ├── __init__.py
│   ├── chroma_client.py           # ChromaDB connection + collection management
│   ├── chunker.py                 # Split agent outputs into embeddable chunks
│   └── retriever.py               # RAG retrieval for Copilot
│
├── utils/
│   ├── __init__.py
│   ├── llm.py                     # Gemini client wrapper
│   ├── json_repair.py             # LLM JSON parse retry logic
│   ├── auth.py                    # JWT validation
│   └── logging.py                 # Structured logging setup
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_agents/
│   │   ├── test_services/
│   │   └── test_nodes/
│   ├── integration/
│   │   ├── test_api/
│   │   └── test_langgraph/
│   └── fixtures/
│       ├── sample_profile.json
│       └── sample_agent_outputs/
│
├── alembic.ini
├── pyproject.toml                 # Dependencies (Poetry or uv)
├── Dockerfile
├── render.yaml                    # Render deployment config
├── .env.example
└── README.md
```

---

## Frontend

```
frontend/
├── app/
│   ├── layout.tsx                 # Root layout (providers, fonts)
│   ├── page.tsx                   # Landing / redirect
│   ├── globals.css
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── signup/page.tsx
│   ├── (onboarding)/
│   │   ├── layout.tsx
│   │   └── [businessId]/
│   │       ├── step-1/page.tsx    # Company basics
│   │       ├── step-2/page.tsx    # Products & services
│   │       ├── step-3/page.tsx    # Financials
│   │       ├── step-4/page.tsx    # Market & competitors
│   │       └── step-5/page.tsx    # Goals & problems
│   └── (dashboard)/
│       ├── layout.tsx             # Sidebar + header
│       └── [businessId]/
│           ├── page.tsx           # Dominate dashboard (home)
│           ├── strategy/page.tsx  # Design outputs
│           ├── actions/page.tsx   # Deliver recommendations
│           ├── analytics/page.tsx # Develop KPIs
│           └── copilot/page.tsx   # AI Copilot chat
│
├── components/
│   ├── ui/                        # Base UI (Button, Card, Input, Badge)
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   └── BusinessSwitcher.tsx
│   ├── onboarding/
│   │   ├── OnboardingWizard.tsx
│   │   ├── StepIndicator.tsx
│   │   └── forms/                 # Step-specific form components
│   ├── dashboard/
│   │   ├── ScoreCard.tsx
│   │   ├── ExecutiveSummary.tsx
│   │   ├── RiskAlerts.tsx
│   │   ├── AIRecommendations.tsx
│   │   └── PerformanceComparison.tsx
│   ├── charts/
│   │   ├── RevenueChart.tsx
│   │   ├── KpiTrendChart.tsx
│   │   ├── ScoreRadarChart.tsx
│   │   └── BudgetPieChart.tsx
│   ├── strategy/
│   │   ├── SWOTMatrix.tsx
│   │   ├── GrowthStrategy.tsx
│   │   ├── QuarterlyGoals.tsx
│   │   └── PriorityTasks.tsx
│   ├── actions/
│   │   ├── RecommendationCard.tsx
│   │   ├── CampaignList.tsx
│   │   └── FilterBar.tsx
│   ├── analytics/
│   │   ├── KpiInputForm.tsx
│   │   ├── KpiTable.tsx
│   │   └── CSVImport.tsx
│   ├── copilot/
│   │   ├── CopilotChat.tsx
│   │   ├── MessageBubble.tsx
│   │   ├── SourceCitation.tsx
│   │   └── QuickActions.tsx
│   └── shared/
│       ├── LoadingSpinner.tsx
│       ├── AgentRunProgress.tsx
│       ├── ErrorBoundary.tsx
│       └── EmptyState.tsx
│
├── hooks/
│   ├── useAuth.ts
│   ├── useBusiness.ts
│   ├── useDashboard.ts
│   ├── useAgentRun.ts             # Polling/WS for agent progress
│   ├── useCopilot.ts
│   └── useKpis.ts
│
├── services/
│   ├── api-client.ts              # Base fetch wrapper with auth
│   ├── business-api.ts
│   ├── onboarding-api.ts
│   ├── strategy-api.ts
│   ├── recommendations-api.ts
│   ├── analytics-api.ts
│   ├── dashboard-api.ts
│   ├── agent-runs-api.ts
│   └── copilot-api.ts
│
├── types/
│   ├── business.ts
│   ├── profile.ts
│   ├── strategy.ts
│   ├── recommendation.ts
│   ├── kpi.ts
│   ├── dashboard.ts
│   ├── agent-run.ts
│   └── copilot.ts
│
├── lib/
│   ├── supabase.ts                # Supabase client
│   ├── constants.ts
│   └── formatters.ts
│
├── public/
│   └── logo.svg
│
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
├── package.json
├── .env.local.example
└── README.md
```

---

## Documentation

```
docs/
├── ARCHITECTURE.md
├── MULTI_AGENT_ARCHITECTURE.md
├── DATABASE_SCHEMA.md
├── API_ARCHITECTURE.md
├── LANGGRAPH_WORKFLOW.md
├── FOLDER_STRUCTURE.md            # This file
├── ROADMAP.md
├── TEAM_ASSIGNMENTS.md
├── RISKS.md
└── ARCHITECTURE_DIAGRAM.md
```

---

## Naming Conventions

| Layer | Convention | Example |
|-------|------------|---------|
| Python files | snake_case | `discovery_agent.py` |
| Python classes | PascalCase | `DiscoveryAgent` |
| TypeScript files | PascalCase for components, camelCase for utils | `ScoreCard.tsx`, `api-client.ts` |
| API routes | kebab-case in URL, snake_case in Python | `/agent-runs/{id}` |
| DB tables | snake_case, plural | `business_profiles` |
| Agent output keys | snake_case | `business_health_score` |
| Environment vars | SCREAMING_SNAKE | `GEMINI_API_KEY` |

---

## Environment Variables

### Backend (`.env`)

```
DATABASE_URL=postgresql+asyncpg://...
SUPABASE_URL=https://...
SUPABASE_JWT_SECRET=...
GEMINI_API_KEY=...
CHROMA_PERSIST_DIR=./chroma_data
CORS_ORIGINS=http://localhost:3000
LOG_LEVEL=INFO
```

### Frontend (`.env.local`)

```
NEXT_PUBLIC_SUPABASE_URL=https://...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```
