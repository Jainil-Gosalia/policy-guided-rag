"""
Explicit policy operator for Policy-Guided RAG.

The query-augmentation mechanism can only *add* topical signal to the query, so
it cannot express negative guidance (DEMOTE/EXCLUDE) and does not reliably
express positive guidance (BOOST) either — a cross-encoder scores topical
relevance, not preference.

This operator acts directly on the candidate ranking using the *structured*
action of each retrieved guidance rule:

    BOOST    add +weight to the target cards' rerank scores
    DEMOTE   subtract weight from the target cards' rerank scores
    EXCLUDE  hard-remove the target cards from the candidate set

EXCLUDE is a structural removal (the same idea as the chunk_type filter), so it
is exact and leakage-safe. BOOST/DEMOTE are soft score adjustments. The operator
runs AFTER cross-encoder scoring and BEFORE the context-only filter, so guidance
still never reaches the LLM — the zero-leakage guarantee is unchanged.

Optionally, BOOST targets that were not retrieved into the candidate pool can be
*injected* (fetched by id and scored) so policy can surface a card that
embedding similarity missed.
"""
from typing import List, Dict, Optional, Tuple, Set


class PolicyOperator:
    """Apply BOOST/DEMOTE/EXCLUDE actions from structured guidance to a ranking."""

    def __init__(self, weight: float = 5.0, inject_boosted: bool = True):
        """
        Args:
            weight: magnitude added (BOOST) / subtracted (DEMOTE) from rerank scores
            inject_boosted: if True, BOOST-target cards absent from the candidate
                pool are fetched and scored so they can be surfaced
        """
        self.weight = weight
        self.inject_boosted = inject_boosted

    @staticmethod
    def parse_actions(guidance_chunks: List[Dict]) -> Tuple[Set[str], Set[str], Set[str]]:
        """Extract (boost, demote, exclude) target card-id sets from retrieved
        guidance chunk metadata. EXCLUDE wins over BOOST/DEMOTE on conflict."""
        boost: Set[str] = set()
        demote: Set[str] = set()
        exclude: Set[str] = set()
        for g in guidance_chunks:
            meta = g.get('metadata', g)  # works whether passed raw or formatted
            action = (meta.get('action') or '').upper()
            raw = meta.get('target_cards') or ''
            targets = [c for c in raw.split(',') if c] if isinstance(raw, str) else list(raw)
            if action == 'BOOST':
                boost.update(targets)
            elif action == 'DEMOTE':
                demote.update(targets)
            elif action == 'EXCLUDE':
                exclude.update(targets)
        # EXCLUDE takes precedence
        boost -= exclude
        demote -= exclude
        return boost, demote, exclude

    def apply(self,
              candidates: List[Dict],
              guidance_chunks: List[Dict],
              reranker=None,
              query: Optional[str] = None,
              vector_store=None) -> List[Dict]:
        """Return a re-ordered candidate list with policy actions applied.

        Args:
            candidates: reranked context chunks, each with a 'rerank_score'
            guidance_chunks: retrieved guidance chunks (with action/target metadata)
            reranker: cross-encoder, needed only to score injected cards
            query: raw query, needed only to score injected cards
            vector_store: store, needed only to fetch injected cards

        Returns:
            Re-sorted list of context chunks (EXCLUDE targets removed).
        """
        boost, demote, exclude = self.parse_actions(guidance_chunks)

        # Optionally inject BOOST targets that are not already candidates.
        if self.inject_boosted and boost and reranker is not None and vector_store is not None:
            present = {c['metadata'].get('card_id') for c in candidates}
            missing = [cid for cid in boost if cid not in present]
            injected = vector_store.get_context_by_card_ids(missing)
            if injected:
                scored = reranker.rerank(query, injected, top_k=len(injected))
                candidates = candidates + scored

        deltas = {cid: self.weight for cid in boost}
        deltas.update({cid: -self.weight for cid in demote})
        return self._finalize(candidates, deltas, exclude, boost,
                              reranker=reranker, query=query, vector_store=vector_store)

    def apply_policy_set(self,
                         candidates: List[Dict],
                         policy_set: List[Dict],
                         items: Dict[str, Dict],
                         query: str,
                         reranker=None,
                         vector_store=None) -> List[Dict]:
        """Apply attribute-PREDICATE policies (governance schedule) to a ranking.

        Unlike ``apply`` (which reads actions off retrieved guidance chunks and is therefore
        gated by guidance-retrieval recall), this evaluates the full policy set's triggers
        against the query, so HARD constraints (EXCLUDE) are applied unconditionally and are
        exact — not dependent on a rule being retrieved.

        Args:
            candidates: reranked context chunks (each with 'rerank_score' and metadata.card_id)
            policy_set: list of predicate policies (see ``predicate`` module)
            items: id -> attribute dict, for predicate resolution
            query: raw user query (for triggers and injection scoring)
            reranker, vector_store: needed only to inject BOOST targets missing from the pool

        Returns:
            Re-sorted list of context chunks with EXCLUDE targets removed.
        """
        from .predicate import applicable_policies, resolve_targets

        deltas: Dict[str, float] = {}
        exclude: set = set()
        boost: set = set()
        for p in applicable_policies(policy_set, query):
            pred = p.get("predicate")
            targets = set(resolve_targets(pred, items)) if pred is not None else set(p.get("target_cards", []))
            action = (p.get("action") or "").upper()
            w = float(p.get("weight", self.weight))
            if action == "EXCLUDE":
                exclude |= targets
            elif action == "BOOST":
                boost |= targets
                for t in targets:
                    deltas[t] = deltas.get(t, 0.0) + w
            elif action == "DEMOTE":
                for t in targets:
                    deltas[t] = deltas.get(t, 0.0) - w

        # EXCLUDE takes precedence over soft adjustments.
        for t in exclude:
            deltas.pop(t, None)
        boost -= exclude
        return self._finalize(candidates, deltas, exclude, boost,
                              reranker=reranker, query=query, vector_store=vector_store)

    def _finalize(self, candidates, deltas, exclude, boost_ids,
                  reranker=None, query=None, vector_store=None) -> List[Dict]:
        """Inject missing BOOST targets, apply score deltas and exclusions, re-sort."""
        if self.inject_boosted and boost_ids and reranker is not None and vector_store is not None:
            present = {c['metadata'].get('card_id') for c in candidates}
            missing = [cid for cid in boost_ids if cid not in present and cid not in exclude]
            injected = vector_store.get_context_by_card_ids(missing)
            if injected:
                scored = reranker.rerank(query, injected, top_k=len(injected))
                candidates = candidates + scored

        adjusted = []
        for c in candidates:
            cid = c['metadata'].get('card_id')
            if cid in exclude:
                continue  # structural removal
            c = dict(c)
            c['policy_score'] = c.get('rerank_score', 0.0) + deltas.get(cid, 0.0)
            adjusted.append(c)

        adjusted.sort(key=lambda x: x['policy_score'], reverse=True)
        return adjusted
