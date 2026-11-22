# FINDINGS — phase 2b: does the method survive messier text?

**Question:** phase 2 recovered intents at NMI 1.0 — but that corpus writes one canonical sentence per issue type, so the score proved the pipeline runs, not that the method works on real tickets. Does a semantic representation do better when the wording varies?

**Setup:** same 20,000 English tickets, 100 known issue types, two representations:

- **A. TF-IDF (1–2 grams) → SVD(150)** — the phase-2 method
- **B. sentence embeddings (all-MiniLM-L6-v2, 384 dims)** — paraphrase-aware

Each evaluated under three text conditions: full cleaned text; **terse** (first 8 words only); **lexical variation** (drop 50% of words, shuffle the rest). Metric: NMI/ARI/purity against the known issue types.

| condition | TF-IDF NMI | embeddings NMI | TF-IDF purity | embeddings purity |
|---|---|---|---|---|
| full text | **1.000** | 0.998 | 1.000 | 0.992 |
| terse (8 words) | **1.000** | 0.994 | 1.000 | 0.982 |
| lexical variation | **0.867** | 0.723 | 0.825 | 0.578 |

MEDIA note: chart in `charts/phase2b_methods.png`.

## What this shows

1. **On templated text, the corpus cannot rank the methods.** Both sit at the ceiling; TF-IDF is marginally ahead and 30× cheaper (1 s vs ~35 s for 20k tickets on two CPU threads). No GPU was needed — the whole comparison ran locally.
2. **Under word-level damage TF-IDF degrades more slowly** (0.867 vs 0.723). But read the cause before drawing a conclusion: the shuffle condition destroys **word order**, and a sentence model is trained on natural order, so this condition is out-of-distribution for embeddings and in-distribution for a bag-of-words model. TF-IDF losing bigrams still keeps the distinctive nouns — which is exactly what this generator encodes.
3. **So the honest answer is: unknown.** The test is biased against the semantic model, and it does not license "TF-IDF is better for real tickets". What it does show is that neither representation can be validated on a corpus where each intent has one canonical sentence.

## What would actually settle it

- **200–500 real tickets, hand-labelled with intent**, sampled to include near-duplicate phrasings ("can't log in", "password not accepted", "account locked out") — then both representations are compared on that set
- Or a paraphrase set: the same 100 intents, each written by two or three different people
- Cost: an afternoon of labelling, no GPU. This is the piece worth doing with real (permitted) data, not with more synthetic text

## Practical recommendation

- **Default to TF-IDF + SVD**: deterministic, milliseconds, no model download, no GPU, and explainable to a non-technical reader ("these are the words that define the group")
- **Reach for embeddings only when the lexicon genuinely differs** — if the same intent appears under unrelated vocabulary (German/English mix, product-specific jargon, spelling variants), bag-of-words will split it while embeddings merge it. Decide that by reading 50 tickets, not by benchmarking
- **Either way, the intent taxonomy matters more than the model.** A 20–30 family taxonomy over 1,000 imported categories changes the analysis far more than choosing between two clustering representations

## Compute

The entire phase 2b ran on this machine's CPU in about three minutes (embeddings: 37 s for 20k texts on two threads). **No Colab units were consumed, and none were needed** — which is the useful conclusion for the GPU-credits question: intent clustering is not a GPU workload. The credits are only justified by an actual training job.
