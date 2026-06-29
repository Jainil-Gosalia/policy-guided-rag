# Experiments

All runs write a timestamped `results/<experiment>/run_<YYYYMMDD_HHMMSS>/results.json` with an
embedded config snapshot (reranker, k-values, `policy_mode`, `policy_weight`, seed) for full
traceability.

## Prerequisites

```bash
pip install -r requirements.txt   # or: pip install -e .
```

First run downloads the embedding model (`sentence-transformers/all-MiniLM-L6-v2`) and the
default reranker (`cross-encoder/ms-marco-MiniLM-L-6-v2`) from Hugging Face.

## Conditions compared

Every benchmark evaluates the same systems so that the *reranker* effect and the *guidance*
effect are isolated:

| Condition | Reranker | Guidance mechanism |
|---|---|---|
| `vanilla` | ✗ (embedding similarity only) | none |
| `rerank_only` | ✓ (raw query) | none |
| `filter` | ✓ (raw query) | hard EXCLUDE only (the "just filter" baseline) |
| `pg_augment` | ✓ (guidance text appended to query) | query augmentation |
| `pg_operator` | ✓ (raw query) | explicit BOOST/DEMOTE/EXCLUDE on scores |

`vanilla → rerank_only` measures the reranker. `rerank_only → pg_*` isolates **guidance**.
`filter → pg_operator` isolates **promotion** (a filter removes; only the operator promotes).
The mechanism is selected by `pipeline.policy_mode ∈ {none, augment, operator, both}`; the
filter is the operator with zero weight and injection disabled.

## Experiments

| Experiment | Command | Dataset | What it measures |
|---|---|---|---|
| Synthetic benchmark | `python scripts/run_experiment.py synthetic_test --dataset synthetic` | synthetic (150 q) | accuracy + **controllability** (BOOST) + **enforcement** (EXCLUDE) + significance |
| Manual benchmark | `python scripts/run_experiment.py manual_test` | manual (15 q) | accuracy across vanilla/rerank/augment on hand-verified gold |
| Reranker comparison | `python scripts/run_experiment.py cross_encoder_comparison` | synthetic | Top-5 + mean rank across 5 cross-encoders |
| Leakage audit | `python experiments/verification/leakage_test.py` | synthetic | guidance reaching the LLM, across all mechanisms (target: 0) |
| Governance (non-card) | `python experiments/governance_test.py` | governance | predicate-policy compliance, relevance, authorized-version hit, latency |
| Catalog drift | `python scripts/governance_drift_demo.py` | governance | predicate policy vs. frozen ID list under corpus drift |

Run all: `bash scripts/run_all_experiments.sh`.

## Non-circular evaluation (important)

The synthetic benchmark separates three label types so the central claim is not
self-fulfilling:

- **`expected_top_cards`** — relevance gold, derived **only** from card attributes matched to
  the query category (`src/data_generation/query_generator.py::_relevance_gold`). It does
  **not** use the guidance rules. Ambiguous/adversarial queries (e.g. "give me free money")
  have empty gold and are excluded from accuracy.
- **`policy_preferred_cards`** — BOOST targets of matching guidance. Used only for the
  controllability metric, never as relevance gold.
- **`policy_excluded_cards`** — EXCLUDE targets of matching guidance. Used only for the
  enforcement metric.

> An earlier version computed `expected_top_cards` by adding the guidance BOOST/DEMOTE term,
> which made the benchmark circular and produced inflated "gains". That has been removed.

## Metrics (`src/evaluation/metrics.py`, `src/evaluation/stats.py`)

- **Top-1 / Top-5 accuracy**, **mean position** (1-indexed; `99` sentinel for "not retrieved").
- **Controllability (BOOST)** — mean rank and top-n hit-rate of `policy_preferred_cards`;
  *steering lift* = `rerank_only` rank − condition rank, with a bootstrap 95% CI.
- **Enforcement (EXCLUDE)** — rate at which `policy_excluded_cards` still appear in the
  top-n (operator target: 0%).
- **Significance** — paired **McNemar** (accuracy) and **Wilcoxon signed-rank** (position),
  plus **bootstrap** CIs for effect sizes.
- **Leakage rate** — fraction of runs where a `guidance` chunk (by id or by text) appears in
  `final_chunks`.

## Default hyperparameters (`config/default.yaml`)

| Parameter | Value | Meaning |
|---|---|---|
| `k_context` | 10 | candidate context chunks retrieved before re-ranking |
| `k_guidance` | 3 | guidance chunks retrieved (raise → stronger enforcement, more relevance cost) |
| `top_n` | 5 | final context chunks returned |
| `policy_mode` | `operator` | guidance mechanism |
| `policy_weight` | 5.0 | BOOST/DEMOTE score magnitude |
| `reranker.default` | `ms-marco-MiniLM-L-6-v2` | cross-encoder used for scoring |
| `seed` | 42 | reproducibility seed |

## The control ↔ relevance trade-off

`k_guidance` (and `policy_weight`) trade policy strength against relevance:

| `k_guidance` | EXCLUDE appears-in-top-n | Top-5 accuracy (operator) | BOOST steering lift |
|---|---|---|---|
| 3 (default) | 6.9% | 57.2% | +25.4 [+19.5, +31.5] |
| 8 | **0.0%** (full enforcement) | 46.4% | +23.0 [+18.2, +28.0] |

(rerank-only Top-5 baseline = 65.9%; results are deterministic — single-threaded HNSW, seed 42.)

Stronger enforcement is available, but removing/demoting more cards removes some that are
genuinely relevant. This trade-off is the honest headline of the operator, not a free lunch.

## Governance experiment (generality beyond cards)

`data/governance/` is a non-card domain: a corporate knowledge base (49 documents, 6
departments × 3 sub-topics, + 10 distractors) governed by a hidden **Data Governance &
Records Schedule** (`governance.md`). The schedule compiles to **attribute-predicate**
policies (`policies.json`) consumed by `PolicyOperator.apply_policy_set`:

- **Hard tier** (`EXCLUDE` restricted / PII / deprecated / legal-hold) is evaluated
  *unconditionally* (trigger-matched, not gated by guidance retrieval) → exact enforcement.
- **Soft tier** (`BOOST` current version, `DEMOTE` wrong jurisdiction) adjusts scores.
- Policies reference item **attributes**, not IDs (`src/models/predicate.py`), so one rule
  covers all matching docs and survives corpus changes.

Metrics: sub-topic **relevance** (governance-independent gold), **compliance violation**
rate (must-exclude doc in top-n; target 0%), **authorized-version** hit/top-1, and per-query
**latency**. Headline: compliance violation 100% → **0.0%** with no relevance loss, ~0.24 s/query,
zero LLM calls. Here filter ≡ operator (policy aligns with relevance, so a filter suffices); the
operator's promotion advantage over the filter is demonstrated on the synthetic set, where
policy-preferred items are *not* the most relevant.

`scripts/governance_drift_demo.py` shows a new restricted document (authored after the policy)
leaking through a frozen ID-list while the attribute predicate still excludes it.

## Reproducibility notes

- On datasets this small, single-run numbers vary; for publication, regenerate with multiple
  seeds (`--seed`) and report mean ± std.
- The vector store is in-memory (ephemeral) by default — each run re-indexes from `data/`,
  so there is no hidden persisted state.
