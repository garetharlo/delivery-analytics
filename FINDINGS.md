# FINDINGS — where the hours actually go

**Source:** UCI ML Repository dataset 498, *Incident management process enriched event log* — a real ITSM tool export (ServiceNow-style schema, anonymised labels) from an Italian company. 141,712 events covering **24,918 incidents**, Feb–Apr 2016.

**Method:** incidents aggregated from the event log (first open → first resolve); elapsed time = cycle time, not agent handle time. Effort = tickets × elapsed time per contact driver. Labels are anonymised (`Category 46`), so findings are structural, not semantic.

---

## 1. Effort concentrates far more than volume

| | share of volume | share of elapsed effort |
|---|---|---|
| Top 5 categories | 39% | **57%** |
| Top 10 categories | 69% | **79%** |

Volume-based prioritisation (the usual "work the biggest queue") systematically misallocates attention. One category is **2.1% of volume and 16% of effort**, with a median cycle time of 389 hours. Ranking by tickets instead of hours hides it entirely.

## 2. The tail owns the time

- **32% of incidents** close in under one hour, and together they account for **~0% of elapsed hours**
- **35% of incidents** run 72 hours or longer, and they hold **96% of all elapsed time**

Two almost disjoint services are running: a fast lane (cheap, quick, candidate for automation) and a slow tail (expensive, invisible in volume dashboards, where all the cost sits).

## 3. Reassignment is the single biggest lever

- **49% of incidents** are reassigned at least once; **22% twice or more**
- Median cycle time: **79.9 h** for reassigned incidents vs **0.7 h** for never-reassigned
- **73% of all elapsed hours** sit inside incidents that were reassigned

Reassignments are not a hygiene metric — they are where the time lives. The four biggest-effort categories are also among the most-reassigned (44–88%).

## 4. The channel mix is structural, not incremental

Contact type across resolved incidents: **Phone 99.1%**, Self-service 0.7%, Email 0.3%, Direct 0.02%.

Self-service is effectively unused, so deflection here is a channel-design problem rather than an optimisation of an existing digital channel. The sub-1-hour categories are the natural first candidates — they are cheap to deflect and expensive to keep on the phone.

---

## Limitations (read before quoting these numbers)

1. **Elapsed time ≠ agent effort.** Cycle time includes queue and waiting for the caller. It is the right measure for *service* cost and the wrong one for *headcount* cost; pairing it with reassignment counts and ticket volume gives a better effort proxy than either alone.
2. **`made_sla` is True for 100% of records** in this extract — the SLA field is unusable, so no SLA-attainment claim can be made from this data.
3. **Anonymised labels.** `Category 46` cannot be explained to a business audience. Phase 2 (text clustering on a text-rich dataset) exists to attach meaning to structure like this.
4. **One company, three months, sealed 2016.** Treat as a method demonstration, not a market benchmark.
5. Derived from public data only. No employer or client data was used.

## Three actions a delivery manager could take from this

1. **Route once.** Target a defined reduction in reassignments (first-time-right triage, account-level routing rules, clear ownership at hand-off). Given 73% of hours sit in reassigned incidents, even a modest reduction moves the cost line.
2. **Govern the tail.** Any incident open beyond 72 h gets a scheduled weekly review with an owner. 35% of tickets are there, holding 96% of the time.
3. **Deflect the fast lane first.** Start with the sub-1-hour categories on the phone channel: highest volume, lowest risk, clearest automation story.

## What would have to be true

- Reassignment is a *cause* of elapsed time, not a symptom of it — test by comparing incidents with identical category/priority that were and were not reassigned
- The sub-1-hour categories are genuinely self-serviceable, not quick *because* a human is involved — test by sampling and by running a deflection pilot with a control group
- Savings estimates should be presented as ranges across 40/60/80% scenarios, never as a single figure
