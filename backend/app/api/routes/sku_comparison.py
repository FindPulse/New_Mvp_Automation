from __future__ import annotations

import io

from fastapi import APIRouter, File, Form, UploadFile

from backend.app.models.schemas import ColumnMapping
from backend.app.services.io.file_reader import read_tabular_file
from backend.app.services.workflows.missing_sku_workflow import run_missing_sku_workflow

router = APIRouter(prefix="/v1/sku", tags=["sku"])


@router.post("/compare")
async def compare_skus(
    vendor_file: UploadFile = File(...),
    website_file: UploadFile = File(...),
    vendor_sku_column: str = Form(...),
    website_sku_column: str = Form("sku"),
    enable_wheel_library_lookup: bool = Form(False),
) -> dict:
    """API version of the missing SKU workflow.

    For now this returns JSON summary only. File download endpoints can be added after the UI stabilizes.
    """
    vendor_bytes = await vendor_file.read()
    website_bytes = await website_file.read()

    vendor_df = read_tabular_file(io.BytesIO(vendor_bytes), vendor_file.filename)
    website_df = read_tabular_file(io.BytesIO(website_bytes), website_file.filename)

    result = run_missing_sku_workflow(
        vendor_df=vendor_df,
        website_df=website_df,
        mapping=ColumnMapping(vendor_sku=vendor_sku_column, website_sku=website_sku_column),
        enable_wheel_library_lookup=enable_wheel_library_lookup,
    )

    return {
        "summary": result.summary.model_dump(),
        "business_summary": result.business_summary,
        "warnings": result.warnings,
    }
