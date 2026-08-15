from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any


class TenderEligibilityResponse(BaseModel):
    minimum_fleet_size: Optional[int] = None
    minimum_annual_turnover: Optional[float] = None
    minimum_experience_years: Optional[int] = None
    minimum_past_contract_value: Optional[float] = None
    minimum_depots_required: Optional[int] = None
    required_geographies: Optional[List[str]] = None
    other_requirements: Optional[List[Dict[str, Any]]] = None

    model_config = ConfigDict(from_attributes=True)


class ScreeningSummaryResponse(BaseModel):
    verdict: str
    reasoning: str
    criteria_results: List[Dict[str, Any]]
    screened_at: str

    model_config = ConfigDict(from_attributes=True)


class TenderResponse(BaseModel):
    id: str
    title: str
    issuing_authority: str
    city: Optional[str] = None
    state: Optional[str] = None
    category: str
    submission_deadline: str
    timezone: str
    days_remaining: int
    is_expired: bool
    emd_amount: Optional[float] = None
    document_fee: Optional[float] = None
    scope_summary: Optional[str] = None
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    document_hash: str
    created_at: str
    screening: Optional[ScreeningSummaryResponse] = None
    eligibility: Optional[TenderEligibilityResponse] = None

    model_config = ConfigDict(from_attributes=True)


class TenderListResponse(BaseModel):
    total: int
    tenders: List[TenderResponse]
