# Database Schema Design

> PostgreSQL via Supabase. All tables use UUID primary keys unless noted.

---

## Entity Relationship Overview

```
users ──────────────< businesses
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
  business_profiles  agent_runs      kpi_snapshots
                          │
                          ▼
                    agent_outputs
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    strategies    recommendations   dashboard_scores
                          │
                          ▼
                  copilot_conversations
                          │
                          ▼
                  copilot_messages
```

---

## Core Tables

### `users`

Managed by Supabase Auth. Extended profile:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, FK → auth.users | Supabase user ID |
| `email` | VARCHAR(255) | NOT NULL, UNIQUE | User email |
| `full_name` | VARCHAR(255) | | Display name |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

### `businesses`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | |
| `owner_id` | UUID | FK → users.id, NOT NULL | Business owner |
| `name` | VARCHAR(255) | NOT NULL | Company name |
| `status` | VARCHAR(50) | NOT NULL, DEFAULT 'onboarding' | onboarding, active, archived |
| `onboarding_step` | INT | DEFAULT 0 | Wizard progress (0–5) |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Indexes**: `idx_businesses_owner_id`

---

## Discover Phase

### `business_profiles`

Structured output of Discovery Agent + onboarding data.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `business_id` | UUID | FK → businesses.id, UNIQUE, NOT NULL | One profile per business |
| `profile_data` | JSONB | NOT NULL | Full Business Profile schema |
| `completeness_score` | INT | CHECK (0–100) | Data quality score |
| `data_gaps` | JSONB | DEFAULT '[]' | Missing fields array |
| `version` | INT | NOT NULL, DEFAULT 1 | Profile version |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Indexes**: `idx_profiles_business_id`, GIN index on `profile_data`

### `onboarding_responses`

Raw wizard step data before agent processing.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `business_id` | UUID | FK → businesses.id, NOT NULL | |
| `step_number` | INT | NOT NULL | Wizard step (1–5) |
| `step_data` | JSONB | NOT NULL | Raw form data for step |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Unique**: `(business_id, step_number)`

---

## Design Phase

### `agent_runs`

Tracks every LangGraph workflow execution.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `business_id` | UUID | FK → businesses.id, NOT NULL | |
| `run_type` | VARCHAR(50) | NOT NULL | full_analysis, copilot_refresh, kpi_reanalysis |
| `status` | VARCHAR(50) | NOT NULL, DEFAULT 'pending' | pending, running, completed, failed, partial |
| `current_node` | VARCHAR(50) | | LangGraph node name |
| `started_at` | TIMESTAMPTZ | | |
| `completed_at` | TIMESTAMPTZ | | |
| `error_message` | TEXT | | Failure details |
| `metadata` | JSONB | DEFAULT '{}' | Token usage, timing per node |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Indexes**: `idx_agent_runs_business_id`, `idx_agent_runs_status`

### `agent_outputs`

Individual agent results linked to a run.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `agent_run_id` | UUID | FK → agent_runs.id, NOT NULL | |
| `business_id` | UUID | FK → businesses.id, NOT NULL | |
| `agent_name` | VARCHAR(50) | NOT NULL | discovery, marketing, sales, etc. |
| `output_data` | JSONB | NOT NULL | Validated agent JSON output |
| `prompt_version` | VARCHAR(20) | NOT NULL | For reproducibility |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Indexes**: `idx_outputs_run_id`, `idx_outputs_business_agent` (business_id, agent_name, created_at DESC)

### `strategies`

CEO Agent synthesized output (Design phase primary artifact).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `business_id` | UUID | FK → businesses.id, NOT NULL | |
| `agent_run_id` | UUID | FK → agent_runs.id, NOT NULL | |
| `swot_analysis` | JSONB | NOT NULL | |
| `growth_strategy` | JSONB | NOT NULL | |
| `market_analysis` | JSONB | NOT NULL | |
| `competitor_analysis` | JSONB | NOT NULL | |
| `quarterly_goals` | JSONB | NOT NULL | |
| `budget_allocation` | JSONB | NOT NULL | |
| `priority_tasks` | JSONB | NOT NULL | |
| `executive_summary` | TEXT | NOT NULL | |
| `is_active` | BOOLEAN | DEFAULT true | Latest strategy flag |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Indexes**: `idx_strategies_business_active` (business_id, is_active)

---

## Deliver Phase

### `recommendations`

Actionable items from Marketing, Sales, Operations agents.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `business_id` | UUID | FK → businesses.id, NOT NULL | |
| `agent_run_id` | UUID | FK → agent_runs.id | |
| `category` | VARCHAR(50) | NOT NULL | marketing, sales, seo, ads, social, ops, pricing, retention |
| `title` | VARCHAR(500) | NOT NULL | |
| `description` | TEXT | NOT NULL | |
| `details` | JSONB | NOT NULL | Category-specific structured data |
| `priority` | INT | NOT NULL, DEFAULT 3 | 1=highest |
| `status` | VARCHAR(50) | DEFAULT 'pending' | pending, in_progress, completed, dismissed |
| `estimated_impact` | VARCHAR(20) | | high, medium, low |
| `estimated_effort` | VARCHAR(20) | | high, medium, low |
| `source_agent` | VARCHAR(50) | NOT NULL | |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Indexes**: `idx_recommendations_business_category`, `idx_recommendations_status`

### `campaigns`

Marketing campaigns generated by Marketing Agent.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `business_id` | UUID | FK → businesses.id, NOT NULL | |
| `recommendation_id` | UUID | FK → recommendations.id | |
| `name` | VARCHAR(255) | NOT NULL | |
| `objective` | TEXT | | |
| `channels` | JSONB | NOT NULL | Array of channel names |
| `budget` | DECIMAL(12,2) | | |
| `duration_weeks` | INT | | |
| `expected_kpis` | JSONB | | |
| `status` | VARCHAR(50) | DEFAULT 'draft' | draft, active, paused, completed |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

---

## Develop Phase

### `kpi_definitions`

Configurable KPIs per business.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `business_id` | UUID | FK → businesses.id, NOT NULL | |
| `metric_name` | VARCHAR(100) | NOT NULL | revenue, conversion_rate, etc. |
| `unit` | VARCHAR(50) | | USD, percent, count |
| `target_value` | DECIMAL(15,4) | | From growth plan |
| `frequency` | VARCHAR(20) | DEFAULT 'monthly' | daily, weekly, monthly |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Unique**: `(business_id, metric_name)`

### `kpi_snapshots`

Time-series KPI data points.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `business_id` | UUID | FK → businesses.id, NOT NULL | |
| `kpi_definition_id` | UUID | FK → kpi_definitions.id | |
| `metric_name` | VARCHAR(100) | NOT NULL | Denormalized for query speed |
| `value` | DECIMAL(15,4) | NOT NULL | |
| `period_start` | DATE | NOT NULL | |
| `period_end` | DATE | NOT NULL | |
| `source` | VARCHAR(50) | DEFAULT 'manual' | manual, csv_import, api |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Indexes**: `idx_kpi_snapshots_business_metric_period` (business_id, metric_name, period_start DESC)

### `performance_comparisons`

Expected vs actual records from Data Analyst Agent.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `business_id` | UUID | FK → businesses.id, NOT NULL | |
| `agent_run_id` | UUID | FK → agent_runs.id | |
| `metric_name` | VARCHAR(100) | NOT NULL | |
| `expected_value` | DECIMAL(15,4) | | |
| `actual_value` | DECIMAL(15,4) | | |
| `variance_percent` | DECIMAL(8,2) | | |
| `status` | VARCHAR(20) | | on_track, at_risk, off_track |
| `period` | VARCHAR(20) | | e.g., "2026-Q2" |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

### `feedback_events`

Triggers for re-analysis loop.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `business_id` | UUID | FK → businesses.id, NOT NULL | |
| `event_type` | VARCHAR(50) | NOT NULL | kpi_deviation, strategy_stale, user_request |
| `payload` | JSONB | NOT NULL | Event details |
| `processed` | BOOLEAN | DEFAULT false | |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

---

## Dominate Phase

### `dashboard_scores`

Latest computed scores from Data Analyst Agent.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `business_id` | UUID | FK → businesses.id, NOT NULL | |
| `agent_run_id` | UUID | FK → agent_runs.id | |
| `business_health_score` | INT | CHECK (0–100) | |
| `growth_score` | INT | CHECK (0–100) | |
| `revenue_opportunity` | INT | CHECK (0–100) | |
| `lead_score` | INT | CHECK (0–100) | |
| `customer_health` | INT | CHECK (0–100) | |
| `market_readiness` | INT | CHECK (0–100) | |
| `risk_alerts` | JSONB | DEFAULT '[]' | |
| `ai_recommendations` | JSONB | DEFAULT '[]' | |
| `executive_summary` | TEXT | | |
| `is_current` | BOOLEAN | DEFAULT true | |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Indexes**: `idx_dashboard_scores_business_current` (business_id, is_current)

---

## Copilot

### `copilot_conversations`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `business_id` | UUID | FK → businesses.id, NOT NULL | |
| `user_id` | UUID | FK → users.id, NOT NULL | |
| `title` | VARCHAR(255) | | Auto-generated from first message |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

### `copilot_messages`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `conversation_id` | UUID | FK → copilot_conversations.id, NOT NULL | |
| `role` | VARCHAR(20) | NOT NULL | user, assistant |
| `content` | TEXT | NOT NULL | |
| `sources` | JSONB | DEFAULT '[]' | RAG source references |
| `intent` | VARCHAR(50) | | Classified intent |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

---

## Row-Level Security (Supabase RLS)

```sql
-- Users can only access their own businesses
CREATE POLICY business_owner ON businesses
  FOR ALL USING (owner_id = auth.uid());

-- Cascade: all child tables check business ownership
CREATE POLICY business_data ON business_profiles
  FOR ALL USING (
    business_id IN (SELECT id FROM businesses WHERE owner_id = auth.uid())
  );
```

Apply equivalent policies to all `business_id`-linked tables.

---

## ChromaDB Collections (Non-Relational)

Not stored in PostgreSQL. Documented here for schema completeness.

| Collection | Document ID Pattern | Metadata Fields |
|------------|--------------------|--------------------|
| `profiles` | `{business_id}_profile_v{version}` | business_id, version, created_at |
| `strategies` | `{business_id}_strategy_{run_id}` | business_id, run_id, created_at |
| `recommendations` | `{business_id}_rec_{rec_id}` | business_id, category, agent_name |
| `analytics` | `{business_id}_analytics_{run_id}` | business_id, run_id, created_at |

---

## Migration Strategy

1. **Phase 2**: Core tables — users, businesses, business_profiles, agent_runs, agent_outputs
2. **Phase 3**: Strategy and recommendations tables
3. **Phase 4**: KPI and dashboard tables
4. **Phase 5**: Copilot tables + RLS policies

Use Alembic for version-controlled migrations in `backend/database/migrations/`.
