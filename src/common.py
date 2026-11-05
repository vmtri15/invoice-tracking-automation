"""Shared paths and small helpers used by every step of the pipeline."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "data" / "sample"
EXTRACT = ROOT / "data" / "extracted"
REPORTS = ROOT / "reports"

SIM_BANNER = (
    "> **SIMULATED DATA.** These numbers come from generated sample data "
    "(src/generate_sample_data.py), not from a real company.\n"
)


def to_money(s: pd.Series) -> pd.Series:
    """'$1,234.50' -> 1234.5. Text that isn't a number becomes NaN."""
    return pd.to_numeric(s.astype(str).str.replace(r"[$,\s]", "", regex=True), errors="coerce")


def qb_status(total: float, balance: float) -> str:
    """QuickBooks has no status field. It is worked out from the balance still owed."""
    if balance <= 0:
        return "Paid"
    return "Partially Paid" if balance < total else "Open"


def fmt_money(df: pd.DataFrame, cols) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        out[c] = out[c].map("{:,.2f}".format)
    return out


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    lines += ["| " + " | ".join(map(str, row)) + " |" for row in df.itertuples(index=False)]
    return "\n".join(lines)
