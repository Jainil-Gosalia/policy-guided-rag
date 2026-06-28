"""
Query augmentation with guidance chunks
"""
from typing import List, Dict, Optional

from ..config.config import Config


class QueryAugmenter:
    """
    Augments user query with guidance chunks for cross-encoder reranking
    """

    def __init__(self,
                 max_guidance_chunks: int = 3,
                 separator: str = " [GUIDANCE] ",
                 config: Optional[Config] = None):
        """Initialize query augmenter

        Args:
            max_guidance_chunks: Maximum number of guidance chunks to include (overrides config)
            separator: Separator between query and guidance (overrides config)
            config: Config object for centralized settings
        """
        # Use config if provided
        if config:
            max_guidance_chunks = max_guidance_chunks or config.pipeline.max_guidance_in_query
            separator = separator or config.query_augmenter.separator

        self.max_guidance_chunks = max_guidance_chunks
        self.separator = separator

    def augment(self,
                query: str,
                guidance_chunks: List[Dict]) -> str:
        """Augment query with guidance chunks

        Args:
            query: Original user query
            guidance_chunks: List of guidance chunk dicts (from vector store)

        Returns:
            Augmented query string
        """
        if not guidance_chunks:
            return query

        # Take top-k guidance chunks
        selected_guidance = guidance_chunks[:self.max_guidance_chunks]

        # Extract text from guidance chunks
        guidance_texts = [chunk['text'] for chunk in selected_guidance]

        # Concatenate
        guidance_str = " ".join(guidance_texts)

        augmented = f"{query}{self.separator}{guidance_str}"

        return augmented

    def augment_batch(self,
                      queries: List[str],
                      guidance_chunks_list: List[List[Dict]]) -> List[str]:
        """Augment multiple queries

        Args:
            queries: List of queries
            guidance_chunks_list: List of guidance chunk lists (one per query)

        Returns:
            List of augmented queries
        """
        return [
            self.augment(q, g)
            for q, g in zip(queries, guidance_chunks_list)
        ]