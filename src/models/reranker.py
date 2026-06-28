"""
Cross-encoder reranker wrapper
"""
from sentence_transformers import CrossEncoder
from typing import List, Dict, Optional

from ..config.config import Config, ModelRegistry


class CrossEncoderReranker:
    """
    Reranks context chunks using cross-encoder with augmented query
    """

    def __init__(self,
                 model_name: Optional[str] = None,
                 config: Optional[Config] = None):
        """Initialize cross-encoder

        Args:
            model_name: Hugging Face model name (overrides config)
            config: Config object for centralized settings
        """
        # Use config if provided
        if config:
            model_name = model_name or config.get_reranker_model()

        # Try to resolve model name through registry if it looks like a short name
        if model_name:
            registry = ModelRegistry()
            resolved = registry.get_reranker_model(model_name)
            if resolved:
                model_name = resolved
        else:
            model_name = "mixedbread-ai/mxbai-rerank-large-v1"

        print(f"Loading cross-encoder: {model_name}")
        self.model = CrossEncoder(model_name)
        self.model_name = model_name
        print("+ Cross-encoder loaded")

    def rerank(self,
               query: str,
               chunks: List[Dict],
               top_k: int = 5) -> List[Dict]:
        """Rerank chunks using cross-encoder

        Args:
            query: Query string (can be augmented with guidance)
            chunks: List of chunk dicts to rerank
            top_k: Number of top chunks to return

        Returns:
            List of reranked chunks with scores
        """
        if not chunks:
            return []

        # Prepare pairs for cross-encoder
        pairs = [[query, chunk['text']] for chunk in chunks]

        # Score all pairs
        scores = self.model.predict(pairs)

        # Add scores to chunks
        for chunk, score in zip(chunks, scores):
            chunk['rerank_score'] = float(score)

        # Sort by score (descending)
        reranked = sorted(chunks, key=lambda x: x['rerank_score'], reverse=True)

        # Return top-k
        return reranked[:top_k]

    def rerank_batch(self,
                     queries: List[str],
                     chunks_list: List[List[Dict]],
                     top_k: int = 5) -> List[List[Dict]]:
        """Rerank multiple query-chunk sets

        Args:
            queries: List of queries
            chunks_list: List of chunk lists (one per query)
            top_k: Number of top chunks per query

        Returns:
            List of reranked chunk lists
        """
        return [
            self.rerank(q, chunks, top_k)
            for q, chunks in zip(queries, chunks_list)
        ]