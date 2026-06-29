"""
Vector store with metadata-based chunk type separation
"""
import chromadb
from typing import List, Dict, Optional
from chromadb.utils import embedding_functions

from ..config.config import Config


class PolicyGuidedVectorStore:
    """
    Vector store that supports separate retrieval of context and guidance chunks
    """

    def __init__(self,
                 collection_name: Optional[str] = None,
                 embedding_model: Optional[str] = None,
                 persist_directory: Optional[str] = None,
                 config: Optional[Config] = None):
        """
        Initialize vector store

        Args:
            collection_name: Name of the ChromaDB collection (overrides config)
            embedding_model: Sentence transformer model for embeddings (overrides config)
            persist_directory: Directory to persist database (None for in-memory)
            config: Config object for centralized settings
        """
        # Use config if provided
        if config:
            collection_name = collection_name or config.vector_store.collection_name
            embedding_model = embedding_model or config.embedding.model
            persist_directory = persist_directory or config.vector_store.persist_directory
        else:
            collection_name = collection_name or "policy_guided_rag"
            embedding_model = embedding_model or "sentence-transformers/all-MiniLM-L6-v2"

        # Initialize ChromaDB client - use EphemeralClient for in-memory (faster for experiments)
        if persist_directory:
            self.client = chromadb.PersistentClient(path=persist_directory)
        else:
            self.client = chromadb.EphemeralClient()

        # Create embedding function
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_model
        )

        # Get or create collection. Build the HNSW index single-threaded so retrieval is
        # deterministic run-to-run (parallel construction reorders ties; the index is
        # ephemeral and rebuilt each run).
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={"description": "Policy-guided RAG with context and guidance chunks",
                      "hnsw:num_threads": 1}
        )

        print(f"+ Initialized vector store with {self.collection.count()} chunks")

    def add_chunks(self,
                   texts: List[str],
                   chunk_ids: List[str],
                   chunk_types: List[str],
                   metadatas: Optional[List[Dict]] = None):
        """
        Add chunks to vector store with type metadata

        Args:
            texts: List of text chunks
            chunk_ids: List of unique IDs for each chunk
            chunk_types: List of types ("context" or "guidance")
            metadatas: Optional additional metadata for each chunk
        """
        if metadatas is None:
            metadatas = [{} for _ in texts]

        # Add chunk_type to metadata
        for i, chunk_type in enumerate(chunk_types):
            metadatas[i]['chunk_type'] = chunk_type

        self.collection.add(
            documents=texts,
            ids=chunk_ids,
            metadatas=metadatas
        )

        print(f"+ Added {len(texts)} chunks to vector store")

    def retrieve_context(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        Retrieve context chunks only

        Args:
            query: Search query
            top_k: Number of chunks to retrieve

        Returns:
            List of dicts with keys: id, text, metadata, distance
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where={"chunk_type": "context"}
        )

        return self._format_results(results)

    def retrieve_guidance(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Retrieve guidance chunks only

        Args:
            query: Search query
            top_k: Number of chunks to retrieve

        Returns:
            List of dicts with keys: id, text, metadata, distance
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where={"chunk_type": "guidance"}
        )

        return self._format_results(results)

    def get_context_by_card_ids(self, card_ids: List[str]) -> List[Dict]:
        """Fetch context chunks for specific card IDs (used for policy injection).

        Lets the PolicyOperator pull a BOOST-target card into the candidate pool
        even when embedding similarity did not surface it. Returns chunks in the
        same dict format as the retrieve_* methods (distance is None — these are
        fetched by id, not ranked).

        Args:
            card_ids: card IDs to fetch context chunks for

        Returns:
            List of chunk dicts (possibly empty).
        """
        if not card_ids:
            return []

        results = self.collection.get(
            where={"$and": [{"chunk_type": "context"}, {"card_id": {"$in": card_ids}}]}
        )

        formatted = []
        for i in range(len(results['ids'])):
            formatted.append({
                'id': results['ids'][i],
                'text': results['documents'][i],
                'metadata': results['metadatas'][i],
                'distance': None,
            })
        return formatted

    def _format_results(self, results: Dict) -> List[Dict]:
        """Format ChromaDB results into clean list of dicts"""
        formatted = []

        for i in range(len(results['ids'][0])):
            formatted.append({
                'id': results['ids'][0][i],
                'text': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i]
            })

        return formatted

    def clear(self):
        """Clear all data from collection"""
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.create_collection(
            name=self.collection.name,
            embedding_function=self.embedding_function
        )
        print("+ Cleared vector store")

    def get_stats(self) -> Dict:
        """Get statistics about stored chunks"""
        total = self.collection.count()

        # Count by type
        context_count = len(self.collection.get(where={"chunk_type": "context"})['ids'])
        guidance_count = len(self.collection.get(where={"chunk_type": "guidance"})['ids'])

        return {
            'total': total,
            'context': context_count,
            'guidance': guidance_count
        }