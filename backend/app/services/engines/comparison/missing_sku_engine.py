from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from backend.app.models.schemas import ComparisonSummary
from backend.app.services.engines.normalization.sku_normalizer import clean_sku


@dataclass
class SkuComparisonResult:
    missing: pd.DataFrame
    matched: pd.DataFrame
    vendor_clean: pd.DataFrame
    website_clean: pd.DataFrame
    duplicate_vendor: pd.DataFrame
    duplicate_website: pd.DataFrame
    summary: ComparisonSummary


def _require_column(df: pd.DataFrame, column: str, label: str) -> None:
    if column not in df.columns:
        raise ValueError(f"{label} SKU column not found: {column}")


def compare_vendor_to_website(
    vendor_df: pd.DataFrame,
    website_df: pd.DataFrame,
    vendor_sku_column: str,
    website_sku_column: str = "sku",
) -> SkuComparisonResult:
    """Compare vendor SKUs against website/platform SKUs using clean_sku.

    Raw SKU values remain untouched. The comparison only uses the generated
    clean_sku column.
    """
    if vendor_df is None or vendor_df.empty:
        raise ValueError("Vendor data is empty.")
    if website_df is None or website_df.empty:
        raise ValueError("Website/platform SKU data is empty.")

    _require_column(vendor_df, vendor_sku_column, "Vendor")
    _require_column(website_df, website_sku_column, "Website/platform")

    vendor_work = vendor_df.copy()
    website_work = website_df.copy()

    vendor_work["original_vendor_sku"] = vendor_work[vendor_sku_column]
    website_work["original_website_sku"] = website_work[website_sku_column]

    vendor_work["clean_sku"] = vendor_work[vendor_sku_column].apply(clean_sku)
    website_work["clean_sku"] = website_work[website_sku_column].apply(clean_sku)

    vendor_clean = vendor_work[vendor_work["clean_sku"] != ""].copy()
    website_clean = website_work[website_work["clean_sku"] != ""].copy()

    website_sku_set = set(website_clean["clean_sku"].dropna().astype(str).tolist())
    vendor_clean["is_on_website"] = vendor_clean["clean_sku"].isin(website_sku_set)
    vendor_clean["is_on_platform"] = vendor_clean["is_on_website"]

    matched = vendor_clean[vendor_clean["is_on_website"]].copy()
    missing = vendor_clean[~vendor_clean["is_on_website"]].copy()

    duplicate_vendor = vendor_clean[vendor_clean["clean_sku"].duplicated(keep=False)].copy()
    duplicate_website = website_clean[website_clean["clean_sku"].duplicated(keep=False)].copy()

    summary = ComparisonSummary(
        vendor_skus=int(len(vendor_clean)),
        website_skus=int(len(website_clean)),
        matched_skus=int(len(matched)),
        missing_skus=int(len(missing)),
        vendor_duplicate_skus=int(vendor_clean["clean_sku"].duplicated().sum()),
        website_duplicate_skus=int(website_clean["clean_sku"].duplicated().sum()),
    )

    return SkuComparisonResult(
        missing=missing,
        matched=matched,
        vendor_clean=vendor_clean,
        website_clean=website_clean,
        duplicate_vendor=duplicate_vendor,
        duplicate_website=duplicate_website,
        summary=summary,
    )


def compare_vendor_vs_platform_skus(
    vendor_df: pd.DataFrame,
    platform_df: pd.DataFrame,
    vendor_sku_col: str,
    platform_sku_col: str = "sku",
) -> dict[str, object]:
    """Backward-compatible wrapper for older Streamlit code."""
    result = compare_vendor_to_website(
        vendor_df=vendor_df,
        website_df=platform_df,
        vendor_sku_column=vendor_sku_col,
        website_sku_column=platform_sku_col,
    )
    return {
        "summary": result.summary.model_dump(),
        "missing_df": result.missing,
        "matched_df": result.matched,
        "vendor_clean_df": result.vendor_clean,
        "platform_clean_df": result.website_clean,
        "duplicate_vendor_df": result.duplicate_vendor,
        "duplicate_platform_df": result.duplicate_website,
    }


# Alias used by a few older snippets.
normalize_sku = clean_sku
