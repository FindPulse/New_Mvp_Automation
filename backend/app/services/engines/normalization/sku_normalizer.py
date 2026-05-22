from __future__ import annotations

import re
from typing import Any

import pandas as pd

_HIDDEN_CHARS_RE = re.compile(r"[\u200B-\u200D\uFEFF]")


def clean_sku(value: Any) -> str:
    """Normalize SKU for matching while preserving the original SKU elsewhere.

    Matching rule:
    - blank/null becomes ""
    - trim
    - uppercase
    - remove hidden/non-printable characters
    - remove all internal whitespace
    """
    if pd.isna(value):
        return ""

    text = str(value).strip()
    text = _HIDDEN_CHARS_RE.sub("", text)
    text = "".join(ch for ch in text if ch.isprintable())
    text = re.sub(r"\s+", "", text)
    return text.upper().strip()


def add_clean_sku_column(
    df: pd.DataFrame,
    source_column: str,
    output_column: str = "clean_sku",
) -> pd.DataFrame:
    if source_column not in df.columns:
        raise KeyError(f"SKU column not found: {source_column}")

    result = df.copy()
    result[output_column] = result[source_column].apply(clean_sku)
    return result


def remove_blank_skus(df: pd.DataFrame, sku_column: str = "clean_sku") -> pd.DataFrame:
    if sku_column not in df.columns:
        raise KeyError(f"Clean SKU column not found: {sku_column}")
    return df[df[sku_column] != ""].copy()
