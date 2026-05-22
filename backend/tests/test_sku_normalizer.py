import pandas as pd

from backend.app.services.engines.normalization.sku_normalizer import add_clean_sku_column, clean_sku


def test_clean_sku_trims_uppercases_and_removes_hidden_chars():
    assert clean_sku("  abc-123\u200b ") == "ABC-123"


def test_add_clean_sku_column():
    df = pd.DataFrame({"SKU": [" a1 ", None, "b2"]})
    result = add_clean_sku_column(df, "SKU")
    assert list(result["clean_sku"]) == ["A1", "", "B2"]
