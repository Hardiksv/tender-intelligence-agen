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
│  ├── Embeddings (Gemini text-embedding-004 & Local Fallback)│
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

The system operates over authentic public government procurement documents in the **Bus Operations** category (Gross Cost Contracts — GCC, wet lease, per-kilometer service contracts):

### Public Tender Procurement Programs in `data/raw/`

| # | Document Filename | Issuing Authority & Scheme | Tender Reference Number | Scope / Bus Quantity |
|---|---|---|---|---|
| **1** | `cesl_pm_edrive_6230_electric_buses_gcc.pdf` | Convergence Energy Services Limited (CESL) / PM E-DRIVE | `CESL/06/2025-26/PM E-Drive/252601015` | **6,230 E-Buses** (2,900 Pan-India STUs + 3,330 Delhi DTC) |
| **2** | `cesl_pm_ebus_sewa_3_3604_buses_gcc.pdf` | CESL / PM-eBus Sewa (Tender 3) | `CESL/06/2026-27/PM-eBus Sewa3/262704003` | **3,604 E-Buses** across 5 State Transport Undertakings |
| **3** | `cesl_pm_ebus_sewa_3_amendment.pdf` | CESL / PM-eBus Sewa (Tender 3) | `CESL/06/2026-27/PM-eBus Sewa3/262704003/Amdt-1` | Official Corrigendum & Bid Deadline Extension |
| **4** | `pm_ebus_sewa_tender_1_full_rfp.pdf` | Ministry of Housing & Urban Affairs (MoHUA) / CESL | `CESL/06/2023-24/PM-eBusSewa/23241106` | **3,600 E-Buses** GCC Operator Selection |
| **5** | `pm_ebus_sewa_tender_1_amend_5.pdf` | MoHUA / CESL | `CESL/06/2023-24/PM-eBusSewa/23241106/Amdt-5` | **3,725 E-Buses** (Quantity Amendment & State Allocations) |
| **6** | `pm_ebus_sewa_tender_2_gcc.pdf` | CESL / PM-eBus Sewa (Phase II) | `CESL/06/2023-24/PM E Bus/ Phase II/ 2324003013` | **4,588 E-Buses** (Revised to 3,132 via Amendment 11) |
| **7** | `dtc_delhi_300_ebuses_gcc.pdf` | Delhi Transport Corporation (DTC) | `2020_DTC_197163_1` | **300 E-Buses** Low-Floor AC GCC Tender |
| **8** | `best_mumbai_2400_ebuses_gcc.pdf` | Brihanmumbai Electric Supply & Transport (BEST) | `2023_BEST_908652_1` | **2,400 E-Buses** GCC Operator RFP |
| **9** | `jctsl_jaipur_450_ebuses_gcc.pdf` | Jaipur City Transport Services Limited (JCTSL) | `2026_JCTS_532359_1` | **450 E-Buses** (400 9M + 50 12M GCC Buses) |
| **10** | `upsrtc_utd_1225_ebuses_gcc.pdf` | Directorate of Urban Transport UP / UPSRTC | `UTD/UP/EV-BUS/1225/2025-26` | **1,225 E-Buses** across 14 Municipal Corporations |
| **11** | `aictsl_indore_50_ebuses_gcc.pdf` | Atal Indore City Transport Services (AICTSL) | `AICTSL/2025/E-BUS/GCC-04` | **50 E-Buses** GCC Per-Km Contract |
| **12** | `ctu_chandigarh_80_ebuses_gcc.pdf` | Chandigarh Transport Undertaking (CTU) | `CTU/2025/EV-80/GCC-02` | **80 MIDI AC E-Buses** GCC Contract |
| **13** | `ksrtc_kerala_wet_lease_buses.pdf` | Kerala State Road Transport Corporation (KSRTC) | `KSRTC/OP/2025/WL-100` | **100 Electric / Diesel Buses** Wet Lease Contract |

---

## Technology Choices & Design Rationale

### 1. Agent Orchestration (Explicit Hand-Rolled Loop)
Implemented as an explicit multi-stage pipeline in `app/agent/pipeline.py`:
1. `PARSE`: Multi-page text extraction with PyMuPDF and English language guardrail check.
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
- **No Canned Synthetics**: Zero hardcoded keyword fallback answers. If the LLM provider is unavailable, a clean service error is returned.
- **Page-Level Grounding**: Every answer is backed by verifiable citations containing document name, page number, and text snippet.

### 4. Database & Vector Storage
- PostgreSQL with `pgvector` extension serves both relational records (tenders, criteria, profiles, logs) and vector embeddings.
- Zero extra vector database services required.
- All migrations managed via Alembic.

### 5. Multi-Environment Deployment
- **Docker Compose**: Containerized Postgres + Backend + Frontend stack for local and VM deployment.
- **Render Blueprint (`render.yaml`)**: Native cloud deployment blueprint with zero-config setup.
