from __future__ import annotations

from typing import Iterable, Optional

import pandas as pd

from backend.app.services.engines.enrichment.wheel_library_engine import lookup_skus_in_wheel_library


REFERENCE_FIELD_MAP = {
    "library_sku": "sku",
    "library_brand": "brand",
    "library_model": "model",
    "library_vendor_part_no": "vendor_part_no",
    "library_mpn": "mpn",
    "library_wheel_diameter": "wheel_diameter",
    "library_wheel_width": "wheel_width",
    "library_bolt_pattern": "bolt_pattern",
    "library_finish": "finish",
    "library_retail_price": "price",
    "library_hub": "center_bore",
    "library_offset": "offset",
    "library_image_url": "image_url",
}


def lookup_reference_products(clean_skus: Iterable[str], db_url: Optional[str] = None) -> pd.DataFrame:
    """Reference catalog lookup backed by the existing wheel library table."""
    return lookup_skus_in_wheel_library(clean_skus, db_url=db_url)


def reference_row_to_fields(row: pd.Series) -> dict[str, object]:
    fields: dict[str, object] = {}
    for source_column, canonical_field in REFERENCE_FIELD_MAP.items():
        if source_column in row.index and pd.notna(row[source_column]) and str(row[source_column]).strip():
            fields[canonical_field] = row[source_column]
    if fields:
        fields.setdefault("category", "Wheels")
    return fields
