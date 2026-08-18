import os
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.core.logging import logger, log_action
from app.llm.client import llm_client
from app.schemas.chat import ChatRequest, ChatResponse, Citation
from app.services.retrieval import retrieve_relevant_context

RAG_PROMPT_TEMPLATE = """You are a grounded Tender Intelligence AI assistant.
Answer the user's question strictly using ONLY the provided tender document context.
Always cite the specific tender title, issuing authority, and document facts from the context.
If the context does not contain sufficient details, state: 'I could not find sufficient evidence in the stored tender documents to answer this confidently.'

CONTEXT:
{context}

QUESTION:
{question}
"""


def load_rag_prompt() -> str:
    """Returns RAG prompt template."""
    return RAG_PROMPT_TEMPLATE


def answer_tender_question(db: Session, request: ChatRequest) -> ChatResponse:
    """
    RAG service answering user questions grounded strictly in retrieved vector/SQL chunks
    and returning metadata-backed citations. No synthetic or hallucinated answers.
    """
    try:
        context_chunks = retrieve_relevant_context(
            db=db,
            question=request.question,
            tender_id_filter=request.tender_id,
            top_k=5
        )
    except Exception as e:
        logger.warning(f"Error in retrieve_relevant_context: {e}")
        context_chunks = []

    if not context_chunks:
        return ChatResponse(
            question=request.question,
            answer="I could not find sufficient evidence in the stored tender documents to answer this confidently.",
            citations=[],
            model_used="none",
            usage={"model": "none", "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "is_estimated": True}
        )

    # Format context string
    formatted_context_list = []
    citations: List[Citation] = []

    for idx, item in enumerate(context_chunks, start=1):
        formatted_context_list.append(
            f"--- SOURCE [{idx}] ---\n"
            f"Tender Title: {item['tender_title']}\n"
            f"Document: {item['document_name']} (Page {item['page_number']})\n"
            f"Content: {item['text']}\n"
        )

        citations.append(Citation(
            tender_id=item["tender_id"],
            tender_title=item["tender_title"],
            document_name=item["document_name"],
            page_number=item["page_number"],
            chunk_index=item["chunk_index"],
            snippet=item["text"][:200] + "..." if len(item["text"]) > 200 else item["text"]
        ))

    context_str = "\n".join(formatted_context_list)
    prompt = RAG_PROMPT_TEMPLATE.replace("{context}", context_str).replace("{question}", request.question)

    try:
        # Call LLM for grounded completion over genuine retrieved context
        res = llm_client.generate(prompt=prompt, temperature=0.0)

        log_action(
            "RAG_QUERY",
            status="SUCCESS",
            details={
                "question": request.question[:40],
                "citations_count": len(citations),
                "model": res["model"]
            },
            extra_meta=res["usage"]
        )

        return ChatResponse(
            question=request.question,
            answer=res["content"],
            citations=citations,
            model_used=res["model"],
            usage=res["usage"]
        )
    except Exception as e:
        logger.error(f"RAG LLM synthesis error: {e}")
        return ChatResponse(
            question=request.question,
            answer=f"Unable to synthesize grounded answer due to LLM provider error ({str(e)}). Please ensure a valid LLM_API_KEY is configured.",
            citations=citations,
            model_used="error",
            usage={"model": "error", "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "is_estimated": True}
        )
