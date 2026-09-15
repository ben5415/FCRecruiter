"""Football knowledge ingestion and pgvector retrieval."""

from agent_service.app.config import get_agent_settings
from agent_service.app.knowledge.embeddings import (
    LocalSentenceTransformerEmbeddingAdapter,
    OllamaEmbeddingAdapter,
    OpenAICompatibleEmbeddingAdapter,
)
from agent_service.app.knowledge.models import EMBEDDING_DIMENSIONS
from agent_service.app.knowledge.service import KnowledgeService
from agent_service.app.shared.database import get_agent_session_factory


def build_knowledge_service_from_settings() -> KnowledgeService:
    settings = get_agent_settings()
    if settings.embedding_dimensions != EMBEDDING_DIMENSIONS:
        raise RuntimeError(
            f"EMBEDDING_DIMENSIONS must be {EMBEDDING_DIMENSIONS} for the current database schema"
        )
    if settings.embedding_backend == "ollama":
        embeddings = OllamaEmbeddingAdapter(
            base_url=settings.ollama_base_url,
            model=settings.ollama_embedding_model,
            dimensions=settings.embedding_dimensions,
            timeout_seconds=settings.embedding_timeout_seconds,
        )
    elif settings.embedding_backend == "local":
        embeddings = LocalSentenceTransformerEmbeddingAdapter(
            model_name=settings.local_embedding_model,
            dimensions=settings.embedding_dimensions,
            device=settings.local_embedding_device,
        )
    elif settings.embedding_backend == "http":
        if not settings.embedding_api_url or not settings.embedding_api_key or not settings.embedding_model:
            raise RuntimeError(
                "HTTP embeddings require EMBEDDING_API_URL, EMBEDDING_API_KEY and EMBEDDING_MODEL"
            )
        embeddings = OpenAICompatibleEmbeddingAdapter(
            api_url=settings.embedding_api_url,
            api_key=settings.embedding_api_key,
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
            timeout_seconds=settings.embedding_timeout_seconds,
        )
    else:
        raise RuntimeError("EMBEDDING_BACKEND must be 'ollama', 'local' or 'http'")
    return KnowledgeService(
        session_factory=get_agent_session_factory(),
        embeddings=embeddings,
        chunk_size=settings.knowledge_chunk_size,
        chunk_overlap=settings.knowledge_chunk_overlap,
    )


__all__ = ["KnowledgeService", "build_knowledge_service_from_settings"]
