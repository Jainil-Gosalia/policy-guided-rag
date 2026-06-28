"""
Configuration loader and model registry
"""
import yaml
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from pathlib import Path


@dataclass
class PipelineConfig:
    """Pipeline hyperparameters"""
    k_context: int = 10
    k_guidance: int = 3
    top_n: int = 5
    max_guidance_in_query: int = 3
    policy_mode: str = "operator"  # augment | operator | both | none
    policy_weight: float = 5.0     # BOOST/DEMOTE magnitude for the operator


@dataclass
class EmbeddingConfig:
    """Embedding model settings"""
    model: str = "sentence-transformers/all-MiniLM-L6-v2"
    dimension: int = 384


@dataclass
class RerankerConfig:
    """Reranker settings"""
    default: str = "mixedbread-ai/mxbai-rerank-large-v1"


@dataclass
class VectorStoreConfig:
    """Vector store settings"""
    collection_name: str = "policy_guided_rag"
    persist_directory: Optional[str] = None


@dataclass
class QueryAugmenterConfig:
    """Query augmentation settings"""
    separator: str = " [GUIDANCE] "


@dataclass
class Config:
    """Main configuration object"""
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    reranker: RerankerConfig = field(default_factory=RerankerConfig)
    vector_store: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    query_augmenter: QueryAugmenterConfig = field(default_factory=QueryAugmenterConfig)
    seed: int = 42

    def get_reranker_model(self) -> str:
        """Get the full reranker model name"""
        return self.reranker.default

    def get_embedding_model(self) -> str:
        """Get the embedding model name"""
        return self.embedding.model


class ModelRegistry:
    """Registry for looking up model information"""

    def __init__(self, models_config_path: Optional[Path] = None):
        if models_config_path is None:
            models_config_path = Path(__file__).parent.parent.parent / "config" / "models.yaml"

        with open(models_config_path, 'r') as f:
            self.models = yaml.safe_load(f)

    def get_embedding_model(self, short_name: str) -> str:
        """Get full embedding model name from short name"""
        return self.models.get('embedding', {}).get(short_name, {}).get('full_name', short_name)

    def get_reranker_model(self, short_name: str) -> str:
        """Get full reranker model name from short name"""
        return self.models.get('reranker', {}).get(short_name, {}).get('full_name', short_name)

    def get_embedding_dimension(self, short_name: str) -> int:
        """Get embedding dimension"""
        return self.models.get('embedding', {}).get(short_name, {}).get('dimension', 384)


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from YAML file"""
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "default.yaml"

    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)

    return Config(
        pipeline=PipelineConfig(**data.get('pipeline', {})),
        embedding=EmbeddingConfig(**data.get('embedding', {})),
        reranker=RerankerConfig(**data.get('reranker', {})),
        vector_store=VectorStoreConfig(**data.get('vector_store', {})),
        query_augmenter=QueryAugmenterConfig(**data.get('query_augmenter', {})),
        seed=data.get('seed', 42)
    )


def override_config(config: Config, overrides: Dict[str, Any]) -> Config:
    """Override config values from a dict (e.g., from CLI)"""
    for key, value in overrides.items():
        if hasattr(config, key):
            if isinstance(value, dict):
                # Handle nested config objects
                nested = getattr(config, key)
                for subkey, subvalue in value.items():
                    if hasattr(nested, subkey):
                        setattr(nested, subkey, subvalue)
            else:
                setattr(config, key, value)
    return config