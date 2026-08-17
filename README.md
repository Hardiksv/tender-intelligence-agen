# Tender Intelligence Agent

A production-grade AI engineering platform for ingesting, parsing, screening, and querying public **Bus Operations** government procurement tenders (Gross Cost Contracts — GCC, wet lease, per-km service contracts). Built with FastAPI, React, PostgreSQL with pgvector, and LiteLLM.

---

## Architecture Overview

```text
React + Vite (Frontend SPA)
        ↓
FastAPI (Python 3.11 Backend)
        ↓
Pipeline: PDF Parser (PyMuPDF) → Structured Extraction (LiteLLM) → Semantic Chunking → Vector Embeddings
        ↓
PostgreSQL + pgvector (Storage & Vector Index)
        ↓
Deterministic Screening Engine (NO-GO > REVIEW > GO) & Grounded RAG with Page Citations
```

---

## Quick Start (< 10 Minutes)

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 16+ with pgvector (or use the built-in automated SQLite fallback for local quickstarts)
- Gemini API key (Google AI Studio)

### 1. Clone & Configure

```bash
git clone https://github.com/Hardiksv/tender-intelligence-agen.git
cd tender-intelligence-agent

# Create environment configuration from template
cp .env.example .env

# Open .env and add your Gemini API key:
# LLM_API_KEY=your_actual_gemini_api_key
```

### 2. Run with Docker (Recommended)

```bash
docker compose up --build
```
- Frontend Web UI: http://localhost:5173
- Backend REST API: http://localhost:8000
- Interactive Swagger Docs: http://localhost:8000/docs

---

## Local Development (Without Docker)

### Terminal 1: Backend
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2: Frontend
```bash
cd frontend
npm install
npm run dev
```

### Terminal 3: Trigger Seed Ingestion
```bash
# Ingest official bus operations tender PDFs in data/raw/
curl -X POST http://localhost:8000/api/ingestion/run
```

---

## Cloud Deployment

### 1. One-Click Deploy on Render (Infrastructure-as-Code)
This repository includes a native [`render.yaml`](render.yaml) blueprint:
1. Connect your GitHub repository to [Render.com](https://render.com).
2. Create a new **Blueprint** instance selecting `render.yaml`.
3. Set the secret `LLM_API_KEY` environment variable in the dashboard.
4. Render automatically provisions the PostgreSQL database, applies pgvector, builds the backend, and deploys the React frontend.

### 2. Railway / Cloud VM / Docker
Deploy directly using the included `Dockerfile` in `backend/` and `frontend/` with PostgreSQL container:
```bash
docker compose up -d
```

---

## Core System Capabilities

### 1. Ingestion & Document Processing
- Ingests real multi-page public procurement RFP PDFs and amendments from `data/raw/`.
- Extracts full text using PyMuPDF with page-level provenance tracking.
- Performs English language guardrail detection.
- Generates SHA-256 document hashes to ensure idempotent ingestion (re-running never creates duplicate records).

### 2. Structured Extraction (LiteLLM Abstraction)
- Uses LiteLLM with structured schema outputs to extract: Title, Authority, City/State, Submission Deadline, EMD Amount, Document Fee, Scope Summary, and Minimum Eligibility Criteria.
- Normalizes monetary values to numerical Indian Rupees (INR).
- Extracts `is_mandatory` flags for qualitative criteria.

### 3. Deterministic Eligibility Screening
- Evaluates extracted eligibility criteria against the company's operating profile (fleet size, annual turnover, experience, past contract size, preferred geographies).
- **Strict Precedence Rules:**
  $$\text{NO-GO} > \text{REVIEW} > \text{GO}$$
  - Any mandatory failure $\to$ **NO-GO**
  - All mandatory pass + ambiguous/qualitative clauses $\to$ **REVIEW**
  - All criteria pass $\to$ **GO**
- Screening logic is 100% deterministic Python — no LLM unpredictability in pass/fail decisions.

### 4. Grounded RAG with Verifiable Citations
- Hybrid routing: SQL query engine for date/deadline questions and pgvector cosine similarity search for clause questions.
- RAG answers are synthesized strictly over retrieved chunks using `backend/prompts/rag.md`.
- Strict anti-hallucination guardrail: Returns *"I could not find sufficient evidence in the stored tender documents to answer this confidently"* when evidence is absent.
- Every claim returns metadata-backed citations with document filename, page number, and snippet.

---

## Running Tests

```bash
cd backend
python -m pytest tests/ -o pythonpath=. -v
```

**Automated Test Suite (30/30 Tests Passing):**
- `test_pipeline_orchestration.py` — Ingestion → extraction → screening agent loop, fallback handling, and DB idempotency.
- `test_pdf_parser.py` — Multi-page extraction, SHA-256 hashing, non-English guardrails.
- `test_extraction.py` — Currency normalization, metric standardization, schema validation.
- `test_screening.py` — Deterministic evaluation and NO-GO precedence rules.
- `test_chunking.py` — Page-aware chunking and vector dimension validation.
- `test_rag_pipeline.py` — Query routing, prompt loading, anti-hallucination guardrail, and citation verification.
- `test_api.py` — Health check, cost tracking, and concurrent ingestion rejection.

**Playwright Browser E2E Tests (5/5 Passing):**
```bash
python scripts/e2e_playwright_test.py
```

---

## Continuous Integration (CI)

GitHub Actions workflow at `.github/workflows/ci.yml`:
1. Spins up a `pgvector/pgvector:pg16` service container.
2. Applies Alembic database migrations.
3. Lints codebase with Ruff.
4. Executes full pytest suite.
5. Verifies frontend production build.
