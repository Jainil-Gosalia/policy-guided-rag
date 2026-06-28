"""
Baseline methods for comparison.

Three conditions are used throughout the experiments so that the contribution of
*guidance* can be isolated from the contribution of *re-ranking*:

    VanillaRAG     embedding similarity only                       (no reranker, no guidance)
    RerankOnlyRAG  embedding -> cross-encoder rerank on RAW query  (reranker, no guidance)
    PolicyGuided   embedding -> cross-encoder rerank on AUGMENTED  (reranker + guidance)

VanillaRAG vs RerankOnlyRAG measures the re-ranker effect.
RerankOnlyRAG vs PolicyGuided measures the *guidance* effect — this is the
comparison that supports the paper's central claim.
"""
from typing import List, Dict, Optional
from .vector_store import PolicyGuidedVectorStore
from .reranker import CrossEncoderReranker

from ..config.config import Config


class VanillaRAG:
    """
    Standard RAG: retrieve context only, no guidance, no reranking
    """

    def __init__(self,
                 vector_store: PolicyGuidedVectorStore,
                 top_k: Optional[int] = None,
                 config: Optional[Config] = None):
        """Initialize vanilla RAG

        Args:
            vector_store: Initialized vector store
            top_k: Number of chunks to retrieve (overrides config)
            config: Config object for centralized settings
        """
        self.vector_store = vector_store

        if config:
            self.top_k = top_k or config.pipeline.top_n
        else:
            self.top_k = top_k or 5

    def retrieve(self, query: str) -> Dict:
        """Retrieve context chunks using vector similarity only

        Args:
            query: User query

        Returns:
            Dict with 'final_chunks'
        """
        # Simple vector retrieval, no guidance
        chunks = self.vector_store.retrieve_context(query, top_k=self.top_k)

        return {'final_chunks': chunks}


class RerankOnlyRAG:
    """
    Ablation baseline: same candidate pool and cross-encoder reranker as the
    policy-guided pipeline, but re-ranks against the *raw* query (no guidance
    augmentation). This is the control that isolates the guidance effect.
    """

    def __init__(self,
                 vector_store: PolicyGuidedVectorStore,
                 reranker: CrossEncoderReranker,
                 k_context: Optional[int] = None,
                 top_n: Optional[int] = None,
                 config: Optional[Config] = None):
        """Initialize rerank-only baseline

        Args:
            vector_store: Initialized vector store
            reranker: Cross-encoder reranker (shared with the PG pipeline)
            k_context: Candidate pool size before reranking (overrides config)
            top_n: Number of final chunks to return (overrides config)
            config: Config object for centralized settings
        """
        self.vector_store = vector_store
        self.reranker = reranker

        if config:
            self.k_context = k_context or config.pipeline.k_context
            self.top_n = top_n or config.pipeline.top_n
        else:
            self.k_context = k_context or 10
            self.top_n = top_n or 5

    def retrieve(self, query: str) -> Dict:
        """Retrieve a candidate pool and rerank against the raw query.

        Args:
            query: User query

        Returns:
            Dict with 'final_chunks'
        """
        context_chunks = self.vector_store.retrieve_context(query, top_k=self.k_context)
        reranked = self.reranker.rerank(query, context_chunks, top_k=self.top_n)

        return {'final_chunks': reranked}