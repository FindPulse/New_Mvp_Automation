from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class FieldRule:
    canonical_name: str
    mapped_column: Optional[str] = None
    library_fallback_column: Optional[str] = None
    required: bool = True
    warning_only: bool = False


DEFAULT_WHEEL_RULES = [
    FieldRule("sku", mapped_column="clean_sku", required=True),
    FieldRule("price", library_fallback_column="library_retail_price", required=True),
    FieldRule("brand", library_fallback_column="library_brand", required=True),
    FieldRule("model", library_fallback_column="library_model", required=True),
    FieldRule("size", library_fallback_column="library_wheel_diameter", required=True),
    FieldRule("bolt_pattern", library_fallback_column="library_bolt_pattern", required=True),
    FieldRule("offset", library_fallback_column="library_offset", required=False, warning_only=True),
    FieldRule("bore", library_fallback_column="library_hub", required=False, warning_only=True),
    FieldRule("finish", library_fallback_column="library_finish", required=False, warning_only=True),
    FieldRule("image", library_fallback_column="library_image_url", required=False, warning_only=True),
]
