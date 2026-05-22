from __future__ import annotations

from typing import Any

from backend.app.models.schemas import FieldValue


def tracked_field(
    value: Any,
    source: str,
    confidence: float,
    original_value: Any = None,
    status: str | None = None,
) -> FieldValue:
    field_status = status or ("ok" if value not in (None, "") and confidence >= 0.8 else "needs_review")
    return FieldValue(
        value=value,
        original_value=original_value if original_value is not None else value,
        source=source,
        confidence=round(float(confidence), 2),
        status=field_status,  # type: ignore[arg-type]
    )
