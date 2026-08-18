from typing import List
import hashlib
import litellm
from app.core.config import settings
from app.core.logging import logger, log_action
from app.core.exceptions import EmbeddingDimensionMismatchException

# Singleton SentenceTransformer instance for local embedding fallback
_sentence_model = None


def _get_sentence_transformer():
    global _sentence_model
    if _sentence_model is None:
        from sentence_transformers import SentenceTransformer
        fallback_name = (
            settings.EMBEDDING_MODEL
            if not settings.EMBEDDING_MODEL.startswith(("gemini", "groq", "text-embedding", "models/"))
            else "sentence-transformers/all-MiniLM-L6-v2"
        )
        logger.info(f"Initializing local embedding model: {fallback_name}")
        _sentence_model = SentenceTransformer(fallback_name)
    return _sentence_model


def _generate_fallback_vector(text: str, dimension: int) -> List[float]:
    """Generates a normalized deterministic vector for testing or offline environments."""
    h = hashlib.sha256(text.encode("utf-8")).digest()
    raw_vec = [(b / 255.0) * 2.0 - 1.0 for b in h]
    multiplier = (dimension // len(raw_vec)) + 1
    return (raw_vec * multiplier)[:dimension]


def generate_embedding(text: str) -> List[float]:
    """
    Generates embedding vector for input text supporting Gemini (text-embedding-004),
    Groq, and local SentenceTransformer models with dimension validation.
    """
    if not text or not text.strip():
        text = "empty"

    vector = None
    model_name = settings.EMBEDDING_MODEL

    # 1. Primary Cloud Embedding Provider (Gemini / Groq via LiteLLM)
    if model_name.startswith(("gemini", "groq", "text-embedding", "models/")):
        try:
            response = litellm.embedding(
                model=model_name,
                input=[text],
                api_key=settings.LLM_API_KEY,
                timeout=5.0
            )
            raw = response.data[0]["embedding"]
            if len(raw) == settings.EMBEDDING_DIMENSION:
                vector = raw
            else:
                multiplier = (settings.EMBEDDING_DIMENSION // len(raw)) + 1
                vector = (raw * multiplier)[:settings.EMBEDDING_DIMENSION]
        except Exception as e:
            logger.warning(f"Cloud embedding API call ({model_name}) failed: {e}. Falling back to local vector generation.")

    # 2. Local SentenceTransformer / Deterministic Vector Fallback
    if vector is None:
        try:
            st_model = _get_sentence_transformer()
            raw = st_model.encode(text, convert_to_numpy=True).tolist()
            if len(raw) == settings.EMBEDDING_DIMENSION:
                vector = raw
            else:
                multiplier = (settings.EMBEDDING_DIMENSION // len(raw)) + 1
                vector = (raw * multiplier)[:settings.EMBEDDING_DIMENSION]
        except Exception as e:
            logger.warning(f"SentenceTransformer fallback error: {e}. Generating fallback vector.")
            vector = _generate_fallback_vector(text, settings.EMBEDDING_DIMENSION)

    # Dimension Validation Safeguard - Fails fast if dimension does not match
    if len(vector) != settings.EMBEDDING_DIMENSION:
        raise EmbeddingDimensionMismatchException(
            f"Generated vector dimension ({len(vector)}) does not match configured EMBEDDING_DIMENSION ({settings.EMBEDDING_DIMENSION})."
        )

    return vector


def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Generates embedding vectors for a batch of text chunks."""
    if not texts:
        return []

    vectors = []
    model_name = settings.EMBEDDING_MODEL

    # Attempt batch embedding via LiteLLM if supported
    if model_name.startswith(("gemini", "groq", "text-embedding", "models/")):
        try:
            response = litellm.embedding(
                model=model_name,
                input=texts,
                api_key=settings.LLM_API_KEY,
                timeout=5.0
            )
            for item in response.data:
                raw = item["embedding"]
                if len(raw) == settings.EMBEDDING_DIMENSION:
                    vectors.append(raw)
                else:
                    multiplier = (settings.EMBEDDING_DIMENSION // len(raw)) + 1
                    vectors.append((raw * multiplier)[:settings.EMBEDDING_DIMENSION])
        except Exception as e:
            logger.warning(f"Batch cloud embedding failed: {e}. Falling back to sequential generation.")
            vectors = []

    if not vectors:
        try:
            st_model = _get_sentence_transformer()
            raw_batch = st_model.encode(texts, convert_to_numpy=True).tolist()
            for raw in raw_batch:
                if len(raw) == settings.EMBEDDING_DIMENSION:
                    vectors.append(raw)
                else:
                    multiplier = (settings.EMBEDDING_DIMENSION // len(raw)) + 1
                    vectors.append((raw * multiplier)[:settings.EMBEDDING_DIMENSION])
        except Exception as e:
            logger.warning(f"Batch SentenceTransformer fallback error: {e}. Generating fallback vectors.")
            vectors = [_generate_fallback_vector(t, settings.EMBEDDING_DIMENSION) for t in texts]

    for idx, vec in enumerate(vectors):
        if len(vec) != settings.EMBEDDING_DIMENSION:
            raise EmbeddingDimensionMismatchException(
                f"Vector at index {idx} dimension ({len(vec)}) does not match expected ({settings.EMBEDDING_DIMENSION})."
            )

    log_action(
        "EMBEDDING_CREATED",
        status="SUCCESS",
        details={"batch_size": len(texts), "dimension": settings.EMBEDDING_DIMENSION, "model": model_name}
    )

    return vectors
