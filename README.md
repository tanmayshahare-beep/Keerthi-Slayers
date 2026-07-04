# Business Growth OS

An **AI-Powered Business Growth Operating System** — not a CRM, not a chatbot. An intelligent executive team that helps business owners discover, design, deliver, develop, and dominate their market.

## Status

**Phase 1: Architecture & Design** — Complete (no implementation yet)

## 5D Framework

| Phase | Purpose |
|-------|---------|
| **Discover** | Collect and structure business information → Business Profile |
| **Design** | Analyze and strategize → SWOT, Growth Strategy, Goals |
| **Deliver** | Convert strategy to actions → Campaigns, SEO, Sales Funnel |
| **Develop** | Measure performance → KPIs, Expected vs Actual |
| **Dominate** | Executive dashboard → Health Scores, AI Recommendations |

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, React, TypeScript, Tailwind CSS, Recharts |
| Backend | FastAPI, Python 3.11+ |
| Database | PostgreSQL (Supabase) |
| Vector DB | ChromaDB |
| AI Orchestration | LangGraph |
| LLM | Google Gemini API |
| Deployment | Vercel (frontend), Render (backend) |

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture Overview](docs/ARCHITECTURE.md) | Problem analysis, modules, system design, communication |
| [Multi-Agent Architecture](docs/MULTI_AGENT_ARCHITECTURE.md) | All 7 agents: roles, I/O, prompts, formats |
| [Database Schema](docs/DATABASE_SCHEMA.md) | PostgreSQL tables, relationships, indexes |
| [API Architecture](docs/API_ARCHITECTURE.md) | REST endpoints, auth, request/response contracts |
| [LangGraph Workflow](docs/LANGGRAPH_WORKFLOW.md) | State graph, nodes, edges, feedback loops |
| [Folder Structure](docs/FOLDER_STRUCTURE.md) | Complete project layout |
| [Development Roadmap](docs/ROADMAP.md) | Phased implementation plan |
| [Team Assignments](docs/TEAM_ASSIGNMENTS.md) | 6-member team responsibilities |
| [Risks & Mitigation](docs/RISKS.md) | Project risks and strategies |
| [Architecture Diagram](docs/ARCHITECTURE_DIAGRAM.md) | One-page system diagram |

## Project Structure (Planned)

```
business-growth-os/
├── frontend/          # Next.js application
├── backend/           # FastAPI + LangGraph + agents
├── docs/              # Architecture & design documents
└── README.md
```

## Getting Started

Implementation begins in **Phase 2**. See [Development Roadmap](docs/ROADMAP.md) for the full plan.
