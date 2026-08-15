from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional, List
from datetime import datetime, timezone

from app.db.database import get_db
from app.db.models import Tender, ScreeningResult, TenderEligibility
from app.schemas.tender import TenderResponse, TenderListResponse, ScreeningSummaryResponse, TenderEligibilityResponse

router = APIRouter(prefix="/api/tenders", tags=["Tenders"])


def format_tender_response(t: Tender) -> TenderResponse:
    now_dt = datetime.now(timezone.utc)
    deadline_dt = t.submission_deadline
    if deadline_dt.tzinfo is None:
        deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)

    time_diff = deadline_dt - now_dt
    days_remaining = max(0, time_diff.days)
    is_expired = time_diff.total_seconds() < 0

    screening_summary = None
    if t.screening_results:
        latest_s = sorted(t.screening_results, key=lambda x: x.screened_at, reverse=True)[0]
        screening_summary = ScreeningSummaryResponse(
            verdict=latest_s.verdict,
            reasoning=latest_s.reasoning,
            criteria_results=latest_s.criteria_results,
            screened_at=latest_s.screened_at.isoformat()
        )

    eligibility_summary = None
    if t.eligibility:
        e = t.eligibility
        eligibility_summary = TenderEligibilityResponse(
            minimum_fleet_size=e.minimum_fleet_size,
            minimum_annual_turnover=float(e.minimum_annual_turnover) if e.minimum_annual_turnover else None,
            minimum_experience_years=e.minimum_experience_years,
            minimum_past_contract_value=float(e.minimum_past_contract_value) if e.minimum_past_contract_value else None,
            required_geographies=e.required_geographies,
            other_requirements=e.other_requirements
        )

    return TenderResponse(
        id=str(t.id),
        title=t.title,
        issuing_authority=t.issuing_authority,
        city=t.city,
        state=t.state,
        category=t.category,
        submission_deadline=t.submission_deadline.isoformat(),
        timezone=t.timezone,
        days_remaining=days_remaining,
        is_expired=is_expired,
        emd_amount=float(t.emd_amount) if t.emd_amount else None,
        document_fee=float(t.document_fee) if t.document_fee else None,
        scope_summary=t.scope_summary,
        source_url=t.source_url,
        source_name=t.source_name,
        document_hash=t.document_hash,
        created_at=t.created_at.isoformat(),
        screening=screening_summary,
        eligibility=eligibility_summary
    )


@router.get("", response_model=TenderListResponse)
async def list_tenders(
    state: Optional[str] = Query(None, description="Filter tenders by state"),
    verdict: Optional[str] = Query(None, description="Filter tenders by GO / NO-GO / REVIEW verdict"),
    search: Optional[str] = Query(None, description="Search term in title or authority"),
    db: Session = Depends(get_db)
):
    stmt = select(Tender).order_by(Tender.submission_deadline.asc())
    tenders = db.scalars(stmt).all()

    filtered = []
    for t in tenders:
        resp = format_tender_response(t)
        
        if state and t.state and state.lower() not in t.state.lower():
            continue
        if verdict and resp.screening and resp.screening.verdict.upper() != verdict.upper():
            continue
        if search and search.lower() not in t.title.lower() and search.lower() not in t.issuing_authority.lower():
            continue
            
        filtered.append(resp)

    return TenderListResponse(total=len(filtered), tenders=filtered)


@router.get("/{tender_id}", response_model=TenderResponse)
async def get_tender_by_id(tender_id: str, db: Session = Depends(get_db)):
    t = db.query(Tender).filter(Tender.id == tender_id).first()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tender {tender_id} not found.")
    return format_tender_response(t)
