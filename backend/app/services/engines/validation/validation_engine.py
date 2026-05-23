from __future__ import annotations

from typing import Iterable

import pandas as pd

from backend.app.models.schemas import ColumnMapping
from backend.app.services.engines.validation.rules import DEFAULT_WHEEL_RULES, FieldRule


EMPTY_MARKERS = {"", "nan", "none", "null", "n/a", "na"}


def is_blank(value: object) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip().lower() in EMPTY_MARKERS


def _resolve_column(row: pd.Series, rule: FieldRule, mapping: ColumnMapping) -> tuple[str | None, object | None]:
    mapped_column = getattr(mapping, rule.canonical_name, None) or rule.mapped_column

    if mapped_column and mapped_column in row.index and not is_blank(row[mapped_column]):
        return mapped_column, row[mapped_column]

    if rule.library_fallback_column and rule.library_fallback_column in row.index:
        return rule.library_fallback_column, row[rule.library_fallback_column]

    return mapped_column or rule.library_fallback_column, None


def validate_rows(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    rules: Iterable[FieldRule] = DEFAULT_WHEEL_RULES,
) -> pd.DataFrame:
    """Classify rows as Ready or Needs Review and add issue_reason."""
    result = df.copy()
    statuses: list[str] = []
    issue_reasons: list[str] = []
    warnings: list[str] = []

    for _, row in result.iterrows():
        row_issues: list[str] = []
        row_warnings: list[str] = []

        for rule in rules:
            _, value = _resolve_column(row, rule, mapping)
            if is_blank(value):
                message = f"Missing {rule.canonical_name}"
                if rule.warning_only:
                    row_warnings.append(message)
                elif rule.required:
                    row_issues.append(message)

        statuses.append("Needs Review" if row_issues else "Ready")
        issue_reasons.append("; ".join(row_issues) if row_issues else "")
        warnings.append("; ".join(row_warnings))

    result["validation_status"] = statuses
    result["issue_reason"] = issue_reasons
    result["validation_warnings"] = warnings
    return result
