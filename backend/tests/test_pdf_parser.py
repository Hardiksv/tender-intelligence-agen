import pytest
import os
from app.services.pdf_parser import parse_pdf_document
from app.services.language import detect_document_language

SEED_PDF_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "raw", "jctsl_jaipur_450_ebuses_gcc.pdf"
)


def test_pdf_parser_success():
    assert os.path.exists(SEED_PDF_PATH), f"Seed PDF not found at {SEED_PDF_PATH}"
    result = parse_pdf_document(SEED_PDF_PATH)

    assert result["file_name"] == "jctsl_jaipur_450_ebuses_gcc.pdf"
    assert result["page_count"] >= 1
    assert len(result["pages"]) >= 1
    assert result["pages"][0]["page_number"] == 1
    assert "Jaipur City Transport Services" in result["full_text"]
    assert len(result["document_hash"]) == 64
    assert result["is_english"] is True


def test_pdf_hash_idempotency():
    result1 = parse_pdf_document(SEED_PDF_PATH)
    result2 = parse_pdf_document(SEED_PDF_PATH)
    assert result1["document_hash"] == result2["document_hash"]


def test_non_english_detection():
    hindi_text = "जयपुर सिटी ट्रांसपोर्ट सर्विसेज लिमिटेड 100 इलेक्ट्रिक बसों के संचालन के लिए निविदा आमंत्रित करती है।"
    is_english, lang = detect_document_language(hindi_text)
    assert is_english is False
    assert lang == "hi"
