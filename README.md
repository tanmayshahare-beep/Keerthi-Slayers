# AI-Assisted Retail Operating System (AROS)

## 1. Overview
**AROS** is a scalable, multi-agent AI operating system designed to sit **on top of** existing retail data warehouses. It ingests raw sales data, segregates it by business vertical (Fashion, Grocery, Electronics), deploys specialized LLM agents to diagnose sales performance, cross-references live local news/weather, and formulates a consensus-driven business strategy.

The final output is a structured JSON strategy that can be written back into the retailer's BI dashboards (e.g., PowerBI, Tableau) or executed via automated API calls to ERP systems.

---

## 2. Architecture Philosophy

To ensure **scalability** and **cost-control**, we strictly separate:

- **Classical Computing (Python/Pandas):** Handles all heavy mathematical aggregation (Top/Bottom SKUs, revenue sums). LLMs are notoriously bad at math; we never send raw row-level data to them.
- **LLM Reasoning (Agents):** Handles *why* something is happening, *what* to do about it, and *mediation* between conflicting departmental strategies.
- **RAG (Retrieval-Augmented Generation):** Ensures the News Agent uses *actual* scraped text, preventing hallucinated news.

---

## 3. Detailed Workflow (Step-by-Step)

| Phase | Component | Technology | Description |
| :--- | :--- | :--- | :--- |
| **1** | **Data Ingest & Segregation** | Python, Pandas, SQLAlchemy | Connects to the retailer's Data Warehouse. Aggregates sales by `location_id` and `sku`. Filters to the Top 50 and Bottom 50 SKUs per business type to fit within LLM context windows. |
| **2** | **Vertical Specialists** | LangGraph + GPT-4o | 3 parallel LLM agents receive their specific aggregated data. They output natural language insights. |
| **3** | **Location Context (RAG)** | Requests, Newspaper3k, ChromaDB | Fetches live news/weather for each store location, scrapes relevant articles, and summarizes them into actionable insights. |
| **4** | **User Strategy Input** | FastAPI | User selects a goal such as `Maximize Profit`, `Clear Inventory`, or `Increase Market Share`. |
| **5** | **Parallel Strategy Agents** | LangGraph | Finance, Supply Chain, Marketing, and HR agents execute concurrently. |
| **6** | **Mediator (CEO Agent)** | GPT-4o + Structured JSON | Resolves conflicting recommendations into one coherent strategy. |
| **7** | **Write-Back** | SQLAlchemy / REST API | Final strategy JSON is stored back in the warehouse. |

---

## 4. Tech Stack for Scalability

| Layer | Technology | Justification |
| :--- | :--- | :--- |
| Orchestration | LangGraph | Multi-agent workflow orchestration |
| LLM | OpenAI GPT-4o / Azure OpenAI | Large context and structured JSON output |
| Data Processing | Pandas + Dask | Efficient aggregation and scaling |
| Vector DB | ChromaDB | News embedding cache |
| Backend | FastAPI + Uvicorn | Async API |
| Background Tasks | Celery + Redis | Batch processing |
| Monitoring | LangSmith | LLM observability |
| Deployment | Docker + Kubernetes | Horizontal scaling |

---

## 5. Integration with Existing Data Architecture

1. Read-only connection to Snowflake, Redshift, BigQuery, PostgreSQL, etc.
2. Trigger via webhooks or scheduled jobs.
3. Write final strategies into `aros_strategy_outputs`.
4. Existing BI dashboards query the new table.

---

## 6. Scalability Considerations

| Challenge | Solution |
| :--- | :--- |
| Token overflow | Send only aggregated KPIs (Top/Bottom 50 SKUs) |
| Latency | Parallel agent execution |
| News hallucination | Strict RAG pipeline |
| Conflicting strategies | CEO mediator + human override |
| Cost | Semantic caching |

---

## 7. Quick Start

```bash
git clone https://github.com/your-repo/aros.git
cd aros

export OPENAI_API_KEY="sk-..."
export DATA_WAREHOUSE_DSN="postgresql://user:pass@localhost:5432/retail_db"
export NEWS_API_KEY="..."

poetry install
poetry run python main.py --store_ids 101,102,103 --goal "Maximize Profit"
```

---

## 8. Future Roadmap

- Predictive time-series forecasting.
- Automated ERP, Shopify, and advertising integrations.

---

## Contributing

Please raise issues for agent prompts or schema changes. All LLM outputs should use Pydantic models.

## License

MIT
