"""AR aging report and month-end AR roll-forward, built from QuickBooks data (the books of record).

Aging: each unpaid invoice's open balance goes into a bucket by days past due:
  Current (not due yet, including due today) | 1-30 | 31-60 | 61-90 | 90+

Month-end roll-forward, per month:
  opening AR + invoiced - collected = closing AR  (closing becomes next month's opening)
"""
import math

import pandas as pd

from .common import SIM_BANNER, fmt_money, md_table

BUCKETS = ["Current", "1-30", "31-60", "61-90", "90+"]
EDGES = [-math.inf, 0, 30, 60, 90, math.inf]  # right-inclusive: 0 -> Current, 30 -> 1-30, 31 -> 31-60, 91 -> 90+


def age_invoices(inv: pd.DataFrame, as_of) -> pd.DataFrame:
    """inv needs: invoice_number, customer, due_date, balance. Only invoices with a balance are aged."""
    df = inv[inv["balance"] > 0].copy()
    df["days_past_due"] = (pd.Timestamp(as_of) - pd.to_datetime(df["due_date"])).dt.days
    df["bucket"] = pd.cut(df["days_past_due"], EDGES, labels=BUCKETS)
    return df


def aging_summary(aged: pd.DataFrame) -> pd.DataFrame:
    out = (aged.groupby("bucket", observed=False)["balance"].agg(invoices="count", balance="sum")
           .reindex(BUCKETS, fill_value=0).reset_index())
    total = out["balance"].sum()
    out["pct_of_total"] = (out["balance"] / total * 100).round(1) if total else 0.0
    out["balance"] = out["balance"].round(2)
    return out


def aging_by_customer(aged: pd.DataFrame) -> pd.DataFrame:
    p = (aged.pivot_table(index="customer", columns="bucket", values="balance", aggfunc="sum",
                          fill_value=0, observed=False).reindex(columns=BUCKETS, fill_value=0))
    p["Total"] = p.sum(axis=1)
    return p.round(2).sort_values("Total", ascending=False).reset_index()


def month_end_summary(inv: pd.DataFrame, pay: pd.DataFrame, as_of) -> pd.DataFrame:
    """inv needs invoice_date, total_amount; pay needs payment_date, amount_applied.
    The first month opens at 0 because the data starts there."""
    as_of = pd.Timestamp(as_of)
    inv_d, pay_d = pd.to_datetime(inv["invoice_date"]), pd.to_datetime(pay["payment_date"])
    invoiced = inv[inv_d <= as_of].groupby(inv_d.dt.to_period("M"))["total_amount"].sum()
    collected = pay[pay_d <= as_of].groupby(pay_d.dt.to_period("M"))["amount_applied"].sum()
    months = pd.period_range(invoiced.index.min(), as_of.to_period("M"), freq="M")
    df = pd.DataFrame({"invoiced": invoiced.reindex(months, fill_value=0.0),
                       "collected": collected.reindex(months, fill_value=0.0)})
    df["closing_ar"] = (df["invoiced"] - df["collected"]).cumsum()
    df["opening_ar"] = df["closing_ar"].shift(fill_value=0.0)
    df.index = df.index.astype(str)
    return df.rename_axis("month").reset_index()[["month", "opening_ar", "invoiced", "collected", "closing_ar"]].round(2)


def write_ar_reports(inv, pay, as_of, out_dir, simulated) -> str:
    out_dir.mkdir(parents=True, exist_ok=True)
    aged = age_invoices(inv, as_of)
    summary, by_cust, month_end = aging_summary(aged), aging_by_customer(aged), month_end_summary(inv, pay, as_of)
    aged.to_csv(out_dir / "ar_aging_detail.csv", index=False)
    summary.to_csv(out_dir / "ar_aging_summary.csv", index=False)
    by_cust.to_csv(out_dir / "ar_aging_by_customer.csv", index=False)
    month_end.to_csv(out_dir / "month_end_summary.csv", index=False)

    aging_total = round(summary["balance"].sum(), 2)
    closing = month_end["closing_ar"].iloc[-1]
    tie = ("ties" if abs(closing - aging_total) < 0.01
           else f"does NOT tie (difference {closing - aging_total:,.2f}: look for credit memos, unapplied cash or dates after as-of)")
    md = "\n".join([
        f"# AR report as of {pd.Timestamp(as_of).date()}", "", SIM_BANNER if simulated else "",
        "## AR aging (open balances, days past due date)", "",
        md_table(fmt_money(summary, ["balance"])), "", f"**Total open AR: ${aging_total:,.2f}**", "",
        "## Top 5 customers by open balance", "",
        md_table(fmt_money(by_cust.head(5), BUCKETS + ["Total"])), "",
        "## Month-end summary (AR roll-forward)", "",
        md_table(fmt_money(month_end, ["opening_ar", "invoiced", "collected", "closing_ar"])), "",
        f"Tie-out: closing AR ${closing:,.2f} vs aging total ${aging_total:,.2f}: **{tie}**.", ""])
    (out_dir / "ar_report.md").write_text(md)
    return md
