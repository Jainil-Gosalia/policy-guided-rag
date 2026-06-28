"""
Cross-encoder comparison experiment
Tests multiple cross-encoder models to find optimal reranker
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.config import Config, load_config
from src.config.paths import PathManager
from src.data.loaders import DataLoader
from src.data.preprocessors import ChunkPreparer
from src.models.vector_store import PolicyGuidedVectorStore
from src.models.reranker import CrossEncoderReranker
from src.models.pipeline import PolicyGuidedPipeline
from src.evaluation.metrics import get_retrieval_metrics


# Models to compare (short name -> full name from models.yaml)
MODELS_TO_COMPARE = [
    'ms-marco-TinyBERT-L-2-v2',
    'ms-marco-MiniLM-L-6-v2',
    'mxbai-rerank-base-v1',
    'mxbai-rerank-large-v1',
    'bge-reranker-base',
]


class CrossEncoderComparisonExperiment:
    """Compare multiple cross-encoder rerankers"""

    def __init__(self, config_overrides=None):
        self.config = load_config()
        if config_overrides:
            for key, value in config_overrides.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)

        self.path_manager = PathManager()
        self.data_loader = DataLoader(self.path_manager)

    def run(self, dataset: str = 'synthetic'):
        print("=" * 70)
        print("CROSS-ENCODER MODEL COMPARISON")
        print("=" * 70)

        # Load queries (skip those with no relevance gold — see EXPERIMENTS.md)
        queries = [q for q in self.data_loader.load_queries(dataset)
                   if q.get('expected_top_cards')]
        print(f"\nLoaded {len(queries)} queries with relevance gold")

        # Setup vector store
        print("\nSetting up vector store...")
        vector_store = self.setup_vector_store(dataset)

        # Run comparison for each model
        results = {}

        for model_name in MODELS_TO_COMPARE:
            print(f"\n{'='*70}")
            print(f"Testing: {model_name}")
            print("=" * 70)

            # Create reranker with specific model
            full_model_name = self.get_full_model_name(model_name)
            reranker = CrossEncoderReranker(model_name=full_model_name)
            pipeline = PolicyGuidedPipeline(vector_store, reranker, config=self.config)

            # Run on subset of queries for speed
            test_queries = queries[:50]  # Use first 50 for speed

            top5_acc = 0
            avg_pos = 0

            for q in test_queries:
                result = pipeline.retrieve(q['query'])
                metrics = get_retrieval_metrics(result['final_chunks'], q['expected_top_cards'])
                top5_acc += metrics['top_5']
                avg_pos += metrics['position']

            n = len(test_queries)
            top5_acc /= n
            avg_pos /= n

            results[model_name] = {
                'top_5_accuracy': top5_acc,
                'avg_position': avg_pos,
                'num_queries': n
            }

            print(f"  Top-5 Accuracy: {top5_acc*100:.1f}%")
            print(f"  Average Position: {avg_pos:.1f}")

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"\n{'Model':<35} {'Top-5':<12} {'Avg Pos':<12}")
        print("-" * 70)

        sorted_results = sorted(results.items(), key=lambda x: x[1]['avg_position'])
        for model_name, metrics in sorted_results:
            print(f"{model_name:<35} {metrics['top_5_accuracy']*100:.1f}%{'':<6} {metrics['avg_position']:.1f}")

        print("=" * 70)

        # Save results
        run_dir = self.path_manager.get_run_dir("cross_encoder_comparison")
        output_file = run_dir / "results.json"

        import json
        from datetime import datetime

        output = {
            'timestamp': datetime.now().isoformat(),
            'experiment': 'cross_encoder_comparison',
            'results': results
        }

        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"\nResults saved to {output_file}")

    def setup_vector_store(self, dataset: str):
        """Setup vector store with data"""
        cards, guidance, queries = self.data_loader.load_dataset(dataset)

        context_chunks = ChunkPreparer.prepare_context_chunks(cards)
        guidance_chunks = ChunkPreparer.prepare_guidance_chunks(guidance)

        vector_store = PolicyGuidedVectorStore(config=self.config)

        all_chunks = context_chunks + guidance_chunks
        texts, ids, types, metadatas = ChunkPreparer.extract_chunk_data(all_chunks)
        vector_store.add_chunks(texts, ids, types, metadatas)

        print(f"  Vector store ready: {len(context_chunks)} context, {len(guidance_chunks)} guidance")
        return vector_store

    def get_full_model_name(self, short_name: str) -> str:
        """Get full model name from models.yaml"""
        from src.config.config import ModelRegistry
        registry = ModelRegistry()
        full_name = registry.get_reranker_model(short_name)
        return full_name if full_name else short_name


def main():
    experiment = CrossEncoderComparisonExperiment()
    experiment.run()


if __name__ == '__main__':
    main()