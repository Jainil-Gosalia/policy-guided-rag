# Data Format

Datasets live under `data/<dataset>/` and consist of three JSON files: `cards.json`
(context items), `guidance.json` (hidden policy rules), and `queries.json` (evaluation
queries with ground truth). Paths are declared in `config/datasets.yaml` and loaded via
`src/data/loaders.py`.

| Dataset | Cards | Guidance rules | Queries | Guidance style |
|---|---|---|---|---|
| `manual` | 15 | 7 | 15 | natural language |
| `synthetic` | 50 | 25 | 150 | explicit (`BOOST`/`DEMOTE`/`EXCLUDE` with named targets) |

> Note: `data/synthetic/metadata.json` is the authoritative count for the synthetic set.

## `cards.json` — context items

Each card becomes a **context chunk** (`chunk_type = "context"`), visible to the LLM.

```json
{
  "id": "card_1",
  "name": "Premium Rewards Plus",
  "annual_fee": 550,
  "rewards": {"dining": "3x points", "travel": "5x points", "other": "1x points"},
  "benefits": ["Priority Pass lounge access", "Travel insurance up to $500k"],
  "credit_score_required": "Excellent (750+)",
  "tags": ["premium", "travel", "lounge", "high-fee"]
}
```

Chunk text is produced by `ChunkPreparer.format_card_chunk()` (`src/data/preprocessors.py`)
as `Card / Annual Fee / Rewards / Benefits`. The `card_id` is preserved in chunk metadata
and is what evaluation matches against.

## `guidance.json` — hidden policy rules

Each rule becomes a **guidance chunk** (`chunk_type = "guidance"`), retrieved separately
and **never** returned to the LLM. Only the `rule` text is embedded/used.

Natural-language style (`manual`):

```json
{
  "id": "guidance_1",
  "rule": "When users ask about lounge access, prioritize Premium Rewards Plus and Travel Elite Card as they offer Priority Pass membership.",
  "priority": "high",
  "applicable_queries": ["lounge", "airport lounge", "priority pass"]
}
```

Explicit style (`synthetic`), which names target cards directly:

```json
{
  "id": "guidance_002",
  "rule": "BOOST card_007, card_012, card_015 for crypto queries. For crypto, bitcoin, cryptocurrency, digital currency queries ALWAYS prioritize these cards.",
  "priority": "high",
  "category": "crypto",
  "applicable_keywords": ["crypto", "bitcoin", "cryptocurrency"],
  "target_cards": ["card_007", "card_012", "card_015"],
  "action": "BOOST"
}
```

> The explicit synthetic style measures the *mechanism's upper bound* (can guidance move
> named items up the ranking?) rather than realistic latent policy. Treat natural-language
> (manual) results as the more conservative signal. See `docs/RESEARCH_PAPER.md` §4.1.

## `queries.json` — evaluation queries

```json
{
  "id": "q002",
  "query": "International travel with no credit history",
  "category": "travel",
  "expected_top_cards": ["card_013", "card_016", "card_018"],
  "policy_preferred_cards": ["card_013", "card_016", "card_018", "card_020"],
  "policy_excluded_cards": ["card_011", "card_013", "card_021"],
  "difficulty": "hard"
}
```

Three label types are kept **deliberately separate** so the evaluation is not circular:

- `expected_top_cards` — **relevance gold**, derived only from card attributes matched to the
  query category, *independently of the guidance rules*. The evaluator reports the best
  (lowest) rank among them. May be empty for ambiguous/adversarial queries (then the query is
  excluded from accuracy). Never derived from guidance.
- `policy_preferred_cards` — `BOOST` targets of guidance matching the query. Used **only** for
  the controllability metric, never as relevance gold.
- `policy_excluded_cards` — `EXCLUDE` targets of guidance matching the query. Used **only** for
  the enforcement metric.
- `category` / `difficulty` — synthetic-set bookkeeping (`easy`/`medium`/`hard`/`expert`).

> Letting guidance define `expected_top_cards` (an earlier bug) makes the benchmark circular —
> the method is then rewarded for reproducing the label generator. Keep these fields distinct.

## Generating synthetic data

```bash
python -m src.data_generation.generate_dataset
```

See `src/data_generation/` for the card, guidance, and query generators and the validator.

## Governance dataset (`data/governance/`, non-card)

A document corpus governed by a hidden schedule, demonstrating generality.

- `documents.json` — items with governance **attributes**: `classification`
  (`public`/`internal`/`confidential`/`restricted`), `status` (`current`/`deprecated`),
  `jurisdiction` (`GLOBAL`/`EU`/`US`), `contains_pii`, `legal_hold`, plus `topic`/`subtopic`.
- `governance.md` — the human-readable **hidden schedule** (never sent to the model).
- `policies.json` — the schedule compiled to **attribute-predicate** policies:
  `{action, tier (hard|soft), weight, trigger.keywords, predicate}`. Predicates reference
  attributes (not IDs); grammar in `src/models/predicate.py`.
- `queries.json` — `{query, topic, subtopic, region, expected_topic_docs (sub-topic gold,
  governance-independent), authorized_doc}`.

Regenerate: `python scripts/make_governance_dataset.py`.
