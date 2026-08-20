from pydantic import BaseModel, ConfigDict
from typing import Optional


class IngestionJobResponse(BaseModel):
    job_id: str
    status: str
    total_documents: int
    completed_documents: int
    failed_documents: int
    current_document: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
