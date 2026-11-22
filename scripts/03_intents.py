"""Step 6 (phase 2, final) — intent economics + clustering validation.

Corpus: s2pidape/support-ticket-dataset (synthetic, English slice = 250,599
tickets, 100 issue types, 11 families), with per-ticket resolution hours,
SLA-breach flag and escalation flag.

Two things are produced:
1. Validation — does free text cluster back onto the 100 known issue types?
   k-means (k=100) on cleaned text, measured by NMI / ARI / purity.
2. Economics — volume, effort and feasibility per intent, from the labels that
   the clustering just proved are recoverable from text.
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from sklearn.preprocessing import normalize

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]   # repo root; tickets.parquet lives here
SCRATCH = ROOT
OUT = ROOT
SEED = 42

BOILERPLATE = [
    r"hi team", r"hi there", r"hello,?", r"hey,?", r"good morning,?", r"dear (support|team)",
    r"i'?m having an issue", r"i am having an issue", r"been struggling with this",
    r"need some help here", r"we'?re a bit stuck", r"reaching out because",
    r"quick question", r"not sure this is the right place,? but", r"hoping you can help:?",
    r"any help appreciated", r"happy to share more detail", r"let me know what you need",
    r"please advise", r"thanks in advance", r"this is fairly urgent for us", r"this started today",
    r"it'?s been happening( since yesterday)?",
    r"on the (desktop client|mobile app|payment gateway|web platform|api platform)",
    r"\bplease\b", r"\bthanks\b", r"\bhello\b", r"\bhi\b", r"\bhey\b", r"\bregards\b",
]
CLEAN = [(re.compile(p, re.I), " ") for p in BOILERPLATE]


def clean(t: str) -> str:
    for rx, rep in CLEAN:
        t = rx.sub(rep, t)
    t = re.sub(r"[^A-Za-z0-9 %\-\.]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


df = pd.read_parquet(SCRATCH / "tickets.parquet")
df = df[df["language"] == "English"].copy()
df["resolution_time_hours"] = pd.to_numeric(df["resolution_time_hours"], errors="coerce")
df["sla_breached"] = df["sla_breached"].astype(str).str.lower().isin(["true", "1", "yes"])
df["escalated"] = df["escalated"].astype(str).str.lower().isin(["true", "1", "yes"])
df["family"] = df["issue_type_id"].astype(str).str.split("_").str[0]
df["intent"] = df["issue_type_id"].astype(str).str.replace("_", " ", regex=False)
df = df[df["issue_description"].notna() & (df["issue_description"].str.len() >= 25)].copy()
print(f"english corpus: {len(df):,} tickets, {df['issue_type_id'].nunique()} issue types, {df['family'].nunique()} families")

# ---------- 1. validation: does text recover the 100 issue types? ----------
s = df.sample(n=40_000, random_state=SEED).reset_index(drop=True)
s["clean"] = s["issue_description"].map(clean)
s = s[s["clean"].str.len() >= 18]
vec = TfidfVectorizer(max_features=30_000, ngram_range=(1, 2), min_df=2, sublinear_tf=True)
X = vec.fit_transform(s["clean"])
Z = normalize(TruncatedSVD(n_components=150, random_state=SEED).fit_transform(X))
k = s["issue_type_id"].nunique()
km = KMeans(n_clusters=k, random_state=SEED, n_init=5).fit(Z)
s["cluster"] = km.labels_

nmi = normalized_mutual_info_score(s["issue_type_id"], s["cluster"])
ari = adjusted_rand_score(s["issue_type_id"], s["cluster"])
# purity: how often the modal true issue type inside a cluster is the cluster's label
pur = s.groupby("cluster")["issue_type_id"].agg(lambda x: x.value_counts().iloc[0] / len(x))
wpur = float((pur * s.groupby("cluster").size()).sum() / len(s))
# and the reverse: how concentrated each issue type is in one cluster
rev_pur = s.groupby("issue_type_id")["cluster"].agg(lambda x: x.value_counts().iloc[0] / len(x))
print(f"clustering (k={k}) vs true issue types: NMI {nmi:.3f} | ARI {ari:.3f} | "
      f"cluster purity {wpur:.3f} | issue-type concentration {rev_pur.mean():.3f}")

# ---------- 2. economics per intent ----------
FEASIBILITY = {
    "authentication": "automatable",   # password/MFA/locked/expired/token resets
    "onboarding": "automatable",       # how-to, configure, invite, where-do-I-find
    "billing": "automatable",          # invoice copy, email change, payment method
    "subscription": "automatable",     # renewal toggle, plan change, seats
    "refunds": "assisted",             # policy decision, agent stays in the loop
    "account": "assisted",             # profile/data requests need identity checks
    "integrations": "assisted",        # API how-to / connector setup, then human
    "security": "assisted",            # access review, docs requests, IP rules
    "performance": "human-only",       # diagnosis required
    "data": "human-only",              # sync corruption / missing records
    "bugs": "human-only",              # defect triage
}
tab = df.groupby(["family", "intent"]).agg(
    tickets=("ticket_id", "count"),
    median_res_h=("resolution_time_hours", "median"),
    mean_res_h=("resolution_time_hours", "mean"),
    total_h=("resolution_time_hours", "sum"),
    sla_breach=("sla_breached", "mean"),
    escalated=("escalated", "mean"),
).reset_index()
tab["feasibility"] = tab["family"].map(FEASIBILITY)
tab["share_of_volume"] = tab["tickets"] / tab["tickets"].sum()
tab["share_of_effort"] = tab["total_h"] / tab["total_h"].sum()
tab = tab.sort_values("total_h", ascending=False).reset_index(drop=True)
tab["effort_cum"] = tab["share_of_effort"].cumsum()

for c in ["median_res_h", "mean_res_h", "total_h", "share_of_volume", "share_of_effort",
          "effort_cum", "sla_breach", "escalated"]:
    tab[c] = tab[c].round(3 if c in ("share_of_volume", "share_of_effort", "effort_cum", "sla_breach", "escalated") else 2)

tab.to_csv(OUT / "data/intents_economics.csv", index=False)

fam = tab.groupby("family").agg(
    tickets=("tickets", "sum"), total_h=("total_h", "sum"),
    median_res_h=("median_res_h", "median"), sla_breach=("sla_breach", "mean"),
    escalated=("escalated", "mean"), feasibility=("feasibility", "first"),
).sort_values("total_h", ascending=False)
fam["share_of_volume"] = (fam["tickets"] / fam["tickets"].sum()).round(3)
fam["share_of_effort"] = (fam["total_h"] / fam["total_h"].sum()).round(3)
fam.to_csv(OUT / "data/effort_by_intent_family.csv")

print("\n=== effort by intent family ===")
print((fam[["tickets", "share_of_volume", "median_res_h", "share_of_effort", "sla_breach", "escalated", "feasibility"]])
      .assign(sla_breach=lambda d: (d.sla_breach * 100).round(1), escalated=lambda d: (d.escalated * 100).round(1),
              share_of_volume=lambda d: (d.share_of_volume * 100).round(1), share_of_effort=lambda d: (d.share_of_effort * 100).round(1))
      .to_string())

print("\n=== top 12 intents by effort ===")
print(tab.head(12)[["intent", "tickets", "share_of_volume", "median_res_h", "share_of_effort",
                    "sla_breach", "escalated", "feasibility"]]
      .assign(share_of_volume=lambda d: (d.share_of_volume * 100).round(1),
              share_of_effort=lambda d: (d.share_of_effort * 100).round(1),
              sla_breach=lambda d: (d.sla_breach * 100).round(1),
              escalated=lambda d: (d.escalated * 100).round(1)).to_string(index=False))

auto_h = fam.loc[fam["feasibility"] == "automatable", "total_h"].sum()
assist_h = fam.loc[fam["feasibility"] == "assisted", "total_h"].sum()
human_h = fam.loc[fam["feasibility"] == "human-only", "total_h"].sum()
tot_h = fam["total_h"].sum()
print(f"\neffort split: automatable {auto_h/tot_h:.1%} | assisted {assist_h/tot_h:.1%} | human-only {human_h/tot_h:.1%}")
for pct in (0.4, 0.6, 0.8):
    saved = auto_h * pct
    print(f"  at {pct:.0%} automation of automatable work: {saved/tot_h:.1%} of total elapsed effort removed "
          f"({saved:,.0f} of {tot_h:,.0f} elapsed hours)")

# concentration
print(f"\ntop 10 intents = {tab['share_of_effort'].head(10).sum():.1%} of effort, "
      f"{tab['share_of_volume'].head(10).sum():.1%} of volume")

# ---------- charts ----------
top = tab.head(15).iloc[::-1]
colors = {"automatable": "#27ae60", "assisted": "#f39c12", "human-only": "#c0392b"}
fig, ax = plt.subplots(figsize=(10, 6.5))
ax.barh(top["intent"], top["share_of_effort"] * 100, color=[colors[f] for f in top["feasibility"]])
ax.set_xlabel("% of total resolution effort")
ax.set_title("Top 15 intents by effort, coloured by automation feasibility")
ax.tick_params(axis="y", labelsize=8)
for i, v in enumerate(top["share_of_effort"] * 100):
    ax.text(v + 0.2, i, f"{v:.1f}%", va="center", fontsize=7)
ax.set_xlim(0, (top["share_of_effort"] * 100).max() * 1.18)
plt.tight_layout()
plt.savefig(OUT / "charts/intents_pareto.png", dpi=140)
plt.close()

fig, ax = plt.subplots(figsize=(8, 5))
vals = [auto_h/tot_h*100, assist_h/tot_h*100, human_h/tot_h*100]
labs = ["automatable\ndeflection/self-service", "assisted\nagent in the loop", "human-only\ndiagnosis"]
ax.bar(labs, vals, color=["#27ae60", "#f39c12", "#c0392b"])
for i, v in enumerate(vals):
    ax.text(i, v + 1, f"{v:.0f}%", ha="center")
ax.set_ylabel("% of resolution effort")
ax.set_title("Where automation could cut effort (synthetic corpus, 250k English tickets)")
plt.tight_layout()
plt.savefig(OUT / "charts/feasibility_split.png", dpi=140)
plt.close()

json.dump({
    "validation": {"nmi": round(nmi, 3), "ari": round(ari, 3),
                   "cluster_purity": round(wpur, 3),
                   "issue_type_concentration": round(float(rev_pur.mean()), 3),
                   "n_issue_types": int(k), "sample": int(len(s)),
                   "caveat": "one canonical sentence per issue type in this synthetic generator, so recovery is near-deterministic and says nothing about messy real text"},
    "effort_split": {"automatable_pct": round(auto_h/tot_h*100, 1),
                     "assisted_pct": round(assist_h/tot_h*100, 1),
                     "human_only_pct": round(human_h/tot_h*100, 1),
                     "total_elapsed_hours": round(float(tot_h), 0)},
    "savings_pct_of_total_effort": {f"{int(p*100)}pct_automation": round(float(auto_h*p/tot_h*100), 1)
                                    for p in (0.4, 0.6, 0.8)},
}, open(OUT / "data/phase2_metrics.json", "w"), indent=2)

print("\nwrote data/intents_economics.csv, data/effort_by_intent_family.csv, data/phase2_metrics.json, charts/")
