import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer, Numeric, DateTime, Enum as SQLEnum, ForeignKey, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.db.database import Base
from app.core.config import settings


class ScreeningVerdictEnum(str, enum.Enum):
    GO = "GO"
    NO_GO = "NO-GO"
    REVIEW = "REVIEW"


class IngestionStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    LANGUAGE_UNSUPPORTED = "LANGUAGE_UNSUPPORTED"


class Tender(Base):
    __tablename__ = "tenders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_ref = Column(String(200), nullable=True, index=True)
    title = Column(String(500), nullable=False)
    issuing_authority = Column(String(300), nullable=False)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    category = Column(String(100), default="bus_operations", nullable=False)
    
    # Bus Quantity Resolution (Original vs Latest Amended)
    original_bus_quantity = Column(Integer, nullable=True)
    latest_bus_quantity = Column(Integer, nullable=True)
    latest_quantity_source = Column(String(300), nullable=True)

    # Deadline Resolution (Original vs Latest Amended)
    submission_deadline = Column(DateTime(timezone=True), nullable=False)
    original_deadline = Column(DateTime(timezone=True), nullable=True)
    latest_deadline = Column(DateTime(timezone=True), nullable=True)
    latest_deadline_source = Column(String(300), nullable=True)
    timezone = Column(String(50), default="Asia/Kolkata", nullable=False)

    # EMD Resolution (Original vs Latest Amended)
    emd_amount = Column(Numeric(15, 2), nullable=True)
    original_emd_amount = Column(Numeric(15, 2), nullable=True)
    latest_emd_amount = Column(Numeric(15, 2), nullable=True)
    latest_emd_source = Column(String(300), nullable=True)

    document_fee = Column(Numeric(15, 2), nullable=True)
    scope_summary = Column(Text, nullable=True)
    source_url = Column(String(1000), nullable=True)
    source_name = Column(String(200), nullable=True)
    raw_document_path = Column(String(1000), nullable=False)
    document_hash = Column(String(64), unique=True, nullable=False, index=True)
    
    # Provenance tracking for every extracted field
    extraction_provenance = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    eligibility = relationship("TenderEligibility", back_populates="tender", uselist=False, cascade="all, delete-orphan")
    screening_results = relationship("ScreeningResult", back_populates="tender", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="tender", cascade="all, delete-orphan")
    chunks = relationship("DocumentChunk", back_populates="tender", cascade="all, delete-orphan")


class TenderEligibility(Base):
    __tablename__ = "tender_eligibility"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, unique=True)
    minimum_fleet_size = Column(Integer, nullable=True)
    minimum_annual_turnover = Column(Numeric(15, 2), nullable=True)
    minimum_experience_years = Column(Integer, nullable=True)
    minimum_past_contract_value = Column(Numeric(15, 2), nullable=True)
    minimum_depots_required = Column(Integer, nullable=True)
    required_geographies = Column(JSONB, nullable=True)
    # other_requirements contains items with explicit is_mandatory: bool
    other_requirements = Column(JSONB, nullable=True)

    tender = relationship("Tender", back_populates="eligibility")


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fleet_size = Column(Integer, nullable=False, default=0)
    annual_turnover = Column(Numeric(15, 2), nullable=False, default=0.0)
    years_experience = Column(Integer, nullable=False, default=0)
    past_contract_sizes = Column(JSONB, nullable=False, default=list)
    preferred_geographies = Column(JSONB, nullable=False, default=list)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class ScreeningResult(Base):
    __tablename__ = "screening_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False)
    verdict = Column(SQLEnum(ScreeningVerdictEnum), nullable=False)
    reasoning = Column(Text, nullable=False)
    criteria_results = Column(JSONB, nullable=False)
    screened_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    tender = relationship("Tender", back_populates="screening_results")


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String(255), nullable=False)
    document_type = Column(String(50), nullable=False, default="ORIGINAL_RFP")  # ORIGINAL_RFP, AMENDMENT, CORRIGENDUM, CLARIFICATION
    amendment_number = Column(String(50), nullable=True)  # e.g., "Amendment 5"
    source_url = Column(String(1000), nullable=True)
    page_count = Column(Integer, nullable=False, default=0)
    document_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    tender = relationship("Tender", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    embedding = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=False)
    chunk_metadata = Column(JSONB, nullable=True)  # Renamed from metadata to avoid SQLAlchemy reserved attribute conflict

    tender = relationship("Tender", back_populates="chunks")
    document = relationship("Document", back_populates="chunks")


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(SQLEnum(IngestionStatusEnum), nullable=False, default=IngestionStatusEnum.PENDING, index=True)
    total_documents = Column(Integer, nullable=False, default=0)
    completed_documents = Column(Integer, nullable=False, default=0)
    failed_documents = Column(Integer, nullable=False, default=0)
    current_document = Column(String(255), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
