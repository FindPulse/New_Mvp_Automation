from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from backend.app.models.schemas import MappingSuggestion


FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "sku": ("sku", "part #", "part#", "part no", "part number", "item no", "item number", "product code"),
    "brand": ("brand", "manufacturer", "vendor", "make"),
    "model": ("model", "style", "line", "design"),
    "size": ("size", "wheel size", "tire size", "rim size"),
    "wheel_diameter": ("diameter", "wheel diameter", "rim diameter", "dia"),
    "wheel_width": ("width", "wheel width", "rim width"),
    "bolt_pattern": ("bolt pattern", "bolt", "pcd", "lug", "bolt circle"),
    "offset": ("offset", "et"),
    "center_bore": ("center bore", "bore", "hub", "hub bore", "cb"),
    "finish": ("finish", "color", "colour"),
    "price": ("price", "cost", "msrp", "retail", "map"),
    "quantity": ("quantity", "qty", "qty avail", "available", "stock", "inventory"),
    "image_url": ("image", "image url", "picture", "photo"),
    "description": ("description", "desc", "long description"),
    "category": ("category", "product type", "type"),
    "mpn": ("mpn", "mfg part", "manufacturer part"),
    "vendor_part_no": ("vendor part", "vendor part no", "supplier part"),
}


@dataclass(frozen=True)
class ColumnScore:
    column: str
    score: float
    reason: str


def _normalize_header(value: object) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[_\-/]+", " ", text)
    return re.sub(r"\s+", " ", text)


def _sample_values(df: pd.DataFrame, column: str, limit: int = 25) -> list[str]:
    return [
        str(value).strip()
        for value in df[column].dropna().head(limit).tolist()
        if str(value).strip()
    ]


def _looks_like_sku(values: Iterable[str]) -> float:
    values = list(values)
    if not values:
        return 0.0
    hits = 0
    for value in values:
        compact = value.replace("-", "").replace("_", "").replace(" ", "")
        has_digit = any(ch.isdigit() for ch in compact)
        has_alpha = any(ch.isalpha() for ch in compact)
        reasonable_length = 3 <= len(compact) <= 40
        if reasonable_length and (has_digit or has_alpha):
            hits += 1
    return hits / len(values)


def score_column_for_field(df: pd.DataFrame, column: str, canonical_field: str) -> ColumnScore:
    header = _normalize_header(column)
    aliases = FIELD_ALIASES.get(canonical_field, ())

    exact_aliases = {_normalize_header(alias) for alias in aliases}
    if header in exact_aliases:
        return ColumnScore(column, 0.96, f"Header matches {canonical_field}")

    for alias in exact_aliases:
        if alias and alias in header:
            return ColumnScore(column, 0.86, f"Header contains {alias}")

    if canonical_field == "sku":
        sku_score = _looks_like_sku(_sample_values(df, column))
        if sku_score >= 0.8:
            return ColumnScore(column, 0.68, "Sample values look like SKUs")

    return ColumnScore(column, 0.0, "")


def auto_map_columns(df: pd.DataFrame, fields: Iterable[str] | None = None) -> dict[str, MappingSuggestion]:
    canonical_fields = list(fields or FIELD_ALIASES.keys())
    mapping: dict[str, MappingSuggestion] = {}

    for field in canonical_fields:
        scores = [score_column_for_field(df, column, field) for column in df.columns]
        scores = [score for score in scores if score.score > 0]
        if not scores:
            mapping[field] = MappingSuggestion(canonical_field=field, confidence=0.0, reason="No likely column")
            continue

        best = sorted(scores, key=lambda item: item.score, reverse=True)[0]
        mapping[field] = MappingSuggestion(
            canonical_field=field,
            source_column=best.column,
            confidence=round(best.score, 2),
            reason=best.reason,
        )

    return mapping
