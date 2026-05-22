from __future__ import annotations

import re

import pandas as pd

from backend.app.models.schemas import ProductDraft


def _value(draft: ProductDraft, field: str, default: str = "") -> str:
    tracked = draft.fields.get(field)
    if tracked is None or tracked.value is None:
        return default
    return str(tracked.value)


def _slug(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def draft_to_woocommerce_row(draft: ProductDraft) -> dict[str, object]:
    title = _value(draft, "title") or " ".join(
        part for part in [_value(draft, "brand"), _value(draft, "model"), _value(draft, "size")] if part
    )
    category = _value(draft, "category", draft.product_type)
    return {
        "Type": "simple",
        "SKU": draft.sku,
        "Name": title,
        "Published": 0,
        "Is featured?": 0,
        "Visibility in catalog": "visible",
        "Short description": _value(draft, "description"),
        "Description": _value(draft, "description"),
        "Regular price": _value(draft, "price"),
        "In stock?": 1 if _value(draft, "quantity") not in {"", "0"} else 0,
        "Stock": _value(draft, "quantity"),
        "Categories": category,
        "Images": _value(draft, "image_url"),
        "Attribute 1 name": "Brand",
        "Attribute 1 value(s)": _value(draft, "brand"),
        "Attribute 1 visible": 1,
        "Attribute 2 name": "Model",
        "Attribute 2 value(s)": _value(draft, "model"),
        "Attribute 2 visible": 1,
        "Attribute 3 name": "Size",
        "Attribute 3 value(s)": _value(draft, "size"),
        "Attribute 3 visible": 1,
        "Attribute 4 name": "Bolt Pattern",
        "Attribute 4 value(s)": _value(draft, "bolt_pattern"),
        "Attribute 4 visible": 1,
        "Attribute 5 name": "Finish",
        "Attribute 5 value(s)": _value(draft, "finish"),
        "Attribute 5 visible": 1,
        "Meta: source_confidence": draft.confidence_score,
        "Meta: recovery_validation": draft.validation_status,
        "Slug": _slug(title or draft.sku),
    }


def build_woocommerce_csv_dataframe(drafts: list[ProductDraft]) -> pd.DataFrame:
    approved_or_ready = [
        draft
        for draft in drafts
        if draft.approval_status == "Approved"
        or (draft.validation_status == "Ready" and draft.approval_status != "Rejected")
    ]
    return pd.DataFrame([draft_to_woocommerce_row(draft) for draft in approved_or_ready])
