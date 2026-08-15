from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class CriterionVerdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"


class FinalVerdict(str, Enum):
    GO = "GO"
    NO_GO = "NO-GO"
    REVIEW = "REVIEW"


class CriterionDetail(BaseModel):
    criterion_name: str = Field(description="Name of the evaluated eligibility criterion.")
    is_mandatory: bool = Field(description="Whether this criterion is mandatory (hard failure triggers NO-GO).")
    verdict: CriterionVerdict = Field(description="Individual criterion evaluation verdict: PASS, FAIL, or REVIEW.")
    company_value: Any = Field(description="Value from the company profile.")
    required_value: Any = Field(description="Required threshold or clause from the tender.")
    reason: str = Field(description="Detailed explanation of evaluation logic.")


class ScreeningResultSchema(BaseModel):
    tender_id: str
    verdict: FinalVerdict
    reasoning: str
    criteria_results: List[CriterionDetail]
    screened_at: str
