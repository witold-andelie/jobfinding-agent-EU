"""Embedders behind the seam (OpenAI-protocol) + similarity factory, offline."""

from job_agent.config import Settings
from job_agent.matching import (
    OpenAICompatibleEmbedder,
    SemanticSimilarity,
    build_embedder,
    default_similarity,
    lexical_similarity,
)
from job_agent.models.candidate import CandidateProfile
from job_agent.models.job import Job


class _FakeEmbeddings:
    @staticmethod
    def create(model, input):  # noqa: A002 - mirrors the OpenAI SDK signature
        # Return a deterministic vector per text so cosine is well-defined.
        vecs = [[float(len(t)), 1.0, 0.0] for t in input]
        data = [type("D", (), {"embedding": v})() for v in vecs]
        return type("R", (), {"data": data})()


class _FakeOpenAI:
    embeddings = _FakeEmbeddings()


def test_embedder_returns_one_vector_per_text() -> None:
    emb = OpenAICompatibleEmbedder(client=_FakeOpenAI())
    vectors = emb.embed(["hello", "world!!"])
    assert len(vectors) == 2 and len(vectors[0]) == 3


def test_semantic_similarity_uses_embedder() -> None:
    sim = SemanticSimilarity(OpenAICompatibleEmbedder(client=_FakeOpenAI()))
    cand = CandidateProfile(nationality="IN", field="x", skills=["y"])
    job = Job(source="s", external_id="1", title="t", company="c", country="DE")
    assert 0.0 <= sim(cand, job) <= 1.0


def test_build_embedder_none_when_unconfigured() -> None:
    s = Settings(embedding_api_key="", embedding_base_url="")
    assert build_embedder(s) is None
    # …and the similarity factory then falls back to offline lexical scoring.
    assert default_similarity(s) is lexical_similarity


def test_build_embedder_when_configured() -> None:
    # base_url alone is enough (local/ollama needs no key); construction shouldn't
    # require the network — only embed() does.
    s = Settings(embedding_base_url="http://localhost:11434/v1")
    embedder = build_embedder(s)
    assert embedder is None or isinstance(embedder, OpenAICompatibleEmbedder)


def test_semantic_similarity_degrades_on_embed_failure() -> None:
    class _BoomEmbedder:
        def embed(self, texts):
            raise RuntimeError("embedding endpoint down")

    sim = SemanticSimilarity(_BoomEmbedder())
    cand = CandidateProfile(nationality="IN", field="x", skills=["y"])
    job = Job(source="s", external_id="1", title="t", company="c", country="DE")
    assert sim(cand, job) == 0.0  # ranking continues, no crash
