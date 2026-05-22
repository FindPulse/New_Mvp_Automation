import json
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from backend.app.services.engines.normalization.attribute_parser import (
    parse_wheel_attributes_from_text,
)


def clean_sku(value: Any) -> str:
    if pd.isna(value):
        return ""

    sku = str(value).strip().upper()
    sku = sku.replace("\u200b", "")
    sku = sku.replace("\xa0", "")
    sku = "".join(ch for ch in sku if ch.isprintable())
    sku = re.sub(r"\s+", "", sku)

    return sku


def clean_value(value: Any) -> Optional[str]:
    if pd.isna(value):
        return None

    text = str(value).strip()
    text = text.replace("\u200b", "")
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    if text == "":
        return None

    return text


def find_column(df: pd.DataFrame, possible_names: List[str]) -> Optional[str]:
    """
    Finds best matching column by exact lowercase match first,
    then partial match.
    """

    lower_to_original = {
        str(col).strip().lower(): col
        for col in df.columns
    }

    for name in possible_names:
        key = name.strip().lower()
        if key in lower_to_original:
            return lower_to_original[key]

    for col in df.columns:
        col_lower = str(col).strip().lower()

        for name in possible_names:
            name_lower = name.strip().lower()

            if name_lower in col_lower:
                return col

    return None


def auto_detect_vendor_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """
    Basic auto-mapping. Later we can improve this using Supabase reference values.
    """

    return {
        "sku": find_column(df, [
            "sku",
            "part #",
            "part no",
            "part number",
            "item no",
            "item number",
            "product sku",
            "variation sku",
            "manufacturer part number",
            "mpn",
        ]),
        "brand": find_column(df, [
            "brand",
            "vendor",
            "manufacturer",
            "make",
        ]),
        "model": find_column(df, [
            "model",
            "wheel model",
            "style",
            "series",
        ]),
        "title": find_column(df, [
            "name",
            "product name",
            "title",
            "description",
            "product title",
        ]),
        "size": find_column(df, [
            "size",
            "wheel size",
            "rim size",
            "diameter width",
        ]),
        "bolt_pattern": find_column(df, [
            "bolt pattern",
            "bolt_pattern",
            "pcd",
            "lug",
            "bolt circle",
        ]),
        "offset": find_column(df, [
            "offset",
            "et",
        ]),
        "center_bore": find_column(df, [
            "center bore",
            "centre bore",
            "bore",
            "hub",
            "hub bore",
            "cb",
        ]),
        "finish": find_column(df, [
            "finish",
            "color",
            "colour",
            "wheel finish",
        ]),
        "price": find_column(df, [
            "price",
            "regular price",
            "msrp",
            "retail",
            "cost",
        ]),
        "quantity": find_column(df, [
            "quantity",
            "qty",
            "stock",
            "inventory",
            "available",
            "on hand",
        ]),
        "image_url": find_column(df, [
            "image",
            "images",
            "image url",
            "image_url",
            "photo",
            "picture",
        ]),
        "description": find_column(df, [
            "description",
            "short description",
            "long description",
            "product description",
        ]),
    }


def get_row_value(row: pd.Series, column_name: Optional[str]) -> Optional[str]:
    if not column_name:
        return None

    if column_name not in row.index:
        return None

    return clean_value(row[column_name])


def make_field(
    value: Optional[str],
    source: str,
    confidence: float,
    status: str = "ok",
) -> Dict[str, Any]:
    return {
        "value": value,
        "source": source,
        "confidence": confidence,
        "status": status,
    }


def choose_field_value(
    explicit_value: Optional[str],
    parsed_value: Optional[str],
    field_name: str,
) -> Dict[str, Any]:
    """
    Explicit vendor column value gets priority.
    Parsed value from title/description is fallback.
    """

    if explicit_value:
        return make_field(
            value=explicit_value,
            source=f"vendor_sheet_column:{field_name}",
            confidence=0.95,
            status="ok",
        )

    if parsed_value:
        return make_field(
            value=parsed_value,
            source="vendor_text_parser",
            confidence=0.85,
            status="ok",
        )

    return make_field(
        value=None,
        source="not_found",
        confidence=0.0,
        status="missing",
    )


def build_text_blob(row: pd.Series, column_mapping: Dict[str, Optional[str]]) -> str:
    """
    Combine title, description, model, size, bolt pattern, finish etc.
    This gives parser more text to detect attributes from.
    """

    text_parts = []

    for field in [
        "title",
        "description",
        "model",
        "size",
        "bolt_pattern",
        "offset",
        "center_bore",
        "finish",
    ]:
        value = get_row_value(row, column_mapping.get(field))

        if value:
            text_parts.append(value)

    return " ".join(text_parts)


def validate_wheel_draft(fields: Dict[str, Dict[str, Any]]) -> Tuple[str, str]:
    """
    MVP validation only.
    Later we will move full validation to product_validation_engine.py
    """

    required_fields = [
        "sku",
        "size",
        "bolt_pattern",
        "finish",
    ]

    missing_fields = []

    for field in required_fields:
        value = fields.get(field, {}).get("value")

        if not value:
            missing_fields.append(field)

    if missing_fields:
        return (
            "Needs Review",
            "Missing required fields: " + ", ".join(missing_fields),
        )

    return "Ready", "Vendor sheet draft has required wheel fields."


def build_vendor_product_drafts(
    missing_df: pd.DataFrame,
    vendor_df: pd.DataFrame,
    vendor_sku_col: str,
    column_mapping: Optional[Dict[str, Optional[str]]] = None,
) -> pd.DataFrame:
    """
    Build product drafts from vendor sheet for SKUs not found in Supabase library.

    Input:
    - missing_df: missing SKUs dataframe. Should contain clean_sku if available.
    - vendor_df: original vendor dataframe.
    - vendor_sku_col: selected SKU column in vendor sheet.
    - column_mapping: optional manual mapping.
    """

    if missing_df is None or missing_df.empty:
        return pd.DataFrame()

    if vendor_df is None or vendor_df.empty:
        raise ValueError("Vendor data is empty.")

    if vendor_sku_col not in vendor_df.columns:
        raise ValueError(f"Vendor SKU column not found: {vendor_sku_col}")

    mapping = column_mapping or auto_detect_vendor_columns(vendor_df)

    vendor_work = vendor_df.copy()
    vendor_work["clean_sku"] = vendor_work[vendor_sku_col].apply(clean_sku)

    missing_work = missing_df.copy()

    if "clean_sku" not in missing_work.columns:
        if vendor_sku_col in missing_work.columns:
            missing_work["clean_sku"] = missing_work[vendor_sku_col].apply(clean_sku)
        else:
            raise ValueError("missing_df must contain clean_sku or vendor SKU column.")

    missing_skus = set(
        missing_work["clean_sku"]
        .dropna()
        .astype(str)
        .str.strip()
        .tolist()
    )

    vendor_missing_rows = vendor_work[
        vendor_work["clean_sku"].isin(missing_skus)
    ].copy()

    drafts = []

    for _, row in vendor_missing_rows.iterrows():
        text_blob = build_text_blob(row, mapping)
        parsed = parse_wheel_attributes_from_text(text_blob)

        sku_value = get_row_value(row, vendor_sku_col)

        brand_value = get_row_value(row, mapping.get("brand"))
        model_value = get_row_value(row, mapping.get("model"))
        title_value = get_row_value(row, mapping.get("title"))
        description_value = get_row_value(row, mapping.get("description"))
        price_value = get_row_value(row, mapping.get("price"))
        quantity_value = get_row_value(row, mapping.get("quantity"))
        image_value = get_row_value(row, mapping.get("image_url"))

        fields = {
            "sku": make_field(
                value=sku_value,
                source=f"vendor_sheet_column:{vendor_sku_col}",
                confidence=1.0 if sku_value else 0.0,
                status="ok" if sku_value else "missing",
            ),
            "brand": make_field(
                value=brand_value,
                source="vendor_sheet_column:brand" if brand_value else "not_found",
                confidence=0.90 if brand_value else 0.0,
                status="ok" if brand_value else "missing",
            ),
            "model": make_field(
                value=model_value,
                source="vendor_sheet_column:model" if model_value else "not_found",
                confidence=0.90 if model_value else 0.0,
                status="ok" if model_value else "missing",
            ),
            "title": make_field(
                value=title_value,
                source="vendor_sheet_column:title" if title_value else "generated_basic",
                confidence=0.80 if title_value else 0.40,
                status="ok" if title_value else "needs_review",
            ),
            "description": make_field(
                value=description_value,
                source="vendor_sheet_column:description" if description_value else "not_found",
                confidence=0.80 if description_value else 0.0,
                status="ok" if description_value else "missing",
            ),
            "size": choose_field_value(
                explicit_value=get_row_value(row, mapping.get("size")),
                parsed_value=parsed.get("size"),
                field_name="size",
            ),
            "wheel_diameter": make_field(
                value=parsed.get("wheel_diameter"),
                source="vendor_text_parser" if parsed.get("wheel_diameter") else "not_found",
                confidence=0.85 if parsed.get("wheel_diameter") else 0.0,
                status="ok" if parsed.get("wheel_diameter") else "missing",
            ),
            "wheel_width": make_field(
                value=parsed.get("wheel_width"),
                source="vendor_text_parser" if parsed.get("wheel_width") else "not_found",
                confidence=0.85 if parsed.get("wheel_width") else 0.0,
                status="ok" if parsed.get("wheel_width") else "missing",
            ),
            "bolt_pattern": choose_field_value(
                explicit_value=get_row_value(row, mapping.get("bolt_pattern")),
                parsed_value=parsed.get("bolt_pattern"),
                field_name="bolt_pattern",
            ),
            "offset": choose_field_value(
                explicit_value=get_row_value(row, mapping.get("offset")),
                parsed_value=parsed.get("offset"),
                field_name="offset",
            ),
            "center_bore": choose_field_value(
                explicit_value=get_row_value(row, mapping.get("center_bore")),
                parsed_value=parsed.get("center_bore"),
                field_name="center_bore",
            ),
            "finish": choose_field_value(
                explicit_value=get_row_value(row, mapping.get("finish")),
                parsed_value=parsed.get("finish"),
                field_name="finish",
            ),
            "price": make_field(
                value=price_value,
                source="vendor_sheet_column:price" if price_value else "not_found",
                confidence=0.90 if price_value else 0.0,
                status="ok" if price_value else "missing",
            ),
            "quantity": make_field(
                value=quantity_value,
                source="vendor_sheet_column:quantity" if quantity_value else "not_found",
                confidence=0.90 if quantity_value else 0.0,
                status="ok" if quantity_value else "missing",
            ),
            "image_url": make_field(
                value=image_value,
                source="vendor_sheet_column:image_url" if image_value else "not_found",
                confidence=0.80 if image_value else 0.0,
                status="ok" if image_value else "missing",
            ),
        }

        validation_status, validation_notes = validate_wheel_draft(fields)

        confidence_values = [
            field["confidence"]
            for field in fields.values()
            if field["value"]
        ]

        confidence_score = (
            sum(confidence_values) / len(confidence_values)
            if confidence_values
            else 0.0
        )

        draft = {
            "sku": fields["sku"]["value"],
            "clean_sku": clean_sku(fields["sku"]["value"]),
            "brand": fields["brand"]["value"],
            "model": fields["model"]["value"],
            "title": fields["title"]["value"],
            "description": fields["description"]["value"],
            "size": fields["size"]["value"],
            "wheel_diameter": fields["wheel_diameter"]["value"],
            "wheel_width": fields["wheel_width"]["value"],
            "bolt_pattern": fields["bolt_pattern"]["value"],
            "offset": fields["offset"]["value"],
            "center_bore": fields["center_bore"]["value"],
            "finish": fields["finish"]["value"],
            "price": fields["price"]["value"],
            "quantity": fields["quantity"]["value"],
            "image_url": fields["image_url"]["value"],
            "draft_source": "vendor_sheet",
            "confidence_score": round(confidence_score, 3),
            "validation_status": validation_status,
            "validation_notes": validation_notes,
            "field_sources_json": json.dumps(fields, ensure_ascii=False),
        }

        drafts.append(draft)

    return pd.DataFrame(drafts)