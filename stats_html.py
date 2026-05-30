"""
stats_html.py — Option B: HTML Chart Generator
================================================
Run this file separately to generate a standalone HTML report
with interactive Chart.js charts. No extra libraries needed.

Usage:
    python stats_html.py

Output:
    data/stats_report.html   (open this file in any web browser)

This reads from the same data/ folder as fitnessproject.py.
"""

# NEW CONCEPT: import statements (same as fitnessproject.py)
import json
import os
from datetime import date, timedelta

# ─────────────────────────────────────────────────────────────────────────────
# FILE PATHS — must match fitnessproject.py locations  [PERSON E]
# ─────────────────────────────────────────────────────────────────────────────
DATA_DIR       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
BOOKINGS_FILE  = os.path.join(DATA_DIR, "bookings.json")
PURCHASES_FILE = os.path.join(DATA_DIR, "purchases.json")
TRAINERS_FILE  = os.path.join(DATA_DIR, "trainers.json")
OUTPUT_FILE    = os.path.join(DATA_DIR, "stats_report.html")

CLASS_TYPES  = ["Pilates", "Yoga", "MMA", "Boxing", "KPop Fitness"]
CLASS_COLORS = ["#1976D2","#388E3C","#D32F2F","#F57C00","#7B1FA2"]
CLASS_REVENUE = {"Pilates": 22, "Yoga": 22, "MMA": 35, "Boxing": 35, "KPop Fitness": 20}
STUDIO_COST   = {"Studio 1": 20, "Studio 2": 20, "Studio 3": 12, "Studio 4": 12}
MONTHLY_RENTAL = 17000


def load_json(filepath, default):
    """Load JSON file; return default if file missing."""
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return default


def compute_stats(cutoff_days):
    """Compute all four statistics for the given day offset cutoff."""
    # NEW CONCEPT: date.today() and timedelta
    today  = date.today()
    cutoff = today - timedelta(days=cutoff_days)

    bookings  = load_json(BOOKINGS_FILE,  [])
    purchases = load_json(PURCHASES_FILE, [])
    trainers  = load_json(TRAINERS_FILE,  [])

    # NEW CONCEPT: Dictionary comprehension — initialise every type to 0
    reg_counts = {ct: 0 for ct in CLASS_TYPES}
    pkg_counts  = {ct: 0 for ct in CLASS_TYPES}
    pkg_revenue = {ct: 0 for ct in CLASS_TYPES}
    trainer_counts = {}

    for b in bookings:
        if date.fromisoformat(b["date"]) >= cutoff:
            if b["type"] in reg_counts:
                reg_counts[b["type"]] += 1
            # NEW CONCEPT: dict.get(key, 0) + 1 — counting without KeyError
            trainer_counts[b["trainer"]] = trainer_counts.get(b["trainer"], 0) + 1

    for p in purchases:
        if date.fromisoformat(p["date"]) >= cutoff:
            if p["type"] in pkg_counts:
                pkg_counts[p["type"]]  += 1
                pkg_revenue[p["type"]] += p["price"]

    # Top 5 trainers — sorted descending, sliced to 5
    # NEW CONCEPT: sorted() with lambda + [:5] slice
    top5 = sorted(trainer_counts.items(), key=lambda x: -x[1])[:5]

    # Profit calculation
    trainer_rates = {t["name"]: t["rate"] for t in trainers}
    slot_groups   = {}
    for b in bookings:
        if date.fromisoformat(b["date"]) < cutoff:
            continue
        sk = b.get("slot_key", "")
        if not sk:
            continue
        if sk not in slot_groups:
            slot_groups[sk] = {"count": 0, "type": b["type"],
                              "studio": b["studio"], "trainer": b["trainer"],
                              "date": b["date"]}
        slot_groups[sk]["count"] += 1

    revenue = elec_cost = trainer_cost = 0
    # NEW CONCEPT: set() — stores unique (year, month) tuples only
    class_months = set()
    for sk, info in slot_groups.items():
        revenue      += info["count"] * CLASS_REVENUE.get(info["type"], 0)
        elec_cost    += STUDIO_COST.get(info["studio"], 0)
        trainer_cost += trainer_rates.get(info["trainer"], 0)
        d = date.fromisoformat(info["date"])
        class_months.add((d.year, d.month))

    rental = len(class_months) * MONTHLY_RENTAL
    profit = revenue - rental - elec_cost - trainer_cost

    return {
        "reg_counts":   reg_counts,
        "pkg_counts":   pkg_counts,
        "pkg_revenue":  pkg_revenue,
        "top5":         top5,
        "revenue":      revenue,
        "rental":       rental,
        "elec_cost":    elec_cost,
        "trainer_cost": trainer_cost,
        "profit":       profit,
        "months":       len(class_months),
    }


def to_js_array(lst):
    """Convert a Python list to a JavaScript array string."""
    # NEW CONCEPT: json.dumps() — converts a Python value to a JSON-compatible string
    return json.dumps(lst)


def generate_html():
    """Build and write the stats_report.html file."""
    today = date.today()

    # Compute stats for all three periods
    stats_4w  = compute_stats(28)
    stats_3m  = compute_stats(91)
    stats_12m = compute_stats(365)

    # NEW CONCEPT: Multi-line string (triple quotes)
    # Used here to write a large block of HTML/JavaScript as one string.
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Arnold's Fitness — Statistics Report</title>
<!-- Chart.js loaded from a CDN (Content Delivery Network) — no installation needed -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f0f2f5; color: #222; }}
  header {{ background: linear-gradient(135deg,#1a237e,#1565c0); color: #fff;
            padding: 28px 40px; }}
  header h1 {{ font-size: 2rem; }}
  header p  {{ opacity: .8; margin-top: 6px; }}
  .tabs {{ display: flex; gap: 8px; padding: 20px 40px 0; background: #fff;
          border-bottom: 2px solid #e0e0e0; }}
  .tab {{ padding: 10px 22px; border-radius: 8px 8px 0 0; cursor: pointer;
          font-weight: 600; background: #e8eaf6; color: #3949ab; border: none;
          font-size: 0.95rem; transition: all .2s; }}
  .tab.active, .tab:hover {{ background: #1565c0; color: #fff; }}
  .panel {{ display: none; padding: 30px 40px; }}
  .panel.active {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
  .card {{ background: #fff; border-radius: 12px; padding: 24px;
          box-shadow: 0 2px 8px rgba(0,0,0,.08); }}
  .card h3 {{ font-size: 1rem; color: #555; margin-bottom: 16px; font-weight: 600;
              text-transform: uppercase; letter-spacing: .05em; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(2,1fr); gap: 12px;
              grid-column: 1/-1; }}
  .kpi {{ background: #fff; border-radius: 10px; padding: 18px 22px;
          box-shadow: 0 2px 8px rgba(0,0,0,.07); }}
  .kpi .val {{ font-size: 2rem; font-weight: 700; color: #1565c0; }}
  .kpi .lbl {{ font-size: .85rem; color: #777; margin-top: 4px; }}
  .profit-pos {{ color: #2e7d32 !important; }}
  .profit-neg {{ color: #c62828 !important; }}
  canvas {{ max-height: 280px; }}
  footer {{ text-align: center; padding: 24px; color: #999; font-size: .85rem; }}
</style>
</head>
<body>

<header>
  <h1>@@@@ Arnold's Fitness — Statistics Dashboard @@@@</h1>
  <p>Generated on {today.strftime('%A, %d %B %Y')} &nbsp;|&nbsp;
    Data from Nov 2025 onwards &nbsp;|&nbsp;
    Use the tabs to switch time periods.</p>
</header>

<div class="tabs">
  <button class="tab active" onclick="showTab('w4')">Last 4 Weeks</button>
  <button class="tab"        onclick="showTab('m3')">Last 3 Months</button>
  <button class="tab"        onclick="showTab('y1')">Last 12 Months</button>
</div>
"""

    # Generate one panel per time period
    for tab_id, label, s in [
        ("w4", "Last 4 Weeks",    stats_4w),
        ("m3", "Last 3 Months",   stats_3m),
        ("y1", "Last 12 Months",  stats_12m),
    ]:
        active = "active" if tab_id == "w4" else ""
        types  = CLASS_TYPES
        colors = CLASS_COLORS

        reg_vals    = [s["reg_counts"][ct]  for ct in types]
        pkg_vals    = [s["pkg_counts"][ct]  for ct in types]
        rev_vals    = [s["pkg_revenue"][ct] for ct in types]
        top5_names  = [t[0] for t in s["top5"]]
        top5_vals   = [t[1] for t in s["top5"]]
        profit_sign = "profit-pos" if s["profit"] >= 0 else "profit-neg"

        html += f"""
<div id="{tab_id}" class="panel {active}">

  <!-- KPI cards -->
  <div class="kpi-grid">
    <div class="kpi"><div class="val">{sum(reg_vals):,}</div><div class="lbl">Total Class Bookings</div></div>
    <div class="kpi"><div class="val">{sum(pkg_vals):,}</div><div class="lbl">Packages Sold</div></div>
    <div class="kpi"><div class="val">${sum(rev_vals):,.0f}</div><div class="lbl">Package Revenue</div></div>
    <div class="kpi"><div class="val {profit_sign}">${s['profit']:,.0f}</div><div class="lbl">Net Profit (SGD)</div></div>
  </div>

  <!-- Registrations bar chart -->
  <div class="card">
    <h3>Class Registrations by Type</h3>
    <canvas id="reg_{tab_id}"></canvas>
  </div>

  <!-- Packages pie chart -->
  <div class="card">
    <h3>Packages Purchased by Type</h3>
    <canvas id="pkg_{tab_id}"></canvas>
  </div>

  <!-- Top 5 trainers -->
  <div class="card">
    <h3>Top 5 Trainers by Bookings</h3>
    <canvas id="top_{tab_id}"></canvas>
  </div>

  <!-- Profit breakdown -->
  <div class="card">
    <h3>Profit Breakdown</h3>
    <canvas id="pnl_{tab_id}"></canvas>
  </div>

</div>

<script>
(function(){{
  // Registrations horizontal bar chart
  new Chart(document.getElementById("reg_{tab_id}"), {{
    type: "bar",
    data: {{
      labels: {to_js_array(types)},
      datasets: [{{ label: "Bookings", data: {to_js_array(reg_vals)},
                  backgroundColor: {to_js_array(colors)}, borderRadius: 6 }}]
    }},
    options: {{ indexAxis: "y", plugins: {{ legend: {{ display: false }} }},
              scales: {{ x: {{ beginAtZero: true }} }} }}
  }});

  // Packages doughnut chart
  new Chart(document.getElementById("pkg_{tab_id}"), {{
    type: "doughnut",
    data: {{
      labels: {to_js_array(types)},
      datasets: [{{ data: {to_js_array(pkg_vals)},
                  backgroundColor: {to_js_array(colors)}, hoverOffset: 10 }}]
    }},
    options: {{ plugins: {{ legend: {{ position: "right" }} }} }}
  }});

  // Top 5 trainers bar chart
  new Chart(document.getElementById("top_{tab_id}"), {{
    type: "bar",
    data: {{
      labels: {to_js_array(top5_names)},
      datasets: [{{ label: "Bookings", data: {to_js_array(top5_vals)},
                  backgroundColor: ["#FFD700","#C0C0C0","#CD7F32","#1976D2","#388E3C"],
                  borderRadius: 6 }}]
    }},
    options: {{ plugins: {{ legend: {{ display: false }} }},
              scales: {{ y: {{ beginAtZero: true }} }} }}
  }});

  // Profit stacked bar chart
  new Chart(document.getElementById("pnl_{tab_id}"), {{
    type: "bar",
    data: {{
      labels: ["Revenue","Rental","Electricity","Trainer Fees","Net Profit"],
      datasets: [{{ label: "SGD $",
                  data: [{s['revenue']:.0f},{-s['rental']:.0f},{-s['elec_cost']:.0f},{-s['trainer_cost']:.0f},{s['profit']:.0f}],
                  backgroundColor: [
                    "#388E3C",
                    "#D32F2F","#E57373","#EF9A9A",
                    "{'#2e7d32' if s['profit']>=0 else '#c62828'}"
                  ],
                  borderRadius: 6 }}]
    }},
    options: {{ plugins: {{ legend: {{ display: false }} }},
              scales: {{ y: {{ beginAtZero: false }} }} }}
  }});
}})();
</script>
"""

    html += """
<footer>Arnold's Fitness Management Portal — Statistics Report</footer>

<script>
function showTab(id) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  event.target.classList.add('active');
}
</script>
</body></html>"""

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        f.write(html)
    print(f"  Stats report generated: {OUTPUT_FILE}")
    print("  Open that file in any web browser to view interactive charts.")


if __name__ == "__main__":
    generate_html()
