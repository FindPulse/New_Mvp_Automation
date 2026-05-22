from __future__ import annotations

from backend.app.models.schemas import ComparisonSummary


def build_business_summary(summary: ComparisonSummary) -> str:
    """Deterministic summary first. AI can be layered later without controlling the result."""
    if summary.missing_skus == 0:
        return (
            "No missing SKUs were found. Vendor and website SKU lists are aligned for this run."
        )

    return (
        f"The run checked {summary.vendor_skus:,} vendor SKUs against "
        f"{summary.website_skus:,} website SKUs. "
        f"It found {summary.missing_skus:,} missing SKUs. "
        f"{summary.missing_found_in_library:,} missing SKUs were found in the wheel library and "
        f"{summary.missing_not_found_in_library:,} were not found in the wheel library. "
        f"After validation, {summary.ready_rows:,} rows are Ready and "
        f"{summary.needs_review_rows:,} rows need review."
    )
