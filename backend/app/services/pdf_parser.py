import hashlib
import os
import pymupdf  # PyMuPDF
from typing import Dict, Any, List

from app.core.exceptions import ParsingException, LanguageUnsupportedException
from app.core.logging import logger, log_action
from app.services.language import detect_document_language


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

    except Exception as e:
        logger.error(f"Error parsing PDF file {file_path}: {str(e)}")
        raise ParsingException(f"Failed to parse PDF document: {str(e)}")
