from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CompanyProfileBase(BaseModel):
    fleet_size: int = Field(default=120, description="Total active operating commercial buses owned/operated.")
    annual_turnover: float = Field(default=150000000.0, description="Annual financial turnover in INR.")
    years_experience: int = Field(default=7, description="Total years of operating experience in transit.")
    past_contract_sizes: list[float] = Field(default_factory=lambda: [75000000.0, 90000000.0], description="List of single executed past contract values in INR.")
    preferred_geographies: list[str] = Field(default_factory=lambda: ["Rajasthan", "Haryana", "Delhi", "Gujarat"], description="Preferred operational states/cities.")


class CompanyProfileCreate(CompanyProfileBase):
    pass


class CompanyProfileUpdate(BaseModel):
    fleet_size: int | None = None
    annual_turnover: float | None = None
    years_experience: int | None = None
    past_contract_sizes: list[float] | None = None
    preferred_geographies: list[str] | None = None


class CompanyProfileResponse(CompanyProfileBase):
    id: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)
