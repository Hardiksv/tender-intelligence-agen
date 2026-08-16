from typing import List
from sentence_transformers import SentenceTransformer
from app.core.config import settings
from app.core.logging import logger, log_action
from app.core.exceptions import EmbeddingDimensionMismatchException

# Singleton SentenceTransformer instance
_model_instance = None


def get_embedding_model() -> SentenceTransformer:
    global _model_instance
    if _model_instance is None:
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        _model_instance = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model_instance


def generate_embedding(text: str) -> List[float]:
    """
    Generates embedding vector for input text and validates vector dimension.
    """
    if not text or not text.strip():
        text = "empty"

    try:
        model = get_embedding_model()
        vector = model.encode(text, convert_to_numpy=True).tolist()
    except Exception as e:
        logger.warning(f"SentenceTransformer embedding load error: {e}. Using deterministic normalized embedding vector.")
        import hashlib
        h = hashlib.sha256(text.encode("utf-8")).digest()
        raw_vec = [(b / 255.0) * 2.0 - 1.0 for b in h]
        vector = (raw_vec * 12)[:settings.EMBEDDING_DIMENSION]

    # Dimension Validation Safeguard
    if len(vector) != settings.EMBEDDING_DIMENSION:
        raise EmbeddingDimensionMismatchException(
            f"Generated vector dimension ({len(vector)}) does not match configured EMBEDDING_DIMENSION ({settings.EMBEDDING_DIMENSION})."
        )

    return vector


def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Generates embedding vectors for a batch of texts."""
    if not texts:
        return []

    try:
        model = get_embedding_model()
        vectors = model.encode(texts, convert_to_numpy=True).tolist()
    except Exception as e:
        logger.warning(f"SentenceTransformer batch error: {e}. Using fallback embedding vectors.")
        vectors = [generate_embedding(t) for t in texts]

    for idx, vec in enumerate(vectors):
        if len(vec) != settings.EMBEDDING_DIMENSION:
            raise EmbeddingDimensionMismatchException(
                f"Vector at index {idx} dimension ({len(vec)}) does not match expected ({settings.EMBEDDING_DIMENSION})."
            )

    log_action(
        "EMBEDDING_CREATED",
        status="SUCCESS",
        details={"batch_size": len(texts), "dimension": settings.EMBEDDING_DIMENSION}
    )

    return vectors
