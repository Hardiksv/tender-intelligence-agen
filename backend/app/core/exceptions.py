class TenderAgentException(Exception):
    """Base exception for Tender Intelligence Agent."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class IngestionException(TenderAgentException):
    """Raised when document ingestion fails."""
    pass


class ConcurrentIngestionException(TenderAgentException):
    """Raised when an ingestion job is already running (HTTP 409)."""
    pass


class ParsingException(TenderAgentException):
    """Raised when PDF parsing fails."""
    pass


class LanguageUnsupportedException(TenderAgentException):
    """Raised when document language is not predominantly English."""
    pass


class ExtractionException(TenderAgentException):
    """Raised when LLM structured extraction fails."""
    pass


class ScreeningException(TenderAgentException):
    """Raised during screening evaluation."""
    pass


class EmbeddingDimensionMismatchException(TenderAgentException):
    """Raised when embedding dimension does not match configured database dimension."""
    pass


class EmbeddingGenerationException(TenderAgentException):
    """Raised when no embedding provider (Jina, cloud LiteLLM, local SentenceTransformer)
    can produce a real vector for the given text. Deliberately NOT swallowed into a
    fake/hash-based vector — a silent fake vector would poison cosine-similarity search
    with meaningless "matches" and no error signal, which is worse than a loud failure."""
    pass


class RAGException(TenderAgentException):
    """Raised during RAG retrieval or context assembly."""
    pass