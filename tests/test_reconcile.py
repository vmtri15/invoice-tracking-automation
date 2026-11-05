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
