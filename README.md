# Customer support analysis agent

A LangGraph workflow that:

1. **Analyzes support transcripts** (LLM) and optionally **stores results in PostgreSQL**.
2. Optionally **ingests policy `.txt` files** into **pgvector** for RAG.
3. **Generates a report** (placeholder node).

---

## Prerequisites

- **Python 3.11+** (3.13 works)
- **OpenAI API key** (`OPENAI_API_KEY`)
- **PostgreSQL** locally (for DB features and policy ingest)
- **pgvector** (only if you use policy store update — see [SETUP_DB.md](SETUP_DB.md))

---

## Quick start (run the agent)

### 1. Clone and install

```bash
cd customer-support-analysis-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Set up the database

Follow **[SETUP_DB.md](SETUP_DB.md)** end-to-end:

- Install & start Postgres  
- Create database `customer_support`  
- Set `POSTGRES_*` (or `DATABASE_URL`) in **`.env`**  
- **`brew install pgvector`** and **`CREATE EXTENSION vector;`** if you will answer **yes** to policy update  

### 3. Configure `.env`

At minimum:

```env
OPENAI_API_KEY=sk-...
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=customer_support
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_password
```

Optional: LangSmith / LangChain tracing keys if you use them.

### 4. Transcripts and policies

- Transcripts live under **`assets/transcripts/`** as `transcript_01.txt`, … (IDs referenced in `agent.py`).
- Policy text files go in **`assets/policies/`** (`.txt`). See `assets/policies/README.md`.

### 5. Run the agent

Always use the **venv** Python so dependencies match:

```bash
source venv/bin/activate
python agent.py
```

Flow:

1. **Transcript analysis** runs (parallel LLM calls; results saved to DB when Postgres is available).
2. Prompt: **`Update policy store? (yes/no)`**
   - **yes** — runs TXT → chunk → embed → **pgvector** (requires pgvector installed + extension).
   - **no** — skips policy ingest.
3. **Report** node runs (`Generating report.......`).

---

## Useful commands

| Command | Purpose |
|---------|---------|
| `python view_db.py` | List rows in `transcript_analyses` |
| `python -c "from node_2_policy_update import run_policy_ingest_pipeline; print(run_policy_ingest_pipeline())"` | Ingest policies only |

---

## Project layout

| Path | Role |
|------|------|
| `agent.py` | LangGraph: transcript → policy? → metrics → report |
| `node_1_transcript_analysis.py` | Transcript LLM + DB write |
| `node_2_policy_update.py` | Policy TXT ingest + embeddings |
| `node_3_calculate_operations_metrics.py` | Operations / resolution KPIs |
| `node_4_calculate_failure_metrics.py` | Failure reason + sentiment metrics |
| `node_5_generate_report.py` | Report node stub |
| `db.py` | Postgres helpers |
| `SETUP_DB.md` | **Database & pgvector setup** |
| `assets/transcripts/` | Input transcripts |
| `assets/policies/` | Policy `.txt` files |

---

## Troubleshooting

| Issue | What to do |
|-------|------------|
| `ModuleNotFoundError` | `pip install -r requirements.txt` inside **venv**; run with `python agent.py` from venv. |
| DB connection refused / auth failed | [SETUP_DB.md](SETUP_DB.md) — start Postgres, fix user/password in `.env`. |
| `type "vector" does not exist` / `vector.control: No such file` | Homebrew `pgvector` may not match `postgresql@16`. Build from source with `PG_CONFIG` pointing at Postgres 16, or use Docker — see [SETUP_DB.md](SETUP_DB.md) §4b–4c. |
| Policy ingest skipped errors | Ensure `.txt` files exist in `assets/policies/`. |

---

## License

Use and modify as needed for your project.
