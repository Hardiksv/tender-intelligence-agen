# Tender Intelligence Agent

A production-quality AI engineering system for intelligently analysing public **Bus Operations** government tenders — ingesting PDFs, extracting structured data via LLM, deterministically screening against a company profile, and providing grounded RAG Q&A with source citations.

---

## Architecture Overview

```
React + Vite + Tailwind
        ↓
FastAPI (Python 3.11)
        ↓
Services: Ingestion · Extraction · Screening · RAG · Discovery
        ↓
PostgreSQL + pgvector
        ↓
LLM Abstraction (LiteLLM → Gemini 2.5 Flash / Pro)
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 16+ with pgvector extension
- Gemini API key (Google AI Studio)

### 1. Clone & Configure

```bash
git clone <repository-url>
cd tender-intelligence-agent
cp .env.example .env
# Edit .env and fill in your credentials
```

### 2. Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/tender_db` |
| `LLM_API_KEY` | Gemini API Key | *required* |
| `LLM_MODEL` | Primary LLM model | `gemini/gemini-2.5-flash` |
| `LLM_FALLBACK_MODEL` | Fallback LLM model | `gemini/gemini-2.5-pro` |
| `EMBEDDING_MODEL` | Sentence-transformers model | `sentence-transformers/all-MiniLM-L6-v2` |
| `EMBEDDING_DIMENSION` | Vector dimension | `384` |
| `TIMEZONE` | Application timezone | `Asia/Kolkata` |
| `FRONTEND_ORIGIN` | CORS allowed frontend origin | `http://localhost:5173` |
| `DISCOVERY_ENABLED` | Automated discovery kill switch | `false` |

### 3. Run with Docker (Recommended)

```bash
docker compose up --build
```
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 4. Run Locally (without Docker)

**Backend:**
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Generate Seed Tender PDFs:**
```bash
python scripts/generate_seed_tenders.py
```

**Trigger Seed Ingestion:**
```bash
curl -X POST http://localhost:8000/api/ingestion/run
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## Database & Alembic

All schema changes are managed via Alembic migrations.

```bash
cd backend

# Apply all migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "describe change"

# Downgrade one step
alembic downgrade -1
```

---

## Ingestion Pipeline

The agent pipeline runs asynchronously via FastAPI BackgroundTasks:

```
POST /api/ingestion/run
    ↓
PDF Parsing (PyMuPDF)
    ↓
Language Detection (English-only guardrail)
    ↓
LLM Structured Extraction (LiteLLM → Gemini)
    ↓
Normalization (INR standardization)
    ↓
PostgreSQL storage (Tender + Eligibility + Document records)
    ↓
Semantic Chunking (page-aware, paragraph-preserving)
    ↓
Embeddings (all-MiniLM-L6-v2, 384-dim)
    ↓
pgvector storage
    ↓
Deterministic Screening (NO-GO > REVIEW > GO precedence)
```

**Check ingestion status:**
```bash
curl http://localhost:8000/api/ingestion/{job_id}
```

**Concurrent ingestion protection:** A second `POST /api/ingestion/run` while a job is running returns `HTTP 409 Conflict`.

---

## Eligibility Screening

Screening is fully deterministic Python — no LLM involvement in pass/fail decisions.

**Verdict precedence (strictly enforced):**
```
NO-GO > REVIEW > GO

- Any mandatory failure → NO-GO (regardless of other results)
- All mandatory pass + ambiguous clauses → REVIEW
- All criteria pass → GO
```

**Hardcoded mandatory fields:**
- `minimum_fleet_size`
- `minimum_annual_turnover`
- `minimum_experience_years`
- `minimum_past_contract_value`

LLM-extracted `other_requirements` items carry an explicit `is_mandatory: bool` flag.

---

## RAG Q&A

Questions are routed to:
- **SQL** for deadline/date queries (e.g. "Which tenders close in 15 days?")
- **pgvector cosine similarity** for semantic clause questions

Answers are strictly grounded in retrieved chunks. The LLM is instructed to respond with:
> "I could not find sufficient evidence in the stored tender documents to answer this confidently."
if context is insufficient.

---

## Automated Discovery (Bonus)

```bash
# Enable in .env
DISCOVERY_ENABLED=true
DISCOVERY_INTERVAL_MINUTES=60
```

Kill switch:
```bash
DISCOVERY_ENABLED=false  # Stops all discovery cycles immediately
```

---

## MCP Server (Bonus)

Exposes `search_tenders`, `get_tender`, `ask_tenders` via Model Context Protocol.

```bash
python backend/app/mcp/server.py
```

**Claude Desktop config** (in `RUNBOOK.md`).

---

## Tests

```bash
cd backend
python -m pytest tests/ -o pythonpath=. -v
```

Test coverage:
- `test_pdf_parser.py` — PDF parsing, hash idempotency, non-English detection
- `test_extraction.py` — Normalization, is_mandatory schema, heuristic extraction
- `test_screening.py` — All verdict precedence cases
- `test_chunking.py` — Page-aware chunking, embedding dimension validation, mismatch fail-fast
- `test_api.py` — Health check, cost tracking, concurrent ingestion rejection

---

## CI

GitHub Actions workflow at `.github/workflows/ci.yml`:
- Spins up `pgvector/pgvector:pg16` service container
- Runs Alembic migrations
- Lints with Ruff
- Runs pytest
- Builds frontend

---

## Limitations & Known Constraints

1. **Seed data** consists of 10 AI-generated representative Bus Operations tenders (structured after real CPPP/state portal documents) due to PDF download access constraints in this environment.
2. **LLM extraction** falls back to heuristic regex extraction when `LLM_API_KEY` is set to the default mock value.
3. **Discovery** is disabled by default (`DISCOVERY_ENABLED=false`). Enable only after reviewing portal terms of service.
4. **Cloud deployment** requires configuring `DATABASE_URL` to a managed PostgreSQL instance with pgvector and updating `FRONTEND_ORIGIN` in `.env`.
