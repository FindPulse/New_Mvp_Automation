from __future__ import annotations

from copy import deepcopy
from typing import Mapping

import pandas as pd

from backend.app.models.schemas import ProductDraft
from backend.app.services.engines.publishing.woocommerce_export_adapter import (
    build_woocommerce_csv_dataframe,
)


def apply_product_edits(drafts: list[ProductDraft], edits: Mapping[str, Mapping[str, object]]) -> list[ProductDraft]:
    updated = deepcopy(drafts)
    for draft in updated:
        sku_edits = edits.get(draft.sku, {})
        for field, value in sku_edits.items():
            if field in draft.fields:
                draft.fields[field].value = value
                draft.fields[field].source = "client_edit"
                draft.fields[field].confidence = 1.0
                draft.fields[field].status = "ok"
    return updated


def set_approval_status(
    drafts: list[ProductDraft],
    approved_skus: set[str],
    rejected_skus: set[str],
) -> list[ProductDraft]:
    updated = deepcopy(drafts)
    for draft in updated:
        if draft.sku in rejected_skus:
            draft.approval_status = "Rejected"
            draft.validation_status = "Rejected"
        elif draft.sku in approved_skus:
            draft.approval_status = "Approved"
    return updated


def build_approval_export(drafts: list[ProductDraft], platform: str = "woocommerce") -> pd.DataFrame:
    if platform.lower() != "woocommerce":
        raise ValueError("Only WooCommerce CSV export is implemented in the MVP.")
    return build_woocommerce_csv_dataframe(drafts)
