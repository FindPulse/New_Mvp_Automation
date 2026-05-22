from __future__ import annotations

import pandas as pd

from backend.app.models.schemas import ProductDraft


def build_shopify_csv_dataframe(_drafts: list[ProductDraft]) -> pd.DataFrame:
    """Deferred until WooCommerce CSV export is stable."""
    return pd.DataFrame()
