"""Pull invoices and payments from QuickBooks Online and save them as CSV.

mock=True : read data/sample/simulated_qbo_*.json (SIMULATED, same shape as the real API response)
mock=False: call the QuickBooks Online API with OAuth 2.0, using credentials from .env

OAuth in one paragraph: the long-lived *refresh token* (from Intuit's OAuth Playground)
is exchanged for a short-lived *access token* (good for 1 hour), which goes in the
Authorization header of each API call. Intuit sometimes rotates the refresh token, so
we save the new one back into .env.
"""
import json
import os

import pandas as pd
import requests
from dotenv import load_dotenv, set_key

from .common import EXTRACT, ROOT, SAMPLE, qb_status

TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
API_BASE = {"sandbox": "https://sandbox-quickbooks.api.intuit.com",
            "production": "https://quickbooks.api.intuit.com"}
PAGE_SIZE = 1000  # QuickBooks returns at most 1000 rows per query


def fetch_mock():
    def load(name, entity):
        return json.loads((SAMPLE / f"simulated_qbo_{name}.json").read_text())["QueryResponse"].get(entity, [])
    return load("invoices", "Invoice"), load("payments", "Payment")


def _env(key):
    if not os.environ.get(key):
        raise SystemExit(f"{key} is missing. Copy .env.example to .env and fill it in, or run in mock mode.")
    return os.environ[key]


def _access_token():
    refresh = _env("QBO_REFRESH_TOKEN")
    r = requests.post(TOKEN_URL, auth=(_env("QBO_CLIENT_ID"), _env("QBO_CLIENT_SECRET")),
                      headers={"Accept": "application/json"},
                      data={"grant_type": "refresh_token", "refresh_token": refresh}, timeout=30)
    r.raise_for_status()
    tok = r.json()
    if tok.get("refresh_token") and tok["refresh_token"] != refresh:
        set_key(str(ROOT / ".env"), "QBO_REFRESH_TOKEN", tok["refresh_token"])  # otherwise the next run fails
    return tok["access_token"]


def _query_all(entity, token):
    base = API_BASE[os.environ.get("QBO_ENVIRONMENT", "sandbox")]
    url = f"{base}/v3/company/{_env('QBO_REALM_ID')}/query"
    rows, start = [], 1
    while True:
        r = requests.get(url, timeout=30,
                         params={"query": f"select * from {entity} STARTPOSITION {start} MAXRESULTS {PAGE_SIZE}",
                                 "minorversion": 75},
                         headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
        r.raise_for_status()
        page = r.json()["QueryResponse"].get(entity, [])
        rows += page
        if len(page) < PAGE_SIZE:
            return rows
        start += PAGE_SIZE


def fetch_live():
    load_dotenv(ROOT / ".env")
    token = _access_token()
    return _query_all("Invoice", token), _query_all("Payment", token)


def _number(inv):
    return inv.get("DocNumber") or f"QBO-{inv['Id']}"  # DocNumber is optional in QuickBooks


def invoices_to_df(raw):
    return pd.DataFrame([{
        "qb_id": i["Id"], "invoice_number": _number(i), "customer": i["CustomerRef"].get("name", ""),
        "invoice_date": i["TxnDate"], "due_date": i.get("DueDate") or i["TxnDate"],
        "total_amount": float(i["TotalAmt"]), "balance": float(i["Balance"]),
        "qb_status": qb_status(float(i["TotalAmt"]), float(i["Balance"])),
    } for i in raw], columns=["qb_id", "invoice_number", "customer", "invoice_date", "due_date",
                              "total_amount", "balance", "qb_status"])


def payments_to_df(raw_payments, raw_invoices):
    """One row per (payment, invoice) pair. A single payment can pay several invoices."""
    id_to_number = {i["Id"]: _number(i) for i in raw_invoices}
    rows = []
    for p in raw_payments:
        for line in p.get("Line", []):
            for t in line.get("LinkedTxn", []):
                if t.get("TxnType") == "Invoice":
                    rows.append({"payment_id": p["Id"], "payment_date": p["TxnDate"],
                                 "customer": p["CustomerRef"].get("name", ""),
                                 "invoice_number": id_to_number.get(t["TxnId"], f"QBO-{t['TxnId']}"),
                                 "amount_applied": float(line["Amount"])})
                    break
    # ponytail: money not applied to an invoice (customer credit) is ignored. Add it if you track unapplied cash.
    return pd.DataFrame(rows, columns=["payment_id", "payment_date", "customer", "invoice_number", "amount_applied"])


def extract(mock: bool, out_dir=EXTRACT):
    raw_inv, raw_pay = fetch_mock() if mock else fetch_live()
    inv, pay = invoices_to_df(raw_inv), payments_to_df(raw_pay, raw_inv)
    out_dir.mkdir(parents=True, exist_ok=True)
    inv.to_csv(out_dir / "qbo_invoices.csv", index=False)
    pay.to_csv(out_dir / "qbo_payments.csv", index=False)
    return inv, pay
