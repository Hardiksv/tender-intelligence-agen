# DESIGN.md — Tender Intelligence Agent

## Architecture

```text
React + Vite (Frontend SPA)
        ↓ HTTP REST
FastAPI (Python 3.11 Backend)
        ↓
┌─────────────────────────────────────────────────────────────┐
│  Services Layer                                             │
│  ├── Ingestion (FastAPI BackgroundTasks, Hash Idempotency)   │
│  ├── PDF Parser (PyMuPDF with Page-Level Metadata)          │
│  ├── Language Detector (English-Only Guardrail)             │
│  ├── Structured Extraction (LiteLLM → Gemini Schema Output) │
│  ├── Normalization (INR Currency & Metric Conversion)       │
│  ├── Screening Engine (Strict Deterministic Python Rules)   │
│  ├── Page-Aware Chunking (Paragraph Preservation)           │
│  ├── Embeddings (Gemini gemini-embedding-001 & Local Fallback)│
│  ├── Retrieval (Hybrid SQL Date Router + Vector Search)     │
│  ├── Grounded RAG (Zero-Hallucination & Provenance Citations│
│  └── Automated Discovery & MCP Server                       │
└─────────────────────────────────────────────────────────────┘
        ↓
PostgreSQL + pgvector (Single Data & Vector Store)
        ↓
LLM Abstraction Layer (LiteLLM)
        ↓
Gemini 2.5 Flash (Primary) / Gemini 2.5 Pro (Fallback)
```

---

## Seed Dataset & Document Integrity

The system operates over publicly downloaded government procurement RFPs and amendments
from Convergence Energy Services Limited (CESL) and the Ministry of Housing and Urban
Affairs (MoHUA), freely accessible from the official PM-eBus Sewa portal
(pm-ebus-sewa.mohua.gov.in) without registration.

### Integrity verification

Every file in `data/raw/` is validated as a genuine PDF before ingestion. `pdf_parser.py`
checks for the `%PDF-` magic header before handing the file to PyMuPDF, and raises a
`ParsingException` if it's missing — a file that merely has a `.pdf` extension is not
proof it's a real PDF. This guardrail exists because an earlier scraping pass saved a
handful of 404/homepage HTML responses with a `.pdf` extension; PyMuPDF will silently
"open" HTML and extract nav-menu text as if it were real document content, with no error
raised anywhere, so a magic-byte check at the ingestion boundary is required.

`scripts/validate_seed_docs.py` runs this same check standalone over the whole `data/raw/`
directory, and `tests/test_seed_data_integrity.py` covers it in the test suite — so a
corrupted or wrong-linked seed file fails fast during development / CI instead of silently
entering the corpus and being fed to the LLM as if it were real tender content.

### Verified Public Tender Documents in `data/raw/` (14 Files, 4 Distinct Programs)

#### PM-eBus Sewa Tender 1 — CESL/06/2023-24/PM-eBusSewa/23241106

| # | Filename | Type | Pages | Size | Scope |
|---|---|---|---|---|---|
| 1 | `pm_ebus_sewa_tender_1_full_rfp.pdf` | Original RFP | 481 | 7.1 MB | 3,600 Electric Buses GCC across 38 cities |
| 2 | `pm_ebus_sewa_tender_1_amend_1.pdf` | Amendment 1 | — | 249 KB | Bid schedule extension, clarifications |
| 3 | `pm_ebus_sewa_tender_1_amend_2.pdf` | Amendment 2 | — | 480 KB | Technical specification updates |
| 4 | `pm_ebus_sewa_tender_1_amend_3.pdf` | Amendment 3 | — | 15.7 MB | Major scope revision — 3,825 buses, state allocations |
| 5 | `pm_ebus_sewa_tender_1_amend_4.pdf` | Amendment 4 | — | 625 KB | Bid schedule & EMD clarifications |
| 6 | `pm_ebus_sewa_tender_1_amend_5.pdf` | Amendment 5 | 340 | 6.5 MB | Revised quantity 3,725 buses + state reallocation |
| 7 | `pm_ebus_sewa_tender_1_amend_6.pdf` | Amendment 6 | — | 220 KB | Deadline extension notice |
| 8 | `pm_ebus_sewa_tender_1_amend_7.pdf` | Amendment 7 | — | 220 KB | Final bid submission extension |

#### PM-eBus Sewa Tender 2 — CESL/06/2023-24/PM E Bus/Phase II/2324003013

| # | Filename | Type | Pages | Size | Scope |
|---|---|---|---|---|---|
| 9 | `pm_ebus_sewa_tender_2_gcc.pdf` | Original RFP + Amdt 11 | 473 | 3.3 MB | 4,588 Buses (revised 3,132 via Amdt 11) |
| 10 | `pm_ebus_sewa_tender_2_amend_2.pdf` | Amendment 2 | — | 220 KB | Bid schedule update |
| 11 | `pm_ebus_sewa_tender_2_amend_3.pdf` | Amendment 3 | — | 220 KB | Deadline and technical clarification |

#### PM-eBus Sewa Tender 3 — CESL/06/2026-27/PM-eBus Sewa3/262704003

| # | Filename | Type | Pages | Size | Scope |
|---|---|---|---|---|---|
| 12 | `cesl_pm_ebus_sewa_3_3604_buses_gcc.pdf` | Original RFP | 521 | 4.0 MB | 3,604 Electric Buses across 5 STUs |
| 13 | `cesl_pm_ebus_sewa_3_amendment.pdf` | Amendment 3 | — | 550 KB | Bid deadline extension corrigendum |

#### PM E-DRIVE Scheme — CESL/06/2025-26/PM E-Drive/252601015

| # | Filename | Type | Pages | Size | Scope |
|---|---|---|---|---|---|
| 14 | `cesl_pm_edrive_6230_electric_buses_gcc.pdf` | Original RFP | 533 | 10.4 MB | 6,230 Electric Buses (2,900 STUs + 3,330 Delhi DTC) |

> **Total Corpus:** 14 PDF documents across 4 central government GCC procurement programs,
> sourced from pm-ebus-sewa.mohua.gov.in and convergence.co.in. Every file is verified by
> `scripts/validate_seed_docs.py` to be a genuine PDF (not a scraper artifact such as an
> HTML error/homepage saved with a `.pdf` extension) before ingestion.

---

## Domain Data Modeling: Lot-Wise EMD & Deadline Resolution

### 1. Lot-Wise / State-Wise EMD Modeling
In central bus aggregation tenders issued by Convergence Energy Services Limited (CESL), Earnest Money Deposit (EMD) is **never a single flat fee**. Bidders are permitted to quote for one or more specific state/city lots, and the required bid security is the cumulative sum of EMD amounts corresponding to those participating lots.

Our data model captures this dual-granularity faithfully:
- **`Tender.emd_amount` (`Numeric(15, 2)`)**: Holds the true cumulative total EMD across all lots (e.g. ₹113.10 Cr for Tender 3, ₹134.82 Cr for PM E-DRIVE).
- **`Tender.emd_breakdown` (`JSONB`)**: Stores the structured lot-wise mapping `{"Lot Name / State": amount_in_INR_crores, ...}` directly extracted from Section 1 (IFB) of the source RFP.
- **`extraction_provenance` (`JSONB`)**: Traces both the scalar total and the lot breakdown back to the specific source document and page number.

#### Ground Truth EMD & Submission Deadlines across Parent Tenders

| Tender Program | Tender Reference | Verified Submission Deadline (Cutoff) | Techno-Commercial Opening | Cumulative EMD (`emd_amount`) | Lot-Wise Structure (`emd_breakdown`) |
|---|---|---|---|---|---|
| **PM-eBus Sewa Tender 3** (3,604 Buses) | `CESL/06/2026-27/PM-eBus Sewa3/262704003` | **05.06.2026 14:30 IST** | 05.06.2026 15:00 IST | **₹113.10 Cr** (`1,131,000,000.0`) | 19 Lots (e.g. Lot 1 Rajasthan ₹8.25 Cr, Lot 7 Karnataka ₹28.00 Cr, Lot 15 Kerala ₹11.48 Cr) |
| **PM E-DRIVE Scheme** (6,230 Buses) | `CESL/06/2025-26/PM E-Drive/252601015` | **10.03.2026 14:30 IST** | 10.03.2026 15:00 IST | **₹134.82 Cr** (`1,348,200,000.0`) | 8 Lots (e.g. Lot 1 Pune ₹5.45 Cr, Lot 3 Mumbai ₹29.50 Cr, Lot 7 Delhi ₹37.20 Cr) |
| **PM-eBus Sewa Tender 1** (3,600 / 3,725 Buses) | `CESL/06/2023-24/PM-eBusSewa/23241106` | **25.01.2024 14:30 IST** | 25.01.2024 15:00 IST | **₹91.89 Cr** (`918,900,000.0`) | 10 States (e.g. Maharashtra ₹37.61 Cr, Bihar ₹10.99 Cr, Gujarat ₹10.21 Cr) |
| **PM-eBus Sewa Tender 2** (4,588 / 3,132 Buses) | `CESL/06/2023-24/PM E Bus/ Phase II/ 2324003013` | **15.11.2024 14:00 IST** | 15.11.2024 15:00 IST | **₹127.55 Cr** (`1,275,500,000.0`) | 21 Lots across Package 1 (₹114.15 Cr) & Package 2 (₹13.40 Cr) |

### 2. Submission Cutoff vs. Opening Time Clarification
Government RFPs distinguish between:
1. **Online Bid Submission Period End Time** (e.g., 05.06.2026 up to 14:30 IST): The strict deadline by which all encrypted bids must be uploaded to the portal.
2. **Techno-Commercial E-Bid Opening Time** (e.g., 05.06.2026 at 15:00 IST): When the procurement committee opens the first envelope.

`submission_deadline` in our schema strictly represents the **bid submission cutoff (14:30 IST)** as this is the operational constraint for bidders.

## Technology Choices & Design Rationale

### 1. Agent Orchestration (Explicit Hand-Rolled Loop)
Implemented as an explicit multi-stage pipeline in `app/agent/pipeline.py`:
1. `PARSE`: Multi-page text extraction with PyMuPDF, magic-byte PDF validation, and English language guardrail check.
2. `HASH_CHECK`: SHA-256 fingerprint verification ensuring idempotent ingestion.
3. `RESOLVE_PARENT`: Creates or retrieves parent `Tender` record and manages amendment hierarchy.
4. `EXTRACT`: Structured schema extraction via LiteLLM (`TenderExtractionSchema`).
5. `CHUNK_AND_EMBED`: Paragraph-preserving semantic chunking and 768-dim vector embeddings.
6. `DETERMINISTIC_SCREEN`: Business rule screening against `CompanyProfile`.

**Why No Heavy Agent Frameworks (LangGraph, CrewAI, Agno)?**
- The pipeline represents a deterministic document processing workflow with strict transaction rollbacks and data provenance.
- Hand-rolled orchestration provides sub-millisecond execution control, zero framework bloat, and total transparency during defense review.

### 2. Strict Deterministic Screening
- LLMs are utilized strictly for extracting structured facts from complex legal text.
- **Evaluation is 100% Deterministic Python**:
  $$\text{NO-GO} > \text{REVIEW} > \text{GO}$$
  - If any mandatory criterion fails $\to$ **NO-GO**
  - If all mandatory criteria pass but optional/ambiguous clauses require assessment $\to$ **REVIEW**
  - If all criteria meet company capabilities $\to$ **GO**
- Guarantees zero hallucination in business-critical bid/no-bid verdicts.

### 3. Grounded RAG with Provenance Citations
- **Strict Anti-Hallucination Guardrail**: When retrieved context lacks sufficient evidence, the agent strictly responds:
  *"I could not find sufficient evidence in the stored tender documents to answer this confidently."*
- **No Canned Synthetics**: `retrieve_relevant_context()` (`app/services/retrieval.py`) only ever returns chunks that came from real SQL rows or real vector similarity search. If nothing is found — including on a fresh deployment with an empty vector store — it returns an empty list, which `rag.py` turns into the honest "insufficient evidence" message above rather than fabricating an answer from any hardcoded source.
- **No Fabricated Embeddings**: `generate_embedding()` (`app/services/embeddings.py`) tries Jina AI → cloud LiteLLM (Gemini/Groq) → local SentenceTransformer, in order. If every real provider fails, it raises `EmbeddingGenerationException` instead of returning a hash-derived placeholder vector, since a semantically meaningless vector would otherwise produce plausible-looking but meaningless similarity scores with no visible error.
- **Page-Level Grounding**: Every answer is backed by verifiable citations containing document name, page number, and text snippet.

### 4. Database & Vector Storage
- PostgreSQL with `pgvector` extension serves both relational records (tenders, criteria, profiles, logs) and vector embeddings.
- Zero extra vector database services required.
- All migrations managed via Alembic.

### 5. Multi-Environment Deployment
- **Docker Compose**: Containerized Postgres + Backend + Frontend stack for local and VM deployment.
- **Render Blueprint (`render.yaml`)**: Native cloud deployment blueprint with zero-config setup.