import pandas as pd

from src.common import SAMPLE
from src.quickbooks_client import extract
from src.reconcile import load_sheet, reconcile


def sheet(*rows):
    return pd.DataFrame(rows, columns=["invoice_number", "customer", "amount", "status"])


def qb(*rows):
    return pd.DataFrame(rows, columns=["invoice_number", "customer", "total_amount", "balance"])


def found(issues):
    return {(r.invoice_number, r.issue_type, r.amount_at_risk) for r in issues.itertuples()}


def test_clean_match_has_no_issues():
    assert reconcile(sheet(("INV-1", "A", 100.0, "Open")), qb(("INV-1", "A", 100.0, 100.0))).empty


def test_missing_on_each_side():
    issues = reconcile(sheet(("INV-1", "A", 100.0, "Open")), qb(("INV-2", "B", 250.0, 250.0)))
    assert found(issues) == {("INV-1", "MISSING_IN_QB", 100.0), ("INV-2", "MISSING_IN_SHEET", 250.0)}


def test_amount_mismatch_risk_is_the_difference():
    issues = reconcile(sheet(("INV-1", "A", 1000.0, "Open")), qb(("INV-1", "A", 100.0, 100.0)))
    assert found(issues) == {("INV-1", "AMOUNT_MISMATCH", 900.0)}


def test_status_mismatch_both_directions():
    issues = reconcile(
        sheet(("INV-1", "A", 500.0, "Paid"), ("INV-2", "A", 300.0, "Open")),
        qb(("INV-1", "A", 500.0, 500.0), ("INV-2", "A", 300.0, 0.0)))
    # Sheet Paid / QB unpaid: risk = QB balance. Sheet Open / QB Paid: risk = sheet amount.
    assert found(issues) == {("INV-1", "STATUS_MISMATCH", 500.0), ("INV-2", "STATUS_MISMATCH", 300.0)}


def test_partial_payment():
    # 1000 invoice, 600 paid, 400 still owed. Sheet "Open" agrees; Sheet "Paid" does not.
    assert reconcile(sheet(("INV-1", "A", 1000.0, "Open")), qb(("INV-1", "A", 1000.0, 400.0))).empty
    issues = reconcile(sheet(("INV-1", "A", 1000.0, "paid ")), qb(("INV-1", "A", 1000.0, 400.0)))
    assert found(issues) == {("INV-1", "STATUS_MISMATCH", 400.0)}


def test_duplicate_number_flags_the_copy_and_matches_the_first():
    issues = reconcile(
        sheet(("INV-1", "A", 100.0, "Open"), (" inv-1 ", "A", 120.0, "Open")),
        qb(("INV-1", "A", 100.0, 100.0)))
    assert found(issues) == {("INV-1", "DUPLICATE_IN_SHEET", 120.0)}  # first row (100) matches QB cleanly


def test_blank_invoice_number_is_reported_not_dropped():
    issues = reconcile(sheet((None, "A", 50.0, "Open")), qb())
    assert found(issues) == {("", "MISSING_INVOICE_NUMBER", 50.0)}


def test_sample_data_finds_exactly_the_planted_problems(tmp_path):
    inv, _ = extract(mock=True, out_dir=tmp_path)
    issues = reconcile(load_sheet(SAMPLE / "simulated_ledger_sheet.csv"), inv)
    planted = pd.read_csv(SAMPLE / "simulated_planted_problems.csv")
    assert set(zip(issues.invoice_number, issues.issue_type)) == set(zip(planted.invoice_number, planted.problem))


def test_google_sheet_read_uses_displayed_values(monkeypatch):
    import sys
    import types

    rows = [["Timestamp", "Customer", "Invoice Number", "Invoice Date", "Due Date", "Amount", "Status", "Validation"],
            ["11/5/2026 17:36:07", "Test Co", "INV-1", "10/1/2026", "10/15/2026", "$1,500.00", "Open", "OK"]]
    seen = {}

    class Sheet:
        def worksheet(self, tab):
            seen["tab"] = tab
            return types.SimpleNamespace(get_all_values=lambda: rows)

    def service_account(filename, scopes):
        seen["key"], seen["scopes"] = filename, scopes
        return types.SimpleNamespace(open_by_key=lambda key: seen.setdefault("id", key) and Sheet())

    monkeypatch.setitem(sys.modules, "gspread", types.SimpleNamespace(service_account=service_account))
    from src.reconcile import load_google_sheet

    df = load_google_sheet("SHEET123", "key.json")
    assert df.to_dict("records") == [{"customer": "Test Co", "invoice_number": "INV-1", "amount": 1500.0, "status": "Open"}]
    assert seen["id"] == "SHEET123" and seen["tab"] == "Form Responses 1"
    assert seen["scopes"] == ["https://www.googleapis.com/auth/spreadsheets.readonly"]  # read-only access


def test_sheet_with_renamed_column_fails_clearly():
    import pytest
    from src.reconcile import clean_sheet

    with pytest.raises(SystemExit, match="Invoice Number"):
        clean_sheet(pd.DataFrame({"Customer": ["A"], "Invoice #": ["1"], "Amount": ["5"], "Status": ["Open"]}))
