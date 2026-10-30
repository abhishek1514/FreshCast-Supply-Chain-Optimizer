"""CSV/Excel ingestion and template helpers."""
from pathlib import Path
import pandas as pd
from app.schema import REQUIRED_COLUMNS


def read_table(file, name: str) -> pd.DataFrame:
    suffix = Path(getattr(file, "name", "upload.csv")).suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(file)
    if suffix == ".csv":
        return pd.read_csv(file)
    raise ValueError(f"Unsupported file type for {name}: use CSV or XLSX")


def blank_template(name: str) -> pd.DataFrame:
    if name not in REQUIRED_COLUMNS:
        raise KeyError(name)
    return pd.DataFrame(columns=REQUIRED_COLUMNS[name])
