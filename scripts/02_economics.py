"""Step 2 — effort economics: which contact drivers consume the elapsed time.

V1 uses elapsed incident time (opened -> resolved) as the effort proxy, plus
reassignment count as a proxy for touch-work, because the public event log has
no explicit handle-time field. Both limitations are reported in FINDINGS.md.
"""
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = "/opt/data/delivery-analytics"
inc = pd.read_csv(f"{BASE}/data/incidents.csv", parse_dates=["opened_at", "resolved_at", "closed_at"])
os.makedirs(f"{BASE}/data", exist_ok=True)
os.makedirs(f"{BASE}/charts", exist_ok=True)

# only incidents that were actually resolved carry a comparable timer
eff = inc[inc["resolution_h"].notna() & (inc["resolution_h"] >= 0)].copy()
print(f"effort universe: {len(eff):,} resolved incidents "
      f"({len(eff)/len(inc):.1%} of all), total elapsed {eff['resolution_h'].sum():,.0f} h")

eff["reassigned"] = eff["reassignment_count"].fillna(0) > 0
eff["reopened"] = eff["reopen_count"].fillna(0) > 0


def driver_table(df, key, min_n=30):
    t = df.groupby(key).agg(
        tickets=("number", "count"),
        median_h=("resolution_h", "median"),
        total_h=("resolution_h", "sum"),
        reopen_rate=("reopened", "mean"),
        reassign_rate=("reassigned", "mean"),
        sla_rate=("made_sla", "mean"),
    )
    t = t[t["tickets"] >= min_n].copy()
    t["vol_share"] = t["tickets"] / t["tickets"].sum()
    t["effort_share"] = t["total_h"] / t["total_h"].sum()
    t = t.sort_values("total_h", ascending=False)
    t["effort_cum"] = t["effort_share"].cumsum()
    t["vol_cum"] = t["vol_share"].cumsum()
    return t


cat = driver_table(eff, "category")
sub = driver_table(eff, "subcategory", min_n=15)
grp = driver_table(eff, "assignment_group", min_n=15)

cat.to_csv(f"{BASE}/data/effort_by_category.csv")
sub.to_csv(f"{BASE}/data/effort_by_subcategory.csv")
grp.to_csv(f"{BASE}/data/effort_by_group.csv")

print("\n=== TOP 12 CATEGORIES BY ELAPSED EFFORT ===")
print((cat.head(12)[["tickets", "vol_share", "median_h", "total_h", "effort_share",
                     "effort_cum", "reopen_rate", "reassign_rate", "sla_rate"]]
       .assign(vol_share=lambda d: (d.vol_share * 100).round(1),
               effort_share=lambda d: (d.effort_share * 100).round(1),
               effort_cum=lambda d: (d.effort_cum * 100).round(1),
               median_h=lambda d: d.median_h.round(1),
               total_h=lambda d: d.total_h.round(0),
               reopen_rate=lambda d: (d.reopen_rate * 100).round(1),
               reassign_rate=lambda d: (d.reassign_rate * 100).round(1),
               sla_rate=lambda d: (d.sla_rate * 100).round(1))).to_string())

print("\npareto at category level: top 5 = %.0f%% of volume, %.0f%% of effort"
      % (cat["vol_cum"].iloc[4] * 100, cat["effort_cum"].iloc[4] * 100))
print("top 10 = %.0f%% of volume, %.0f%% of effort"
      % (cat["vol_cum"].iloc[min(9, len(cat) - 1)] * 100, cat["effort_cum"].iloc[min(9, len(cat) - 1)] * 100))

print("\n=== TOP 10 SUBCATEGORIES BY EFFORT ===")
print((sub.head(10)[["tickets", "median_h", "total_h", "effort_share", "reassign_rate"]]
       .assign(effort_share=lambda d: (d.effort_share * 100).round(1),
               median_h=lambda d: d.median_h.round(1),
               total_h=lambda d: d.total_h.round(0),
               reassign_rate=lambda d: (d.reassign_rate * 100).round(1))).to_string())

# reassignment: extra elapsed time
re_h = eff.loc[eff["reassigned"], "resolution_h"]
no_h = eff.loc[~eff["reassigned"], "resolution_h"]
extra = re_h.median() - no_h.median()
print(f"\nreassignment: {eff['reassigned'].mean():.1%} of incidents, "
      f"median {re_h.median():.1f} h vs {no_h.median():.1f} h unreassigned "
      f"(+{extra:.1f} h, {extra*re_h.median()**0 and 0 or 0:.0f})")
print(f"elapsed hours sitting in reassigned incidents: {re_h.sum():,.0f} h "
      f"({re_h.sum()/eff['resolution_h'].sum():.1%} of all elapsed)")

# SLA
sla_by_cat = (eff.groupby("category")["made_sla"].agg(["mean", "count"])
              .query("count >= 100").sort_values("mean"))
print("\nworst SLA categories (>=100 tickets):")
print((sla_by_cat.head(6).assign(mean=lambda d: (d['mean'] * 100).round(1))).to_string())

# ---- charts
top = cat.head(12).iloc[::-1]
fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(top.index, top["effort_share"] * 100, color="#c0392b")
ax.set_xlabel("% of total elapsed effort")
ax.set_title("Where the hours go — top 12 categories (UCI 498 incident log)")
for i, (v, n) in enumerate(zip(top["effort_share"] * 100, top["tickets"])):
    ax.text(v + 0.3, i, f"{v:.0f}%  ({n:,} tickets)", va="center", fontsize=8)
ax.set_xlim(0, (top["effort_share"] * 100).max() * 1.25)
plt.tight_layout()
plt.savefig(f"{BASE}/charts/pareto_effort_by_category.png", dpi=140)
plt.close()

fig, ax = plt.subplots(figsize=(9, 5))
order = cat.sort_values("effort_cum").head(15)
ax.plot(range(1, len(order) + 1), order["effort_cum"] * 100, marker="o", color="#2c3e50")
ax.bar(range(1, len(order) + 1), order["vol_share"] * 100, alpha=0.35, color="#7f8c8d")
ax.set_xlabel("rank (categories, sorted by effort)")
ax.set_ylabel("% (bar = volume share, line = cumulative effort)")
ax.set_title("Effort concentrates far more than volume")
plt.tight_layout()
plt.savefig(f"{BASE}/charts/pareto_curve.png", dpi=140)
plt.close()

fig, ax = plt.subplots(figsize=(9, 6))
s = sla_by_cat.head(10).iloc[::-1]
ax.barh(s.index, s["mean"] * 100, color="#e67e22")
ax.set_xlabel("SLA attainment %")
ax.set_title("Worst SLA attainment categories (>=100 tickets)")
ax.set_xlim(0, 100)
plt.tight_layout()
plt.savefig(f"{BASE}/charts/sla_by_category.png", dpi=140)
plt.close()

print("\nwrote charts + csvs to", BASE)
