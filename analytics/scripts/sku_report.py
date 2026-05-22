from __future__ import annotations

import pandas as pd


def build_basic_sku_health_report(summary_csv_path: str) -> pd.DataFrame:
    """Load comparison_summary.csv for simple reporting."""
    return pd.read_csv(summary_csv_path)
