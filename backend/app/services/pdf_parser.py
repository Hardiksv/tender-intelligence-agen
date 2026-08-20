import hashlib
import os
import pymupdf  # PyMuPDF
from typing import Dict, Any, List

from app.core.exceptions import ParsingException, LanguageUnsupportedException
from app.core.logging import logger, log_action
from app.services.language import detect_document_language

# Real PDF files always start with this magic header (spec: ISO 32000).
# A scraper that saves a 404 page / WordPress homepage as "something.pdf" will
# NOT have this header — pymupdf will still happily "open" that HTML and
# extract garbage nav-menu text without ever raising an error, which is how
# 4 broken files silently entered this project's seed set. Fail loud, here.
_PDF_MAGIC = b"%PDF-"


def _validate_is_real_pdf(file_path: str, file_bytes: bytes) -> None:
    """Guards against non-PDF content (HTML error pages, etc.) saved with a .pdf extension."""
    header = file_bytes[:1024].lstrip(b"\xef\xbb\xbf")  # tolerate BOM
    if not header.startswith(_PDF_MAGIC):
        snippet = file_bytes[:120].decode("utf-8", errors="replace").strip().replace("\n", " ")
        raise ParsingException(
            f"'{os.path.basename(file_path)}' does not have a valid PDF header (%PDF-). "
            f"This usually means a scraper saved an HTML/error page with a .pdf extension. "
            f"First bytes: {snippet!r}"
        )


def parse_pdf_document(file_path: str) -> Dict[str, Any]:
    """
    Parses a PDF document into page-aware text chunks, computes SHA-256 document hash,
    and runs language detection.
    """
    if not os.path.exists(file_path):
        raise ParsingException(f"File not found at path: {file_path}")

    try:
        # Compute SHA-256 hash of raw file bytes for idempotency
        with open(file_path, "rb") as f:
            file_bytes = f.read()
            doc_hash = hashlib.sha256(file_bytes).hexdigest()

        # Reject non-PDF content BEFORE handing it to pymupdf, which will
        # otherwise silently "parse" HTML/text as if it were real document content.
        _validate_is_real_pdf(file_path, file_bytes)

        doc = pymupdf.open(file_path)
        page_count = len(doc)
        pages_data: List[Dict[str, Any]] = []
        full_text_parts: List[str] = []

        for page_idx in range(page_count):
            page = doc.load_page(page_idx)
            page_text = page.get_text("text") or ""
            page_number = page_idx + 1

            pages_data.append({
                "page_number": page_number,
                "text": page_text.strip()
            })
            full_text_parts.append(page_text.strip())

        doc.close()
        full_text = "\n\n".join(full_text_parts)

        # Language Detection Guardrail
        is_english, detected_lang = detect_document_language(full_text)

        result = {
            "file_name": os.path.basename(file_path),
            "file_path": file_path,
            "document_hash": doc_hash,
            "page_count": page_count,
            "pages": pages_data,
            "full_text": full_text,
            "detected_language": detected_lang,
            "is_english": is_english
        }

        log_action(
            "PDF_PARSED",
            status="SUCCESS",
            details={
                "file_name": os.path.basename(file_path),
                "page_count": page_count,
                "document_hash": doc_hash[:12],
                "detected_language": detected_lang
            }
        )

        return result

    except ParsingException:
        raise
    except Exception as e:
        logger.error(f"Error parsing PDF file {file_path}: {str(e)}")
        raise ParsingException(f"Failed to parse PDF document: {str(e)}")