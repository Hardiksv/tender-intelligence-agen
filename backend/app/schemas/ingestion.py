from typing import Optional

from pydantic import BaseModel, ConfigDict


class IngestionJobResponse(BaseModel):
    job_id: str
    status: str
    total_documents: int
    completed_documents: int
    failed_documents: int
    current_document: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None

    model_config = ConfigDict(from_attributes=True)
