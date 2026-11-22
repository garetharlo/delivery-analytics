"""Step 1 — incident-level dataset from the UCI 498 ITSM event log.

Source: 'Incident management process enriched event log' (UCI ML Repository, id 498)
Real ITSM tool export (ServiceNow-like schema), anonymised labels, 141,712 events.

Produces data/incidents.csv: one row per incident with volume, handle time and
effort-relevant attributes.
"""
import os
import zipfile
import pandas as pd

RAW = "/workspace/hermes/cache/scratch/uci498.zip"
OUT = "/opt/data/delivery-analytics/data"
os.makedirs(OUT, exist_ok=True)

z = zipfile.ZipFile(RAW)
df = pd.read_csv(z.open("incident_event_log.csv"))

for c in ["opened_at", "sys_created_at", "sys_updated_at", "resolved_at", "closed_at"]:
    df[c] = pd.to_datetime(df[c], format="%d/%m/%Y %H:%M", errors="coerce")

df["number"] = df["number"].astype(str)
print(f"{len(df):,} events / {df['number'].nunique():,} incidents")

def mode_or_na(s):
    s = s.dropna()
    s = s[s.astype(str).str.strip() != "?"]
    return s.mode().iloc[0] if len(s.mode()) else ""

g = df.groupby("number")
inc = pd.DataFrame({
    "opened_at": g["opened_at"].min(),
    "resolved_at": g["resolved_at"].min(),
    "closed_at": g["closed_at"].min(),
    "priority": g["priority"].apply(mode_or_na),
    "impact": g["impact"].apply(mode_or_na),
    "urgency": g["urgency"].apply(mode_or_na),
    "category": g["category"].apply(mode_or_na),
    "subcategory": g["subcategory"].apply(mode_or_na),
    "symptom": g["u_symptom"].apply(mode_or_na),
    "assignment_group": g["assignment_group"].apply(mode_or_na),
    "contact_type": g["contact_type"].apply(mode_or_na),
    "reopen_count": g["reopen_count"].max(),
    "reassignment_count": g["reassignment_count"].max(),
    "made_sla": g["made_sla"].max(),
    "resolved_by": g["resolved_by"].apply(mode_or_na),
    "cmdb_ci": g["cmdb_ci"].apply(mode_or_na),
})

inc["resolution_h"] = (inc["resolved_at"] - inc["opened_at"]).dt.total_seconds() / 3600
# incidents that were closed but never "resolved" (cancelled/duplicate) have no handle time
inc["closed_h"] = (inc["closed_at"] - inc["opened_at"]).dt.total_seconds() / 3600

inc = inc.reset_index()
inc.to_csv(f"{OUT}/incidents.csv", index=False)
print(inc.head(3).to_string()[:600])
print("\nshape:", inc.shape)
print("with resolution time:", inc["resolution_h"].notna().sum(),
      f"({inc['resolution_h'].notna().mean():.1%})")
print("reopen>0:", (inc["reopen_count"].fillna(0) > 0).mean().round(4),
      "| reassigned>0:", (inc["reassignment_count"].fillna(0) > 0).mean().round(4))
print("categories:", inc["category"].replace("", pd.NA).dropna().nunique(),
      "| subcategories:", inc["subcategory"].replace("", pd.NA).dropna().nunique(),
      "| groups:", inc["assignment_group"].replace("", pd.NA).dropna().nunique())
print("label coverage: category %.1f%% subcategory %.1f%% group %.1f%%" % (
    100 * (inc["category"] != "").mean(), 100 * (inc["subcategory"] != "").mean(),
    100 * (inc["assignment_group"] != "").mean()))
