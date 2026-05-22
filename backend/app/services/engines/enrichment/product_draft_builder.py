from __future__ import annotations

from typing import Mapping

import pandas as pd

from backend.app.models.schemas import MappingSuggestion, ProductDraft
from backend.app.services.engines.intelligence.confidence_scorer import product_confidence_score
from backend.app.services.engines.intelligence.field_source_tracker import tracked_field
from backend.app.services.engines.normalization.attribute_normalizer import normalize_attribute


COMMON_FIELDS = [
    "sku",
    "brand",
    "model",
    "title",
    "description",
    "price",
    "quantity",
    "image_url",
    "category",
]

WHEEL_FIELDS = [
    "size",
    "wheel_diameter",
    "wheel_width",
    "bolt_pattern",
    "offset",
    "center_bore",
    "finish",
    "load_rating",
    "vendor_part_no",
    "mpn",
]


def _not_blank(value: object) -> bool:
    return pd.notna(value) and str(value).strip() != ""


def build_product_draft(
    clean_sku: str,
    vendor_row: pd.Series,
    column_mapping: Mapping[str, MappingSuggestion],
    reference_fields: Mapping[str, object] | None = None,
    product_type: str = "Wheels",
) -> ProductDraft:
    fields = {"sku": tracked_field(clean_sku, "vendor_sheet_normalized", 1.0, clean_sku, "ok")}
    reference_fields = reference_fields or {}

    for field in COMMON_FIELDS + WHEEL_FIELDS:
        if field == "sku":
            continue

        if field in reference_fields and _not_blank(reference_fields[field]):
            fields[field] = tracked_field(reference_fields[field], "reference_catalog", 0.94)
            continue

        suggestion = column_mapping.get(field)
        source_column = suggestion.source_column if suggestion else None
        if source_column and source_column in vendor_row.index and _not_blank(vendor_row[source_column]):
            original = vendor_row[source_column]
            normalized, confidence, status = normalize_attribute(field, original)
            source = "vendor_sheet_normalized" if normalized != original else "vendor_sheet"
            fields[field] = tracked_field(normalized, source, confidence, original, "ok" if status == "ok" else "needs_review")

    if "category" not in fields:
        fields["category"] = tracked_field(product_type, "system_default", 0.82, product_type, "ok")

    if "title" not in fields and all(key in fields for key in ("brand", "model", "size")):
        title = f"{fields['brand'].value} {fields['model'].value} {fields['size'].value}".strip()
        fields["title"] = tracked_field(title, "deterministic_rule", 0.82, title, "ok")

    draft = ProductDraft(sku=clean_sku, product_type=product_type, fields=fields)  # type: ignore[arg-type]
    draft.confidence_score = product_confidence_score(draft)
    return draft


def drafts_to_dataframe(drafts: list[ProductDraft], include_sources: bool = True) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for draft in drafts:
        row = draft.flat_values()
        if include_sources:
            for field, tracked in draft.fields.items():
                row[f"{field}_source"] = tracked.source
                row[f"{field}_confidence"] = tracked.confidence
                row[f"{field}_status"] = tracked.status
        rows.append(row)
    return pd.DataFrame(rows)
