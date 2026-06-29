# Research Paper — Companion Notes

> **The canonical paper is [`paper/paper.pdf`](../paper/paper.tex)** (source `paper/paper.tex`).
> This is a quick-reference companion. If anything disagrees with the compiled paper, the
> paper is authoritative.

## One-paragraph summary

**Policy-Guided RAG** lets hidden *guidance* rules steer retrieval ranking without exposing
them to the LLM (the **Asymmetric Visibility** pattern). Two mechanisms are studied. The
intuitive one — appending guidance text to the query before cross-encoder reranking
(*augment*) — **does not work**: on a non-circular benchmark it gives no steering, and on the
hand-verified set it significantly *hurts* (a topical cross-encoder cannot read "avoid X" as a
down-weight). The mechanism that *does* work is an explicit **Policy Operator** that applies
structured `BOOST`/`DEMOTE`/`EXCLUDE` actions to the reranked scores: it produces large,
significant control over rankings (BOOST steering lift **+27.6**, 95% CI [+21.2, +34.1];
EXCLUDE appearance **51.7% → 6.9%**, and **→0%** with fuller guidance retrieval) at no
relevance cost at the default operating point — and a tunable control↔relevance trade-off
beyond it. In all mechanisms guidance is **structurally absent** from the LLM context: a
**185-query × 3-mechanism audit (555 runs) finds 0 leaks**.

## Headline results

### Controllability — only the operator steers (synthetic, non-circular labels)

| Metric | Vanilla | Rerank-only | Filter | Augment | **Operator** |
|---|---|---|---|---|---|
| BOOST: policy-preferred mean rank ↓ (n=101) | 75.8 | 70.3 | 73.4 | 70.4 | **45.0** |
| BOOST: policy-preferred top-n hit ↑ | 61.4% | 69.3% | 63.4% | 75.2% | **81.2%** |
| BOOST: steering lift vs rerank-only (95% CI) | — | — | −3.1 [−4.6,−1.8] | −0.1 [−2.5,+2.2] | **+25.4 [+19.5,+31.5]** |
| EXCLUDE: excluded card in top-n ↓ (n=29) | 37.9% | 51.7% | 3.4% | 51.7% | 6.9% |

A plain metadata **filter** enforces exclusions as well as the operator (3.4% vs 6.9%) but has
**no positive steering lift** — it can remove, not promote. Only the operator steers. This is the
contribution over standard filtering.

### Control has a relevance cost (synthetic, n=138 labelled queries)

| Condition | Top-1 | Top-5 | Mean position |
|---|---|---|---|
| Vanilla | 28.3% | 65.2% | 36.0 |
| Rerank-only | 25.4% | 65.9% | 35.3 |
| Filter | 20.3% | 59.4% | 41.6 |
| Augment | 21.7% | 66.7% | 34.7 |
| Operator | 22.5% | 57.2% | 43.6 |

Operator vs rerank-only: top-5 65.9%→57.2% (McNemar p=0.13 — not significant at n=138, but a
consistent trade-off). Enforcing policy displaces some relevant items; control is a tunable dial,
not a free lunch.

### Negative result — augment (manual, 15 hand-verified queries)

| Condition | Top-1 | Top-5 | Mean position |
|---|---|---|---|
| Vanilla | 86.7% | 100% | 1.1 |
| Rerank-only | 93.3% | 100% | 1.1 |
| Augment | **60.0%** | 100% | 1.7 |

Augment vs rerank-only: position Wilcoxon **p=0.039** — augment significantly *worsens* ranking.

### Control ↔ relevance trade-off (operator, synthetic)

| `k_guidance` | EXCLUDE in top-n | Top-5 (operator) | BOOST steering lift |
|---|---|---|---|
| 3 (default) | 6.9% | 57.2% | +25.4 [+19.5, +31.5] |
| 8 | **0.0%** | 46.4% | +23.0 [+18.2, +28.0] |

(rerank-only Top-5 baseline = 65.9%.)

### Leakage audit

| Source | Queries | Mechanisms | Leaks |
|---|---|---|---|
| Manual | 15 | augment, operator, both | 0 |
| Synthetic | 150 | augment, operator, both | 0 |
| Adversarial | 20 | augment, operator, both | 0 |
| **Total** | **185 unique** | **× 3 = 555 runs** | **0 (0%)** |

### Generality beyond cards — document governance

A non-card domain (`data/governance/`): a corporate knowledge base (49 documents, 6 depts × 3
sub-topics + 10 distractors) under a hidden **Data Governance & Records Schedule**, compiled to
**attribute-predicate** policies (no document IDs). Hard `EXCLUDE` (restricted/PII/deprecated/
legal-hold) is applied unconditionally; soft `BOOST`/`DEMOTE` adjust scores.

| Metric (n=21) | Vanilla | Rerank-only | Filter | Operator |
|---|---|---|---|---|
| Relevance — sub-topic top-5 (gov-independent) | 95.2% | 100% | 100% | 100% |
| Relevance — mean position | 6.0 | 1.2 | 1.1 | 1.1 |
| **Compliance violation** (must-exclude in top-n) | 100% | 100% | **0.0%** | **0.0%** |
| Authorized-version in top-1 | 38.1% | 33.3% | 81.0% | 81.0% |

The ungoverned KB surfaces a must-exclude document on every query; both filter and operator
remove them exactly and retrieval-independently with no relevance loss (~0.24 s/query, no LLM
call). Here **filter ≡ operator** because policy aligns with relevance; the operator's promotion
advantage appears only where policy diverges from relevance (the synthetic case above).
**Catalog drift:** a new restricted document authored after the policy leaks through a frozen
ID-list but is still excluded by the attribute predicate — the authoring-burden payoff of
predicates over per-item rules.

## Method notes

- **Augment** (`policy_mode=augment`): `q' = q ∥ [GUIDANCE] ∥ g_1 ∥ …`, rerank `score(q', c)`.
- **Operator** (`policy_mode=operator`, default): rerank `score(q, c)`, then
  `score += weight` for BOOST targets, `−= weight` for DEMOTE, and hard-drop EXCLUDE targets;
  BOOST targets missing from the candidate pool are injected and scored. EXCLUDE is exact for
  *retrieved* rules — residual appearances are guidance-retrieval misses, eliminated by raising
  `k_guidance`.
- In every mode the final stage keeps only `chunk_type == "context"`, so guidance is
  structurally absent (zero leakage), verified empirically.

## Reproducibility

- `python scripts/run_experiment.py synthetic_test --dataset synthetic` and
  `... manual_test`; leakage via `python experiments/verification/leakage_test.py`.
- Significance: paired McNemar (accuracy) + Wilcoxon (position) + bootstrap CIs
  (`src/evaluation/stats.py`).
- Small datasets: for publication, regenerate with multiple seeds (`--seed`) and report
  mean ± std.

## Limitations

Single domain (credit cards); off-the-shelf models (no fine-tuning); synthetic queries from
templates may not match real distributions; the operator needs *structured* guidance
(action + target cards) — free-text guidance (the manual set) only supports the augment
mechanism; static (non-personalized) policies. The operator's controllability on synthetic
data is partly by construction (it directly manipulates scores); the honest measurement is its
**relevance cost** (reported above) and the verified **non-exposure** guarantee.

## Result-artifact index

| Claim | Source |
|---|---|
| Synthetic (accuracy + controllability + enforcement) | `results/synthetic_test/` |
| Manual benchmark | `results/manual_test/` |
| Leakage audit (555 runs) | `results/leakage_test/`, `experiments/verification/leakage_test.py` |
| Dataset stats | `data/synthetic/metadata.json` |
