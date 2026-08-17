from typing import List, Dict, Any, Optional
import os
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import Tender, DocumentChunk, Document
from app.services.embeddings import generate_embedding
from app.core.logging import log_action


def route_query_type(question: str) -> str:
    """Simple query router detecting SQL vs Vector intent."""
    q_lower = question.lower()
    date_keywords = ["close", "closing", "deadline", "next 15 days", "days remaining", "expire", "due date"]
    
    if any(k in q_lower for k in date_keywords):
        return "STRUCTURED_SQL"
    return "VECTOR_SEARCH"


def retrieve_relevant_context(
    db: Session,
    question: str,
    tender_id_filter: Optional[str] = None,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Hybrid retriever combining SQL date queries and pgvector cosine similarity search.
    """
    query_type = route_query_type(question)
    retrieved_context: List[Dict[str, Any]] = []

    if query_type == "STRUCTURED_SQL":
        # Deadline query logic: tenders closing in next 15 days
        now_dt = datetime.now(timezone.utc)
        future_dt = now_dt + timedelta(days=30)
        
        stmt = select(Tender).where(Tender.submission_deadline >= now_dt)
        if tender_id_filter:
            stmt = stmt.where(Tender.id == tender_id_filter)
        
        tenders = db.scalars(stmt.limit(top_k)).all()
        for t in tenders:
            dl = t.submission_deadline
            if dl.tzinfo is None:
                dl = dl.replace(tzinfo=timezone.utc)
            days_left = (dl - now_dt).days
            raw_fname = os.path.basename(t.raw_document_path) if t.raw_document_path else "RFP.pdf"
            retrieved_context.append({
                "tender_id": str(t.id),
                "tender_title": t.title,
                "document_name": raw_fname,
                "page_number": 1,
                "chunk_index": 0,
                "text": f"Tender Title: '{t.title}', Issuing Authority: '{t.issuing_authority}', State: '{t.state}'. Deadline: {t.submission_deadline.isoformat()} ({days_left} days remaining). EMD: INR {t.emd_amount}.",
                "similarity_score": 1.0
            })
    else:
        # Vector Similarity Search
        query_vector = generate_embedding(question)
        
        is_postgres = (db.bind.dialect.name == "postgresql") if db.bind else False

        if is_postgres:
            # cosine_distance returns a value in [0.0, 2.0] for normalized vectors;
            # similarity = 1.0 - cosine_distance gives [−1.0, 1.0], clamped to [0.0, 1.0]
            distance_col = DocumentChunk.embedding.cosine_distance(query_vector).label("cos_dist")

            stmt = select(DocumentChunk, Tender.title, Document.file_name, distance_col).join(
                Tender, DocumentChunk.tender_id == Tender.id
            ).join(
                Document, DocumentChunk.document_id == Document.id
            )

            if tender_id_filter:
                stmt = stmt.where(DocumentChunk.tender_id == tender_id_filter)

            stmt = stmt.order_by(distance_col).limit(top_k)
            results = db.execute(stmt).all()

            for row in results:
                chunk: DocumentChunk = row[0]
                title: str = row[1]
                file_name: str = row[2]
                cos_dist: float = float(row[3])
                similarity_score = round(max(0.0, 1.0 - cos_dist), 4)

                retrieved_context.append({
                    "tender_id": str(chunk.tender_id),
                    "tender_title": title,
                    "document_name": file_name,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.chunk_text,
                    "similarity_score": similarity_score
                })
        else:
            # High-performance cosine similarity computation for SQLite / standalone mode
            import numpy as np
            q_arr = np.array(query_vector, dtype=np.float32)
            q_norm = np.linalg.norm(q_arr)

            stmt = select(DocumentChunk, Tender.title, Document.file_name).join(
                Tender, DocumentChunk.tender_id == Tender.id
            ).join(
                Document, DocumentChunk.document_id == Document.id
            )
            if tender_id_filter:
                stmt = stmt.where(DocumentChunk.tender_id == tender_id_filter)

            rows = db.execute(stmt).all()
            scored_rows = []
            for row in rows:
                chunk, title, file_name = row[0], row[1], row[2]
                emb = chunk.embedding
                if isinstance(emb, list):
                    emb_arr = np.array(emb, dtype=np.float32)
                    denom = q_norm * np.linalg.norm(emb_arr)
                    sim = float(np.dot(q_arr, emb_arr) / denom) if denom > 0 else 0.0
                    scored_rows.append((sim, chunk, title, file_name))
            
            scored_rows.sort(key=lambda x: x[0], reverse=True)
            for sim, chunk, title, file_name in scored_rows[:top_k]:
                retrieved_context.append({
                    "tender_id": str(chunk.tender_id),
                    "tender_title": title,
                    "document_name": file_name,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.chunk_text,
                    "similarity_score": round(sim, 4)
                })

    log_action(
        "RAG_RETRIEVAL_COMPLETED",
        status="SUCCESS",
        details={
            "question": question[:50],
            "query_type": query_type,
            "retrieved_count": len(retrieved_context)
        }
    )

    return retrieved_context
