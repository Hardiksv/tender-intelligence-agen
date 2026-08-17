import pytest
from app.services.normalization import normalize_currency_to_inr, normalize_fleet_size
from app.services.extraction import extract_tender_structured_data
from app.schemas.extraction import OtherRequirementItem


def test_currency_normalization():
    val1, _ = normalize_currency_to_inr("INR 120 Crore")
    assert val1 == 1_200_000_000.0

    val2, _ = normalize_currency_to_inr("Rs 25 Lakhs")
    assert val2 == 2_500_000.0

    val3, _ = normalize_currency_to_inr("5000000.0")
    assert val3 == 5_000_000.0


def test_fleet_size_normalization():
    assert normalize_fleet_size("80 buses") == 80
    assert normalize_fleet_size(150) == 150


def test_is_mandatory_flag_schema():
    item = OtherRequirementItem(
        requirement_text="Depot management experience",
        is_mandatory=True,
        page_number=3
    )
    assert item.is_mandatory is True
    assert item.requirement_text == "Depot management experience"


def test_extraction_on_text():
    sample_text = """
    JAIPUR CITY TRANSPORT SERVICES LIMITED
    Tender for 100 Electric Buses on GCC Basis.
    Submission Deadline: 2026-09-15T15:00:00+05:30.
    EMD: Rs 50 Lakhs.
    Fleet size of 80 buses required. Turnover Rs 120 Crore required. Minimum 5 years of experience.
    """
    res = extract_tender_structured_data(sample_text, "test_tender.pdf")
    data = res["extraction"]

    assert data.title is not None
    assert data.eligibility.minimum_fleet_size == 80
    assert data.eligibility.minimum_annual_turnover == 1_200_000_000.0
    assert data.eligibility.minimum_experience_years == 5
