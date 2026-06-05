"""CV↔job relevance: offline lexical default + pluggable Embedder seam."""

from job_agent.matching import SemanticSimilarity, cosine, lexical_similarity, shortlist
from job_agent.models.candidate import CandidateProfile
from job_agent.models.job import Job


def _job(ext: str, title: str, desc: str = "") -> Job:
    return Job(source="s", external_id=ext, title=title, company="C", country="DE",
               description=desc)


def test_lexical_similarity_rewards_overlap() -> None:
    cand = CandidateProfile(nationality="FR", field="software", skills=["python", "kubernetes"])
    relevant = _job("1", "Python Backend Engineer", "Build services with python and kubernetes.")
    irrelevant = _job("2", "Pastry Chef", "Bake croissants in the morning.")
    assert lexical_similarity(cand, relevant) > lexical_similarity(cand, irrelevant)
    assert lexical_similarity(cand, irrelevant) == 0.0


def test_relevance_orders_within_feasibility_tier() -> None:
    # EU candidate => both jobs green; the more relevant one must rank first.
    cand = CandidateProfile(nationality="FR", field="data", skills=["python", "sql", "pandas"])
    jobs = [_job("chef", "Pastry Chef", "baking"),
            _job("data", "Data Analyst", "python sql pandas dashboards")]
    ranked = shortlist(cand, jobs)
    assert ranked[0].job.external_id == "data"
    assert ranked[0].similarity > 0


def test_semantic_similarity_with_fake_embedder() -> None:
    # Identical vectors => cosine 1.0; the seam works without any real provider.
    class _FakeEmbedder:
        def embed(self, texts: list[str]) -> list[list[float]]:
            return [[1.0, 0.0, 0.0] for _ in texts]

    sim = SemanticSimilarity(_FakeEmbedder())
    cand = CandidateProfile(nationality="IN", field="x", skills=["y"])
    assert sim(cand, _job("1", "anything")) == 1.0


def test_cosine_basic() -> None:
    assert cosine([1, 0], [1, 0]) == 1.0
    assert cosine([1, 0], [0, 1]) == 0.0
