# Honda Lease vs Finance Analyzer

A Python tool that pulls live payment data from Honda's API and generates an interactive dashboard comparing lease vs. finance costs over 6 years.

## Live Dashboard

**[View Dashboard →](https://YOUR_USERNAME.github.io/HondaInterview)**

## What it does

- Fetches real-time lease and finance payment data from Honda's API
- Models two full lease cycles (months 1–36 and 37–72) with projected MSRP inflation
- Calculates year-by-year cumulative spend for lease vs. finance
- Compares net cost of financing (gross paid minus estimated resale value)
- Supports multiple models and scenarios

## Repo structure

```
HondaInterview/
├── honda_payments.py     # Data pipeline — fetches API data, outputs CSVs
├── dashboard.html        # Interactive dashboard (open directly or via GitHub Pages)
├── output/
│   ├── lease_data.csv        # Lease terms, signing breakdown, 6yr totals
│   ├── finance_data.csv      # Finance terms, gross and net costs
│   └── yearly_schedule.csv   # Year-by-year cumulative spend
└── README.md
```

## How to run

### Requirements

```bash
pip install curl_cffi
```

### Add models and scenarios

Edit `honda_payments.py` to add more Honda model IDs and payment scenarios:

```python
MODELS = {
    "2026 Civic Sport Hybrid Sedan": "FE4F8TJW",
    "2026 Ridgeline Sport": "YOUR_MODEL_ID",
}

SCENARIOS = [
    {
        "label": "no down payment",
        "zip": "90250",
        "leaseTerm": 36,
        "financeTerm": 60,
        "annualMileage": 15000,
        "apr": 5.49,
        "downPayment": 3740,
        "financeDownPayment": 0,
        "fico": 740,
        "financeFico": 740,
    },
]
```

### Run

```bash
python honda_payments.py
```

Outputs three CSV files to `output/`. The dashboard reads directly from these files.

## Methodology

| Assumption | Value |
|---|---|
| Lease cycle length | 36 months |
| Finance term | 60 months |
| Lease cycle 2 MSRP inflation | 4% annualized |
| Lease cycle 2 residual % | Same as cycle 1 (from API) |
| Lease cycle 2 money factor | Same as cycle 1 (from API) |
| Estimated resale at year 6 | 40% of MSRP |
| ZIP code | 90250 (Hawthorne, CA) |
| FICO score | 740 |

Residual value for lease cycle 1 is back-calculated from the API's pre-tax monthly payment using the standard lease formula:

```
MonthlyPayment = ((cap_cost - residual) / term) + ((cap_cost + residual) × money_factor)
```

## Key findings (current data)

Finance wins on net cost across all scenarios for both models. The Ridgeline's gap is larger (~$13k) because its residual percentage (60%) is lower than the Civic's (66%), meaning more depreciation is paid per lease cycle.
