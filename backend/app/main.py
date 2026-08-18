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

from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi

# Root-level Route Aliases for assignment compliance and Vercel compatibility
@app.get("/", tags=["Root"])
@app.get("/api", tags=["Root"])
async def root_index():
    """Root status endpoint."""
    return {
        "status": "online",
        "app": "Tender Intelligence Agent API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "api_docs_url": "/api/docs",
        "health_url": "/health"
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
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/api/openapi.json" if app.openapi_url else "/openapi.json",
        title=app.title + " - Swagger UI"
    )

@app.get("/api/openapi.json", include_in_schema=False)
async def custom_openapi():
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


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
