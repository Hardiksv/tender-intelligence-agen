# RUNBOOK.md — Tender Intelligence Agent

## Startup

**Local (no Docker):**
```bash
# 1. Start PostgreSQL with pgvector
# (ensure pgvector extension is available on your PostgreSQL instance)

# 2. Configure environment
cp .env.example .env
# Edit DATABASE_URL and LLM_API_KEY in .env

# 3. Run migrations
cd backend && alembic upgrade head

# 4. Start backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 5. Start frontend (new terminal)
cd frontend && npm run dev
```

**Docker (full stack):**
```bash
docker compose up --build
```

---

## Shutdown

```bash
# Docker
docker compose down

# Local: Ctrl+C in each terminal running backend/frontend
```

---

## Logs

```bash
# Docker logs
docker compose logs backend -f
docker compose logs frontend -f

# Local: stdout/stderr in the running terminal
# JSON structured logs are emitted for all AGENT_EVENT entries
```

---

## Migrations

```bash
cd backend

# Apply latest migrations
alembic upgrade head

# Check current revision
alembic current

# Create a new migration (after model changes)
alembic revision --autogenerate -m "add new column"

# Rollback one step
alembic downgrade -1
```

---

## Seed Data Ingestion

**Step 1 — Generate Seed PDFs (if not already present):**
```bash
python scripts/generate_seed_tenders.py
```

**Step 2 — Trigger Ingestion via API:**
```bash
curl -X POST http://localhost:8000/api/ingestion/run
```

**Step 3 — Check Job Status:**
```bash
curl http://localhost:8000/api/ingestion/{job_id}
```

Expected response:
```json
{
  "job_id": "...",
  "status": "RUNNING",
  "total_documents": 10,
  "completed_documents": 6,
  "failed_documents": 0,
  "current_document": "tender_007.pdf"
}
```

---

## Concurrent Ingestion Behavior

If you call `POST /api/ingestion/run` while a job is already RUNNING:
```json
HTTP 409 Conflict
{
  "detail": "An ingestion job is already currently running.",
  "error_code": "CONCURRENT_INGESTION_RUNNING"
}
```
Wait for the running job to complete, then retry.

---

## Company Profile Update

```bash
curl -X PUT http://localhost:8000/api/profile \
  -H "Content-Type: application/json" \
  -d '{
    "fleet_size": 150,
    "annual_turnover": 200000000,
    "years_experience": 8,
    "past_contract_sizes": [80000000, 120000000],
    "preferred_geographies": ["Rajasthan", "Haryana", "Gujarat"]
  }'
```

After updating profile, re-screen any tender:
```bash
curl -X POST http://localhost:8000/api/tenders/{tender_id}/screen
```

---

## RAG Chat

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What turnover does the Jaipur tender require?"}'
```

---

## Discovery

**Enable discovery:**
```env
DISCOVERY_ENABLED=true
DISCOVERY_INTERVAL_MINUTES=60
```

**Kill switch (immediate stop):**
```env
DISCOVERY_ENABLED=false
```

The scheduler checks the kill switch on every cycle. No restart needed.

---

## MCP Server

**Start standalone MCP server:**
```bash
python backend/app/mcp/server.py
```

**Claude Desktop Configuration:**

Add to your Claude Desktop `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "tender-intelligence": {
      "command": "python",
      "args": [
        "C:/Users/hardi/Desktop/tender-intelligence-agent/backend/app/mcp/server.py"
      ],
      "env": {
        "DATABASE_URL": "postgresql://postgres:YOUR_PASSWORD@localhost:5432/tender_db",
        "LLM_API_KEY": "YOUR_GEMINI_API_KEY",
        "LLM_MODEL": "gemini/gemini-2.5-flash",
        "EMBEDDING_MODEL": "sentence-transformers/all-MiniLM-L6-v2",
        "EMBEDDING_DIMENSION": "384",
        "TIMEZONE": "Asia/Kolkata"
      }
    }
  }
}
```

> Note: Never commit actual API keys. The above is a placeholder example.

**Test MCP tools:**
```bash
# Using mcp CLI (if installed):
mcp call tender-intelligence search_tenders '{"query": "electric bus"}'
mcp call tender-intelligence ask_tenders '{"question": "What fleet size does Jaipur tender require?"}'
```

---

## Tests

```bash
cd backend
python -m pytest tests/ -o pythonpath=. -v
```

---

## CI

GitHub Actions workflow: `.github/workflows/ci.yml`

Runs on every push to `main` or `develop`:
1. Starts `pgvector/pgvector:pg16` service container
2. Runs `alembic upgrade head`
3. Lints with Ruff
4. Runs full pytest suite
5. Builds frontend

---

## Common Failure Scenarios

### LLM Rate Limit
```
litellm.RateLimitError
```
**Resolution:** Wait and retry. LiteLLM automatically falls back to `LLM_FALLBACK_MODEL`. If both fail, heuristic extraction is used and marked as `is_estimated: true`.

### Database Failure
```
sqlalchemy.exc.OperationalError: could not connect to server
```
**Resolution:** Verify `DATABASE_URL` in `.env`. Ensure PostgreSQL is running: `docker compose up postgres`.

### Discovery Source Failure
**Resolution:** Check logs for `[Discovery]` prefix. Verify portal is accessible. The scheduler continues on next interval automatically.

### Migration Failure
```
alembic.util.exc.CommandError
```
**Resolution:** Run `alembic current` to check state. Fix the migration file and re-run `alembic upgrade head`.

### Ingestion Failure (mid-pipeline)
Check `GET /api/ingestion/{job_id}` — `error_message` field will contain the cause. Fix the issue and trigger a new ingestion run.
