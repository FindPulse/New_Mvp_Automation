from __future__ import annotations

import pandas as pd

from backend.app.models.schemas import MappingSuggestion, ProductDraft
from backend.app.services.engines.enrichment.product_draft_builder import build_product_draft
from backend.app.services.engines.intelligence.catalog_reference_engine import (
    reference_row_to_fields,
)


def build_drafts_from_missing_rows(
    missing_df: pd.DataFrame,
    column_mapping: dict[str, MappingSuggestion],
    reference_matches_df: pd.DataFrame | None = None,
    product_type: str = "Wheels",
) -> list[ProductDraft]:
    reference_by_sku: dict[str, pd.Series] = {}
    if reference_matches_df is not None and not reference_matches_df.empty:
        for _, row in reference_matches_df.iterrows():
            if "clean_sku" in row.index and pd.notna(row["clean_sku"]):
                reference_by_sku[str(row["clean_sku"])] = row

    drafts: list[ProductDraft] = []
    for _, vendor_row in missing_df.iterrows():
        clean_sku = str(vendor_row["clean_sku"])
        reference_fields = {}
        if clean_sku in reference_by_sku:
            reference_fields = reference_row_to_fields(reference_by_sku[clean_sku])

        drafts.append(
            build_product_draft(
                clean_sku=clean_sku,
                vendor_row=vendor_row,
                column_mapping=column_mapping,
                reference_fields=reference_fields,
                product_type=product_type,
            )
        )

    return drafts
