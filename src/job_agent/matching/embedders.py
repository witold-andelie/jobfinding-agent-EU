"""Concrete embedders behind the ``Embedder`` seam (DeepSeek has no embeddings API).

``OpenAICompatibleEmbedder`` speaks the OpenAI embeddings protocol, so the same code
serves OpenAI (text-embedding-3-small), Jina, Voyage, or a LOCAL server (ollama /
text-embeddings-inference) just by changing ``embedding_base_url`` — including a
key-free local option. Lazy SDK import + DI client seam keep it offline-testable.
"""

from __future__ import annotations

from typing import Any

from job_agent.config import MissingCredentialsError, Settings, get_settings
from job_agent.matching.similarity import SemanticSimilarity, lexical_similarity
from job_agent.matching.shortlist import Similarity


class OpenAICompatibleEmbedder:
    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        _settings = settings if settings is not None else get_settings()
        self._model = _settings.embedding_model
        if client is not None:
            self._client = client
            return
        if not _settings.embedding_api_key and not _settings.embedding_base_url:
            raise MissingCredentialsError(
                "No embedding endpoint: set EMBEDDING_API_KEY (and EMBEDDING_BASE_URL "
                "for Jina/Voyage/local)."
            )
        from openai import OpenAI  # lazy import — package stays import-safe offline

        self._client = OpenAI(
            api_key=_settings.embedding_api_key or "not-needed",
            base_url=_settings.embedding_base_url or None,
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in resp.data]


def build_embedder(settings: Settings | None = None) -> OpenAICompatibleEmbedder | None:
    """Construct an embedder if one is configured, else ``None`` (→ lexical fallback)."""
    s = settings if settings is not None else get_settings()
    if not (s.embedding_api_key or s.embedding_base_url):
        return None
    try:
        return OpenAICompatibleEmbedder(s)
    except Exception:  # noqa: BLE001 - misconfig → fall back to lexical, never crash
        return None


def default_similarity(settings: Settings | None = None) -> Similarity:
    """Semantic similarity when an embedder is configured; offline lexical otherwise."""
    embedder = build_embedder(settings)
    return SemanticSimilarity(embedder) if embedder is not None else lexical_similarity
