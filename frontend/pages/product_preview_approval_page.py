from __future__ import annotations

import pandas as pd
import streamlit as st

from backend.app.models.schemas import ProductDraft
from backend.app.services.workflows.product_approval_workflow import (
    apply_product_edits,
    build_approval_export,
    set_approval_status,
)


EDITABLE_FIELDS = [
    "brand",
    "model",
    "title",
    "description",
    "price",
    "quantity",
    "image_url",
    "category",
    "size",
    "wheel_diameter",
    "wheel_width",
    "bolt_pattern",
    "offset",
    "center_bore",
    "finish",
]


def render_product_preview_approval(drafts: list[ProductDraft]) -> list[ProductDraft]:
    st.subheader("Product Recovery Preview")
    if not drafts:
        st.info("No product drafts yet.")
        return drafts

    rows = []
    for draft in drafts:
        row = draft.flat_values()
        rows.append({field: row.get(field, "") for field in ["sku", *EDITABLE_FIELDS, "validation_status", "validation_notes"]})

    edited_df = st.data_editor(pd.DataFrame(rows), use_container_width=True, num_rows="fixed")
    edits = {
        str(row["sku"]): {field: row.get(field, "") for field in EDITABLE_FIELDS if field in edited_df.columns}
        for _, row in edited_df.iterrows()
    }

    edited_drafts = apply_product_edits(drafts, edits)

    sku_options = [draft.sku for draft in edited_drafts]
    col1, col2 = st.columns(2)
    with col1:
        approved = set(st.multiselect("Approve SKUs for export", sku_options))
    with col2:
        rejected = set(st.multiselect("Reject SKUs", sku_options))

    approved_drafts = set_approval_status(edited_drafts, approved, rejected)
    woo_df = build_approval_export(approved_drafts, platform="woocommerce")
    st.download_button(
        "Download WooCommerce CSV",
        data=woo_df.to_csv(index=False).encode("utf-8"),
        file_name="ready_to_upload_woocommerce.csv",
        mime="text/csv",
        disabled=woo_df.empty,
    )
    return approved_drafts
