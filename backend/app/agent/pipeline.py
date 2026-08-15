import os
import json
import glob
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.logging import logger, log_action
from app.db.database import SessionLocal
from app.db.models import (
    Tender, TenderEligibility, CompanyProfile, ScreeningResult,
    Document, DocumentChunk, IngestionJob, IngestionStatusEnum
)
from app.services.pdf_parser import parse_pdf_document
from app.services.extraction import extract_tender_structured_data
from app.services.chunking import chunk_document_pages
from app.services.embeddings import generate_embeddings_batch
from app.schemas.profile import CompanyProfileBase

SEED_DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "raw")
)

# Catalog mapping files to parent tender opportunities & child metadata
def get_or_create_default_profile(db: Session) -> CompanyProfile:
    profile = db.query(CompanyProfile).first()
    if not profile:
        profile = CompanyProfile(
            fleet_size=120,
            annual_turnover=150000000.0,
            years_experience=7,
            past_contract_sizes=[75000000.0, 90000000.0],
            preferred_geographies=["Rajasthan", "Haryana", "Delhi", "Gujarat"]
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile
CATALOG = {
    "cesl_pm_ebus_sewa_3_3604_buses_gcc.pdf": {
        "tender_ref": "CESL/06/2026-27/PM-eBus Sewa3/262704003",
        "is_parent": True,
        "document_type": "ORIGINAL_RFP",
        "amendment_number": None,
        "title": "Selection of Bus Operator for Procurement, Supply, Operation and Maintenance of 3,604 Electric Buses and Development of Allied Electric and Civil Infrastructure on Gross Cost Contracting (GCC) under PM-eBus Sewa (Tender 3)",
        "issuing_authority": "Convergence Energy Services Limited (CESL)",
        "city": "Pan-India",
        "state": "National",
        "original_bus_quantity": 3604,
        "latest_bus_quantity": 3604,
        "latest_quantity_source": "Original RFP",
        "submission_deadline": "2026-09-02T15:00:00+05:30",
        "emd_amount": 10000000.0,
        "document_fee": 25000.0,
        "source_url": "http://www.convergence.co.in/public/upload/tender_pdf/x845qy239kcl5sk8ld.pdf"
    },
    "cesl_pm_ebus_sewa_3_amendment.pdf": {
        "tender_ref": "CESL/06/2026-27/PM-eBus Sewa3/262704003",
        "is_parent": False,
        "document_type": "AMENDMENT",
        "amendment_number": "Amendment No. 3",
        "source_url": "http://www.convergence.co.in/public/upload/tender_pdf/l6hjmz7na83xqvad64.pdf"
    },
    "cesl_pm_edrive_6230_electric_buses_gcc.pdf": {
        "tender_ref": "CESL/06/2025-26/PM E-Drive/252601015",
        "is_parent": True,
        "document_type": "ORIGINAL_RFP",
        "amendment_number": None,
        "title": "Selection of Bus Operator for Procurement, Supply, Operation & Maintenance and Development of Allied Electric & Civil Infrastructure on Gross Cost Contracting (GCC) for 2,900 Electric Buses under PM E-DRIVE Scheme Tender-II & 3,330 for Delhi",
        "issuing_authority": "Convergence Energy Services Limited (CESL)",
        "city": "Pan-India & Delhi",
        "state": "National",
        "original_bus_quantity": 6230,
        "latest_bus_quantity": 6230,
        "latest_quantity_source": "Original RFP",
        "submission_deadline": "2026-03-10T15:00:00+05:30",
        "emd_amount": 15000000.0,
        "document_fee": 25000.0,
        "source_url": "http://www.convergence.co.in/public/images/1978.pdf"
    },
    "pm_ebus_sewa_tender_1_full_rfp.pdf": {
        "tender_ref": "CESL/06/2023-24/PM-eBusSewa/23241106",
        "is_parent": True,
        "document_type": "ORIGINAL_RFP",
        "amendment_number": None,
        "title": "Selection of Bus Operator for Procurement, Supply, Operation and Maintenance of 3,600 Electric Buses and Development of Allied Electric and Civil Infrastructure on Gross Cost Contracting (GCC) under PM-eBus Sewa (Tender 1)",
        "issuing_authority": "Convergence Energy Services Limited (CESL)",
        "city": "Pan-India",
        "state": "National",
        "original_bus_quantity": 3600,
        "latest_bus_quantity": 3600,
        "latest_quantity_source": "Original RFP",
        "submission_deadline": "2024-01-25T15:00:00+05:30",
        "emd_amount": 10000000.0,
        "document_fee": 25000.0,
        "source_url": "https://pm-ebus-sewa.mohua.gov.in/wp-content/uploads/2025/10/1919-1.pdf"
    },
    "pm_ebus_sewa_tender_1_amend_5.pdf": {
        "tender_ref": "CESL/06/2023-24/PM-eBusSewa/23241106",
        "is_parent": False,
        "document_type": "AMENDMENT",
        "amendment_number": "Amendment No. 5",
        "latest_bus_quantity": 3725,
        "latest_quantity_source": "Amendment No. 5 (Ref: CESL/06/2023-24/PM-eBusSewa/23241106/Amdt-5 Dated 17-01-2024)",
        "source_url": "https://pm-ebus-sewa.mohua.gov.in/wp-content/uploads/2025/10/AmendNo_5_tenderNo1919.pdf"
    },
    "pm_ebus_sewa_tender_2_gcc.pdf": {
        "tender_ref": "CESL/06/2023-24/PM E Bus/ Phase II/ 2324003013",
        "is_parent": True,
        "document_type": "ORIGINAL_RFP",
        "amendment_number": "Amendment No. 11",
        "title": "Selection of Bus Contractor for Procurement, Supply and Maintenance for 4,588 Electric Buses and Development of Allied Electric & Civil Infrastructure on Gross Cost Contract (GCC) model under PM-ebus Sewa Scheme (Tender 2)",
        "issuing_authority": "Convergence Energy Services Limited (CESL)",
        "city": "Pan-India",
        "state": "National",
        "original_bus_quantity": 4588,
        "latest_bus_quantity": 3132,
        "latest_quantity_source": "Amendment No. 11 (Ref: CESL/06/2023-24/PM E Bus/ Phase II/ 2324003013/ Amdt-11 Dated 29.10.2024)",
        "submission_deadline": "2024-11-15T15:00:00+05:30",
        "emd_amount": 10000000.0,
        "document_fee": 25000.0,
        "source_url": "https://pm-ebus-sewa.mohua.gov.in/wp-content/uploads/2025/11/CESL-PM-eBus-Sewa-Tender-2-Amend-11_Clear-Copy-1.pdf"
    },
    "best_mumbai_2400_ebuses_gcc.pdf": {
        "tender_ref": "2023_BEST_908652_1",
        "is_parent": True,
        "document_type": "ORIGINAL_RFP",
        "title": "Selection of Bus Operator for Procurement, Supply, Operation and Maintenance of 2,400 Single Decker Air Conditioned Electric Buses on Gross Cost Contract (GCC) Model",
        "issuing_authority": "Brihanmumbai Electric Supply & Transport Undertaking (BEST)",
        "city": "Mumbai",
        "state": "Maharashtra",
        "original_bus_quantity": 2400,
        "latest_bus_quantity": 2400,
        "latest_quantity_source": "Original RFP",
        "submission_deadline": "2024-03-20T15:00:00+05:30",
        "emd_amount": 12000000.0,
        "document_fee": 25000.0,
        "source_url": "https://mahatenders.gov.in"
    },
    "jctsl_jaipur_450_ebuses_gcc.pdf": {
        "tender_ref": "2026_JCTS_532359_1",
        "is_parent": True,
        "document_type": "ORIGINAL_RFP",
        "title": "Selection of Bus Operator for Procurement, Supply, Operation and Maintenance of 400 (9M) and 50 (12M) AC Fully Built Pure Electric Buses on Gross Cost Contracting (GCC) in Jaipur",
        "issuing_authority": "Jaipur City Transport Services Limited (JCTSL)",
        "city": "Jaipur",
        "state": "Rajasthan",
        "original_bus_quantity": 450,
        "latest_bus_quantity": 450,
        "latest_quantity_source": "Original RFP",
        "submission_deadline": "2026-06-30T17:00:00+05:30",
        "emd_amount": 5000000.0,
        "document_fee": 10000.0,
        "source_url": "https://sppp.rajasthan.gov.in"
    },
    "upsrtc_utd_1225_ebuses_gcc.pdf": {
        "tender_ref": "UTD/UP/EV-BUS/1225/2025-26",
        "is_parent": True,
        "document_type": "ORIGINAL_RFP",
        "title": "Selection of Bus Operator for Procurement, Supply, Operation and Maintenance of 1,225 Electric Buses under Gross Cost Contract (GCC) Model across 14 Municipal Corporations",
        "issuing_authority": "Directorate of Urban Transport, UP / UPSRTC",
        "city": "Lucknow",
        "state": "Uttar Pradesh",
        "original_bus_quantity": 1225,
        "latest_bus_quantity": 1225,
        "latest_quantity_source": "Original RFP",
        "submission_deadline": "2025-10-15T15:00:00+05:30",
        "emd_amount": 8000000.0,
        "document_fee": 15000.0,
        "source_url": "https://etender.up.nic.in"
    },
    "dtc_delhi_300_ebuses_gcc.pdf": {
        "tender_ref": "2020_DTC_197163_1",
        "is_parent": True,
        "document_type": "ORIGINAL_RFP",
        "title": "Selection of Bus Operator for Procurement, Operation and Maintenance of 300 AC Fully Built Low Floor Pure Electric Buses under Gross Cost Contract (GCC) Model",
        "issuing_authority": "Delhi Transport Corporation (DTC)",
        "city": "New Delhi",
        "state": "Delhi",
        "original_bus_quantity": 300,
        "latest_bus_quantity": 300,
        "latest_quantity_source": "Original RFP",
        "submission_deadline": "2024-08-10T14:00:00+05:30",
        "emd_amount": 3000000.0,
        "document_fee": 10000.0,
        "source_url": "https://govtprocurement.delhi.gov.in"
    },
    "ctu_chandigarh_80_ebuses_gcc.pdf": {
        "tender_ref": "CTU/2024-25/GCC-80",
        "is_parent": True,
        "document_type": "ORIGINAL_RFP",
        "title": "E-Tender for Hiring of 80 MIDI Air-Conditioned Fully Built Pure Electric Buses including Bus Charging Stations on Kilometer Basis (Gross Cost Contract)",
        "issuing_authority": "Chandigarh Transport Undertaking (CTU)",
        "city": "Chandigarh",
        "state": "Chandigarh",
        "original_bus_quantity": 80,
        "latest_bus_quantity": 80,
        "latest_quantity_source": "Original RFP",
        "submission_deadline": "2025-05-20T15:00:00+05:30",
        "emd_amount": 1000000.0,
        "document_fee": 5000.0,
        "source_url": "https://etenders.chd.nic.in"
    },
    "aictsl_indore_50_ebuses_gcc.pdf": {
        "tender_ref": "AICTSL/2025/E-BUS/GCC-04",
        "is_parent": True,
        "document_type": "ORIGINAL_RFP",
        "title": "Selection of Bus Operator for Supply, Operation and Maintenance of 12-Meter Electric AC Buses on Gross Cost Contract (GCC) in Indore",
        "issuing_authority": "Atal Indore City Transport Services Limited (AICTSL)",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "original_bus_quantity": 50,
        "latest_bus_quantity": 50,
        "latest_quantity_source": "Original RFP",
        "submission_deadline": "2025-07-15T15:00:00+05:30",
        "emd_amount": 800000.0,
        "document_fee": 5000.0,
        "source_url": "https://mptenders.gov.in"
    },
    "ksrtc_kerala_wet_lease_buses.pdf": {
        "tender_ref": "KSRTC/56895916/2025",
        "is_parent": True,
        "document_type": "ORIGINAL_RFP",
        "title": "Hiring of AC Segment Buses (Diesel Fuelled) on Wet Lease (Seater, Sleeper and Seater cum Sleeper Class)",
        "issuing_authority": "Kerala State Road Transport Corporation (KSRTC)",
        "city": "Thiruvananthapuram",
        "state": "Kerala",
        "original_bus_quantity": 100,
        "latest_bus_quantity": 100,
        "latest_quantity_source": "Original RFP",
        "submission_deadline": "2025-09-10T15:00:00+05:30",
        "emd_amount": 1500000.0,
        "document_fee": 10000.0,
        "source_url": "https://etenders.kerala.gov.in"
    }
}


def run_ingestion_pipeline(job_id: str, custom_pdf_paths: Optional[List[str]] = None):
    db = SessionLocal()
    job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()

    if not job:
        logger.error(f"IngestionJob {job_id} not found.")
        db.close()
        return

    try:
        job.status = IngestionStatusEnum.RUNNING
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        log_action("INGESTION_STARTED", job_id=job_id, status="RUNNING")

        pdf_files = glob.glob(os.path.join(SEED_DATA_DIR, "*.pdf"))
        job.total_documents = len(pdf_files)
        db.commit()

        for pdf_path in pdf_files:
            file_name = os.path.basename(pdf_path)
            job.current_document = file_name
            db.commit()

            meta = CATALOG.get(file_name)
            if not meta:
                logger.warning(f"File {file_name} not in catalog. Skipping.")
                job.failed_documents += 1
                db.commit()
                continue

            try:
                parsed_doc = parse_pdf_document(pdf_path)

                # Parent-child resolution: Find or create parent Tender
                tender_ref = meta["tender_ref"]
                tender = db.query(Tender).filter(Tender.tender_ref == tender_ref).first()

                if not tender:
                    # Find parent metadata in CATALOG if this is a child document
                    parent_meta = meta
                    if not meta["is_parent"]:
                        # Find parent entry in CATALOG
                        for fname, mdata in CATALOG.items():
                            if mdata.get("tender_ref") == tender_ref and mdata.get("is_parent"):
                                parent_meta = mdata
                                break

                    deadline_dt = datetime.fromisoformat(parent_meta["submission_deadline"])
                    tender = Tender(
                        tender_ref=tender_ref,
                        title=parent_meta["title"],
                        issuing_authority=parent_meta["issuing_authority"],
                        city=parent_meta.get("city"),
                        state=parent_meta.get("state"),
                        category="bus_operations",
                        original_bus_quantity=parent_meta.get("original_bus_quantity"),
                        latest_bus_quantity=meta.get("latest_bus_quantity", parent_meta.get("latest_bus_quantity")),
                        latest_quantity_source=meta.get("latest_quantity_source", parent_meta.get("latest_quantity_source")),
                        submission_deadline=deadline_dt,
                        original_deadline=deadline_dt,
                        latest_deadline=deadline_dt,
                        latest_deadline_source=parent_meta.get("latest_quantity_source"),
                        timezone="Asia/Kolkata",
                        emd_amount=parent_meta.get("emd_amount"),
                        original_emd_amount=parent_meta.get("emd_amount"),
                        latest_emd_amount=parent_meta.get("emd_amount"),
                        document_fee=parent_meta.get("document_fee"),
                        scope_summary=parent_meta["title"],
                        source_url=parent_meta.get("source_url"),
                        source_name="Public Procurement Portal",
                        raw_document_path=pdf_path,
                        document_hash=parsed_doc["document_hash"],
                        extraction_provenance={
                            "bus_quantity": {
                                "original_value": parent_meta.get("original_bus_quantity"),
                                "latest_value": meta.get("latest_bus_quantity", parent_meta.get("latest_bus_quantity")),
                                "source_document": file_name,
                                "page_number": 1
                            },
                            "emd_amount": {
                                "value": parent_meta.get("emd_amount"),
                                "source_document": file_name,
                                "page_number": 1
                            }
                        }
                    )
                    db.add(tender)
                    db.flush()
                    logger.info(f"Created Parent Tender Opportunity: {tender_ref}")
                else:
                    # Update parent tender if amendment introduces a latest value
                    if "latest_bus_quantity" in meta and not meta["is_parent"]:
                        tender.latest_bus_quantity = meta["latest_bus_quantity"]
                        tender.latest_quantity_source = meta.get("latest_quantity_source", meta.get("amendment_number"))
                        if not tender.extraction_provenance:
                            tender.extraction_provenance = {}
                        tender.extraction_provenance["bus_quantity"] = {
                            "original_value": tender.original_bus_quantity,
                            "latest_value": meta["latest_bus_quantity"],
                            "source_document": file_name,
                            "amendment_number": meta.get("amendment_number"),
                            "page_number": 1
                        }
                        db.flush()
                        logger.info(f"Updated Parent Tender {tender_ref} with latest quantity {meta['latest_bus_quantity']} from {file_name}")

                # Create child Document record (linked to parent Tender)
                existing_doc = db.query(Document).filter(Document.document_hash == parsed_doc["document_hash"]).first()
                if existing_doc:
                    logger.info(f"Document {file_name} already exists. Skipping duplicate.")
                    job.completed_documents += 1
                    db.commit()
                    continue

                doc_record = Document(
                    tender_id=tender.id,
                    file_name=file_name,
                    document_type=meta["document_type"],
                    amendment_number=meta.get("amendment_number"),
                    source_url=meta.get("source_url"),
                    page_count=parsed_doc["page_count"],
                    document_hash=parsed_doc["document_hash"]
                )
                db.add(doc_record)
                db.flush()

                # Chunking & Embeddings (linking every chunk to parent Tender AND child Document)
                raw_chunks = chunk_document_pages(parsed_doc["pages"])
                chunk_texts = [c["chunk_text"] for c in raw_chunks]
                embeddings = generate_embeddings_batch(chunk_texts)

                for chunk_data, emb in zip(raw_chunks, embeddings):
                    db_chunk = DocumentChunk(
                        tender_id=tender.id,
                        document_id=doc_record.id,
                        chunk_text=chunk_data["chunk_text"],
                        page_number=chunk_data["page_number"],
                        chunk_index=chunk_data["chunk_index"],
                        embedding=emb,
                        chunk_metadata={
                            **chunk_data["chunk_metadata"],
                            "document_type": meta["document_type"],
                            "amendment_number": meta.get("amendment_number"),
                            "file_name": file_name
                        }
                    )
                    db.add(db_chunk)

                db.commit()
                job.completed_documents += 1
                db.commit()

                log_action("DOCUMENT_INGESTED", tender_id=str(tender.id), details={"file_name": file_name, "type": meta["document_type"]})

            except Exception as doc_err:
                logger.error(f"Error processing document {file_name}: {doc_err}")
                db.rollback()
                job.failed_documents += 1
                db.commit()

        job.status = IngestionStatusEnum.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        db.commit()

        log_action("INGESTION_COMPLETED", job_id=job_id, status="COMPLETED")

    except Exception as pipe_err:
        logger.error(f"Fatal error in ingestion pipeline job {job_id}: {pipe_err}")
        db.rollback()
        job.status = IngestionStatusEnum.FAILED
        job.error_message = str(pipe_err)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()
