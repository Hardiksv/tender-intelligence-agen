from fastapi import FastAPI, Request, status, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.core.config import settings
from app.core.logging import logger, log_action
from app.core.exceptions import (
    TenderAgentException,
    ConcurrentIngestionException,
    EmbeddingDimensionMismatchException,
    LanguageUnsupportedException
)

from app.api import tenders, screening, profile, chat, ingestion
from app.db.database import get_db

app = FastAPI(
    title="Tender Intelligence Agent API",
    description="Production-grade AI pipeline for public Bus Operations tender analysis, screening, and RAG Q&A",
    version="1.0.0"
)

def init_db_if_empty():
    """Initializes schema and pre-seeds catalog parent tenders on serverless cold starts."""
    try:
        from app.db.database import SessionLocal, Base, engine
        from app.db.models import Tender, CompanyProfile, TenderEligibility, ScreeningResult
        from app.agent.pipeline import CATALOG, get_or_create_default_profile
        from app.services.screening import screen_tender_eligibility
        from app.schemas.profile import CompanyProfileBase
        from app.schemas.extraction import TenderEligibilitySchema
        from datetime import datetime
        import hashlib

        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            profile_db = get_or_create_default_profile(db)
            if db.query(Tender).count() == 0:
                logger.info("Database empty on startup. Pre-seeding catalog parent tenders...")
                for fname, meta in CATALOG.items():
                    if not meta.get("is_parent"):
                        continue
                    t_ref = meta["tender_ref"]
                    if db.query(Tender).filter(Tender.tender_ref == t_ref).first():
                        continue
                    deadline_dt = datetime.fromisoformat(meta["submission_deadline"])
                    doc_hash = hashlib.sha256(fname.encode("utf-8")).hexdigest()
                    t = Tender(
                        tender_ref=t_ref,
                        title=meta["title"],
                        issuing_authority=meta["issuing_authority"],
                        city=meta.get("city"),
                        state=meta.get("state"),
                        category="bus_operations",
                        original_bus_quantity=meta.get("original_bus_quantity"),
                        latest_bus_quantity=meta.get("latest_bus_quantity"),
                        latest_quantity_source=meta.get("latest_quantity_source"),
                        submission_deadline=deadline_dt,
                        original_deadline=deadline_dt,
                        latest_deadline=deadline_dt,
                        timezone="Asia/Kolkata",
                        emd_amount=meta.get("emd_amount"),
                        original_emd_amount=meta.get("emd_amount"),
                        latest_emd_amount=meta.get("emd_amount"),
                        emd_breakdown=meta.get("emd_breakdown"),
                        document_fee=meta.get("document_fee"),
                        scope_summary=meta["title"],
                        source_url=meta.get("source_url"),
                        source_name="Public Procurement Portal",
                        raw_document_path=fname,
                        document_hash=doc_hash,
                        extraction_provenance={
                            "bus_quantity": {"latest_value": meta.get("latest_bus_quantity"), "source_document": fname},
                            "emd_amount": {"value": meta.get("emd_amount"), "breakdown": meta.get("emd_breakdown"), "source_document": fname}
                        }
                    )
                    db.add(t)
                    db.flush()

                    # Default eligibility & deterministic screening verdict
                    elig = TenderEligibility(
                        tender_id=t.id,
                        minimum_fleet_size=80,
                        minimum_annual_turnover=100000000.0,
                        minimum_experience_years=5,
                        minimum_past_contract_value=50000000.0,
                        required_geographies=[t.state] if t.state and t.state != "National" else ["National"],
                        other_requirements=[]
                    )
                    db.add(elig)
                    db.flush()

                    profile_base = CompanyProfileBase(
                        fleet_size=profile_db.fleet_size,
                        annual_turnover=float(profile_db.annual_turnover),
                        years_experience=profile_db.years_experience,
                        past_contract_sizes=[float(v) for v in profile_db.past_contract_sizes],
                        preferred_geographies=profile_db.preferred_geographies
                    )
                    elig_schema = TenderEligibilitySchema(
                        minimum_fleet_size=elig.minimum_fleet_size,
                        minimum_annual_turnover=float(elig.minimum_annual_turnover),
                        minimum_experience_years=elig.minimum_experience_years,
                        minimum_past_contract_value=float(elig.minimum_past_contract_value),
                        required_geographies=elig.required_geographies,
                        other_requirements=[]
                    )
                    s_res = screen_tender_eligibility(
                        tender_id=str(t.id),
                        tender_title=t.title,
                        tender_state=t.state,
                        eligibility=elig_schema,
                        profile=profile_base
                    )
                    screening_db = ScreeningResult(
                        tender_id=t.id,
                        verdict=s_res.verdict.value,
                        reasoning=s_res.reasoning,
                        criteria_results=[c.model_dump() for c in s_res.criteria_results]
                    )
                    db.add(screening_db)
                db.commit()
                logger.info("Successfully seeded catalog parent tenders on startup.")
        except Exception as e:
            logger.warning(f"Error during startup seeding: {e}")
            db.rollback()
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Failed to initialize database: {e}")

# Run startup initialization
init_db_if_empty()

# CORS Configuration
origins = [
    settings.FRONTEND_ORIGIN,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000"
] if settings.FRONTEND_ORIGIN else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not settings.FRONTEND_ORIGIN else origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(ConcurrentIngestionException)
async def concurrent_ingestion_handler(request: Request, exc: ConcurrentIngestionException):
    log_action("INGESTION_REJECTED_CONCURRENT", status="REJECTED", details={"message": exc.message})
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": exc.message, "error_code": "CONCURRENT_INGESTION_RUNNING"}
    )


@app.exception_handler(EmbeddingDimensionMismatchException)
async def embedding_mismatch_handler(request: Request, exc: EmbeddingDimensionMismatchException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message, "error_code": "EMBEDDING_DIMENSION_MISMATCH"}
    )


@app.exception_handler(LanguageUnsupportedException)
async def language_unsupported_handler(request: Request, exc: LanguageUnsupportedException):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.message, "error_code": "LANGUAGE_UNSUPPORTED"}
    )


@app.exception_handler(TenderAgentException)
async def tender_agent_exception_handler(request: Request, exc: TenderAgentException):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": exc.message, "details": exc.details}
    )


# Include API Routers
app.include_router(tenders.router)
app.include_router(screening.router)
app.include_router(profile.router)
app.include_router(chat.router)
app.include_router(ingestion.router)

# Root-level Route Aliases for assignment compliance and Vercel compatibility
@app.get("/", tags=["Root"])
@app.get("/api", tags=["Root"])
@app.get("/api/", tags=["Root"])
@app.get("/api/index", tags=["Root"])
@app.get("/api/index.py", tags=["Root"])
async def root_index():
    """Root status endpoint."""
    return {
        "status": "online",
        "app": "Tender Intelligence Agent API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "api_docs_url": "/api/docs",
        "health_url": "/health",
        "api_health_url": "/api/health"
    }

@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "app": "Tender Intelligence Agent",
        "version": "1.0.0",
        "timezone": settings.TIMEZONE
    }

@app.get("/api/docs", include_in_schema=False)
async def api_docs():
    return get_swagger_ui_html(
        openapi_url="/api/openapi.json",
        title="Tender Intelligence Agent - API Docs"
    )

@app.get("/api/openapi.json", include_in_schema=False)
async def api_openapi():
    return JSONResponse(get_openapi(title=app.title, version=app.version, routes=app.routes))

@app.get("/tenders", tags=["Tenders Alias"])
async def list_tenders_alias(db = Depends(get_db)):
    return await tenders.list_tenders(db=db)

@app.post("/ask", tags=["RAG Alias"])
async def ask_alias(req: chat.ChatRequest, db = Depends(get_db)):
    return await chat.chat_qna(req, db=db)

@app.post("/search", tags=["Search Alias"])
async def search_alias(req: chat.ChatRequest, db = Depends(get_db)):
    return await chat.chat_qna(req, db=db)

@app.post("/ingest", tags=["Ingestion Alias"])
async def ingest_alias(background_tasks: BackgroundTasks, db = Depends(get_db)):
    return await ingestion.trigger_ingestion_run(background_tasks, db=db)


@app.get("/api/debug-routing", tags=["Debug"])
async def debug_routing(request: Request):
    """Debug endpoint to inspect exact ASGI path and headers received from Vercel."""
    return {
        "url_path": request.url.path,
        "scope_path": request.scope.get("path"),
        "scope_raw_path": request.scope.get("raw_path", b"").decode("utf-8", errors="replace"),
        "query_string": request.scope.get("query_string", b"").decode("utf-8", errors="replace"),
        "headers": {k.decode("utf-8", errors="replace"): v.decode("utf-8", errors="replace") for k, v in request.scope.get("headers", [])}
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
