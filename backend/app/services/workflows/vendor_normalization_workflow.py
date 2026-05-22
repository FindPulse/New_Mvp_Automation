from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from backend.app.models.schemas import MappingSuggestion, VendorNormalizationResult
from backend.app.services.engines.normalization.vendor_normalization_engine import (
    normalize_vendor_for_comparison,
)


@dataclass
class VendorNormalizationWorkflowOutput:
    normalized_df: pd.DataFrame
    result: VendorNormalizationResult


def run_vendor_normalization_workflow(
    vendor_df: pd.DataFrame,
    mapping: dict[str, MappingSuggestion] | None = None,
) -> VendorNormalizationWorkflowOutput:
    normalized_df, result = normalize_vendor_for_comparison(vendor_df, mapping=mapping)
    return VendorNormalizationWorkflowOutput(normalized_df=normalized_df, result=result)
