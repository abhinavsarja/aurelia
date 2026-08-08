# AURELIA frontend

React + TypeScript + Chart.js dashboard. Filters and charts load from FastAPI
(`/dashboard/catalog`, `/dashboard/snapshot`). Chat uses `POST /ask`.

## Run

```bash
# terminal 1 — backend
uvicorn aurelia.api:app --reload --port 8001

# terminal 2 — frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 (Vite proxies `/api` → `:8001`).
