from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.db.database import get_db
from app.db.models import Tender, ScreeningResult
from app.schemas.screening import ScreeningResultSchema, FinalVerdict, CriterionVerdict
from app.schemas.profile import CompanyProfileBase
from app.schemas.extraction import TenderEligibilitySchema, OtherRequirementItem
from app.services.screening import screen_tender_eligibility
from app.agent.pipeline import get_or_create_default_profile

router = APIRouter(prefix="/api/tenders", tags=["Screening"])


@router.get("/{tender_id}/screening", response_model=ScreeningResultSchema)
async def get_tender_screening(tender_id: str, db: Session = Depends(get_db)):
    t = db.query(Tender).filter(Tender.id == tender_id).first()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tender not found")

    latest_s = db.query(ScreeningResult).filter(ScreeningResult.tender_id == tender_id).order_by(ScreeningResult.screened_at.desc()).first()
    if not latest_s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Screening result not found for this tender.")

    return ScreeningResultSchema(
        tender_id=str(t.id),
        verdict=FinalVerdict(latest_s.verdict),
        reasoning=latest_s.reasoning,
        criteria_results=latest_s.criteria_results,
        screened_at=latest_s.screened_at.isoformat()
    )


@router.post("/{tender_id}/screen", response_model=ScreeningResultSchema)
async def run_tender_screening(tender_id: str, db: Session = Depends(get_db)):
    t = db.query(Tender).filter(Tender.id == tender_id).first()
    if not t or not t.eligibility:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tender or eligibility details not found")

    profile_db = get_or_create_default_profile(db)
    profile_base = CompanyProfileBase(
        fleet_size=profile_db.fleet_size,
        annual_turnover=float(profile_db.annual_turnover),
        years_experience=profile_db.years_experience,
        past_contract_sizes=profile_db.past_contract_sizes,
        preferred_geographies=profile_db.preferred_geographies
    )

    other_items = [
        OtherRequirementItem(
            requirement_text=req.get("requirement_text", ""),
            is_mandatory=req.get("is_mandatory", True),
            page_number=req.get("page_number"),
            clause_ref=req.get("clause_ref")
        ) for req in (t.eligibility.other_requirements or [])
    ]

    eligibility_schema = TenderEligibilitySchema(
        minimum_fleet_size=t.eligibility.minimum_fleet_size,
        minimum_annual_turnover=float(t.eligibility.minimum_annual_turnover) if t.eligibility.minimum_annual_turnover else None,
        minimum_experience_years=t.eligibility.minimum_experience_years,
        minimum_past_contract_value=float(t.eligibility.minimum_past_contract_value) if t.eligibility.minimum_past_contract_value else None,
        required_geographies=t.eligibility.required_geographies or [],
        other_requirements=other_items
    )

    res = screen_tender_eligibility(
        tender_id=str(t.id),
        tender_title=t.title,
        tender_state=t.state,
        eligibility=eligibility_schema,
        profile=profile_base
    )

    screening_model = ScreeningResult(
        tender_id=t.id,
        verdict=res.verdict.value,
        reasoning=res.reasoning,
        criteria_results=[c.model_dump() for c in res.criteria_results]
    )
    db.add(screening_model)
    db.commit()

    return res
