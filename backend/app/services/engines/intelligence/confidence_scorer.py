from __future__ import annotations

from backend.app.models.schemas import ProductDraft


def product_confidence_score(draft: ProductDraft) -> float:
    values = [field.confidence for field in draft.fields.values() if field.value not in (None, "")]
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)
