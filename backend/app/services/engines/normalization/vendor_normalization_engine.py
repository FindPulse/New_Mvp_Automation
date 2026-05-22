from __future__ import annotations

import pandas as pd

from backend.app.models.schemas import MappingSuggestion, VendorNormalizationResult
from backend.app.services.engines.normalization.column_auto_mapper import auto_map_columns
from backend.app.services.engines.normalization.sku_normalizer import add_clean_sku_column, remove_blank_skus


def normalize_vendor_for_comparison(
    vendor_df: pd.DataFrame,
    mapping: dict[str, MappingSuggestion] | None = None,
) -> tuple[pd.DataFrame, VendorNormalizationResult]:
    """Phase B normalization: preserve raw data and add clean_sku only."""
    detected_mapping = mapping or auto_map_columns(vendor_df)
    sku_column = detected_mapping.get("sku", MappingSuggestion(canonical_field="sku")).source_column
    warnings: list[str] = []

    if not sku_column:
        raise ValueError("Could not detect a vendor SKU column. Please map it manually.")

    normalized = add_clean_sku_column(vendor_df.copy(), sku_column)
    clean = remove_blank_skus(normalized, "clean_sku")
    duplicate_count = int(clean["clean_sku"].duplicated().sum())
    if duplicate_count:
        warnings.append(f"{duplicate_count} duplicate normalized vendor SKUs detected.")

    result = VendorNormalizationResult(
        mapping=detected_mapping,
        row_count=int(len(vendor_df)),
        clean_sku_count=int(len(clean)),
        duplicate_sku_count=duplicate_count,
        warnings=warnings,
    )
    return normalized, result
