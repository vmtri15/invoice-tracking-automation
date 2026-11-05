# AR report as of 2026-10-31

> **SIMULATED DATA.** These numbers come from generated sample data (src/generate_sample_data.py), not from a real company.

## AR aging (open balances, days past due date)

| bucket | invoices | balance | pct_of_total |
|---|---|---|---|
| Current | 29 | 106,907.64 | 53.6 |
| 1-30 | 20 | 43,807.70 | 22.0 |
| 31-60 | 7 | 24,488.31 | 12.3 |
| 61-90 | 4 | 14,274.70 | 7.2 |
| 90+ | 6 | 9,804.82 | 4.9 |

**Total open AR: $199,283.17**

## Top 5 customers by open balance

| customer | Current | 1-30 | 31-60 | 61-90 | 90+ | Total |
|---|---|---|---|---|---|---|
| Eastgate Foods | 32,796.98 | 2,629.53 | 2,632.82 | 6,191.00 | 0.00 | 44,250.33 |
| Summit Cycle Shop | 18,654.81 | 1,201.16 | 0.00 | 0.00 | 2,007.87 | 21,863.84 |
| Redwater Brewing | 4,510.23 | 9,432.15 | 0.00 | 2,915.46 | 0.00 | 16,857.84 |
| Tidewater Textiles | 8,490.03 | 0.00 | 0.00 | 3,243.65 | 793.59 | 12,527.27 |
| Bluebird Dental Group | 2,081.38 | 2,071.03 | 4,357.65 | 0.00 | 3,779.58 | 12,289.64 |

## Month-end summary (AR roll-forward)

| month | opening_ar | invoiced | collected | closing_ar |
|---|---|---|---|---|
| 2026-06 | 0.00 | 158,521.10 | 16,670.12 | 141,850.98 |
| 2026-07 | 141,850.98 | 134,808.14 | 119,553.10 | 157,106.02 |
| 2026-08 | 157,106.02 | 169,046.02 | 104,749.36 | 221,402.68 |
| 2026-09 | 221,402.68 | 168,935.16 | 174,904.22 | 215,433.62 |
| 2026-10 | 215,433.62 | 120,039.85 | 136,190.30 | 199,283.17 |

Tie-out: closing AR $199,283.17 vs aging total $199,283.17: **ties**.
