from __future__ import annotations

from typing import Iterable, Optional

import pandas as pd

from backend.app.db.postgres import get_postgres_connection

LIBRARY_COLUMNS = [
    "clean_sku",
    "library_sku",
    "library_brand",
    "library_model",
    "library_vendor_part_no",
    "library_mpn",
    "library_wheel_diameter",
    "library_wheel_width",
    "library_bolt_pattern",
    "library_finish",
    "library_retail_price",
    "library_hub",
    "library_offset",
    "library_image_url",
]


def empty_library_matches() -> pd.DataFrame:
    return pd.DataFrame(columns=LIBRARY_COLUMNS)


def lookup_skus_in_wheel_library(
    clean_skus: Iterable[str],
    db_url: Optional[str] = None,
    chunk_size: int = 5000,
) -> pd.DataFrame:
    """Check clean SKUs against public.wheel_library_raw.

    This is the modular version of the original lookup_skus_in_wheel_library function.
    """
    sku_list: list[str] = []
    seen: set[str] = set()

    for sku in clean_skus:
        if pd.isna(sku):
            continue
        sku_text = str(sku).strip().upper()
        if sku_text and sku_text not in seen:
            seen.add(sku_text)
            sku_list.append(sku_text)

    if not sku_list:
        return empty_library_matches()

    query = """
        SELECT DISTINCT ON (sku_clean)
            sku_clean,
            sku AS library_sku,
            brand AS library_brand,
            model AS library_model,
            vendor_part_no AS library_vendor_part_no,
            mpn AS library_mpn,
            wheel_diameter AS library_wheel_diameter,
            wheel_width AS library_wheel_width,
            bolt_pattern AS library_bolt_pattern,
            finish AS library_finish,
            retail_price AS library_retail_price,
            hub AS library_hub,
            simpleoffset AS library_offset,
            image_url AS library_image_url
        FROM public.wheel_library_raw
        WHERE sku_clean = ANY(%s)
        ORDER BY sku_clean, db_row_id;
    """

    rows: list[dict[str, object]] = []

    with get_postgres_connection(db_url) as conn:
        with conn.cursor() as cur:
            for start in range(0, len(sku_list), chunk_size):
                chunk = sku_list[start: start + chunk_size]
                cur.execute(query, (chunk,))
                for row in cur.fetchall():
                    rows.append(dict(zip(LIBRARY_COLUMNS, row)))

    return pd.DataFrame(rows, columns=LIBRARY_COLUMNS)


def enrich_missing_skus_with_library(
    missing_df: pd.DataFrame,
    library_matches_df: pd.DataFrame | None,
) -> pd.DataFrame:
    if library_matches_df is None or library_matches_df.empty:
        library_matches_df = empty_library_matches()

    result = missing_df.merge(library_matches_df, on="clean_sku", how="left")
    result["wheel_library_status"] = result["library_sku"].apply(
        lambda value: "Found in Wheel Library"
        if pd.notna(value) and str(value).strip() != ""
        else "Not Found in Wheel Library"
    )
    result["suggested_action"] = result["wheel_library_status"].apply(
        lambda status: "Can prepare import from wheel library"
        if status == "Found in Wheel Library"
        else "Needs manual review / not in master library"
    )
    return result
