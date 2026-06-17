from curl_cffi import requests as cf_requests
import json
import time
import csv

BASE_URL = "https://automobiles.honda.com/platform/api/v1/payments"

MODELS = {
    "2026 Civic Sport Hybrid Sedan": "FE4F8TJW",
    # Add more model IDs here as you find them
    # "CR-V":    "XXXXXXXX",
    # "Accord":  "XXXXXXXX",
}

SCENARIOS = [
    {
        "label": "Standard (Good Credit, 15k miles/yr)",
        "zip": "90250",
        "leaseTerm": 36,
        "financeTerm": 60,
        "annualMileage": 15000,
        "apr": 5.49,
        "downPayment": 3740,
        "financeDownPayment": 0,
        "fico": 740,
        "financeFico": 740,
        "leaseOrFinance" : 0
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
        try:
            print(f"  Response text: {response.text[:500]}")
        except:
            pass
        return None


def extract_key_data(data):
    if not data:
        return None
    
    lease = data["LeaseResults"]["NoLeaseSpecial"] or {}
    finance = data["FinanceResults"]["NoFinanceSpecial"] or {}
    model = data["Vehicle"]
    return {
        "leaseData": {
            "MonthlyPayment":    lease.get("MonthlyPayment"),
            "TotalDueAtSigning": lease.get("TotalDueAtSigning"),
            "Term":              lease.get("Term"),
            "MoneyFactor":       lease.get("MoneyFactor"),
            "AnnualMileage":     lease.get("AnnualMileage"),

            # due at signing breakdown
            "DownPayment":       lease.get("DownPayment", 3740.00),
            "AcquisitionFee":    lease.get("AcquisitionFee", 595.00),
            "FirstMonthPayment": lease.get("FirstMonthPayment", lease.get("MonthlyPayment")),
            "MonthlySalesTax":   lease.get("MonthlySalesTax", 0),
            "UpfrontSalesTax":   lease.get("UpfrontSalesTax", 0),
        },
        "financeData": {
            "MonthlyPayment":    finance.get("MonthlyPayment"),
            "TotalDueAtSigning": finance.get("TotalDueAtSigning"),
            "AmountFinanced":    finance.get("AmountFinanced"),
            "Term":              finance.get("Term"),
            "Apr":               finance.get("Apr"),
        },
        "modelData": {
            "MSRP": model.get("MSRP")
        }
    }

def cost_analysis(lease, finance, lease2_monthly_increase=0.04):
    """
    Compare 6-year total cost of:
      - Two consecutive 36-month leases
      - One 60-month finance + 1 year owned free
    
    lease2_monthly_increase: assumed price increase for 2nd lease (default 4%)
    """
    if not lease or not finance:
        return None
    tax_rate = lease.get("MonthlySalesTax", 0) / lease.get("PreTaxMonthlyPayment", 1)

    l1_monthly = lease.get("MonthlyPayment", 0)
    l1_signing = lease.get("TotalDueAtSigning", 0)
    l2_monthly = round(l1_monthly * (1 + lease2_monthly_increase), 2)
    l2_signing = l1_signing  # assume same

    lease1_total = l1_signing + (l1_monthly * 36)
    lease2_total = l2_signing + (l2_monthly * 36)
    lease_6yr_total = lease1_total + lease2_total

    f_monthly = finance.get("MonthlyPayment", 0)
    f_signing = finance.get("TotalDueAtSigning", 0)
    finance_gross = f_signing + (f_monthly * 60)

    # Civic hybrids hold ~40% of value at 6 years — adjust as needed
    msrp = 26850
    estimated_resale = round(msrp * 0.40, 2)
    finance_net = finance_gross - estimated_resale

    cheaper = "lease" if lease_6yr_total < finance_net else "finance"
    savings = round(abs(lease_6yr_total - finance_net), 2)
    breakeven_resale = round(finance_gross - lease_6yr_total, 2)

    return {
        "lease_1yr_monthly": l1_monthly,
        "lease_1yr_signing": l1_signing,
        "lease_1yr_total": round(lease1_total, 2),
        "lease_2yr_monthly": l2_monthly,
        "lease_2yr_signing": l2_signing,
        "lease_2yr_total": round(lease2_total, 2),
        "lease_6yr_total": round(lease_6yr_total, 2),
        "finance_monthly": f_monthly,
        "finance_signing": f_signing,
        "finance_gross_60mo": round(finance_gross, 2),
        "finance_estimated_resale": estimated_resale,
        "finance_net_6yr": round(finance_net, 2),
        "cheaper_option": cheaper,
        "savings": savings,
        "breakeven_resale": breakeven_resale,
    }


def main():
    all_results = []
    session = get_session()

    for model_name, model_id in MODELS.items():
        for scenario in SCENARIOS:
            print(f"\nFetching: {model_name} - {scenario['label']}...")
            data = fetch_payments(session, model_name, model_id, scenario)
            extracted = extract_key_data(data)

            print("=" * 60)
            print(f"Model:    {model_name}")
            print(f"Scenario: {scenario['label']}")
            print("=" * 60)
            if extracted:
                print(f"  Lease Monthly:   ${extracted['leaseData']}")
                print(f"  Finance Monthly: ${extracted['financeData']}")
            print("\n  Full Response:")
            #print(json.dumps(data, indent=2) if data else "  No data returned")
            

            all_results.append({
                "model": model_name,
                "scenario": scenario["label"],
                "params": scenario,
                "extracted": extracted,
                #"raw": data,
            })

            time.sleep(0.5)

    with open("honda_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print("\nAll results saved to honda_results.json")

    with open("honda_results.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Model", "Scenario",
            "Lease Monthly", "Lease Due at Signing", "Lease Term", "Money Factor", "Annual Mileage",
            "Finance Monthly", "Finance Amount Financed", "Finance Term", "Finance APR",
        ])
        for r in all_results:
            l = r["extracted"]["leaseData"]
            fi = r["extracted"]["financeData"]
            writer.writerow([
                r["model"], r["scenario"],
                l.get("MonthlyPayment"), l.get("TotalDueAtSigning"), l.get("Term"),
                l.get("MoneyFactor"), l.get("AnnualMileage"),
                fi.get("MonthlyPayment"), fi.get("AmountFinanced"), fi.get("Term"), fi.get("Apr"),
            ])

print("Saved to honda_results.csv")


if __name__ == "__main__":
    main()