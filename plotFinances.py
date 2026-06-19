"""
plot_finance_scenarios.py

Produces two figures per car model:
  1. Finance cumulative spend — first 3 scenarios (down payment comparison)
  2. Lease cumulative spend  — last 2 scenarios (mileage comparison)

Usage:
    python plot_finance_scenarios.py
"""

import csv
import os
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker


# ── Load CSV ──────────────────────────────────────────────────────────────────

def load_csv(path):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            parsed = {}
            for k, v in row.items():
                v = v.strip()
                try:
                    parsed[k] = float(v)
                except ValueError:
                    parsed[k] = v
            rows.append(parsed)
    return rows


BASE = os.path.join(os.path.dirname(__file__), "output")
schedule = load_csv(os.path.join(BASE, "yearly_schedule.csv"))

# ── Config ────────────────────────────────────────────────────────────────────

models = list(dict.fromkeys(r["Model"] for r in schedule))
all_scenarios = list(dict.fromkeys(r["Scenario"] for r in schedule))

# First 3 scenarios → finance comparison
FINANCE_SCENARIOS = all_scenarios[:3]
# Last 2 scenarios → lease mileage comparison
LEASE_SCENARIOS = all_scenarios[-2:]

LEASE_LABELS = [
    "Lease · 15k mi/yr, $5k down",
    "Lease · 10k mi/yr, $5k down",
]
FINANCE_LABEL = "Finance · $5k down (ref)"
FINANCE_SCENARIO_LABELS = [
    "$0 down",
    "$2.5k down",
    "$5k down",
]
FINANCE_SCENARIO_LABELS = [
    "$0 down",
    "$2.5k down",
    "$5k down",
]
STYLES = ["-", "--", ":"]
COLORS = ["#378ADD", "#1D9E75", "#E07B39"]
BG    = "#F5F5F3"
GRID  = "#E0DFD9"
TEXT  = "#1A1A18"
MUTED = "#6B6B67"

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_rows(model, scenario):
    return sorted(
        [r for r in schedule if r["Model"] == model and r["Scenario"] == scenario],
        key=lambda r: r["Year"]
    )

def plot_figure(model, scenario_list, y_col, title_prefix, file_suffix, vline_label=None, vline_x=None):
    fig, ax = plt.subplots(figsize=(7, 5), facecolor=BG)
    ax.set_facecolor(BG)
    fig.suptitle(f"{title_prefix}\n{model}", fontsize=12, fontweight="600", color=TEXT)

    n = len(scenario_list)
    offsets = [18, 0, -18][:n]

    for i, scenario in enumerate(scenario_list):
        rows = get_rows(model, scenario)
        if not rows:
            continue
        years = [int(r["Year"]) for r in rows]
        values = [r[y_col] for r in rows]
        final = values[-1]

        ax.plot(years, values,
                color=COLORS[i], linestyle=STYLES[i], linewidth=2,
                marker="o", markersize=6,
                label=f"{FINANCE_SCENARIO_LABELS[i]}  (total: ${final:,.0f})")

        ax.annotate(f"${final:,.0f}",
                    xy=(years[-1], final),
                    xytext=(8, offsets[i]), textcoords="offset points",
                    fontsize=8.5, color=COLORS[i], va="center")

    if vline_x:
        ax.axvline(x=vline_x, color=MUTED, linewidth=0.8, linestyle="--", alpha=0.5)
        ax.text(vline_x + 0.05, ax.get_ylim()[0], vline_label or "",
                fontsize=7.5, color=MUTED, va="bottom")

    ax.set_xlabel("Year", fontsize=10, color=MUTED)
    ax.set_ylabel("Cumulative Spend ($)", fontsize=10, color=MUTED)
    ax.set_xticks(range(1, 7))
    ax.set_xticklabels([f"Yr {y}" for y in range(1, 7)])
    ax.set_xlim(0.5, 7.0)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(GRID)
    ax.legend(fontsize=9, framealpha=0, labelcolor=MUTED, loc="upper left")

    safe_name = model.replace(" ", "_").replace("/", "_")
    out_path = os.path.join(BASE, f"{file_suffix}_{safe_name}.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=BG)
    print(f"Saved → {out_path}")
    plt.show()
    plt.close()

# ── Generate figures ──────────────────────────────────────────────────────────

for model in models:
    # Figure 1: Finance cumulative — first 3 scenarios
    plot_figure(
        model=model,
        scenario_list=FINANCE_SCENARIOS,
        y_col="FinanceCumulative",
        title_prefix="Finance — Cumulative Spend by Down Payment",
        file_suffix="finance_scenarios",
        vline_x=5,
        vline_label="loan done",
    )

    # Figure 2: Lease cumulative — last 2 scenarios (mileage comparison)
    fig, ax = plt.subplots(figsize=(9, 5), facecolor=BG)
    ax.set_facecolor(BG)
    fig.suptitle(f"Lease — Cumulative Spend by Mileage Tier\n{model}", fontsize=12, fontweight="600", color=TEXT)

    # Collect all final values so we can sort and stagger cleanly
    lease_finals = []
    for i, scenario in enumerate(LEASE_SCENARIOS):
        rows = get_rows(model, scenario)
        if not rows:
            continue
        years = [int(r["Year"]) for r in rows]
        values = [r["LeaseCumulative"] for r in rows]
        lease_finals.append((values[-1], i, scenario, years, values))

    fin_ref_scenario = all_scenarios[-1]
    fin_rows = get_rows(model, fin_ref_scenario)
    fin_final = fin_rows[-1]["FinanceCumulative"] if fin_rows else None

    # Sort all 3 final values to assign vertical offsets without overlap
    all_finals = sorted(
        [(v, "lease", i, LEASE_LABELS[i], y, vals) for v, i, s, y, vals in lease_finals] +
        ([(fin_final, "finance", 2, FINANCE_LABEL,
           [int(r["Year"]) for r in fin_rows],
           [r["FinanceCumulative"] for r in fin_rows])] if fin_rows else []),
        key=lambda x: x[0]
    )

    n_lines = len(all_finals)
    y_offsets = [-16, 0, 16] if n_lines == 3 else [-12, 12]

    for rank, (final, kind, idx, label, years, values) in enumerate(all_finals):
        color = COLORS[idx]
        if kind == "lease":
            style = STYLES[idx]
            lw = 2; ms = 6; marker = "o"
        else:
            style = "--"; lw = 1.5; ms = 5; marker = "s"

        ax.plot(years, values, color=color, linestyle=style, linewidth=lw,
                marker=marker, markersize=ms, label=f"{label}  (${final:,.0f})")

        ax.annotate(f"${final:,.0f}",
                    xy=(years[-1], final),
                    xytext=(10, y_offsets[rank]),
                    textcoords="offset points",
                    fontsize=8.5, color=color, va="center", fontweight="500")

    ax.axvline(x=5, color=MUTED, linewidth=0.8, linestyle="--", alpha=0.5)
    ax.text(5.05, ax.get_ylim()[0], "loan done", fontsize=7.5, color=MUTED, va="bottom")
    ax.set_xlabel("Year", fontsize=10, color=MUTED)
    ax.set_ylabel("Cumulative Spend ($)", fontsize=10, color=MUTED)
    ax.set_xticks(range(1, 7))
    ax.set_xticklabels([f"Yr {y}" for y in range(1, 7)])
    ax.set_xlim(0.5, 7.8)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(GRID)
    ax.legend(fontsize=9, framealpha=0, labelcolor=MUTED, loc="upper left")

    safe_name = model.replace(" ", "_").replace("/", "_")
    out_path = os.path.join(BASE, f"lease_mileage_{safe_name}.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=BG)
    print(f"Saved → {out_path}")
    plt.show()
    plt.close()