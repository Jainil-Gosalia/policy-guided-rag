# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Policy-Guided RAG is a research implementation of **Asymmetric Visibility** for controllable retrieval: hidden business rules or safety constraints (*guidance*) influence retrieval ranking without ever being exposed to the LLM or users. Guidance is retrieved separately, used to influence ranking, then **structurally filtered out** before generation (only `chunk_type == 'context'` chunks reach the LLM).

Two guidance mechanisms are implemented and compared:
- **augment** — append guidance text to the query before cross-encoder reranking (does NOT steer reliably; a topical cross-encoder can't express preference/negation).
- **operator** (default) — apply structured `BOOST`/`DEMOTE`/`EXCLUDE` actions directly to reranked scores; this is the mechanism that achieves controllable ranking.

## Commands

```bash
pip install -r requirements.txt        # or: pip install -e .

# Experiments (each writes results/<exp>/run_<ts>/results.json with a config snapshot)
python scripts/run_experiment.py synthetic_test --dataset synthetic   # 4 conditions + stats
python scripts/run_experiment.py manual_test                          # hand-verified set
python scripts/run_experiment.py cross_encoder_comparison
python experiments/verification/leakage_test.py                       # 185q × 3 mechanisms
bash scripts/run_all_experiments.sh                                   # everything

# Override the mechanism / hyperparameters
python scripts/run_experiment.py synthetic_test --policy-mode operator --policy-weight 5.0 --k-guidance 8

# Regenerate the synthetic dataset (non-circular labels, seed 42)
python -m src.data_generation.generate_dataset --output data --name synthetic --seed 42

pytest                                  # fast unit tests (no model download)
```

## Architecture

```
User Query → Dual Retrieval (context + guidance) → Cross-Encoder Rerank
          → Policy Operator (BOOST/DEMOTE/EXCLUDE)  [or query augmentation]
          → Filter to context-only → Final Chunks
```

### Core Components (under `src/`)

- **`models/pipeline.py`** — end-to-end pipeline; `policy_mode ∈ {augment, operator, both, none}`.
- **`models/vector_store.py`** — ChromaDB store with `retrieve_context()` / `retrieve_guidance()` via `chunk_type` metadata filtering, plus `get_context_by_card_ids()` for policy injection.
- **`models/reranker.py`** — cross-encoder reranker (default: `cross-encoder/ms-marco-MiniLM-L-6-v2`).
- **`models/query_augmenter.py`** — the augment mechanism (appends guidance text).
- **`models/policy_operator.py`** — the operator mechanism (structured BOOST/DEMOTE/EXCLUDE).
- **`models/baselines.py`** — `VanillaRAG` (embeddings only) and `RerankOnlyRAG` (reranker, no guidance) for isolating the guidance effect.
- **`evaluation/metrics.py`** — accuracy, mean rank, controllability/enforcement helpers.
- **`evaluation/stats.py`** — McNemar, Wilcoxon, bootstrap CIs.
- **`data_generation/`** — synthetic generator with **non-circular** labels (relevance gold from card attributes; policy targets kept separate).

### Evaluation conditions

`vanilla` → `rerank_only` → {`pg_augment`, `pg_operator`}. The `rerank_only → pg_*` contrast isolates the guidance effect. Relevance gold is independent of guidance; controllability (BOOST) and enforcement (EXCLUDE) are measured by separate metrics. See `docs/EXPERIMENTS.md`.

### Key design pattern

Asymmetric visibility = guidance influences ranking (augment or operator) but the final stage keeps only `chunk_type == 'context'`, so guidance is structurally absent from the LLM context (verified leak-free over 555 runs).
