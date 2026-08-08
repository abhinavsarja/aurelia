# AURELIA

Retail trading performance Q&A backend. Ask a question; the model chooses a fixed tool; numbers come from code, not the model.

## Layout

| Path | Purpose |
|---|---|
| `aurelia/` | Installable Python package (API, agent, tools, analysis) |
| `db/` | Operational SQL (`schema.sql`, `load_csv.sql`) |
| `data/` | CSV backfill and documents |
| `documentation/` | Architecture HTML, PDF, Chainlit intro markdown |
| `scripts/` | Data / document generators (run from repo root) |
| `tests/` | Decomposition identity checks |
| `chainlit_app.py` | Optional chat UI harness |

## Setup

```bash
# 1. Postgres (applies db/schema.sql on first boot)
docker compose up -d

# 2. Load CSVs (from repo root)
./reset.sh

# 3. Install the package
python -m venv .venv && source .venv/bin/activate
pip install -e .

# 4. Environment
cp .env.example .env   # or create .env with:
# OPENAI_API_KEY=sk-...
# DATABASE_URL is optional — defaults to postgresql+psycopg://aurelia:local@localhost:5432/aurelia
```

## FastAPI (Postman / scripts)

```bash
uvicorn aurelia.api:app --reload
```

| Method | Path | Body |
|---|---|---|
| `GET` | `/health` | — |
| `POST` | `/ask` | `{ "question": "what were bag sales last week" }` |
| `POST` | `/reload` | — (after a weekly publish) |

`POST /ask` returns the same shape the Chainlit UI uses:

```json
{
  "question": "...",
  "answer": "...",
  "tool_calls": [{"tool": "get_sales", "arguments": {...}}],
  "tool_results": [{...}],
  "latency_ms": 1234
}
```

### curl

```bash
curl -s http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"what were bag sales last week"}' | python -m json.tool
```

### Many questions (loop)

```bash
while IFS= read -r q; do
  curl -s http://127.0.0.1:8000/ask \
    -H 'Content-Type: application/json' \
    -d "$(python -c "import json,sys; print(json.dumps({'question': sys.argv[1]}))" "$q")"
  echo
done <<'EOF'
what were bag sales last week
which models are behind target in July
why did MRL-CB-TAN drop last month
EOF
```

## Frontend dashboard

React + Chart.js UI matching the mockup (chat on the right; mock answers until API is wired):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Chat hits `POST /ask` via the Vite proxy — run `uvicorn aurelia.api:app --reload --port 8001` alongside.

## Optional Chainlit UI

```bash
chainlit run chainlit_app.py -w
```

Intro copy lives in `documentation/chainlit.md`. Chainlit may warn that root `chainlit.md` is missing; that is expected.

**Note:** If you set `DATABASE_URL` in `.env`, Chainlit may try to use it for its own chat persistence (needs `asyncpg`). Prefer leaving `DATABASE_URL` unset and using the package default, or install `asyncpg` if you want Chainlit persistence.

## Tests

```bash
python tests/test_decompose.py
```

## Generators

Run from the repo root so relative `data/` paths resolve:

```bash
python scripts/generate_data.py
python scripts/generate_documents.py
python scripts/generate_news.py
```
