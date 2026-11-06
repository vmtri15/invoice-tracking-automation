"""Reconcile the Google Sheet AR ledger against QuickBooks, matching on invoice number.

Rules (one output row per problem; one invoice can have two problems):
  MISSING_INVOICE_NUMBER  Sheet row with no invoice number: can't be matched.  At risk: sheet amount
  DUPLICATE_IN_SHEET      Same number entered again. Extra copies are flagged;  At risk: the copy's amount
                          the first (earliest) row is the one we match.
  MISSING_IN_QB           In the Sheet, not in QuickBooks.                       At risk: sheet amount
  MISSING_IN_SHEET        In QuickBooks, not in the Sheet.                       At risk: QuickBooks amount
  AMOUNT_MISMATCH         Sheet amount != QuickBooks total.                     At risk: |difference|
  STATUS_MISMATCH         Paid in one system, not paid in the other.
                          Sheet Paid, QB unpaid -> cash we think we have but don't. At risk: QB balance
                          Sheet Open, QB Paid   -> Sheet overstates AR.              At risk: sheet amount
  A partial payment in QB (0 < balance < total) still counts as "not paid", so Sheet "Open" matches it.
"""
import pandas as pd

from .common import SIM_BANNER, fmt_money, md_table, qb_status, to_money

ISSUE_TYPES = ["MISSING_INVOICE_NUMBER", "DUPLICATE_IN_SHEET", "MISSING_IN_QB", "MISSING_IN_SHEET",
               "AMOUNT_MISMATCH", "STATUS_MISMATCH"]
COLS = ["invoice_number", "customer", "issue_type", "sheet_amount", "qb_amount", "sheet_status",
        "qb_status", "amount_at_risk", "detail"]


SHEET_COLUMNS = {"Customer": "customer", "Invoice Number": "invoice_number", "Amount": "amount", "Status": "status"}


def clean_sheet(df: pd.DataFrame) -> pd.DataFrame:
    """Same cleaning whether the Sheet comes from a CSV export or straight from Google."""
    missing = [c for c in SHEET_COLUMNS if c not in df.columns]
    if missing:
        raise SystemExit(f"Sheet is missing column(s) {missing}. Expected the Form's headers: {list(SHEET_COLUMNS)}")
    df = df.rename(columns=SHEET_COLUMNS)
    df["amount"] = to_money(df["amount"])
    return df[list(SHEET_COLUMNS.values())]


def load_sheet(path) -> pd.DataFrame:
    """Read the CSV exported from the Google Sheet (File > Download > CSV)."""
    return clean_sheet(pd.read_csv(path, dtype=str))


def load_google_sheet(sheet_id, key_file, tab="Form Responses 1") -> pd.DataFrame:
    """Read the Sheet live through the Google Sheets API with a service account (read-only)."""
    import gspread  # only needed for the live read

    gc = gspread.service_account(filename=key_file, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    rows = gc.open_by_key(sheet_id).worksheet(tab).get_all_values()  # values as displayed, like the CSV export
    if not rows:
        raise SystemExit(f"Tab '{tab}' is empty")
    return clean_sheet(pd.DataFrame(rows[1:], columns=rows[0]))


def _norm(s: pd.Series) -> pd.Series:
    return s.fillna("").astype(str).str.strip().str.upper()  # " inv-1 " and "INV-1" are the same invoice


def reconcile(sheet: pd.DataFrame, qb: pd.DataFrame) -> pd.DataFrame:
    """sheet: invoice_number, customer, amount, status (rows in entry order)
       qb:    invoice_number, customer, total_amount, balance"""
    issues = []

    def add(r, issue, sheet_amount=None, qb_amount=None, sheet_status=None, q_status=None, risk=0.0, detail=""):
        issues.append(dict(invoice_number=r.invoice_number, customer=r.customer, issue_type=issue,
                           sheet_amount=sheet_amount, qb_amount=qb_amount, sheet_status=sheet_status,
                           qb_status=q_status, amount_at_risk=round(float(risk), 2), detail=detail))

    s = sheet.assign(invoice_number=_norm(sheet["invoice_number"]),
                     amount=sheet["amount"].fillna(0),  # unreadable amount -> 0, so it surfaces as a mismatch
                     sheet_status=sheet["status"].fillna("").str.strip().str.lower()
                                  .map(lambda x: "Paid" if x == "paid" else "Open"))

    blank = s["invoice_number"] == ""
    for r in s[blank].itertuples():
        add(r, "MISSING_INVOICE_NUMBER", r.amount, None, r.sheet_status, None, r.amount, "Sheet row has no invoice number")
    s = s[~blank]

    dup = s.duplicated("invoice_number", keep="first")
    counts = s["invoice_number"].value_counts()
    for r in s[dup].itertuples():
        add(r, "DUPLICATE_IN_SHEET", r.amount, None, r.sheet_status, None, r.amount,
            f"Entered {counts[r.invoice_number]} times in the Sheet; first entry used for matching")
    s = s[~dup]

    q = qb.assign(invoice_number=_norm(qb["invoice_number"])).drop_duplicates("invoice_number")
    m = s.rename(columns={"customer": "sheet_customer"}).merge(
        q.rename(columns={"customer": "qb_customer"}), on="invoice_number", how="outer", indicator="where")
    m["customer"] = m["sheet_customer"].fillna(m["qb_customer"])

    for r in m.itertuples():
        if r.where == "left_only":
            add(r, "MISSING_IN_QB", r.amount, None, r.sheet_status, None, r.amount, "In the Sheet, not in QuickBooks")
            continue
        q_status = qb_status(r.total_amount, r.balance)
        if r.where == "right_only":
            add(r, "MISSING_IN_SHEET", None, r.total_amount, None, q_status, r.total_amount, "In QuickBooks, not in the Sheet")
            continue
        diff = round(r.amount - r.total_amount, 2)
        if diff != 0:
            add(r, "AMOUNT_MISMATCH", r.amount, r.total_amount, r.sheet_status, q_status, abs(diff),
                f"Sheet {r.amount:,.2f} vs QuickBooks {r.total_amount:,.2f} (diff {diff:+,.2f})")
        if (r.sheet_status == "Paid") != (q_status == "Paid"):
            risk = r.balance if r.sheet_status == "Paid" else r.amount
            add(r, "STATUS_MISMATCH", r.amount, r.total_amount, r.sheet_status, q_status, risk,
                f"Sheet says {r.sheet_status}, QuickBooks says {q_status} (balance {r.balance:,.2f})")

    return pd.DataFrame(issues, columns=COLS).sort_values(["issue_type", "invoice_number"], ignore_index=True)


def write_reconciliation(sheet, qb, issues, out_dir, simulated) -> str:
    out_dir.mkdir(parents=True, exist_ok=True)
    issues.to_csv(out_dir / "reconciliation_report.csv", index=False)

    sn, qn = set(_norm(sheet["invoice_number"])) - {""}, set(_norm(qb["invoice_number"]))
    both = sn & qn
    with_diff = set(issues.loc[issues.issue_type.isin(["AMOUNT_MISMATCH", "STATUS_MISMATCH"]), "invoice_number"])
    by_type = (issues.groupby("issue_type")["amount_at_risk"].agg(count="count", dollars_at_risk="sum")
               .reindex(ISSUE_TYPES, fill_value=0).reset_index())
    top = issues.nlargest(10, "amount_at_risk")[["invoice_number", "customer", "issue_type", "amount_at_risk"]]

    md = "\n".join([
        "# Reconciliation summary: Google Sheet AR ledger vs QuickBooks", "",
        SIM_BANNER if simulated else "",
        f"- Invoices in Sheet: **{len(sn)}** | in QuickBooks: **{len(qn)}** | in both: **{len(both)}**",
        f"- Matched with no differences: **{len(both - with_diff)}**",
        f"- Exceptions found: **{len(issues)}** | Total dollars at risk: **${issues.amount_at_risk.sum():,.2f}**", "",
        "## Exceptions by type", "", md_table(fmt_money(by_type, ["dollars_at_risk"])), "",
        "## Ten largest exceptions", "", md_table(fmt_money(top, ["amount_at_risk"])), "",
        "Full list: `reconciliation_report.csv`. How \"dollars at risk\" is defined: see `src/reconcile.py`.", ""])
    (out_dir / "reconciliation_summary.md").write_text(md)
    return md
