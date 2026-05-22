from __future__ import annotations

import io
from pathlib import Path
from typing import BinaryIO, Union

import pandas as pd


AllowedFile = Union[str, Path, BinaryIO, io.BytesIO]


def read_tabular_file(file_obj: AllowedFile, file_name: str | None = None) -> pd.DataFrame:
    """Read CSV/XLSX into a DataFrame.

    This replaces the original Streamlit-only read_file/read_file_from_bytes helpers.
    It raises normal Python exceptions so UI/API layers can decide how to display errors.
    """
    name = (file_name or getattr(file_obj, "name", "")).lower()

    if name.endswith(".csv"):
        return pd.read_csv(file_obj)
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(file_obj)

    raise ValueError("Only CSV and Excel files are allowed.")


def read_tabular_bytes(file_name: str, file_bytes: bytes) -> pd.DataFrame:
    return read_tabular_file(io.BytesIO(file_bytes), file_name=file_name)
