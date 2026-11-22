# delivery-analytics

Where do service desk hours actually go — and how much of that work is removable?

Two datasets, one question, answered in numbers: effort per contact driver, the volume-vs-effort gap, the cost of reassignment, and which intents are worth automating.

- **[`FINDINGS.md`](FINDINGS.md)** — phase 1: effort economics on a real ITSM event log
- **[`FINDINGS-PHASE2.md`](FINDINGS-PHASE2.md)** — phase 2: named intents, automation feasibility, savings range
- **[`FINDINGS-PHASE2B.md`](FINDINGS-PHASE2B.md)** — phase 2b: does the clustering method survive messier text?

## Headline results

**Phase 1 — real event log** (UCI 498, 24,918 incidents)

- Top 10 categories = **69% of volume but 79% of elapsed effort**
- **32% of tickets** close in under an hour but hold **~0% of the hours**; **35%** run ≥72 h and hold **96%**
- **49% of incidents** are reassigned; they contain **73% of all elapsed hours** (median 79.9 h vs 0.7 h)
- **99% of contacts are phone**, 0.7% self-service
- **62% of resolved incidents met SLA** — but only **9% of Critical** and **1% of High**; 46% when reassigned vs 77% when not

**Phase 2 — named intents** (250,599 English tickets, 100 issue types)

- Top 10 intents = **11% of volume but 42.6% of effort**
- Two families — **security (17.7%)** and **refunds (15.7%)** — are **33% of effort from 17% of volume**, and are policy work, not technical
- Effort split: **automatable 9.6%** (from 31% of tickets), **assisted 65.6%**, **human-only 24.9%**
- Automating 40 / 60 / 80% of the automatable share removes **4% / 6% / 8%** of total elapsed effort — the automatable intents are the *fast* ones, so the real win there is contact volume, not hours

**Phase 2b — method check** (20,000 of the same tickets)

- TF-IDF and sentence embeddings both recover the 100 issue types almost perfectly on full and terse text (NMI ≥ 0.99), so this corpus cannot rank them
- With half the words dropped and the rest shuffled, TF-IDF holds up better (NMI 0.87 vs 0.72) — but that test is biased against the embedding model, so it does not show TF-IDF is better on real tickets
- Clustering is not a GPU job: the whole comparison runs on a laptop CPU in a few minutes

## Data

| Phase | Source | Rows |
|---|---|---|
| 1 | [UCI ML Repository 498](https://archive.ics.uci.edu/dataset/498/incident+management+process+enriched+event+log) — real ITSM export, anonymised labels (CC BY 4.0) | 141,712 events / 24,918 incidents |
| 2 | [s2pidape/support-ticket-dataset](https://huggingface.co/datasets/s2pidape/support-ticket-dataset) — synthetic, English slice | 250,599 tickets |

No employer or client data is used, at any point, in any form.

## How to reproduce

```bash
# run from the repo root
pip install pandas pyarrow matplotlib scikit-learn

# phase 1
curl -L -o uci498.zip "https://archive.ics.uci.edu/static/public/498/incident+management+process+enriched+event+log.zip"
python scripts/01_build_incidents.py
python scripts/02_economics.py

# phase 2
curl -L -o tickets.parquet "https://huggingface.co/datasets/s2pidape/support-ticket-dataset/resolve/refs%2Fconvert%2Fparquet/humans_only/train/0000.parquet"
python scripts/03_intents.py

# phase 2b (uses tickets.parquet from phase 2; downloads the MiniLM model on first run)
pip install sentence-transformers
python scripts/03b_embeddings.py
```

## Outputs

```
data/incidents.csv                 # one row per incident (24,918)
data/effort_by_category.csv        # phase 1: volume, cycle time, effort share, SLA
data/effort_by_subcategory.csv
data/effort_by_group.csv
data/intents_economics.csv         # phase 2: per-intent volume, effort, SLA, feasibility
data/effort_by_intent_family.csv
data/phase2_metrics.json           # validation + savings scenarios, machine-readable
data/phase2b_method_comparison.csv # phase 2b: NMI / ARI / purity and timings per method and condition
data/phase2b_metrics.json
charts/pareto_effort_by_category.png
charts/pareto_curve.png
charts/sla_by_category.png
charts/intents_pareto.png          # top intents coloured by feasibility
charts/feasibility_split.png
charts/phase2b_methods.png         # TF-IDF vs embeddings under degraded text
```

## Method notes

- **Cycle time, not handle time.** Elapsed = opened → resolved, which includes queue and waiting. It is the right measure for service cost, the wrong one for headcount; reassignment count is used as a second, touch-based proxy.
- **SLA = final state.** `made_sla` is read from each incident's last event, because the flag flips to False once the SLA is breached. (An earlier version took `max()` over events and reported 100% attainment — an aggregation bug.)
- **Feasibility is a documented judgement**, not model output: one explicit dict in `scripts/03_intents.py` gives each family a default, and any automatable-family intent with a median of 15 h or more or an SLA breach of 30% or more is moved to *assisted*. (An earlier version labelled whole families and reported 11–22% savings; 65% of those "automatable" hours were six slow, ~80%-escalated intents.)
- **Boilerplate stripping matters.** The synthetic corpus repeats stock phrases; without removing them, clusters form around "Hi team" rather than around the problem being reported.
- **Validation is flattering and flagged as such.** Text recovers the 100 issue types at NMI 1.0 *because* the generator writes one canonical sentence per type — evidence the pipeline works, not evidence about messy real text.

## Licence

Code MIT. Phase-1 data: CC BY 4.0 (UCI). Phase-2 data: see the Hugging Face dataset card.
