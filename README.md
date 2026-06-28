# Policy-Guided RAG: Asymmetric Visibility for Controllable Retrieval

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

Research implementation of **Policy-Guided RAG**: hidden *guidance* rules steer retrieval
ranking **without ever being exposed to the user or the language model**.

> **Asymmetric Visibility** — guidance influences the *process* (re-ranking) while
> remaining structurally absent from the *product* (the context handed to the LLM).

---

## What this repo shows

1. **A working control mechanism — the Policy Operator.** Retrieved guidance carries
   structured actions (`BOOST` / `DEMOTE` / `EXCLUDE`) that are applied directly to the
   reranked candidate scores. This gives **precise, statistically significant control** over
   what surfaces — and a tunable trade-off against relevance.
2. **A structural zero-leakage guarantee.** Because the final stage keeps only
   `chunk_type == "context"` chunks, guidance is *structurally absent* from the LLM context,
   not merely hidden. Verified over **185 queries × 3 mechanisms = 555 runs, 0 leaks**.
3. **An honest negative result.** The intuitive *query-augmentation* mechanism (append
   guidance text to the query, then rerank) **does not steer retrieval** — null on synthetic
   data and significantly *harmful* on the hand-verified set. A topical cross-encoder cannot
   read "avoid card X" as a down-weight; negative guidance is impossible to express this way.

4. **Generality beyond business rules.** The same mechanism governs a **document corpus**
   under a hidden *Data Governance & Records Schedule* — using **attribute predicates**
   (`classification == restricted`) rather than item IDs, so policies need no per-item coding
   and survive corpus drift.

The evaluation is deliberately **non-circular**: relevance labels are derived from item
attributes *independently of the guidance rules*, and policy influence is measured by
separate controllability/enforcement metrics. (An earlier version of this benchmark baked
the guidance into the gold labels — see [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md).)

## The pipeline

```
User query q
   ├─► vector search  WHERE chunk_type = "context"   → candidate context chunks
   └─► vector search  WHERE chunk_type = "guidance"   → guidance chunks (HIDDEN, structured)
            │
            ▼   cross-encoder rerank(q, context_i)            → scores
            ▼   PolicyOperator: score += BOOST / −= DEMOTE; drop EXCLUDE targets
            ▼   keep only chunk_type == "context" → top-n
   final context  ── guidance fully removed ──►  LLM
```

Four guidance mechanisms are selectable via `pipeline.policy_mode`:
`operator` (default), `augment` (the original query-text method), `both`, `none`.

## Key results

**Controllability — the operator works (synthetic, non-circular labels).**

| Metric | Vanilla | Rerank-only | Augment | **Operator** |
|---|---|---|---|---|
| BOOST: policy-preferred mean rank ↓ (n=101) | 75.8 | 70.3 | 70.4 | **42.7** |
| BOOST: policy-preferred top-n hit ↑ | 61.4% | 69.3% | 75.2% | **80.2%** |
| BOOST: steering lift vs rerank-only (95% CI) | — | — | −0.1 [−2.5, +2.2] | **+27.6 [+21.2, +34.1]** |
| EXCLUDE: excluded card appears in top-n ↓ (n=29) | 37.9% | 51.7% | 51.7% | **6.9%** |

The operator's BOOST lift is large and its CI excludes zero; augment's does not. EXCLUDE is
hard removal — the residual 6.9% is guidance-*retrieval* misses, and goes to **0%** at
`k_guidance=8` (at a measurable relevance cost — the control↔relevance trade-off).

**Relevance is preserved (synthetic, n=138 labelled queries).**

| Metric | Vanilla | Rerank-only | Augment | Operator |
|---|---|---|---|---|
| Top-5 accuracy | 65.2% | 65.9% | 66.7% | 68.1% |
| Mean target position | 36.0 | 35.3 | 34.7 | 33.0 |

Operator vs rerank-only is not significantly different on accuracy (McNemar p=0.79) — control
comes at **no relevance cost** at the default operating point.

**Negative result — augment does not help (and can hurt).**

| Benchmark | Metric | Vanilla | Rerank-only | Augment |
|---|---|---|---|---|
| Manual (15 hand-verified) | Top-1 accuracy | 86.7% | 93.3% | **60.0%** |
| Manual | Mean position (PG vs rerank-only) | — | 1.1 | 1.7 (Wilcoxon **p=0.039**) |

**Leakage — structural guarantee holds.** 185 unique queries (15 manual + 150 synthetic +
20 adversarial) × {augment, operator, both} = **555 runs, 0 leaks**.

See [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md) and [`docs/RESEARCH_PAPER.md`](docs/RESEARCH_PAPER.md)
for full methodology, the control↔relevance trade-off, ablations, and limitations.

## Beyond cards: document governance

To show this is a general retrieval property — not a credit-card trick — the same operator
governs a **corporate knowledge base** (49 documents, 6 departments × 3 sub-topics, + 10
distractors) under a hidden **Data Governance & Records Schedule** (`data/governance/governance.md`).
The schedule compiles to **attribute-predicate** policies (`data/governance/policies.json`):
hard `EXCLUDE` of restricted / PII / deprecated / legal-hold documents; soft `BOOST` of the
current authoritative version; `DEMOTE` of wrong-jurisdiction editions.

| Metric (21 queries) | Vanilla | Rerank-only | **Operator** |
|---|---|---|---|
| Relevance — sub-topic top-5 (governance-independent gold) | 95.2% | 100% | 100% (no harm) |
| Relevance — mean position | 6.0 | 1.2 | 1.1 |
| **Compliance violation** (restricted/PII/deprecated/hold in top-n) | 100% | 100% | **0.0%** |
| Authorized-version hit | 95.2% | 100% | 100% |
| Latency (retrieve+rerank+operator) | — | — | ~0.4 s, **0 LLM calls** |

The ungoverned KB surfaces a must-exclude document on **every** query (they're topically
relevant); the operator removes them **exactly and retrieval-independently** while preserving
topical relevance. Hard constraints are evaluated unconditionally (not gated by guidance
retrieval), so enforcement is a guarantee, not best-effort.

**Catalog-drift robustness** (`python scripts/governance_drift_demo.py`): a *new* restricted
document authored after the policy is **leaked by a frozen ID-list** (compliance failure) but
**still excluded by the attribute predicate** — the authoring-burden payoff of predicates.

**On latency/cost:** the operator adds only predicate evaluation (microseconds) and makes no
model call; an LLM-parse alternative (routing chunks + rules + a system prompt through an LLM
to emit structured output) adds a generation round-trip, per-query token cost, and
hallucination risk. In this design policies are not even in the retrievable corpus, so they
**cannot leak by any path**.

## Installation

```bash
git clone https://github.com/Jainil-Gosalia/policy-guided-rag
cd policy-guided-rag
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt                    # or: pip install -e .
```

Python 3.10+. First run downloads the embedding + reranker models from Hugging Face.

## Reproducing the experiments

```bash
# Headline conditions: vanilla / rerank-only / augment / operator
python scripts/run_experiment.py synthetic_test --dataset synthetic
python scripts/run_experiment.py manual_test

# Control vs relevance trade-off: stronger enforcement via more guidance retrieval
python scripts/run_experiment.py synthetic_test --dataset synthetic --k-guidance 8

# Switch the guidance mechanism explicitly
python scripts/run_experiment.py synthetic_test --policy-mode augment
python scripts/run_experiment.py synthetic_test --policy-mode operator --policy-weight 5.0

# Information-leakage audit (185 queries × all mechanisms; also a regression test)
python experiments/verification/leakage_test.py

# Non-card governance demonstration + catalog-drift robustness
python scripts/make_governance_dataset.py
python experiments/governance_test.py
python scripts/governance_drift_demo.py

# Regenerate the synthetic dataset (non-circular labels)
python -m src.data_generation.generate_dataset --output data --name synthetic --seed 42

# Everything at once
bash scripts/run_all_experiments.sh
```

Each run writes a timestamped `results/<experiment>/run_<ts>/results.json` with an embedded
config snapshot (reranker, k-values, policy_mode/weight, seed) for traceability.

## Repository layout

```
policy_rag/
├── src/
│   ├── models/             # vector_store, reranker, query_augmenter, policy_operator,
│   │                       #   predicate (attribute engine), pipeline, baselines
│   ├── data/               # loaders, preprocessors (chunking)
│   ├── data_generation/    # synthetic dataset generator (non-circular labels)
│   ├── evaluation/         # metrics, stats (McNemar / Wilcoxon / bootstrap)
│   └── config/             # YAML-backed config + path manager
├── config/                 # default.yaml, models.yaml, datasets.yaml
├── data/
│   ├── manual/             # 15 cards · 7 guidance · 15 hand-verified queries
│   ├── synthetic/          # 50 cards · 27 guidance (BOOST/DEMOTE/EXCLUDE) · 150 queries
│   └── governance/         # non-card: documents · governance.md (hidden schedule) · predicate policies
├── experiments/            # manual_test, synthetic_test, governance_test, cross_encoder_comparison
│   └── verification/       # leakage_test (all mechanisms)
├── results/                # committed run artifacts (back the numbers above)
├── tests/                  # fast pytest suite (no model download)
├── paper/                  # LaTeX paper + build scripts + compiled PDF
└── docs/                   # RESEARCH_PAPER.md, EXPERIMENTS.md, DATA_FORMAT.md
```

## Tests

```bash
pytest            # fast unit tests (metrics, stats, config, data integrity)
```

## Citation

```bibtex
@article{gosalia2026policyguidedrag,
  title   = {Policy-Guided RAG: Asymmetric Visibility for Controllable Retrieval},
  author  = {Gosalia, Jainil},
  year    = {2026}
}
```

See [`CITATION.cff`](CITATION.cff) for machine-readable metadata.

## License

[MIT](LICENSE) © 2026 Jainil Gosalia.
