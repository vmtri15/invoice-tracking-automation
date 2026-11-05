# Reconciliation summary: Google Sheet AR ledger vs QuickBooks


- Invoices in Sheet: **4** | in QuickBooks: **31** | in both: **2**
- Matched with no differences: **1**
- Exceptions found: **33** | Total dollars at risk: **$15,522.57**

## Exceptions by type

| issue_type | count | dollars_at_risk |
|---|---|---|
| MISSING_INVOICE_NUMBER | 0 | 0.00 |
| DUPLICATE_IN_SHEET | 1 | 1,500.00 |
| MISSING_IN_QB | 2 | 4,250.50 |
| MISSING_IN_SHEET | 29 | 7,402.55 |
| AMOUNT_MISMATCH | 0 | 0.00 |
| STATUS_MISMATCH | 1 | 2,369.52 |

## Ten largest exceptions

| invoice_number | customer | issue_type | amount_at_risk |
|---|---|---|---|
| INV-2 | Demo LLC | MISSING_IN_QB | 2,750.50 |
| 1004 | Cool Cars | STATUS_MISMATCH | 2,369.52 |
| INV-1 | Test Co | DUPLICATE_IN_SHEET | 1,500.00 |
| INV-1 | Test Co | MISSING_IN_QB | 1,500.00 |
| 1015 | Paulsen Medical Supplies | MISSING_IN_SHEET | 954.75 |
| 1007 | John Melton | MISSING_IN_SHEET | 750.00 |
| 1033 | Geeta Kalapatapu | MISSING_IN_SHEET | 629.10 |
| 1036 | 0969 Ocean View Road | MISSING_IN_SHEET | 477.50 |
| 1029 | Dukes Basketball Camp | MISSING_IN_SHEET | 460.40 |
| 1021 | Amy's Bird Sanctuary | MISSING_IN_SHEET | 459.00 |

Full list: `reconciliation_report.csv`. How "dollars at risk" is defined: see `src/reconcile.py`.
