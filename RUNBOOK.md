# RUNBOOK.md — Tender Intelligence Agent

## Startup

**Local (without Docker):**
```bash
# 1. Start PostgreSQL with pgvector (or let backend use zero-config SQLite test mode)
# 2. Configure environment
cp .env.example .env
# Edit DATABASE_URL and LLM_API_KEY in .env

# 3. Run database migrations
cd backend && alembic upgrade head

# 4. Start FastAPI backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 5. Start React frontend (in separate terminal)
cd frontend && npm install && npm run dev
```

**Docker (Full Stack Compose):**
```bash
docker compose up --build
```

---

## Cloud Deployment (Render / Railway / Docker)

**Deploy on Render:**
1. Connect repository on [Render](https://render.com).
2. Select **New Blueprint** using `render.yaml`.
3. Fill in secret `LLM_API_KEY`.
4. Deploy completes in <5 minutes.

---

## Shutdown

```bash
# Docker
docker compose down

# Local: Ctrl+C in terminals running backend and frontend
```

---

## Logs & Audit Tracing

```bash
# Docker logs
docker compose logs backend -f
docker compose logs frontend -f

# Local structured logs:
# JSON structured logs are emitted for all AGENT_EVENT, EXTRACTION, SCREENING, and RAG operations.
```

---

## Database Migrations (Alembic)

```bash
cd backend

# Apply latest migrations
alembic upgrade head

# Check current revision
alembic current

# Create a new migration (after model changes)
alembic revision --autogenerate -m "describe change"

# Rollback one step
alembic downgrade -1
```

---

## Seed Data Ingestion

**Trigger Ingestion via API:**
```bash
curl -X POST http://localhost:8000/api/ingestion/run
```

**Check Ingestion Job Status:**
```bash
curl http://localhost:8000/api/ingestion/{job_id}
```

Expected response:
```json
{
  "job_id": "...",
  "status": "COMPLETED",
  "total_documents": 13,
  "completed_documents": 13,
  "failed_documents": 0,
  "current_document": null
}
```

---

## Concurrent Ingestion Protection

If you call `POST /api/ingestion/run` while an ingestion job is already running:
```json
HTTP 409 Conflict
{
  "detail": "An ingestion job is already currently running.",
  "error_code": "CONCURRENT_INGESTION_RUNNING"
}
```

---

## Company Profile Management

```bash
# Update Company Operating Capabilities
curl -X PUT http://localhost:8000/api/profile \
  -H "Content-Type: application/json" \
  -d '{
    "fleet_size": 120,
    "annual_turnover": 150000000,
    "years_experience": 7,
    "past_contract_sizes": [75000000, 90000000],
    "preferred_geographies": ["Rajasthan", "Haryana", "Delhi", "Gujarat"]
  }'

# Re-screen a tender against updated profile
curl -X POST http://localhost:8000/api/tenders/{tender_id}/screen
```

---

## Grounded RAG Chat

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the EMD requirement for CESL PM-eBus Sewa Tender 3?"}'
```

---

## Automated Discovery Scheduler (Bonus)

**Enable discovery:**
```env
DISCOVERY_ENABLED=true
DISCOVERY_INTERVAL_MINUTES=60
```

**Kill switch (instant deactivation):**
```env
DISCOVERY_ENABLED=false
```

---

## MCP Server (Bonus)

**Start standalone MCP server:**
```bash
python backend/app/mcp/server.py
```

**Claude Desktop Configuration (`claude_desktop_config.json`):**
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
        "EMBEDDING_MODEL": "gemini/text-embedding-004",
        "EMBEDDING_DIMENSION": "768",
        "TIMEZONE": "Asia/Kolkata"
      }
    }
  }
}
```

---

## Tests

```bash
# Backend unit & integration tests
cd backend
python -m pytest tests/ -o pythonpath=. -v

# Playwright E2E browser automation suite
python scripts/e2e_playwright_test.py
```
