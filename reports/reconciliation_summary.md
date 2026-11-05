# Reconciliation summary: Google Sheet AR ledger vs QuickBooks

> **SIMULATED DATA.** These numbers come from generated sample data (src/generate_sample_data.py), not from a real company.

- Invoices in Sheet: **195** | in QuickBooks: **195** | in both: **190**
- Matched with no differences: **178**
- Exceptions found: **25** | Total dollars at risk: **$78,897.85**

## Exceptions by type

| issue_type | count | dollars_at_risk |
|---|---|---|
| MISSING_INVOICE_NUMBER | 0 | 0.00 |
| DUPLICATE_IN_SHEET | 3 | 14,414.26 |
| MISSING_IN_QB | 5 | 10,823.52 |
| MISSING_IN_SHEET | 5 | 28,905.53 |
| AMOUNT_MISMATCH | 6 | 1,765.40 |
| STATUS_MISMATCH | 6 | 22,989.14 |

## Ten largest exceptions

| invoice_number | customer | issue_type | amount_at_risk |
|---|---|---|---|
| INV-1053 | Eastgate Foods | MISSING_IN_SHEET | 11,713.06 |
| INV-1099 | Maple and Finch Bakery | DUPLICATE_IN_SHEET | 7,758.37 |
| INV-1012 | Cobalt Freight Co | MISSING_IN_SHEET | 6,806.28 |
| INV-1013 | Redwater Brewing | MISSING_IN_SHEET | 6,120.25 |
| INV-1068 | Harbor Light Marine | STATUS_MISMATCH | 5,959.12 |
| INV-1024 | Bluebird Dental Group | STATUS_MISMATCH | 5,613.48 |
| INV-1128 | Granite Peak Builders | DUPLICATE_IN_SHEET | 4,988.46 |
| INV-1127 | Pinecrest Schools | STATUS_MISMATCH | 4,873.40 |
| INV-1082 | Bluebird Dental Group | MISSING_IN_SHEET | 2,902.19 |
| INV-1184 | Juniper Analytics | MISSING_IN_QB | 2,822.68 |

Full list: `reconciliation_report.csv`. How "dollars at risk" is defined: see `src/reconcile.py`.
