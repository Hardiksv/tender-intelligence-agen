# DESIGN.md — Tender Intelligence Agent

## Architecture

```
React + Vite + Tailwind CSS
        ↓ HTTP REST
FastAPI (Python 3.11)
        ↓
┌──────────────────────────────────┐
│  Services Layer                  │
│  ├── Ingestion (BackgroundTasks) │
│  ├── PDF Parser (PyMuPDF)        │
│  ├── Language Detector           │
│  ├── LLM Extraction              │
│  ├── Normalization               │
│  ├── Screening Engine            │
│  ├── Chunking                    │
│  ├── Embeddings                  │
│  ├── Retrieval (Hybrid)          │
│  ├── RAG Service                 │
│  └── Discovery (Bonus)           │
└──────────────────────────────────┘
        ↓
PostgreSQL + pgvector
        ↓
LLM Abstraction Layer (LiteLLM)
        ↓
Gemini 2.5 Flash / Pro
```

## Real Seed Dataset Audit & Contingency Rule

> [!IMPORTANT]
> **Data Integrity Verification**: All synthetic/generated data and out-of-category entries (general EVs, upkeep services, unverified notices) were completely purged. The current dataset consists strictly of **100% real, publicly downloaded government procurement PDF documents** from official portals (Ministry of Housing and Urban Affairs - MoHUA and Convergence Energy Services Limited - CESL).

### Verified Real Bus Operations Tender Documents in `data/raw/`

| # | Filename | Source Portal & URL | Tender Reference / ID | Pages | Description |
|---|---|---|---|---|---|
| **1** | `cesl_pm_ebus_sewa_3_3604_buses_gcc.pdf` | [CESL Portal](http://www.convergence.co.in/public/upload/tender_pdf/x845qy239kcl5sk8ld.pdf) | `CESL/06/2026-27/PM-eBus Sewa3/262704003` | **521** | PM-eBus Sewa Tender 3 for Selection of Bus Operator for 3,604 Electric Buses (GCC) |
| **2** | `cesl_pm_edrive_6230_electric_buses_gcc.pdf` | [CESL Portal](http://www.convergence.co.in/public/images/1978.pdf) | `CESL/06/2025-26/PM-EDRIVE/1978` | **533** | PM E-DRIVE Scheme GCC Bus Operator Selection for 6,230 Electric Buses |
| **3** | `pm_ebus_sewa_tender_1_full_rfp.pdf` | [MoHUA Portal](https://pm-ebus-sewa.mohua.gov.in/wp-content/uploads/2025/10/1919-1.pdf) | `CESL/06/2023-24/PM-eBusSewa/23241106` | **481** | PM-eBus Sewa Tender 1 Full RfP Document for Bus Operations |
| **4** | `pm_ebus_sewa_tender_2_gcc.pdf` | [MoHUA Portal](https://pm-ebus-sewa.mohua.gov.in/wp-content/uploads/2025/11/CESL-PM-eBus-Sewa-Tender-2-Amend-11_Clear-Copy-1.pdf) | `CESL/06/2023-24/PM E Bus/Phase II/2324003013` | **473** | PM-eBus Sewa Tender 2 Bus Operator Selection GCC |
| **5** | `pm_ebus_sewa_tender_1_amend_5.pdf` | [MoHUA Portal](https://pm-ebus-sewa.mohua.gov.in/wp-content/uploads/2025/10/AmendNo_5_tenderNo1919.pdf) | `CESL/06/2023-24/PM-eBusSewa/23241106/Amdt-5` | **340** | Amendment No. 5 to PM-eBus Sewa Tender 1 |
| **6** | `cesl_mhi_eoi_phase_2_stu_e_buses.pdf` | [CESL Portal](http://www.convergence.co.in/public/images/MHI%20EoI%20Phase%202.pdf) | `PM E-DRIVE/EoI/STU/2025-26` | **18** | PM E-DRIVE Expression of Interest (EoI) for STUs & City Bus Authorities |
| **7** | `cesl_pm_ebus_sewa_3_amendment.pdf` | [CESL Portal](http://www.convergence.co.in/public/upload/tender_pdf/l6hjmz7na83xqvad64.pdf) | `CESL/06/2026-27/PM-eBus Sewa3/262704003/Amdt-3` | **1** | Amendment No. 3 to PM-eBus Sewa Tender 3 |

### Shortfall Documentation (3-Hour Contingency Rule Applied)
- **Target Dataset Size:** 10 real documents
- **Verified Real Count:** **7 real bus operations documents**
- **Shortfall:** 3 documents
- **Reason:** State-level NIC GePNIC portals (*eprocure.gov.in*, *etenders.kerala.gov.in*, *etender.up.nic.in*) enforce session authentication and Class-3 Digital Signature Certificate (DSC) vendor login to download work item packages.
- **Action Taken:** Per the explicit 3-hour contingency rule in the prompt, zero fake documents were generated to pad the count, and all non-bus/out-of-category entries (general 3W/EVs, upkeep agencies, cancelled IBTM tenders) were discarded. The system operates strictly on the 7 verified real government bus operations documents totaling **2,367 total pages**.

---

## Technology Choices

### Agent Orchestration Design (Hand-Rolled Loop)

The ingestion → extraction → screening pipeline is implemented as an explicit 7-stage hand-rolled orchestration loop in `app/agent/pipeline.py:run_ingestion_pipeline()`.

```
PDF
 ↓
1. CATALOG_LOOKUP (Resolve file to parent tender & metadata)
 ↓
2. PARSE (PyMuPDF text extraction + language guardrail + SHA-256 hash)
 ↓
3. PARENT_RESOLVE (Create/retrieve parent Tender record, handle amendment versioning)
 ↓
4. DOCUMENT_RECORD (Create child Document record linked to parent)
 ↓
5. EXTRACT (Extract structured data via LiteLLM schema -> populate TenderEligibility table)
 ↓
6. CHUNK & EMBED (Sentence chunking -> 384-dim embeddings -> DocumentChunk table)
 ↓
7. SCREEN (Deterministic rule engine against CompanyProfile -> ScreeningResult table)
 ↓
DONE (Update IngestionJob status -> COMPLETED)
```

**Justification for Hand-Rolled Loop vs Frameworks (LangGraph, Agno, CrewAI):**
1. **Single-Process Determinism**: The pipeline operates as a deterministic, single-host background task. It requires neither distributed agent messaging nor multi-agent negotiation overhead.
2. **Explicit Stage Control**: Pure Python orchestration allows precise transaction rollbacks (`db.rollback()`), per-document error isolation, and verifiable data provenance without framework black-box abstractions.
3. **No Unnecessary Dependencies**: Avoids bulky framework dependency trees while delivering 100% of the core requirement: automated PDF ingestion, structured schema extraction, and deterministic screening against company criteria.

### FastAPI
Chosen for native async support, automatic OpenAPI docs, BackgroundTasks for async ingestion, and Pydantic V2 integration. No unnecessary microservices introduced.

### PostgreSQL + pgvector
Single database serving both relational data (tenders, profiles, screening) and vector similarity search (document chunks). Eliminates the need for a separate vector store service.

### Alembic
All schema changes versioned via Alembic migrations. Zero manual SQL ALTER TABLE commands. The same migration files run locally, in Docker, and in CI.

### LiteLLM
Abstraction layer so business logic never imports vendor-specific SDKs. Model names are pinned in environment variables (`LLM_MODEL`, `LLM_FALLBACK_MODEL`). Switching from Gemini to any other provider requires only an `.env` change.

### Pinned Models
- **Primary:** `gemini/gemini-2.5-flash` — low cost, fast structured output
- **Fallback:** `gemini/gemini-2.5-pro` — more powerful, triggered on schema parse failures

### Embedding Model
- **Model:** `sentence-transformers/all-MiniLM-L6-v2`
- **Dimension:** 384
- **Reason:** Open-source, no API cost, strong English semantic similarity, reasonable size for CPU inference
- **Validation:** Embedding dimension is asserted against `EMBEDDING_DIMENSION` config before every database write

### Deterministic Screening
LLMs extract requirements. Python compares values. No LLM involvement in pass/fail decisions. This ensures:
- Reproducibility
- Zero hallucination risk in eligibility outcomes
- Auditability for live defense

### Verdict Precedence
```
NO-GO > REVIEW > GO

Implemented in: app/services/screening.py

Logic:
1. Check all mandatory fields: fleet, turnover, experience, past_contract_value
2. If ANY mandatory field fails → NO-GO (immediate, regardless of other criteria)
3. If all mandatory pass but optional/ambiguous items exist → REVIEW
4. All criteria pass → GO
```

### FastAPI BackgroundTasks
Ingestion runs asynchronously. HTTP 202 Accepted returned immediately with `job_id`. Client polls `GET /api/ingestion/{job_id}` for status. No Redis/Celery/Kafka introduced.

### Concurrent Ingestion Protection
Before creating a new `IngestionJob` with `RUNNING` status, the endpoint queries for existing `RUNNING` jobs. If found → `HTTP 409 Conflict`. This prevents duplicate ingestion runs from parallel API calls.

### Non-English PDF Guardrail
`langdetect` runs on the full extracted text before LLM extraction. Non-English documents are marked `LANGUAGE_UNSUPPORTED`, logged, and skipped from extraction. Original PDF is preserved.

### Hybrid Retrieval
A simple intent router checks the question for date/deadline keywords → SQL query. All other questions → pgvector cosine similarity search. Both paths attach page-level citation metadata.

### CORS Policy
Configured via `FRONTEND_ORIGIN` environment variable. Uses explicit allow_origins list. Never `["*"]` in production.

### Timezone Strategy
All deadlines stored as timezone-aware `DateTime(timezone=True)`. Default assumption: `Asia/Kolkata` (UTC+5:30). Countdown calculations compare `datetime.now(timezone.utc)` with stored timezone-aware deadline.

### Discovery Source Adapters
`TenderSource` abstract class defines `discover()` and `fetch_document()`. New portals added by implementing a new adapter class. Kill switch: `DISCOVERY_ENABLED=false`.

### MCP Architecture
MCP Server (`app/mcp/server.py`) calls existing service methods directly — no duplication of DB logic, screening, or RAG. Tools: `search_tenders`, `get_tender`, `ask_tenders`.

### CI Database Strategy
GitHub Actions uses `pgvector/pgvector:pg16` as a service container. Alembic runs migrations against this ephemeral test DB before pytest. Same migration files used in local dev and CI.

---

## Cost Tracking

### Primary Usage Source
LiteLLM response metadata: `response.usage.prompt_tokens`, `response.usage.completion_tokens`, `response.usage.total_tokens`

### Verified Pricing (Gemini 2.5 Flash — web-verified August 2026)
| Token Type | Rate |
|---|---|
| Input tokens | $0.30 / 1M tokens |
| Output tokens | $2.50 / 1M tokens |

### Approximate Seed Dataset Cost (10 tenders × 3 pages each)
| Operation | Est. Input Tokens | Est. Output Tokens | Est. Cost (USD) |
|---|---|---|---|
| Extraction (10 docs) | ~30,000 | ~10,000 | ~$0.034 |
| RAG queries (per question) | ~5,000 | ~500 | ~$0.003 |
| Screening LLM (none — deterministic) | 0 | 0 | $0.00 |
| **Total seed run** | ~35,000 | ~10,500 | **~$0.037** |

> All figures above are **Estimated** (based on verified per-token pricing and approximate document sizes).
> **Measured** usage is captured from LiteLLM metadata per-request and logged with `is_estimated: false` when available.

### Measured vs Estimated
- `is_estimated: false` → actual token counts from LiteLLM response metadata
- `is_estimated: true` → manual estimate used as documented fallback when metadata unavailable
