"""
Base experiment class for Policy-Guided RAG
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.config import Config, load_config, override_config
from src.config.paths import PathManager
from src.data.loaders import DataLoader
from src.data.preprocessors import ChunkPreparer
from src.models.vector_store import PolicyGuidedVectorStore
from src.models.reranker import CrossEncoderReranker
from src.models.pipeline import PolicyGuidedPipeline
from src.models.baselines import VanillaRAG, RerankOnlyRAG, MetadataFilterRAG
from src.evaluation.metrics import get_retrieval_metrics, compute_detailed_metrics


class BaseExperiment:
    """Base class for all experiments with config loading and result saving"""

    def __init__(self,
                 experiment_name: str,
                 config_overrides: Optional[Dict[str, Any]] = None):
        """Initialize experiment

        Args:
            experiment_name: Name of the experiment
            config_overrides: Optional dict to override config values
        """
        self.experiment_name = experiment_name

        # Load config
        self.config = load_config()
        if config_overrides:
            self.config = override_config(self.config, config_overrides)

        # Initialize components
        self.path_manager = PathManager()
        self.data_loader = DataLoader(self.path_manager)

        # Results storage
        self.vanilla_metrics_list = []
        self.pg_metrics_list = []
        self.detailed_results = []

    def setup_vector_store(self, dataset: str = 'manual') -> PolicyGuidedVectorStore:
        """Setup vector store with data from a dataset

        Args:
            dataset: Dataset name ('manual' or 'synthetic')

        Returns:
            Initialized vector store with chunks
        """
        # Load data
        cards, guidance, queries = self.data_loader.load_dataset(dataset)

        # Prepare chunks
        context_chunks = ChunkPreparer.prepare_context_chunks(cards)
        guidance_chunks = ChunkPreparer.prepare_guidance_chunks(guidance)

        # Create vector store
        vector_store = PolicyGuidedVectorStore(config=self.config)

        # Add all chunks
        all_chunks = context_chunks + guidance_chunks
        texts, ids, types, metadatas = ChunkPreparer.extract_chunk_data(all_chunks)
        vector_store.add_chunks(texts, ids, types, metadatas)

        print(f"  Vector store ready: {len(context_chunks)} context, {len(guidance_chunks)} guidance")

        return vector_store

    def create_reranker(self) -> CrossEncoderReranker:
        """Create a cross-encoder reranker (load once, share across conditions)."""
        return CrossEncoderReranker(config=self.config)

    def create_pipeline(self,
                        vector_store: PolicyGuidedVectorStore,
                        reranker: Optional[CrossEncoderReranker] = None,
                        policy_mode: Optional[str] = None) -> PolicyGuidedPipeline:
        """Create policy-guided pipeline

        Args:
            vector_store: Initialized vector store
            reranker: Optional shared reranker (created if not provided)
            policy_mode: Optional override of the guidance mechanism
                ("augment" | "operator" | "both" | "none")

        Returns:
            Policy-guided pipeline
        """
        reranker = reranker or self.create_reranker()
        return PolicyGuidedPipeline(vector_store, reranker,
                                    policy_mode=policy_mode, config=self.config)

    def create_baseline(self, vector_store: PolicyGuidedVectorStore) -> VanillaRAG:
        """Create vanilla RAG baseline (embedding similarity only)

        Args:
            vector_store: Initialized vector store

        Returns:
            Vanilla RAG baseline
        """
        return VanillaRAG(vector_store, config=self.config)

    def create_rerank_only(self,
                           vector_store: PolicyGuidedVectorStore,
                           reranker: Optional[CrossEncoderReranker] = None) -> RerankOnlyRAG:
        """Create the rerank-only ablation baseline (reranker, no guidance).

        Shares the reranker with the PG pipeline so the only difference is the
        guidance augmentation of the query.

        Args:
            vector_store: Initialized vector store
            reranker: Optional shared reranker (created if not provided)

        Returns:
            Rerank-only baseline
        """
        reranker = reranker or self.create_reranker()
        return RerankOnlyRAG(vector_store, reranker, config=self.config)

    def create_filter(self,
                      vector_store: PolicyGuidedVectorStore,
                      reranker: Optional[CrossEncoderReranker] = None) -> MetadataFilterRAG:
        """Create the rule-based metadata-filter baseline (rerank + hard EXCLUDE only)."""
        reranker = reranker or self.create_reranker()
        return MetadataFilterRAG(vector_store, reranker, config=self.config)

    def run_query(self,
                  query: str,
                  expected: List[str],
                  pipeline: PolicyGuidedPipeline,
                  baseline: VanillaRAG = None) -> Dict:
        """Run a single query through both pipelines

        Args:
            query: Query text
            expected: Expected card IDs
            pipeline: Policy-guided pipeline
            baseline: Optional vanilla baseline

        Returns:
            Dict with metrics for both
        """
        # Run policy-guided
        pg_result = pipeline.retrieve(query)
        pg_metrics = get_retrieval_metrics(pg_result['final_chunks'], expected)

        result = {
            'query': query[:50],
            'expected': expected,
            'pg': pg_metrics
        }

        # Run baseline if provided
        if baseline:
            vanilla_result = baseline.retrieve(query)
            vanilla_metrics = get_retrieval_metrics(vanilla_result['final_chunks'], expected)

            # Determine improvement
            if pg_metrics['position'] < vanilla_metrics['position']:
                improvement = "IMPROVED"
            elif pg_metrics['position'] > vanilla_metrics['position']:
                improvement = "WORSE"
            else:
                improvement = "SAME"

            result['vanilla'] = vanilla_metrics
            result['improvement'] = improvement

        return result

    def compute_summary(self) -> Dict:
        """Compute summary metrics

        Returns:
            Dict with aggregated metrics
        """
        n = len(self.pg_metrics_list)

        if n == 0:
            return {}

        if self.vanilla_metrics_list:
            return compute_detailed_metrics(self.pg_metrics_list, self.vanilla_metrics_list)
        else:
            # Policy-guided only
            return {
                'policy_guided': {
                    'top_1_accuracy': sum(m['top_1'] for m in self.pg_metrics_list) / n,
                    'top_5_accuracy': sum(m['top_5'] for m in self.pg_metrics_list) / n,
                    'avg_position': sum(m['position'] for m in self.pg_metrics_list) / n
                }
            }

    def save_results(self, results: Dict) -> Path:
        """Save results to file

        Args:
            results: Results dict to save

        Returns:
            Path to saved file
        """
        run_dir = self.path_manager.get_run_dir(self.experiment_name)

        # Snapshot config
        config_snapshot = {
            'pipeline': self.config.pipeline.__dict__,
            'embedding': self.config.embedding.__dict__,
            'reranker': self.config.reranker.__dict__,
            'vector_store': self.config.vector_store.__dict__,
            'seed': self.config.seed
        }

        output = {
            'timestamp': datetime.now().isoformat(),
            'experiment': self.experiment_name,
            'config': config_snapshot,
            'results': results
        }

        output_file = run_dir / 'results.json'
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"\nResults saved to {output_file}")
        return output_file

    def print_summary(self, results: Dict):
        """Print summary of results

        Args:
            results: Results dict
        """
        print("\n" + "="*70)
        print("SUMMARY RESULTS")
        print("="*70)

        pg = results.get('policy_guided', {})
        vanilla = results.get('vanilla', {})
        improvement = results.get('improvement', {})

        print(f"\n{'Metric':<30} {'Vanilla':<15} {'Policy-Guided':<15} {'Change':<15}")
        print("-"*70)

        if vanilla:
            print(f"{'Top-1 Accuracy':<30} {vanilla.get('top_1_accuracy', 0)*100:.1f}%{'':<8} {pg.get('top_1_accuracy', 0)*100:.1f}%{'':<8} {improvement.get('top_1_delta', 0)*100:+.1f}%")
            print(f"{'Top-5 Accuracy':<30} {vanilla.get('top_5_accuracy', 0)*100:.1f}%{'':<8} {pg.get('top_5_accuracy', 0)*100:.1f}%{'':<8} {improvement.get('top_5_delta', 0)*100:+.1f}%")
            print(f"{'Average Position':<30} {vanilla.get('avg_position', 0):.1f}{'':<12} {pg.get('avg_position', 0):.1f}{'':<12} {improvement.get('position_delta', 0):+.1f}")
            print("-"*70)
            print(f"\nQueries improved: {improvement.get('queries_improved', 0)*100:.1f}%")
        else:
            print(f"{'Top-1 Accuracy':<30} {pg.get('top_1_accuracy', 0)*100:.1f}%")
            print(f"{'Top-5 Accuracy':<30} {pg.get('top_5_accuracy', 0)*100:.1f}%")
            print(f"{'Average Position':<30} {pg.get('avg_position', 0):.1f}")

        print("="*70)

    def run(self, dataset: str = 'manual'):
        """Run the experiment - override in subclass

        Args:
            dataset: Dataset to use
        """
        raise NotImplementedError("Subclasses must implement run()")