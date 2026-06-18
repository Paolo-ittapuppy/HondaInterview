from curl_cffi import requests as cf_requests
import json
import time
import csv
import os

BASE_URL = "https://automobiles.honda.com/platform/api/v1/payments"

MODELS = {
    "2026 Civic Sport Hybrid Sedan": "FE4F8TJW",
    "2026 Ridgeline Sport":    "YK3F6TKNW",
    # "Accord":  "XXXXXXXX",
}

SCENARIOS = [
    {
        "label": "no down payment",
        "zip": "90250",
        "leaseTerm": 36,
        "financeTerm": 60,
        "annualMileage": 15000,
        "apr": 4.87,
        "downPayment": 3740,
        "financeDownPayment": 0,
        "fico": 740,
        "financeFico": 740,
    },
    {
        "label": "with down payment",
        "zip": "90250",
        "leaseTerm": 36,
        "financeTerm": 60,
        "annualMileage": 15000,
        "apr": 4.87,
        "downPayment": 2500,
        "financeDownPayment": 2500,
        "fico": 740,
        "financeFico": 740,
    },
    {
        "label": "with bigger down payment",
        "zip": "90250",
        "leaseTerm": 36,
        "financeTerm": 60,
        "annualMileage": 15000,
        "apr": 4.87,
        "downPayment": 5000,
        "financeDownPayment": 5000,
        "fico": 740,
        "financeFico": 740,
    },

]


def get_session():
    session = cf_requests.Session(impersonate="chrome120")
    print("Warming up session on Honda homepage...")
    try:
        session.get("https://automobiles.honda.com/", timeout=15)
        time.sleep(1)
    except Exception as e:
        print(f"Warning: {e}")
    return session


def fetch_payments(session, model_name, model_id, scenario):
    params = {
        "zip": scenario["zip"],
        "leaseTerm": scenario["leaseTerm"],
        "financeTerm": scenario["financeTerm"],
        "annualMileage": scenario["annualMileage"],
        "apr": scenario["apr"],
        "modelId": model_id,
        "downPayment": scenario["downPayment"],
        "financeDownPayment": scenario["financeDownPayment"],
        "fico": scenario["fico"],
        "financeFico": scenario["financeFico"],
        "includeOffers": "true",
    }
    try:
        response = session.get(BASE_URL, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  Error: {e}")
        return None


def find_residual(msrp, down_payment, acquisition_fee, money_factor, preTax_monthly_payment, term):
    adjusted_cap_cost = msrp - down_payment + acquisition_fee
    residual = (preTax_monthly_payment - adjusted_cap_cost / term - adjusted_cap_cost * money_factor) / (money_factor - 1 / term)
    return round(residual, 2)


def estimate_lease2(msrp, lease_row, residual_pct, taxrate, msrp_inflation=0.04, term=36):
    future_msrp = msrp * (1 + msrp_inflation) ** (term / 12)
    future_down = lease_row["DownPayment"]
    future_acq = lease_row["AcquisitionFee"]
    future_cap_cost = future_msrp - future_down + future_acq
    future_residual = future_msrp * residual_pct
    mf = lease_row["MoneyFactor"]
    depreciation = (future_cap_cost - future_residual) / term
    finance_fee = (future_cap_cost + future_residual) * mf
    base_payment = depreciation + finance_fee
    monthly = round(base_payment * (1 + taxrate / 100), 2)
    signing = round(monthly + future_down + future_acq, 2)
    return {
        "FutureMSRP": round(future_msrp, 2),
        "FutureResidual": round(future_residual, 2),
        "MonthlyPayment": monthly,
        "TotalDueAtSigning": signing,
    }


def build_yearly_schedule(lease1_monthly, lease1_signing, lease2_monthly, lease2_signing, fin_monthly, fin_signing, fin_term):
    rows = []
    lease_cumulative = 0
    finance_cumulative = 0

    for month in range(1, 73):
        year = (month - 1) // 12 + 1
        in_lease1 = month <= 36
        l_monthly = lease1_monthly if in_lease1 else lease2_monthly
        l_sign = lease1_signing if month == 1 else (lease2_signing if month == 37 else 0)
        lease_cumulative += l_monthly + l_sign

        f_monthly = fin_monthly if month <= fin_term else 0
        f_sign = fin_signing if month == 1 else 0
        finance_cumulative += f_monthly + f_sign

        if month % 12 == 0:
            rows.append({
                "Year": year,
                "Month": month,
                "LeaseMonthly": round(l_monthly, 2),
                "LeaseCumulative": round(lease_cumulative, 2),
                "FinanceMonthly": round(f_monthly, 2),
                "FinanceCumulative": round(finance_cumulative, 2),
                "Difference_LeaseMinusFinance": round(lease_cumulative - finance_cumulative, 2),
            })
    return rows


def process(data, scenario, model_name):
    lease_raw = data.get("LeaseResults", {}).get("NoLeaseSpecial") or {}
    fin_raw = data.get("FinanceResults", {}).get("NoFinanceSpecial") or {}
    msrp = data.get("Vehicle", {}).get("MSRP", 0)
    tax_rate = data.get("FinanceResults", {}).get("SalesTax", {}).get("UpfrontTaxRate", 0)

    down = lease_raw.get("DownPayment", scenario["downPayment"])
    acq = lease_raw.get("AcquisitionFee", 595.00)
    mf = lease_raw.get("MoneyFactor", 0)
    pre_tax = lease_raw.get("PreTaxMonthlyPayment", 0)
    term = lease_raw.get("Term", 36)

    residual = find_residual(msrp, down, acq, mf, pre_tax, term)
    residual_pct = round(residual / msrp, 4) if msrp else 0

    lease_row = {
        "DownPayment": down,
        "AcquisitionFee": acq,
        "MoneyFactor": mf,
    }
    lease2 = estimate_lease2(msrp, lease_row, residual_pct, tax_rate)

    lease1_monthly = lease_raw.get("MonthlyPayment", 0)
    lease1_signing = lease_raw.get("TotalDueAtSigning", 0)
    fin_monthly = fin_raw.get("MonthlyPayment", 0)
    fin_signing = fin_raw.get("TotalDueAtSigning", 0)
    fin_term = fin_raw.get("Term", scenario["financeTerm"])

    l1_total = round(lease1_signing + lease1_monthly * 36, 2)
    l2_total = round(lease2["TotalDueAtSigning"] + lease2["MonthlyPayment"] * 36, 2)
    lease_6yr = round(l1_total + l2_total, 2)

    fin_gross = round(fin_signing + fin_monthly * fin_term, 2)
    est_resale = round(msrp * 0.40, 2)
    fin_net = round(fin_gross - est_resale, 2)

    lease_csv_row = {
        "Model": model_name,
        "Scenario": scenario["label"],
        "MSRP": msrp,
        "TaxRate": tax_rate,
        "ResidualValue": residual,
        "ResidualPct": residual_pct,
        # Lease 1
        "L1_MonthlyPayment": lease1_monthly,
        "L1_PreTaxMonthly": pre_tax,
        "L1_TotalDueAtSigning": lease1_signing,
        "L1_Term": term,
        "L1_MoneyFactor": mf,
        "L1_AnnualMileage": lease_raw.get("AnnualMileage", scenario["annualMileage"]),
        "L1_DownPayment": down,
        "L1_AcquisitionFee": acq,
        "L1_FirstMonthPayment": lease_raw.get("FirstMonthPayment", lease1_monthly),
        "L1_MonthlySalesTax": lease_raw.get("MonthlySalesTax", 0),
        "L1_UpfrontSalesTax": lease_raw.get("UpfrontSalesTax", 0),
        "L1_3YrTotal": l1_total,
        # Lease 2 (projected)
        "L2_FutureMSRP": lease2["FutureMSRP"],
        "L2_FutureResidual": lease2["FutureResidual"],
        "L2_MonthlyPayment": lease2["MonthlyPayment"],
        "L2_TotalDueAtSigning": lease2["TotalDueAtSigning"],
        "L2_3YrTotal": l2_total,
        # 6yr totals
        "Lease_6YrTotal": lease_6yr,
    }

    finance_csv_row = {
        "Model": model_name,
        "Scenario": scenario["label"],
        "MSRP": msrp,
        "TaxRate": tax_rate,
        "F_MonthlyPayment": fin_monthly,
        "F_TotalDueAtSigning": fin_signing,
        "F_AmountFinanced": fin_raw.get("AmountFinanced", 0),
        "F_Term": fin_term,
        "F_APR": fin_raw.get("Apr", scenario["apr"]),
        "F_GrossTotal": fin_gross,
        "F_EstimatedResale": est_resale,
        "F_NetTotal": fin_net,
    }

    yearly_rows = build_yearly_schedule(
        lease1_monthly, lease1_signing,
        lease2["MonthlyPayment"], lease2["TotalDueAtSigning"],
        fin_monthly, fin_signing, fin_term,
    )

    return lease_csv_row, finance_csv_row, yearly_rows


def write_csv(filename, rows, fieldnames):
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Saved {filename} ({len(rows)} rows)")


def main():
    session = get_session()
    lease_rows = []
    finance_rows = []
    yearly_rows = []

    for model_name, model_id in MODELS.items():
        for scenario in SCENARIOS:
            print(f"\nFetching: {model_name} — {scenario['label']}...")
            data = fetch_payments(session, model_name, model_id, scenario)
            if not data:
                print("  Skipping — no data returned.")
                continue

            lease_row, finance_row, yearly = process(data, scenario, model_name)
            lease_rows.append(lease_row)
            finance_rows.append(finance_row)

            # Tag each yearly row with model + scenario for the dashboard
            for r in yearly:
                r["Model"] = model_name
                r["Scenario"] = scenario["label"]
            yearly_rows.extend(yearly)

            print(f"  Lease 1 monthly:   ${lease_row['L1_MonthlyPayment']}")
            print(f"  Lease 2 monthly:   ${lease_row['L2_MonthlyPayment']} (projected)")
            print(f"  Finance monthly:   ${finance_row['F_MonthlyPayment']}")
            print(f"  Lease 6yr total:   ${lease_row['Lease_6YrTotal']}")
            print(f"  Finance net total: ${finance_row['F_NetTotal']}")

            time.sleep(0.5)

    os.makedirs("output", exist_ok=True)

    write_csv(
        "output/lease_data.csv",
        lease_rows,
        fieldnames=list(lease_rows[0].keys()) if lease_rows else [],
    )
    write_csv(
        "output/finance_data.csv",
        finance_rows,
        fieldnames=list(finance_rows[0].keys()) if finance_rows else [],
    )
    write_csv(
        "output/yearly_schedule.csv",
        yearly_rows,
        fieldnames=list(yearly_rows[0].keys()) if yearly_rows else [],
    )

    print("\nDone! Upload the 3 files in output/ to Claude to generate your dashboard.")


if __name__ == "__main__":
    main()