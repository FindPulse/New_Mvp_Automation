from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from backend.app.models.schemas import ColumnMapping, ComparisonSummary, MappingSuggestion, ProductDraft
from backend.app.services.engines.comparison.missing_sku_engine import compare_vendor_to_website
from backend.app.services.engines.enrichment.enrichment_waterfall import build_drafts_from_missing_rows
from backend.app.services.engines.enrichment.product_draft_builder import drafts_to_dataframe
from backend.app.services.engines.export.csv_export_engine import CsvExportPackage, build_csv_exports
from backend.app.services.engines.intelligence.catalog_reference_engine import lookup_reference_products
from backend.app.services.engines.summary.summary_engine import build_business_summary
from backend.app.services.engines.validation.product_validation_engine import validate_product_drafts


@dataclass
class MissingProductRecoveryOutput:
    final_missing_df: pd.DataFrame
    product_drafts: list[ProductDraft]
    drafts_df: pd.DataFrame
    exports: CsvExportPackage
    summary: ComparisonSummary
    business_summary: str
    warnings: list[str] = field(default_factory=list)


def column_mapping_to_suggestions(mapping: ColumnMapping) -> dict[str, MappingSuggestion]:
    pairs = {
        "sku": mapping.vendor_sku,
        "brand": mapping.brand,
        "model": mapping.model,
        "size": mapping.size,
        "bolt_pattern": mapping.bolt_pattern,
        "offset": mapping.offset,
        "center_bore": mapping.bore,
        "finish": mapping.finish,
        "image_url": mapping.image,
        "price": mapping.price,
    }
    return {
        field: MappingSuggestion(
            canonical_field=field,
            source_column=column,
            confidence=1.0 if column else 0.0,
            reason="User-selected mapping" if column else "Not mapped",
        )
        for field, column in pairs.items()
    }


def run_missing_product_recovery_workflow(
    vendor_df: pd.DataFrame,
    website_df: pd.DataFrame,
    mapping: ColumnMapping,
    product_type: str = "Wheels",
    enable_reference_lookup: bool = True,
    supabase_db_url: Optional[str] = None,
) -> MissingProductRecoveryOutput:
    warnings: list[str] = []
    comparison = compare_vendor_to_website(
        vendor_df=vendor_df,
        website_df=website_df,
        vendor_sku_column=mapping.vendor_sku,
        website_sku_column=mapping.website_sku,
    )
    summary = comparison.summary

    reference_matches_df = pd.DataFrame()
    if enable_reference_lookup and not comparison.missing.empty:
        try:
            reference_matches_df = lookup_reference_products(
                comparison.missing["clean_sku"].unique(),
                db_url=supabase_db_url,
            )
        except Exception as exc:
            warnings.append(f"Reference catalog lookup failed: {exc}")

    draft_mapping = column_mapping_to_suggestions(mapping)
    drafts = build_drafts_from_missing_rows(
        comparison.missing,
        column_mapping=draft_mapping,
        reference_matches_df=reference_matches_df,
        product_type=product_type,
    )
    drafts = validate_product_drafts(drafts)
    drafts_df = drafts_to_dataframe(drafts)

    final_df = comparison.missing.copy()
    if not drafts_df.empty:
        status_df = drafts_df[["sku", "validation_status", "validation_notes", "confidence_score"]].rename(
            columns={"sku": "clean_sku"}
        )
        final_df = final_df.merge(status_df, on="clean_sku", how="left")
        final_df["issue_reason"] = final_df["validation_notes"]
        final_df["validation_warnings"] = ""
    else:
        final_df["validation_status"] = []
        final_df["issue_reason"] = []
        final_df["validation_warnings"] = []

    if not reference_matches_df.empty:
        found = set(reference_matches_df["clean_sku"].dropna().astype(str))
        summary.missing_found_in_library = int(final_df["clean_sku"].astype(str).isin(found).sum())
    summary.missing_not_found_in_library = int(summary.missing_skus - summary.missing_found_in_library)
    summary.ready_rows = int(sum(draft.validation_status == "Ready" for draft in drafts))
    summary.needs_review_rows = int(sum(draft.validation_status == "Needs Review" for draft in drafts))

    exports = build_csv_exports(final_df, summary)
    business_summary = build_business_summary(summary)

    return MissingProductRecoveryOutput(
        final_missing_df=final_df,
        product_drafts=drafts,
        drafts_df=drafts_df,
        exports=exports,
        summary=summary,
        business_summary=business_summary,
        warnings=warnings,
    )
