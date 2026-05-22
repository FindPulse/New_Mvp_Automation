import pandas as pd

from backend.app.models.schemas import ColumnMapping
from backend.app.services.engines.validation.validation_engine import validate_rows


def test_validation_marks_ready_when_library_fallback_fields_exist():
    df = pd.DataFrame(
        {
            "clean_sku": ["SKU1"],
            "library_retail_price": ["100"],
            "library_brand": ["Brand"],
            "library_model": ["Model"],
            "library_wheel_diameter": ["20"],
            "library_bolt_pattern": ["5x114.3"],
        }
    )
    result = validate_rows(df, ColumnMapping(vendor_sku="SKU"))
    assert result.loc[0, "validation_status"] == "Ready"


def test_validation_marks_needs_review_when_required_fields_missing():
    df = pd.DataFrame({"clean_sku": ["SKU1"]})
    result = validate_rows(df, ColumnMapping(vendor_sku="SKU"))
    assert result.loc[0, "validation_status"] == "Needs Review"
    assert "Missing price" in result.loc[0, "issue_reason"]
