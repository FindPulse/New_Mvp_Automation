from __future__ import annotations

import pandas as pd
import streamlit as st

from backend.app.services.workflows.vendor_normalization_workflow import (
    run_vendor_normalization_workflow,
)


def render_vendor_normalization_preview(vendor_df: pd.DataFrame) -> None:
    output = run_vendor_normalization_workflow(vendor_df)
    st.session_state.vendor_normalization = output

    st.subheader("Vendor Normalization Preview")
    st.write(
        f"Rows: {output.result.row_count:,} | Clean SKUs: {output.result.clean_sku_count:,} | "
        f"Duplicate clean SKUs: {output.result.duplicate_sku_count:,}"
    )

    mapping_rows = [
        {
            "field": field,
            "detected_column": suggestion.source_column,
            "confidence": suggestion.confidence,
            "reason": suggestion.reason,
        }
        for field, suggestion in output.result.mapping.items()
    ]
    st.dataframe(pd.DataFrame(mapping_rows), use_container_width=True)
    st.dataframe(output.normalized_df.head(50), use_container_width=True)

    for warning in output.result.warnings:
        st.warning(warning)
