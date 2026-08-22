from typing import Any, Optional

from pydantic import BaseModel, Field


class Citation(BaseModel):
    tender_id: str = Field(description="UUID of the tender source.")
    tender_title: str = Field(description="Title of the tender source.")
    document_name: str = Field(description="File name of the document.")
    page_number: int = Field(description="Page number where evidence is found.")
    chunk_index: int = Field(description="Chunk index number.")
    snippet: str = Field(description="Verbatim excerpt from the document page.")


class ChatRequest(BaseModel):
    question: str = Field(description="Natural language question about stored tenders.")
    tender_id: str | None = Field(default=None, description="Optional tender ID filter to constrain Q&A context.")


class ChatResponse(BaseModel):
    question: str
    answer: str
    citations: list[Citation]
    model_used: str
    usage: dict[str, Any]
