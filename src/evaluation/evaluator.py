"""
Evaluation orchestration for Policy-Guided RAG
"""
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from .metrics import get_retrieval_metrics, compute_detailed_metrics
from ..config.paths import PathManager


class Evaluator:
    """Orchestrates evaluation of retrieval results"""

    def __init__(self, path_manager: Optional[PathManager] = None):
        self.path_manager = path_manager or PathManager()

    def evaluate_query(self, query_result: Dict, expected_cards: List[str]) -> Dict:
        """Evaluate a single query result

        Args:
            query_result: Dict with 'final_chunks' key
            expected_cards: List of expected card IDs

        Returns:
            Dict with metrics
        """
        return get_retrieval_metrics(query_result['final_chunks'], expected_cards)

    def evaluate_batch(self,
                       queries: List[Dict],
                       pipeline_result_fn,
                       baseline_result_fn=None) -> Dict:
        """Evaluate a batch of queries

        Args:
            queries: List of query dicts with 'query' and optionally 'expected_top_cards'
            pipeline_result_fn: Function that takes a query and returns result
            baseline_result_fn: Optional baseline function for comparison

        Returns:
            Dict with aggregated metrics and detailed results
        """
        detailed_results = []
        pg_metrics_list = []
        vanilla_metrics_list = []

        for q in queries:
            query_text = q['query']
            expected = q.get('expected_top_cards', [])

            # Run policy-guided pipeline
            pg_result = pipeline_result_fn(query_text)
            pg_metrics = self.evaluate_query(pg_result, expected)
            pg_metrics_list.append(pg_metrics)

            # Optionally run baseline
            if baseline_result_fn:
                vanilla_result = baseline_result_fn(query_text)
                vanilla_metrics = self.evaluate_query(vanilla_result, expected)
                vanilla_metrics_list.append(vanilla_metrics)

                # Determine improvement
                if pg_metrics['position'] < vanilla_metrics['position']:
                    improvement = "IMPROVED"
                elif pg_metrics['position'] > vanilla_metrics['position']:
                    improvement = "WORSE"
                else:
                    improvement = "SAME"
            else:
                improvement = "N/A"

            detailed_results.append({
                'query': query_text[:50],
                'expected': expected,
                'pg': pg_metrics,
                'improvement': improvement
            })

        # Compute aggregated metrics
        result = {
            'num_queries': len(queries),
            'policy_guided': {
                'top_1_accuracy': sum(m['top_1'] for m in pg_metrics_list) / len(pg_metrics_list),
                'top_5_accuracy': sum(m['top_5'] for m in pg_metrics_list) / len(pg_metrics_list),
                'avg_position': sum(m['position'] for m in pg_metrics_list) / len(pg_metrics_list)
            },
            'detailed': detailed_results
        }

        # Add baseline comparison if available
        if vanilla_metrics_list:
            comparison = compute_detailed_metrics(pg_metrics_list, vanilla_metrics_list)
            result['vanilla'] = comparison['vanilla']
            result['improvement'] = comparison['improvement']

        return result

    def save_results(self,
                     results: Dict,
                     experiment_name: str,
                     config_snapshot: Optional[Dict] = None) -> Path:
        """Save results to file

        Args:
            results: Results dict to save
            experiment_name: Name of the experiment
            config_snapshot: Optional config snapshot to include

        Returns:
            Path to saved file
        """
        run_dir = self.path_manager.get_run_dir(experiment_name)

        # Add metadata
        output = {
            'timestamp': datetime.now().isoformat(),
            'experiment': experiment_name,
            'results': results
        }

        if config_snapshot:
            output['config'] = config_snapshot

        output_file = run_dir / 'results.json'
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)

        return output_file