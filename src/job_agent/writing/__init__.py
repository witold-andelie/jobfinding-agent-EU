"""Writer — non-fabricated cover letter + tailored CV variant (.docx) via DeepSeek."""

from job_agent.writing.cover_letter import generate_cover_letter, unsupported_claims
from job_agent.writing.cv_variant import (
    build_cv_docx,
    generate_cv_variant,
    rank_skills,
    tailored_summary,
)

__all__ = [
    "build_cv_docx",
    "generate_cover_letter",
    "generate_cv_variant",
    "rank_skills",
    "tailored_summary",
    "unsupported_claims",
]
