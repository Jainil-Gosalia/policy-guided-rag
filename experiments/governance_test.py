"""
Governance experiment (non-card domain).

A corporate knowledge base governed by a hidden Data Governance & Records Schedule
(`data/governance/`). Documents carry governance attributes (classification, status,
jurisdiction, PII, legal hold); the schedule is compiled to attribute-PREDICATE policies
that shape retrieval and are never shown to the user/LLM.

Conditions:
    vanilla      embedding similarity only
    rerank_only  cross-encoder rerank on the raw query (no governance)
    operator     rerank + predicate policy operator (hard EXCLUDE + soft BOOST/DEMOTE)

Metrics:
    * Topic relevance (governance-independent gold): top-5 accuracy, mean position
    * Governance COMPLIANCE: rate at which a must-exclude doc (restricted / PII /
      deprecated / legal-hold) appears in the top-n  (operator target: 0%)
    * AUTHORIZED-version hit: does the current/region-correct doc reach the top-n
    * PROMOTION capability: authorized doc absent from rerank_only top-n but surfaced
      by the operator (a filter cannot do this)
    * Per-query LATENCY of the retrieve->rerank->operator path
"""
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:  # ensure non-ASCII output works on Windows consoles (cp1252)
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from experiments.base import BaseExperiment
from src.models.vector_store import PolicyGuidedVectorStore
from src.models.baselines import VanillaRAG, RerankOnlyRAG
from src.models.policy_operator import PolicyOperator
from src.evaluation.metrics import get_retrieval_metrics as _metrics, any_in_top_n
from src.evaluation.stats import paired_comparison

DATA = Path(__file__).parent.parent / "data" / "governance"
MUST_EXCLUDE = lambda a: (a["classification"] == "restricted" or a["contains_pii"]
                          or a["status"] in ("deprecated", "superseded") or a["legal_hold"])


class GovernanceTestExperiment(BaseExperiment):
    """Asymmetric visibility on a document corpus governed by a hidden schedule."""

    def __init__(self, config_overrides=None):
        super().__init__("governance_test", config_overrides)

    def _load(self):
        docs = json.loads((DATA / "documents.json").read_text(encoding="utf-8"))
        queries = json.loads((DATA / "queries.json").read_text(encoding="utf-8"))
        policies = json.loads((DATA / "policies.json").read_text(encoding="utf-8"))
        return docs, queries, policies

    def _build_store(self, docs):
        vs = PolicyGuidedVectorStore(config=self.config)
        vs.add_chunks(
            texts=[d["text"] for d in docs],
            chunk_ids=[d["id"] for d in docs],
            chunk_types=["context"] * len(docs),
            metadatas=[{"card_id": d["id"]} for d in docs],  # reuse 'card_id' as the item key
        )
        return vs

    def run(self, dataset: str = "governance", extra_docs=None):
        print("=" * 70)
        print("GOVERNANCE EXPERIMENT (non-card: corporate KB + hidden schedule)")
        print("=" * 70)
        docs, queries, policies = self._load()
        if extra_docs:
            docs = docs + extra_docs
        items = {d["id"]: d for d in docs}
        print(f"\n{len(docs)} documents, {len(queries)} queries, {len(policies)} predicate policies")

        vs = self._build_store(docs)
        reranker = self.create_reranker()
        vanilla = VanillaRAG(vs, config=self.config)
        rerank_only = RerankOnlyRAG(vs, reranker, config=self.config)
        operator = PolicyOperator(weight=self.config.pipeline.policy_weight)
        top_n = self.config.pipeline.top_n

        conds = ["vanilla", "rerank_only", "operator"]
        acc = {c: [] for c in conds}
        compliance = {c: [] for c in conds}     # 1 if a must-exclude doc leaks into top-n
        authorized = {c: [] for c in conds}     # 1 if authorized doc in top-n
        promo_ro, promo_op = [], []
        latencies = []

        for q in queries:
            gold = q["expected_topic_docs"]
            auth = q["authorized_doc"]

            finals = {}
            finals["vanilla"] = vanilla.retrieve(q["query"])["final_chunks"][:top_n]
            finals["rerank_only"] = rerank_only.retrieve(q["query"])["final_chunks"][:top_n]

            t0 = time.perf_counter()
            pool = vs.retrieve_context(q["query"], top_k=self.config.pipeline.k_context)
            reranked = reranker.rerank(q["query"], pool, top_k=len(pool))
            opped = operator.apply_policy_set(reranked, policies, items, q["query"],
                                              reranker=reranker, vector_store=vs)
            finals["operator"] = opped[:top_n]
            latencies.append((time.perf_counter() - t0) * 1000.0)

            for c in conds:
                ids = [x["metadata"]["card_id"] for x in finals[c]]
                acc[c].append(_metrics(finals[c], gold))
                compliance[c].append(int(any(MUST_EXCLUDE(items[i]) for i in ids if i in items)))
                authorized[c].append(int(auth in ids))

            ro_ids = [x["metadata"]["card_id"] for x in finals["rerank_only"]]
            op_ids = [x["metadata"]["card_id"] for x in finals["operator"]]
            promo_ro.append(int(auth in ro_ids))
            promo_op.append(int(auth in op_ids))

        results = self._summarize(conds, acc, compliance, authorized, promo_ro, promo_op, latencies, queries)
        self._print(results)
        self.save_results(results)
        print("=" * 70)
        return results

    def _agg(self, ms):
        n = len(ms)
        return {"top_1": sum(m["top_1"] for m in ms) / n,
                "top_5": sum(m["top_5"] for m in ms) / n,
                "avg_pos": sum(m["position"] for m in ms) / n, "n": n}

    def _summarize(self, conds, acc, compliance, authorized, promo_ro, promo_op, lat, queries):
        n = len(queries)
        promotions = sum(1 for r, o in zip(promo_ro, promo_op) if o and not r)
        lat_sorted = sorted(lat)
        return {
            "dataset": "governance",
            "n_queries": n,
            "accuracy": {c: self._agg(acc[c]) for c in conds},
            "compliance_violation_rate": {c: sum(compliance[c]) / n for c in conds},
            "authorized_hit_rate": {c: sum(authorized[c]) / n for c in conds},
            "promotion": {"rerank_only_auth_hits": sum(promo_ro),
                          "operator_auth_hits": sum(promo_op),
                          "promotions_operator_only": promotions},
            "authorized_significance": paired_comparison(
                [{"top_1": h, "top_5": h, "position": 1 if h else 99} for h in promo_ro],
                [{"top_1": h, "top_5": h, "position": 1 if h else 99} for h in promo_op],
                "rerank_only", "operator"),
            "latency_ms": {"mean": sum(lat) / n, "p50": lat_sorted[n // 2],
                           "p95": lat_sorted[min(n - 1, int(0.95 * n))], "max": max(lat)},
        }

    def _print(self, r):
        print("\n" + "=" * 70)
        print(f"RELEVANCE — sub-topic gold, governance-independent (n={r['n_queries']})")
        print("=" * 70)
        print(f"{'Condition':<14}{'Top-1':>9}{'Top-5':>9}{'AvgPos':>9}")
        for c, a in r["accuracy"].items():
            print(f"{c:<14}{a['top_1']*100:>8.1f}%{a['top_5']*100:>8.1f}%{a['avg_pos']:>9.1f}")

        print("\n" + "=" * 70)
        print("GOVERNANCE COMPLIANCE  (must-exclude doc appears in top-n; lower is better)")
        print("=" * 70)
        for c, v in r["compliance_violation_rate"].items():
            print(f"  {c:<14}{v*100:>6.1f}%")
        print("  (operator target: 0.0% — hard predicate exclusion, retrieval-independent)")

        print("\n" + "=" * 70)
        print("AUTHORIZED-VERSION HIT  (current/region-correct doc in top-n)")
        print("=" * 70)
        for c, v in r["authorized_hit_rate"].items():
            print(f"  {c:<14}{v*100:>6.1f}%")
        p = r["promotion"]
        sig = r["authorized_significance"]["top_5_mcnemar"]
        print(f"\n  Promotion (a filter can't do this): operator surfaces the authorized doc in "
              f"{p['promotions_operator_only']} queries where rerank-only did not "
              f"(McNemar p={sig['p_value']:.4f}).")

        lat = r["latency_ms"]
        print("\n" + "=" * 70)
        print("LATENCY — retrieve + rerank + policy operator (CPU)")
        print("=" * 70)
        print(f"  mean {lat['mean']:.1f} ms | p50 {lat['p50']:.1f} | p95 {lat['p95']:.1f} | max {lat['max']:.1f}")
        print("  The operator adds only attribute predicate evaluation (microseconds); it makes")
        print("  no LLM call. An LLM-parse alternative (~10 chunks + ~12 rules + system prompt ->")
        print("  structured output) adds a full generation round-trip (hundreds of ms to seconds),")
        print("  per-query token cost, and hallucination risk -- avoided here by construction.")


def main():
    GovernanceTestExperiment().run()


if __name__ == "__main__":
    main()
