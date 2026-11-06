"""Run the whole pipeline: QuickBooks extract -> reconciliation -> AR reports.

  python -m src.run_pipeline                                    # mock mode, SIMULATED sample data
  python -m src.run_pipeline --live --sheet path/to/sheet.csv   # real QuickBooks sandbox + your Sheet export
  python -m src.run_pipeline --live                             # ...reading the Google Sheet live (GOOGLE_* in .env)

Live runs write to reports/live/ (git-ignored) so they never overwrite the simulated reports.
"""
import argparse
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from . import generate_sample_data
from .ar_reports import write_ar_reports
from .common import REPORTS, ROOT, SAMPLE
from .quickbooks_client import extract
from .reconcile import load_google_sheet, load_sheet, reconcile, write_reconciliation


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--live", action="store_true", help="call the QuickBooks API (needs .env); default is mock mode")
    ap.add_argument("--sheet", help="CSV exported from the Google Sheet (live mode reads Google directly if omitted)")
    ap.add_argument("--out", help="report folder (default: reports/, or reports/live/ in live mode)")
    ap.add_argument("--as-of", help="report date YYYY-MM-DD (default: today, or the sample's date in mock mode)")
    args = ap.parse_args(argv)
    load_dotenv(ROOT / ".env")
    if args.live and not args.sheet and not (os.environ.get("GOOGLE_SHEET_ID") and os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")):
        ap.error("--live needs --sheet, or GOOGLE_SHEET_ID and GOOGLE_SERVICE_ACCOUNT_FILE in .env")
    simulated = not args.live
    out = Path(args.out) if args.out else REPORTS if simulated else REPORTS / "live"
    as_of = (date.fromisoformat(args.as_of) if args.as_of
             else generate_sample_data.AS_OF if simulated else date.today())

    print(f"Mode: {'MOCK (simulated data)' if simulated else 'LIVE (QuickBooks API)'} | as of {as_of}")
    if simulated and not (SAMPLE / "simulated_qbo_invoices.json").exists():
        print("1/4 Generating simulated sample data")
        generate_sample_data.main()
    print("2/4 Extracting QuickBooks invoices and payments -> data/extracted/")
    inv, pay = extract(mock=simulated)
    print(f"     {len(inv)} invoices, {len(pay)} payment lines")
    print(f"3/4 Reconciling Sheet vs QuickBooks -> {out.name}/reconciliation_*")
    if args.sheet or simulated:
        sheet = load_sheet(args.sheet or SAMPLE / "simulated_ledger_sheet.csv")
    else:
        print("     reading the Google Sheet live through the Sheets API")
        sheet = load_google_sheet(os.environ["GOOGLE_SHEET_ID"], ROOT / os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"])
    issues = reconcile(sheet, inv)
    write_reconciliation(sheet, inv, issues, out, simulated)
    print(f"     {len(issues)} exceptions, ${issues.amount_at_risk.sum():,.2f} at risk")
    print(f"4/4 Building AR aging + month-end summary -> {out.name}/ar_*")
    write_ar_reports(inv, pay, as_of, out, simulated)
    print(f"Done. Start with {out.name}/reconciliation_summary.md and {out.name}/ar_report.md")


if __name__ == "__main__":
    main()
