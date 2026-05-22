from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd

FINISH_ABBREVIATIONS = {
    "SB": "Satin Black",
    "GB": "Gloss Black",
    "MB": "Matte Black",
    "CH": "Chrome",
    "GM": "Gunmetal",
}


def is_blank(value: Any) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip().lower() in {"", "nan", "none", "null", "n/a", "na"}


def normalize_size(value: Any) -> str:
    if is_blank(value):
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"\s*[xX]\s*", "x", text)
    text = re.sub(r"\s+", "", text)
    return text


def normalize_bolt_pattern(value: Any) -> str:
    if is_blank(value):
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"\s*[xX]\s*", "x", text)
    text = text.replace(" ", "")
    return text


def normalize_decimal_text(value: Any) -> str:
    if is_blank(value):
        return ""
    text = re.sub(r"[^0-9.\-]", "", str(value))
    if text in {"", ".", "-"}:
        return ""
    try:
        number = Decimal(text)
    except InvalidOperation:
        return ""
    return format(number.normalize(), "f")


def normalize_quantity(value: Any) -> str:
    if is_blank(value):
        return ""
    match = re.search(r"-?\d+", str(value))
    return match.group(0) if match else ""


def normalize_finish(value: Any) -> tuple[str, float, str]:
    if is_blank(value):
        return "", 0.0, "missing"
    text = str(value).strip()
    key = text.upper().replace(".", "")
    if key in FINISH_ABBREVIATIONS:
        return FINISH_ABBREVIATIONS[key], 0.74, "abbreviation_expanded_needs_review"
    return re.sub(r"\s+", " ", text).title(), 0.9, "ok"


def normalize_attribute(field: str, value: Any) -> tuple[Any, float, str]:
    if field in {"size"}:
        normalized = normalize_size(value)
        return normalized, 0.92 if normalized else 0.0, "ok" if normalized else "missing"
    if field == "bolt_pattern":
        normalized = normalize_bolt_pattern(value)
        return normalized, 0.92 if normalized else 0.0, "ok" if normalized else "missing"
    if field in {"price", "wheel_diameter", "wheel_width", "offset", "center_bore"}:
        normalized = normalize_decimal_text(value)
        return normalized, 0.9 if normalized else 0.0, "ok" if normalized else "missing"
    if field == "quantity":
        normalized = normalize_quantity(value)
        return normalized, 0.9 if normalized else 0.0, "ok" if normalized else "missing"
    if field == "finish":
        return normalize_finish(value)
    if is_blank(value):
        return "", 0.0, "missing"
    return str(value).strip(), 0.88, "ok"
