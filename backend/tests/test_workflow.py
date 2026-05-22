import pandas as pd

from backend.app.models.schemas import ColumnMapping
from backend.app.services.workflows.missing_sku_workflow import run_missing_sku_workflow


def test_workflow_without_library_lookup_generates_exports():
    vendor = pd.DataFrame({"SKU": ["A", "B"], "Brand": ["X", "Y"]})
    website = pd.DataFrame({"sku": ["A"]})

    result = run_missing_sku_workflow(
        vendor,
        website,
        ColumnMapping(vendor_sku="SKU", website_sku="sku", brand="Brand"),
        enable_wheel_library_lookup=False,
    )

    assert result.summary.missing_skus == 1
    csvs = result.exports.as_csv_text()
    assert "ready_to_upload.csv" in csvs
    assert "needs_review.csv" in csvs
    assert "comparison_summary.csv" in csvs
