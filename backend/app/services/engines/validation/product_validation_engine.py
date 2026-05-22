from __future__ import annotations

import re

from backend.app.models.schemas import ProductDraft
from backend.app.services.engines.validation.platform_validation_rules import (
    TIRE_REQUIRED_FIELDS,
    WHEEL_REQUIRED_FIELDS,
)


SIZE_RE = re.compile(r"^\d{2,3}(?:\.\d+)?x\d{1,2}(?:\.\d+)?$", re.IGNORECASE)
BOLT_RE = re.compile(r"^\d+x\d+(?:\.\d+)?$", re.IGNORECASE)


def _field_value(draft: ProductDraft, field: str) -> object:
    tracked = draft.fields.get(field)
    return tracked.value if tracked else None


def _blank(value: object) -> bool:
    return value is None or str(value).strip() == ""


def validate_product_draft(draft: ProductDraft, min_confidence: float = 0.75) -> ProductDraft:
    notes: list[str] = []
    required = WHEEL_REQUIRED_FIELDS if draft.product_type == "Wheels" else TIRE_REQUIRED_FIELDS

    for field in required:
        if field == "size" and draft.product_type == "Wheels":
            has_size = not _blank(_field_value(draft, "size"))
            has_dimensions = not _blank(_field_value(draft, "wheel_diameter")) and not _blank(
                _field_value(draft, "wheel_width")
            )
            if not has_size and not has_dimensions:
                notes.append("Missing size or wheel diameter + width")
            continue
        if _blank(_field_value(draft, field)):
            notes.append(f"Missing {field}")

    size = _field_value(draft, "size")
    if not _blank(size) and draft.product_type == "Wheels" and not SIZE_RE.match(str(size)):
        notes.append("Invalid wheel size format")

    bolt_pattern = _field_value(draft, "bolt_pattern")
    if not _blank(bolt_pattern) and not BOLT_RE.match(str(bolt_pattern)):
        notes.append("Invalid bolt pattern format")

    for field, tracked in draft.fields.items():
        if tracked.confidence < min_confidence:
            notes.append(f"Low confidence {field}")
        if tracked.source == "llm_suggestion" and field in required:
            notes.append(f"AI-generated critical value: {field}")

    if _blank(_field_value(draft, "image_url")):
        notes.append("Missing image")

    draft.validation_notes = sorted(set(notes))
    draft.validation_status = "Needs Review" if draft.validation_notes else "Ready"
    return draft


def validate_product_drafts(drafts: list[ProductDraft], min_confidence: float = 0.75) -> list[ProductDraft]:
    return [validate_product_draft(draft, min_confidence=min_confidence) for draft in drafts]
