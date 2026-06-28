"""
End-to-end policy-guided RAG pipeline.

The pipeline supports several ways for guidance to influence ranking, selected
by ``policy_mode``:

    "augment"   guidance rule TEXT is appended to the query before reranking
                (the original query-augmentation mechanism)
    "operator"  guidance ACTIONS (BOOST/DEMOTE/EXCLUDE) are applied to the
                reranked scores by the PolicyOperator (raw query is reranked)
    "both"      augment the query AND apply the operator
    "none"      reranker only, guidance ignored (equivalent to RerankOnlyRAG)

In every mode the final stage keeps only ``chunk_type == 'context'`` chunks, so
guidance is structurally absent from the LLM-facing context (zero leakage).
"""
from typing import List, Dict, Optional
from .vector_store import PolicyGuidedVectorStore
from .query_augmenter import QueryAugmenter
from .reranker import CrossEncoderReranker
from .policy_operator import PolicyOperator

from ..config.config import Config


class PolicyGuidedPipeline:
    """
    Full pipeline: dual retrieval -> (augment | operator) -> reranking -> filtering
    """

    def __init__(self,
                 vector_store: PolicyGuidedVectorStore,
                 reranker: CrossEncoderReranker,
                 k_context: Optional[int] = None,
                 k_guidance: Optional[int] = None,
                 top_n: Optional[int] = None,
                 max_guidance_in_query: Optional[int] = None,
                 policy_mode: Optional[str] = None,
                 policy_weight: Optional[float] = None,
                 config: Optional[Config] = None):
        """Initialize pipeline

        Args:
            vector_store: Initialized vector store
            reranker: Initialized cross-encoder reranker
            k_context: Number of context chunks to retrieve initially (overrides config)
            k_guidance: Number of guidance chunks to retrieve (overrides config)
            top_n: Number of final context chunks to return (overrides config)
            max_guidance_in_query: Max guidance chunks in augmented query (overrides config)
            policy_mode: One of "augment", "operator", "both", "none" (overrides config)
            policy_weight: BOOST/DEMOTE magnitude for the operator (overrides config)
            config: Config object for centralized settings
        """
        self.vector_store = vector_store
        self.reranker = reranker

        if config:
            self.k_context = k_context or config.pipeline.k_context
            self.k_guidance = k_guidance or config.pipeline.k_guidance
            self.top_n = top_n or config.pipeline.top_n
            max_guidance_in_query = max_guidance_in_query or config.pipeline.max_guidance_in_query
            self.policy_mode = policy_mode or config.pipeline.policy_mode
            policy_weight = policy_weight if policy_weight is not None else config.pipeline.policy_weight
        else:
            self.k_context = k_context or 10
            self.k_guidance = k_guidance or 3
            self.top_n = top_n or 5
            max_guidance_in_query = max_guidance_in_query or 3
            self.policy_mode = policy_mode or "augment"
            policy_weight = policy_weight if policy_weight is not None else 5.0

        self.query_augmenter = QueryAugmenter(max_guidance_chunks=max_guidance_in_query)
        self.policy_operator = PolicyOperator(weight=policy_weight)

    def retrieve(self, query: str, return_intermediate: bool = False) -> Dict:
        """Run full retrieval pipeline

        Args:
            query: User query
            return_intermediate: If True, return intermediate results for debugging

        Returns:
            Dict with 'final_chunks' and optionally intermediate results
        """
        use_augment = self.policy_mode in ("augment", "both")
        use_operator = self.policy_mode in ("operator", "both")

        # Step 1: Dual retrieval
        context_chunks = self.vector_store.retrieve_context(query, top_k=self.k_context)
        guidance_chunks = self.vector_store.retrieve_guidance(query, top_k=self.k_guidance)

        # Step 2: Query augmentation (text mechanism), if enabled
        rerank_query = (
            self.query_augmenter.augment(query, guidance_chunks) if use_augment else query
        )

        # Step 3: Cross-encoder reranking over the full candidate pool
        reranked_chunks = self.reranker.rerank(
            rerank_query, context_chunks, top_k=len(context_chunks)
        )

        # Step 3.5: Explicit policy operator (BOOST/DEMOTE/EXCLUDE), if enabled
        if use_operator:
            reranked_chunks = self.policy_operator.apply(
                reranked_chunks, guidance_chunks,
                reranker=self.reranker, query=query, vector_store=self.vector_store,
            )

        # Step 4: Post-rerank filtering (only context chunks reach the LLM)
        final_chunks = [
            chunk for chunk in reranked_chunks
            if chunk['metadata'].get('chunk_type') == 'context'
        ][:self.top_n]

        result = {'final_chunks': final_chunks}

        if return_intermediate:
            result.update({
                'context_chunks': context_chunks,
                'guidance_chunks': guidance_chunks,
                'augmented_query': rerank_query,
                'reranked_chunks': reranked_chunks,
                'policy_mode': self.policy_mode,
            })

        return result
