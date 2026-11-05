from datetime import date, timedelta

import pandas as pd

from src.ar_reports import age_invoices, aging_summary, month_end_summary

AS_OF = date(2026, 10, 31)


def inv_due(days_past_due, balance=100.0):
    return {"invoice_number": f"D{days_past_due}", "customer": "A",
            "due_date": (AS_OF - timedelta(days=days_past_due)).isoformat(), "balance": balance}


def test_bucket_edges():
    days = [-10, 0, 1, 30, 31, 60, 61, 90, 91, 200]
    aged = age_invoices(pd.DataFrame([inv_due(d) for d in days]), AS_OF)
    assert dict(zip(aged.days_past_due, aged.bucket.astype(str))) == {
        -10: "Current", 0: "Current", 1: "1-30", 30: "1-30", 31: "31-60",
        60: "31-60", 61: "61-90", 90: "61-90", 91: "90+", 200: "90+"}


def test_invoice_due_today_is_current_not_overdue():
    aged = age_invoices(pd.DataFrame([inv_due(0)]), AS_OF)
    assert aged.iloc[0].bucket == "Current" and aged.iloc[0].days_past_due == 0


def test_paid_excluded_and_partial_uses_open_balance():
    df = pd.DataFrame([inv_due(10, balance=0.0), inv_due(45, balance=400.0)])  # paid; partial (400 still owed)
    s = aging_summary(age_invoices(df, AS_OF)).set_index("bucket")
    assert s.loc["31-60", "balance"] == 400.0 and s["invoices"].sum() == 1
    assert list(s.index) == ["Current", "1-30", "31-60", "61-90", "90+"]  # empty buckets still shown


def test_month_end_roll_forward():
    inv = pd.DataFrame({"invoice_date": ["2026-01-10", "2026-02-05"], "total_amount": [1000.0, 500.0]})
    pay = pd.DataFrame({"payment_date": ["2026-01-20", "2026-03-02"], "amount_applied": [400.0, 600.0]})
    m = month_end_summary(inv, pay, date(2026, 3, 31))
    assert m.to_dict("records") == [
        {"month": "2026-01", "opening_ar": 0.0, "invoiced": 1000.0, "collected": 400.0, "closing_ar": 600.0},
        {"month": "2026-02", "opening_ar": 600.0, "invoiced": 500.0, "collected": 0.0, "closing_ar": 1100.0},
        {"month": "2026-03", "opening_ar": 1100.0, "invoiced": 0.0, "collected": 600.0, "closing_ar": 500.0},
    ]
