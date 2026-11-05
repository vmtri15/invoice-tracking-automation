"""Run the whole pipeline: QuickBooks extract -> reconciliation -> AR reports.

  python -m src.run_pipeline                                    # mock mode, SIMULATED sample data
  python -m src.run_pipeline --live --sheet path/to/sheet.csv   # real QuickBooks sandbox + your Sheet export
"""
import argparse
from datetime import date

from . import generate_sample_data
from .ar_reports import write_ar_reports
from .common import REPORTS, SAMPLE
from .quickbooks_client import extract
from .reconcile import load_sheet, reconcile, write_reconciliation


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--live", action="store_true", help="call the QuickBooks API (needs .env); default is mock mode")
    ap.add_argument("--sheet", help="CSV exported from the Google Sheet (required with --live)")
    ap.add_argument("--as-of", help="report date YYYY-MM-DD (default: today, or the sample's date in mock mode)")
    args = ap.parse_args(argv)
    if args.live and not args.sheet:
        ap.error("--live needs --sheet")
    simulated = not args.live
    as_of = (date.fromisoformat(args.as_of) if args.as_of
             else generate_sample_data.AS_OF if simulated else date.today())

    print(f"Mode: {'MOCK (simulated data)' if simulated else 'LIVE (QuickBooks API)'} | as of {as_of}")
    if simulated and not (SAMPLE / "simulated_qbo_invoices.json").exists():
        print("1/4 Generating simulated sample data")
        generate_sample_data.main()
    print("2/4 Extracting QuickBooks invoices and payments -> data/extracted/")
    inv, pay = extract(mock=simulated)
    print(f"     {len(inv)} invoices, {len(pay)} payment lines")
    print("3/4 Reconciling Sheet vs QuickBooks -> reports/reconciliation_*")
    sheet = load_sheet(args.sheet or SAMPLE / "simulated_ledger_sheet.csv")
    issues = reconcile(sheet, inv)
    write_reconciliation(sheet, inv, issues, REPORTS, simulated)
    print(f"     {len(issues)} exceptions, ${issues.amount_at_risk.sum():,.2f} at risk")
    print("4/4 Building AR aging + month-end summary -> reports/ar_*")
    write_ar_reports(inv, pay, as_of, REPORTS, simulated)
    print("Done. Start with reports/reconciliation_summary.md and reports/ar_report.md")


if __name__ == "__main__":
    main()
