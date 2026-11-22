# delivery-analytics

Where do service desk hours actually go — and how much of that work is removable?

This repo takes a real ITSM incident event log and answers that with numbers: effort per contact driver, the volume-vs-effort gap, and the cost of reassignment. Written for service delivery management, not for a Kaggle leaderboard.

**Read [`FINDINGS.md`](FINDINGS.md) first** — it is one page and contains every headline number.

## Headline results (UCI 498, 24,918 incidents)

- Top 10 categories = **69% of volume but 79% of elapsed effort**
- **32% of tickets** close in under an hour but hold **~0% of the hours**; **35%** run ≥72 h and hold **96%**
- **49% of incidents** are reassigned; they contain **73% of all elapsed hours** (median 79.9 h vs 0.7 h)
- **99% of contacts are phone**, 0.7% self-service

## Data

[UCI ML Repository 498 — Incident management process enriched event log](https://archive.ics.uci.edu/dataset/498/incident+management+process+enriched+event+log) (CC BY 4.0). Real ITSM export, anonymised labels, 141,712 events / 24,918 incidents.

No employer or client data is used, at any point, in any form.

## How to reproduce

```bash
pip install pandas matplotlib
curl -L -o uci498.zip "https://archive.ics.uci.edu/static/public/498/incident+management+process+enriched+event+log.zip"
python scripts/01_build_incidents.py   # event log -> incident-level table
python scripts/02_economics.py         # effort tables, Pareto, charts
```

## Outputs

```
data/incidents.csv             # one row per incident (24,918)
data/effort_by_category.csv    # volume, cycle time, effort share, reassignment, SLA
data/effort_by_subcategory.csv
data/effort_by_group.csv
charts/pareto_effort_by_category.png
charts/pareto_curve.png        # effort concentrates more than volume
charts/sla_by_category.png
```

## Method notes

- **Cycle time, not handle time.** Elapsed = opened → resolved, which includes queue and waiting. It is the right measure for service cost, the wrong one for headcount; reassignment count is used as a second, touch-based proxy.
- **`made_sla` is 100% True** in this extract, so no SLA claim is made from it.
- **Labels are anonymised** (`Category 46`), so this phase reports structure only.

## Phase 2 (planned)

Attach meaning to structure: embed ticket text from a text-rich public dataset, cluster with HDBSCAN into ~20 intents covering 80% of volume, then label each intent with an automation-feasibility class (automatable / assisted / human-only) and produce the savings range. GPU use: embeddings only, under 2 compute units on a T4.

## Licence

Code MIT. Data remains under its original UCI licence (CC BY 4.0).
