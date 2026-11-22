"""Step 7 (phase 2b) — does the intent finding survive a paraphrase-aware method,
and does it survive messier text?

Compares two representations on the same 20k sample:
  A) TF-IDF (1-2 grams) -> SVD(150)      [the method used in phase 2]
  B) sentence embeddings (MiniLM-L6)      [paraphrase-aware, semantic]

Each run twice:
  i)  full cleaned text
  ii) truncated to the first 8 words  — simulates terse, real-world tickets where
      only the symptom survives and the phrasing varies

Metric: agreement with the 100 known issue types (NMI, ARI, purity). The point is
not to find a winner on a synthetic corpus, but to see which representation is
more robust when the text gets thinner — that is the property that matters on
real ticket data.
"""
import json
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from sklearn.preprocessing import normalize
from sentence_transformers import SentenceTransformer

torch.set_num_threads(max(1, torch.get_num_threads()))
SCRATCH = Path("/workspace/hermes/cache/scratch/delivery-analytics")
OUT = Path("/opt/data/delivery-analytics")
SEED, N = 42, 20_000

BOILER = [r"hi team", r"hi there", r"hello,?", r"hey,?", r"good morning,?", r"dear (support|team)",
          r"i'?m having an issue", r"been struggling with this", r"need some help here",
          r"we'?re a bit stuck", r"reaching out because", r"quick question",
          r"not sure this is the right place,? but", r"hoping you can help:?", r"any help appreciated",
          r"happy to share more detail", r"let me know what you need", r"please advise",
          r"thanks in advance", r"this is fairly urgent for us", r"this started today",
          r"it'?s been happening( since yesterday)?",
          r"on the (desktop client|mobile app|payment gateway|web platform|api platform)",
          r"\bplease\b", r"\bthanks\b", r"\bhello\b", r"\bhi\b", r"\bhey\b", r"\bregards\b"]
CLEAN = [(re.compile(p, re.I), " ") for p in BOILER]


def clean(t):
    for rx, rep in CLEAN:
        t = rx.sub(rep, t)
    t = re.sub(r"[^A-Za-z0-9 %\-\.]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


df = pd.read_parquet(SCRATCH / "tickets.parquet")
df = df[df["language"] == "English"].copy()
df = df[df["issue_description"].notna() & (df["issue_description"].str.len() >= 25)]
s = df.sample(n=N, random_state=SEED).reset_index(drop=True)
s["clean"] = s["issue_description"].map(clean)
s = s[s["clean"].str.len() >= 18].reset_index(drop=True)
s["terse"] = s["clean"].str.split().str[:8].str.join(" ")
k = s["issue_type_id"].nunique()

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
print(f"{len(s):,} tickets | {k} issue types | MiniLM on CPU, threads={torch.get_num_threads()}")


def evaluate(Z, tag):
    t0 = time.time()
    km = KMeans(n_clusters=k, random_state=SEED, n_init=5).fit(Z)
    lab = km.labels_
    nmi = normalized_mutual_info_score(s["issue_type_id"], lab)
    ari = adjusted_rand_score(s["issue_type_id"], lab)
    pur = pd.Series(lab).groupby(lab).apply(lambda x: s.loc[x.index, "issue_type_id"].value_counts().iloc[0] / len(x))
    wpur = float((pur * pd.Series(lab).value_counts().sort_index()).sum() / len(lab))
    print(f"  {tag:34s} NMI {nmi:.3f}  ARI {ari:.3f}  purity {wpur:.3f}  ({time.time()-t0:.0f}s)")
    return {"method": tag, "nmi": round(float(nmi), 3), "ari": round(float(ari), 3),
            "purity": round(wpur, 3), "seconds": round(time.time() - t0, 1)}


results = []


def vary(text, rng):
    """Simulate how different people describe the same fault: drop half the
    words and shuffle the rest. Real tickets differ lexically far more than
    this generator does; the point is to see which representation degrades first."""
    words = text.split()
    keep = [w for w in words if rng.random() > 0.5] or words
    rng.shuffle(keep)
    return " ".join(keep)


rng = np.random.default_rng(SEED)
s["vary"] = s["clean"].map(lambda t: vary(t, rng))

for cond, col in (("full", "clean"),
                  ("terse (first 8 words)", "terse"),
                  ("lexical variation (50% drop + shuffle)", "vary")):
    print(f"\n== {cond} text ==")
    vec = TfidfVectorizer(max_features=30_000, ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    X = vec.fit_transform(s[col])
    Z_tfidf = normalize(TruncatedSVD(n_components=150, random_state=SEED).fit_transform(X))
    results.append(evaluate(Z_tfidf, f"tfidf+svd [{cond}]"))

    t0 = time.time()
    emb = model.encode(s[col].tolist(), batch_size=128, show_progress_bar=False,
                       convert_to_numpy=True, normalize_embeddings=True)
    print(f"  embeddings computed in {time.time()-t0:.0f}s (dim {emb.shape[1]})")
    results.append(evaluate(emb, f"minilm embeddings [{cond}]"))

res = pd.DataFrame(results)
res.to_csv(OUT / "data/phase2b_method_comparison.csv", index=False)
json.dump({"sample": int(len(s)), "issue_types": int(k),
           "model": "sentence-transformers/all-MiniLM-L6-v2",
           "results": results,
           "note": "synthetic corpus has one canonical sentence per issue type, so both methods are near-ceiling on full text; the terse condition is the informative one"},
          open(OUT / "data/phase2b_metrics.json", "w"), indent=2)

piv = res.pivot(index="method", columns="method", values="nmi") if False else None
print("\n=== summary ===")
print(res.pivot_table(index=["method"], values=["nmi", "ari", "purity"]).round(3).to_string())
print("\nwrote data/phase2b_method_comparison.csv + data/phase2b_metrics.json")
