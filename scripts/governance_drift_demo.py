#!/usr/bin/env python
"""
Catalog-drift robustness: predicate policies vs. hand-compiled ID lists.

A governance rule authored as "EXCLUDE these document IDs" is frozen at authoring time and
silently fails when new documents are added. The same rule authored as an attribute PREDICATE
("EXCLUDE classification == restricted") keeps holding. This demo adds a brand-new restricted
document (authored AFTER the policy) and shows the predicate operator still excludes it while
the ID-list equivalent leaks it.

No models required — operates at the ranking/operator layer.

Run: python scripts/governance_drift_demo.py
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from src.models.policy_operator import PolicyOperator
from src.models.predicate import resolve_targets, applicable_policies

DATA = Path(__file__).parent.parent / "data" / "governance"


def main():
    docs = json.loads((DATA / "documents.json").read_text(encoding="utf-8"))
    policies = json.loads((DATA / "policies.json").read_text(encoding="utf-8"))
    items = {d["id"]: d for d in docs}

    query = "I'm working from home and can't reach internal systems — how do I get connected?"

    # A new restricted+PII document for an existing sub-topic, authored AFTER the ID-list policy.
    new_doc = {
        "id": "doc_vpn_access_setup_NEW_restricted", "topic": "vpn_access", "subtopic": "setup",
        "status": "current", "classification": "restricted",
        "jurisdiction": "GLOBAL", "contains_pii": True, "legal_hold": False,
        "text": "Requesting VPN access (restricted, contains PII): submit the access request and import the profile.",
    }
    items_drift = dict(items); items_drift[new_doc["id"]] = new_doc

    # Candidate pool a reranker might produce for the VPN query (incl. the new restricted doc).
    pool_ids = ["doc_vpn_access_setup_current", "doc_vpn_access_setup_deprecated",
                new_doc["id"], "doc_vpn_access_mfa_current", "doc_vpn_access_trouble_current"]
    candidates = [{"metadata": {"card_id": i, "chunk_type": "context"}, "rerank_score": 5.0 - n}
                  for n, i in enumerate(pool_ids)]

    op = PolicyOperator(weight=5.0, inject_boosted=False)

    # (A) PREDICATE policies — evaluated against the CURRENT corpus (includes the new doc).
    pred_out = op.apply_policy_set(candidates, policies, items_drift, query)
    pred_ids = [c["metadata"]["card_id"] for c in pred_out]

    # (B) ID-LIST equivalent — exclusion lists compiled BEFORE the new doc existed.
    #     Resolve each EXCLUDE policy's predicate over the ORIGINAL corpus only, freeze to ids.
    frozen_exclude = set()
    for p in applicable_policies(policies, query):
        if p.get("action", "").upper() == "EXCLUDE":
            frozen_exclude.update(resolve_targets(p.get("predicate"), items))  # original items
    idlist_guidance = [{"metadata": {"action": "EXCLUDE", "target_cards": ",".join(sorted(frozen_exclude))}}]
    idlist_out = op.apply(candidates, idlist_guidance)
    idlist_ids = [c["metadata"]["card_id"] for c in idlist_out]

    print("=" * 70)
    print("CATALOG-DRIFT ROBUSTNESS: predicate policy vs. frozen ID list")
    print("=" * 70)
    print(f"\nNew doc authored after the policy: {new_doc['id']}")
    print(f"  (classification=restricted, contains_pii=True)\n")
    print(f"ID-list policy froze EXCLUDE = {sorted(frozen_exclude)}")
    print(f"  -> does NOT contain the new id (it didn't exist at authoring time)\n")
    print(f"Survivors with FROZEN ID-LIST policy : {idlist_ids}")
    leaked = new_doc['id'] in idlist_ids
    print(f"   new restricted doc leaked? {'YES — COMPLIANCE FAILURE' if leaked else 'no'}\n")
    print(f"Survivors with PREDICATE policy      : {pred_ids}")
    held = new_doc['id'] not in pred_ids
    print(f"   new restricted doc excluded? {'YES — still compliant' if held else 'NO'}")
    print("=" * 70)
    assert leaked and held, "drift demo expected ID-list to leak and predicate to hold"
    print("Predicate policies survive corpus drift; frozen ID lists do not.")


if __name__ == "__main__":
    main()
