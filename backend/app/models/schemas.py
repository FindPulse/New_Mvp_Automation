from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class ComparisonSummary(BaseModel):
    vendor_skus: int = 0
    website_skus: int = 0
    matched_skus: int = 0
    missing_skus: int = 0
    vendor_duplicate_skus: int = 0
    website_duplicate_skus: int = 0
    missing_found_in_library: int = 0
    missing_not_found_in_library: int = 0
    ready_rows: int = 0
    needs_review_rows: int = 0


class ColumnMapping(BaseModel):
    vendor_sku: str
    website_sku: str = "sku"
    price: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    size: Optional[str] = None
    bolt_pattern: Optional[str] = None
    offset: Optional[str] = None
    bore: Optional[str] = None
    finish: Optional[str] = None
    image: Optional[str] = None


class MappingSuggestion(BaseModel):
    canonical_field: str
    source_column: Optional[str] = None
    confidence: float = 0.0
    reason: str = ""


FieldStatus = Literal["ok", "needs_review", "missing"]
ApprovalStatus = Literal["Pending", "Approved", "Rejected"]


class FieldValue(BaseModel):
    value: Any = None
    original_value: Any = None
    source: str = "unknown"
    confidence: float = 0.0
    status: FieldStatus = "needs_review"


class ProductDraft(BaseModel):
    sku: str
    product_type: str = "Wheels"
    fields: Dict[str, FieldValue] = Field(default_factory=dict)
    confidence_score: float = 0.0
    validation_status: str = "Needs Review"
    validation_notes: list[str] = Field(default_factory=list)
    approval_status: ApprovalStatus = "Pending"

    def flat_values(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "sku": self.sku,
            "product_type": self.product_type,
            "confidence_score": self.confidence_score,
            "validation_status": self.validation_status,
            "validation_notes": "; ".join(self.validation_notes),
            "approval_status": self.approval_status,
        }
        for field_name, tracked in self.fields.items():
            row[field_name] = tracked.value
        return row


class VendorNormalizationResult(BaseModel):
    mapping: Dict[str, MappingSuggestion] = Field(default_factory=dict)
    row_count: int = 0
    clean_sku_count: int = 0
    duplicate_sku_count: int = 0
    warnings: list[str] = Field(default_factory=list)


class WorkflowResult(BaseModel):
    summary: ComparisonSummary
    csv_files: Dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
