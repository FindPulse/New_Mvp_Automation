import pandas as pd

from backend.app.services.engines.normalization.column_auto_mapper import auto_map_columns
from backend.app.services.workflows.vendor_normalization_workflow import run_vendor_normalization_workflow


def test_auto_map_columns_detects_sku_and_attributes():
    df = pd.DataFrame({"Part #": ["abc-1"], "Wheel Size": ["20 X 9"], "PCD": ["5 X 120"]})
    mapping = auto_map_columns(df)

    assert mapping["sku"].source_column == "Part #"
    assert mapping["size"].source_column == "Wheel Size"
    assert mapping["bolt_pattern"].source_column == "PCD"


def test_vendor_normalization_preserves_raw_and_adds_clean_sku():
    df = pd.DataFrame({"Part #": [" abc-1 ", "abc-1", None]})
    output = run_vendor_normalization_workflow(df)

    assert "Part #" in output.normalized_df.columns
    assert list(output.normalized_df["clean_sku"]) == ["ABC-1", "ABC-1", ""]
    assert output.result.duplicate_sku_count == 1
