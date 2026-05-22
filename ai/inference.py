from __future__ import annotations

from backend.app.models.schemas import ComparisonSummary
from backend.app.services.engines.summary.summary_engine import build_business_summary


def summarize_run(summary: ComparisonSummary, use_openai: bool = False) -> str:
    """AI boundary.

    Current implementation returns deterministic summary. If OpenAI is added later, only pass calculated counts
    and issue summaries, never raw 50k-row files.
    """
    return build_business_summary(summary)
