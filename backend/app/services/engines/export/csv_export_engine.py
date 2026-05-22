from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from backend.app.models.schemas import ComparisonSummary


@dataclass
class CsvExportPackage:
    ready_to_upload: pd.DataFrame
    needs_review: pd.DataFrame
    comparison_summary: pd.DataFrame

    def as_csv_text(self) -> dict[str, str]:
        return {
            "ready_to_upload.csv": self.ready_to_upload.to_csv(index=False),
            "needs_review.csv": self.needs_review.to_csv(index=False),
            "comparison_summary.csv": self.comparison_summary.to_csv(index=False),
        }


def build_summary_dataframe(summary: ComparisonSummary) -> pd.DataFrame:
    return pd.DataFrame([summary.model_dump()])


def build_csv_exports(final_df: pd.DataFrame, summary: ComparisonSummary) -> CsvExportPackage:
    if final_df.empty:
        ready = final_df.copy()
        needs_review = final_df.copy()
    else:
        ready = final_df[final_df["validation_status"] == "Ready"].copy()
        needs_review = final_df[final_df["validation_status"] == "Needs Review"].copy()

    return CsvExportPackage(
        ready_to_upload=ready,
        needs_review=needs_review,
        comparison_summary=build_summary_dataframe(summary),
    )
