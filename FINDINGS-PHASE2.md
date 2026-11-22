# FINDINGS — phase 2: from anonymous structure to named intents

**Source:** `s2pidape/support-ticket-dataset` (synthetic, English slice = **250,599 tickets**, **100 issue types** in **11 families**), with resolution hours, SLA-breach flag and escalation flag per ticket.

**Method:** template boilerplate stripped → TF-IDF (1–2 grams) → SVD(150) → k-means (k=100). Phase-1-style discovery on the same text with HDBSCAN produced 88 clusters at 7.1% noise, so the structure is not an artefact of choosing k. Intent economics then come from the labels the clustering proved recoverable from text.

---

## 1. Effort concentrates at intent level more than at family level

| | share of volume | share of elapsed effort |
|---|---|---|
| Top 10 intents | 11.0% | **42.6%** |
| 11 families | evenly spread (~9% each) | 4.4%–17.7% |

At family granularity the corpus looks flat — every family is ~9% of volume. At intent granularity it is sharply skewed: ten intents carry 42.6% of the time. A dashboard built on the eight category labels would show nothing to act on.

## 2. The policy intents own the effort

- **security** — 8.9% of volume, **17.7% of effort**, 20.8% SLA breach
- **refunds** — 8.1% of volume, **15.7% of effort**, 20.6% breach
- Together: **17% of volume, 33% of effort** — and neither is a technical fault. They are policy and paperwork: GDPR requests, data deletion, refund appeals, chargebacks.

The worst single intents by SLA breach are all policy or defect: data corruption 56.8%, security GDPR request 51.8%, delete-my-data 51.2%, refund-denied appeal 57.1%. Every one of the top-12 effort intents escalates at ~80%.

## 3. The automatable work is fast; the expensive work is not automatable

Effort split by feasibility class:

- **automatable — 27.6%** of effort (authentication, onboarding, billing, subscription)
- **assisted — 47.5%** (account changes, security requests, refunds, integrations)
- **human-only — 24.9%** (bugs, data corruption, performance)

Savings on total elapsed effort at 40 / 60 / 80% automation of the automatable share:

| scenario | effort removed |
|---|---|
| 40% | 11.0% |
| 60% | 16.6% |
| 80% | 22.1% |

But note *where* the automatable effort sits: onboarding has a median of **0.42 h** and a 1.1% breach rate; authentication 2.06 h. These intents are cheap per ticket — so automating them cuts **contact volume** (and queue pressure) far more than it cuts elapsed hours. The very intents that dominate elapsed time are the ones no chatbot will close.

The largest prize is therefore not autonomy but the **47.5% assisted band** — agent-in-the-loop drafting, pre-filled forms, automatic evidence gathering for GDPR/refund workflows.

## 4. Validation — and why it flatters

Clustering recovers the 100 issue types at **NMI 1.0, ARI 1.0, purity 1.0**. That is a property of the generator, not a result: each issue type has one canonical sentence, so recovery is near-deterministic. It proves the pipeline works end to end; it says nothing about messy real text, where two people describe the same fault differently. Treat phase 1's structure-only findings as the honest baseline.

---

## Limitations

1. **Synthetic corpus.** Distributions and phrasing are generated. Useful for method and for the shape of the argument, not as a market benchmark.
2. **Elapsed time, not handle time.** `resolution_time_hours` is calendar time to resolution; it includes queueing. Savings are quoted as a share of elapsed effort for exactly this reason — no FTE claim is made, because the dataset has no agent-touch measure.
3. **Feasibility is a judgement, not a model output.** Each family is mapped to automatable / assisted / human-only in code (one dict, fully visible), and the mapping is debatable — `onboarding_training_request` is classified automatable although a human trainer may be needed.
4. **One company's taxonomy.** 100 issue types in 11 families is this generator's design; a real ServiceNow instance typically carries 500–2,000 category/subcategory pairs, which is itself a finding (see action 1).

## Three actions

1. **Collapse the taxonomy before analysing it.** An instance with 1,000+ category pairs cannot produce a priority list; a 20–30 intent taxonomy over the same tickets can. Building that intent layer is a two-week exercise with an admin and a service manager, and it makes every later automation decision arguable with data.
2. **Automate the fast lane** — authentication, onboarding, subscription, billing. Low median time per ticket, so the win is volume and queue relief, not hours. Measure deflection rate and re-open rate, not just contacts avoided.
3. **Attack the policy intents with workflow, not AI.** Security and refunds are 33% of effort with ~21% SLA breach. Templates, pre-filled evidence packs, approval routing and clear decision rules remove elapsed time here far more reliably than a model would.

## What would have to be true

- The feasibility mapping matches your real intents (spot-check 30 tickets per family)
- Deflected contacts do not reappear as reopens or escalations — measure both, with a control group
- The 47.5% assisted band can be served with an agent still owning the decision — that is a workflow and governance question, not a model question
