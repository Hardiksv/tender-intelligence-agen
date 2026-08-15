from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.db.models import IngestionJob, IngestionStatusEnum
from app.schemas.ingestion import IngestionJobResponse
from app.core.exceptions import ConcurrentIngestionException
from app.agent.pipeline import run_ingestion_pipeline

router = APIRouter(prefix="/api/ingestion", tags=["Ingestion"])


@router.post("/run", response_model=IngestionJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_ingestion_run(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Triggers asynchronous background ingestion of seed PDF tender documents.
    Protects against concurrent job execution by raising HTTP 409 Conflict if a job is RUNNING.
    """
    active_job = db.query(IngestionJob).filter(IngestionJob.status == IngestionStatusEnum.RUNNING).first()
    if active_job:
        raise ConcurrentIngestionException(
            f"An ingestion job (ID: {active_job.id}) is already currently running."
        )

    job = IngestionJob(
        status=IngestionStatusEnum.PENDING,
        total_documents=0,
        completed_documents=0,
        failed_documents=0
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Launch in FastAPI BackgroundTasks
    background_tasks.add_task(run_ingestion_pipeline, str(job.id))

    return IngestionJobResponse(
        job_id=str(job.id),
        status=job.status.value,
        total_documents=job.total_documents,
        completed_documents=job.completed_documents,
        failed_documents=job.failed_documents,
        current_document=job.current_document,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        error_message=job.error_message
    )


@router.get("/{job_id}", response_model=IngestionJobResponse)
async def get_ingestion_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ingestion job {job_id} not found.")

    return IngestionJobResponse(
        job_id=str(job.id),
        status=job.status.value,
        total_documents=job.total_documents,
        completed_documents=job.completed_documents,
        failed_documents=job.failed_documents,
        current_document=job.current_document,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        error_message=job.error_message
    )
