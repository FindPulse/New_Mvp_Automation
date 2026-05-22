from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from backend.app.models.schemas import ColumnMapping, ComparisonSummary
from backend.app.services.engines.comparison.missing_sku_engine import compare_vendor_to_website
from backend.app.services.engines.enrichment.wheel_library_engine import (
    enrich_missing_skus_with_library,
    lookup_skus_in_wheel_library,
)
from backend.app.services.engines.export.csv_export_engine import CsvExportPackage, build_csv_exports
from backend.app.services.engines.summary.summary_engine import build_business_summary
from backend.app.services.engines.validation.validation_engine import validate_rows


@dataclass
class MissingSkuWorkflowOutput:
    final_missing_df: pd.DataFrame
    exports: CsvExportPackage
    summary: ComparisonSummary
    business_summary: str
    warnings: list[str] = field(default_factory=list)


def run_missing_sku_workflow(
    vendor_df: pd.DataFrame,
    website_df: pd.DataFrame,
    mapping: ColumnMapping,
    enable_wheel_library_lookup: bool = True,
    supabase_db_url: Optional[str] = None,
) -> MissingSkuWorkflowOutput:
    """End-to-end workflow used by Streamlit and FastAPI."""
    warnings: list[str] = []

    comparison = compare_vendor_to_website(
        vendor_df=vendor_df,
        website_df=website_df,
        vendor_sku_column=mapping.vendor_sku,
        website_sku_column=mapping.website_sku,
    )

    summary = comparison.summary

    if comparison.missing.empty:
        final_df = comparison.missing.copy()
        final_df["wheel_library_status"] = []
        final_df["suggested_action"] = []
        final_df["validation_status"] = []
        final_df["issue_reason"] = []
        final_df["validation_warnings"] = []
    else:
        if enable_wheel_library_lookup:
            try:
                library_matches_df = lookup_skus_in_wheel_library(
                    comparison.missing["clean_sku"].unique(),
                    db_url=supabase_db_url,
                )
                final_df = enrich_missing_skus_with_library(comparison.missing, library_matches_df)
            except Exception as exc:
                warnings.append(f"Wheel library lookup failed: {exc}")
                final_df = comparison.missing.copy()
                final_df["wheel_library_status"] = "Not Checked"
                final_df["suggested_action"] = "Needs review because library lookup failed"
        else:
            final_df = comparison.missing.copy()
            final_df["wheel_library_status"] = "Not Checked"
            final_df["suggested_action"] = "Needs review because library lookup is disabled"

        final_df = validate_rows(final_df, mapping=mapping)

    if not final_df.empty and "wheel_library_status" in final_df.columns:
        summary.missing_found_in_library = int(
            (final_df["wheel_library_status"] == "Found in Wheel Library").sum()
        )
        summary.missing_not_found_in_library = int(
            (final_df["wheel_library_status"] == "Not Found in Wheel Library").sum()
        )

    if not final_df.empty and "validation_status" in final_df.columns:
        summary.ready_rows = int((final_df["validation_status"] == "Ready").sum())
        summary.needs_review_rows = int((final_df["validation_status"] == "Needs Review").sum())

    exports = build_csv_exports(final_df, summary)
    business_summary = build_business_summary(summary)

    return MissingSkuWorkflowOutput(
        final_missing_df=final_df,
        exports=exports,
        summary=summary,
        business_summary=business_summary,
        warnings=warnings,
    )
