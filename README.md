# AURELIA

Retail trading performance Q&A for accessories retail (demo). Ask a question; the model chooses a fixed tool; numbers come from code and Postgres — not from the model inventing figures.

Stack: **FastAPI** backend · **React** dashboard · **Postgres + pgvector** · optional **Chainlit** chat harness.

---

## Prerequisites

- Python **3.11+**
- Node.js **18+** and npm
- Docker Desktop (for Postgres)
- An **OpenAI API key**

---

## Quick start (environment ready)

Run these from the **repo root** unless noted.

### 1. Environment file

```bash
cp .env.example .env
```

Edit `.env` and set:

```bash
OPENAI_API_KEY=sk-...
# Optional — default matches docker-compose:
# DATABASE_URL=postgresql+psycopg://aurelia:local@localhost:5432/aurelia
```

### 2. Postgres

```bash
docker compose up -d
```

- Image: `pgvector/pgvector:pg16`
- Host: `localhost:5432`
- User / password / DB: `aurelia` / `local` / `aurelia`
- `db/schema.sql` is applied automatically on **first** container boot

Check it is healthy:

```bash
docker compose ps
docker exec aurelia-pg pg_isready -U aurelia -d aurelia
```

### 3. Python package

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
# Optional (Chainlit chat persistence if you set DATABASE_URL for Chainlit):
# pip install -e ".[dev]"
```

### 4. Load sales / product CSVs into Postgres

```bash
./reset.sh
```

This runs `db/load_csv.sql` against the local DB (publishes weekly data the API reads).

### 5. Ingest documents for RAG (meetings, news)

Needed for meeting / competitor / `explain_gap` document answers:

```bash
python3 -m aurelia.rag.ingest
# Full rebuild:
# python3 -m aurelia.rag.ingest --force
```

### 6. Sanity checks

```bash
# API can load data
python3 -c "from aurelia import db; print(db.load() and db.meta())"

# Decomposition identity tests (no OpenAI)
python3 tests/test_decompose.py

# Health once the API is running (step below)
curl -s http://127.0.0.1:8001/health
```

If those succeed, the environment is ready.

---

## Start the services

Use **three terminals** (with the venv activated for Python).

### Backend (FastAPI) — port 8001

```bash
source .venv/bin/activate
uvicorn aurelia.api:app --reload --port 8001
```

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Status + data meta |
| `POST` | `/ask` | `{ "question": "..." }` → answer + tools |
| `POST` | `/reload` | Reload frames after a data publish |
| `GET` | `/dashboard/catalog` | Filter catalogue |
| `GET` | `/dashboard/snapshot` | KPI / charts / table payload |

Example:

```bash
curl -s http://127.0.0.1:8001/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"what were bag sales last week"}' | python3 -m json.tool
```

### Frontend (Vite + React) — port 5173

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The Vite proxy forwards `/api/*` to the backend on **8001**, so the API must be running.

### Postgres

Already started with `docker compose up -d`. Stop / start later with:

```bash
docker compose stop
docker compose start
# Tear down volume (wipes DB; re-run ./reset.sh + ingest after):
# docker compose down -v
```

---

## Optional: Chainlit UI

```bash
source .venv/bin/activate
chainlit run chainlit_app.py -w
```

Intro copy: `documentation/chainlit.md`. Prefer leaving `DATABASE_URL` unset for Chainlit’s own persistence, or install `asyncpg` via `pip install -e ".[dev]"`.

---

## Golden / regression questions

Live OpenAI calls (costs money, needs network):

```bash
source .venv/bin/activate
python3 tests/run_golden.py              # full set
python3 tests/run_golden.py --only D     # diagnostics only
```

Results (passes and failures) are written to `tests/golden_results.json`.

---

## Project layout

| Path | Purpose |
|------|---------|
| `aurelia/` | Package: API, agent, tools, analysis, RAG, dashboard |
| `db/` | `schema.sql`, `load_csv.sql` |
| `data/` | CSVs, documents, news feed |
| `frontend/` | React dashboard |
| `documentation/` | Architecture notes, PDFs |
| `scripts/` | Generators for demo data / docs / news |
| `tests/` | Unit + golden checks |
| `chainlit_app.py` | Optional chat UI |

---

## Regenerating demo data

From repo root (after changing generators):

```bash
python3 scripts/generate_data.py
python3 scripts/generate_documents.py
python3 scripts/generate_news.py
./reset.sh
python3 -m aurelia.rag.ingest --force
```

---

## Troubleshooting

| Symptom | What to try |
|---------|-------------|
| `connection refused` on `:5432` | `docker compose up -d` and wait for healthy |
| Empty / no published sales | `./reset.sh` |
| Meeting / news answers empty | `python3 -m aurelia.rag.ingest` |
| Frontend chat fails | Backend on **8001**, not 8000 |
| Wrong Python / missing packages | Use `python3`, venv, `pip install -e .` |
| Golden run hangs | OpenAI timeouts are set; Ctrl+C and retry; check `OPENAI_API_KEY` |
