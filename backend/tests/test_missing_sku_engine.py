import pandas as pd

from backend.app.services.engines.comparison.missing_sku_engine import compare_vendor_to_website


def test_compare_vendor_to_website_finds_missing_skus():
    vendor = pd.DataFrame({"VendorSKU": ["A", "B", "C", "C"]})
    website = pd.DataFrame({"sku": ["A", "B"]})

    result = compare_vendor_to_website(vendor, website, "VendorSKU", "sku")

    assert result.summary.vendor_skus == 4
    assert result.summary.website_skus == 2
    assert result.summary.matched_skus == 2
    assert result.summary.missing_skus == 2
    assert result.summary.vendor_duplicate_skus == 1
    assert set(result.missing["clean_sku"]) == {"C"}
