"""
plot_finance_scenarios.py

Reads output/yearly_schedule.csv and plots finance cumulative spend over 6 years
for each scenario, one graph per car model.

Usage:
    python plot_finance_scenarios.py

Output:
    output/finance_scenarios.png
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

# ── Organise ──────────────────────────────────────────────────────────────────

models    = list(dict.fromkeys(r["Model"]    for r in schedule))
scenarios = list(dict.fromkeys(r["Scenario"] for r in schedule))

COLORS = ["#378ADD", "#1D9E75", "#E07B39"]
STYLES = ["-", "--", ":"]

# ── Plot ──────────────────────────────────────────────────────────────────────

BG   = "#F5F5F3"
GRID = "#E0DFD9"
TEXT = "#1A1A18"
MUTED = "#6B6B67"

for model in models:
    fig, ax = plt.subplots(figsize=(7, 5), facecolor=BG)
    ax.set_facecolor(BG)

    fig.suptitle(f"Finance — Cumulative Spend by Down Payment Scenario\n{model}",
                 fontsize=12, fontweight="600", color=TEXT)

    for i, scenario in enumerate(scenarios):
        rows = sorted(
            [r for r in schedule if r["Model"] == model and r["Scenario"] == scenario],
            key=lambda r: r["Year"]
        )
        years = [int(r["Year"]) for r in rows]
        cumulative = [r["FinanceCumulative"] for r in rows]
        final_total = cumulative[-1]

        ax.plot(years, cumulative,
                color=COLORS[i], linestyle=STYLES[i], linewidth=2,
                marker="o", markersize=6,
                label=f"{scenario}  (total: ${final_total:,.0f})")

        offsets = [18, 0, -18]
        ax.annotate(f"${final_total:,.0f}",
                    xy=(years[-1], final_total),
                    xytext=(8, offsets[i]), textcoords="offset points",
                    fontsize=8.5, color=COLORS[i], va="center")

    # Mark loan payoff at year 5
    ax.axvline(x=5, color=MUTED, linewidth=0.8, linestyle="--", alpha=0.5)
    ymin = ax.get_ylim()[0]
    ax.text(5.05, ymin, "loan done", fontsize=7.5, color=MUTED, va="bottom")

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
    out_path = os.path.join(BASE, f"finance_scenarios_{safe_name}.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=BG)
    print(f"Saved → {out_path}")
    plt.show()