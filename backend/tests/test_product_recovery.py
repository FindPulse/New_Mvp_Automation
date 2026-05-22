import pandas as pd

from backend.app.models.schemas import ColumnMapping, MappingSuggestion
from backend.app.services.engines.enrichment.product_draft_builder import build_product_draft
from backend.app.services.engines.publishing.woocommerce_export_adapter import build_woocommerce_csv_dataframe
from backend.app.services.engines.validation.product_validation_engine import validate_product_draft
from backend.app.services.workflows.missing_product_recovery_workflow import run_missing_product_recovery_workflow


def test_product_draft_tracks_sources_and_validates_ready():
    row = pd.Series(
        {
            "clean_sku": "ABC-1",
            "Brand": "Vossen",
            "Model": "HF-5",
            "Size": "20 X 9",
            "PCD": "5 X 120",
            "Finish": "Satin Black",
            "Image": "https://example.com/img.jpg",
        }
    )
    mapping = {
        "brand": MappingSuggestion(canonical_field="brand", source_column="Brand", confidence=1.0),
        "model": MappingSuggestion(canonical_field="model", source_column="Model", confidence=1.0),
        "size": MappingSuggestion(canonical_field="size", source_column="Size", confidence=1.0),
        "bolt_pattern": MappingSuggestion(canonical_field="bolt_pattern", source_column="PCD", confidence=1.0),
        "finish": MappingSuggestion(canonical_field="finish", source_column="Finish", confidence=1.0),
        "image_url": MappingSuggestion(canonical_field="image_url", source_column="Image", confidence=1.0),
    }

    draft = validate_product_draft(build_product_draft("ABC-1", row, mapping))

    assert draft.fields["size"].value == "20x9"
    assert draft.fields["bolt_pattern"].value == "5x120"
    assert draft.fields["size"].source == "vendor_sheet_normalized"
    assert draft.validation_status == "Ready"


def test_recovery_workflow_builds_vendor_fallback_drafts_without_reference_lookup():
    vendor = pd.DataFrame(
        {
            "SKU": ["A", "B"],
            "Brand": ["Brand", "Brand"],
            "Model": ["Model", "Model"],
            "Size": ["20x9", "20x9"],
            "Bolt": ["5x120", "5x120"],
            "Finish": ["Black", "Black"],
            "Image": ["https://example.com/a.jpg", "https://example.com/b.jpg"],
        }
    )
    website = pd.DataFrame({"sku": ["A"]})
    result = run_missing_product_recovery_workflow(
        vendor,
        website,
        ColumnMapping(
            vendor_sku="SKU",
            website_sku="sku",
            brand="Brand",
            model="Model",
            size="Size",
            bolt_pattern="Bolt",
            finish="Finish",
            image="Image",
        ),
        enable_reference_lookup=False,
    )

    assert result.summary.missing_skus == 1
    assert result.product_drafts[0].sku == "B"
    assert result.product_drafts[0].validation_status == "Ready"


def test_woocommerce_export_uses_only_ready_or_approved_not_rejected():
    row = pd.Series(
        {
            "clean_sku": "ABC-1",
            "Brand": "Vossen",
            "Model": "HF-5",
            "Size": "20x9",
            "PCD": "5x120",
            "Finish": "Satin Black",
            "Image": "https://example.com/img.jpg",
        }
    )
    mapping = {
        "brand": MappingSuggestion(canonical_field="brand", source_column="Brand", confidence=1.0),
        "model": MappingSuggestion(canonical_field="model", source_column="Model", confidence=1.0),
        "size": MappingSuggestion(canonical_field="size", source_column="Size", confidence=1.0),
        "bolt_pattern": MappingSuggestion(canonical_field="bolt_pattern", source_column="PCD", confidence=1.0),
        "finish": MappingSuggestion(canonical_field="finish", source_column="Finish", confidence=1.0),
        "image_url": MappingSuggestion(canonical_field="image_url", source_column="Image", confidence=1.0),
    }
    draft = validate_product_draft(build_product_draft("ABC-1", row, mapping))

    export_df = build_woocommerce_csv_dataframe([draft])

    assert list(export_df["SKU"]) == ["ABC-1"]
    assert export_df.loc[0, "Published"] == 0
