from __future__ import annotations

import pandas as pd


def find_product_type_category(categories_df: pd.DataFrame, product_type: str):
    if categories_df is None or categories_df.empty:
        return None

    product_type_clean = product_type.strip().lower()
    if product_type_clean == "tires":
        possible_names = ["tires", "tire"]
    elif product_type_clean == "wheels":
        possible_names = ["wheels", "wheel"]
    else:
        possible_names = [product_type_clean]

    temp_df = categories_df.copy()
    temp_df["name_clean"] = temp_df["name"].astype(str).str.strip().str.lower()
    temp_df["slug_clean"] = temp_df["slug"].astype(str).str.strip().str.lower()

    matched = temp_df[
        temp_df["name_clean"].isin(possible_names) | temp_df["slug_clean"].isin(possible_names)
    ]
    return None if matched.empty else matched.iloc[0]


def get_brand_categories_for_product_type(categories_df: pd.DataFrame, product_type: str):
    product_type_row = find_product_type_category(categories_df, product_type)
    if product_type_row is None:
        return None, None

    parent_id = int(product_type_row["id"])
    brand_df = categories_df[categories_df["parent"] == parent_id].copy()
    if not brand_df.empty:
        brand_df = brand_df.sort_values(by=["count", "name"], ascending=[False, True])
    return brand_df, product_type_row
