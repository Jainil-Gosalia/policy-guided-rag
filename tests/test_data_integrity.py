"""Data-integrity tests: validate dataset JSON structure without loading models."""
import json

import pytest

DATASETS = ["manual", "synthetic"]


def _read(root, *parts):
    with open(root.joinpath(*parts), "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("dataset", DATASETS)
def test_dataset_files_exist_and_parse(project_root, dataset):
    base = project_root / "data" / dataset
    for fname in ("cards.json", "guidance.json", "queries.json"):
        assert (base / fname).exists(), f"missing {dataset}/{fname}"


@pytest.mark.parametrize("dataset", DATASETS)
def test_cards_have_required_fields(project_root, dataset):
    cards = _read(project_root, "data", dataset, "cards.json")
    assert len(cards) > 0
    ids = set()
    for c in cards:
        assert "id" in c and "name" in c and "annual_fee" in c
        ids.add(c["id"])
    assert len(ids) == len(cards), "card ids must be unique"


@pytest.mark.parametrize("dataset", DATASETS)
def test_guidance_have_rule_text(project_root, dataset):
    guidance = _read(project_root, "data", dataset, "guidance.json")
    assert len(guidance) > 0
    for g in guidance:
        assert g.get("rule"), "every guidance rule needs non-empty 'rule' text"


@pytest.mark.parametrize("dataset", DATASETS)
def test_queries_reference_existing_cards(project_root, dataset):
    cards = _read(project_root, "data", dataset, "cards.json")
    queries = _read(project_root, "data", dataset, "queries.json")
    card_ids = {c["id"] for c in cards}
    assert len(queries) > 0
    # Most queries have relevance gold; ambiguous/adversarial categories may have
    # an empty gold by design (no objective relevant card) and are excluded from
    # accuracy. Any gold/policy card IDs that ARE present must reference real cards.
    n_with_gold = 0
    for q in queries:
        assert q.get("query"), "query text required"
        expected = q.get("expected_top_cards", [])
        n_with_gold += int(bool(expected))
        for cid in expected:
            assert cid in card_ids, f"{dataset}: query references unknown card {cid}"
        for cid in q.get("policy_preferred_cards", []):
            assert cid in card_ids, f"{dataset}: policy_preferred references unknown card {cid}"
        for cid in q.get("policy_excluded_cards", []):
            assert cid in card_ids, f"{dataset}: policy_excluded references unknown card {cid}"
    # The benchmark must retain a substantial labelled subset.
    assert n_with_gold >= max(5, len(queries) // 2), \
        f"{dataset}: too few queries with relevance gold ({n_with_gold}/{len(queries)})"
