"""
Result comparison utilities for Policy-Guided RAG
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class ResultComparator:
    """Compare results between different runs or configurations"""

    @staticmethod
    def load_result(result_path: Path) -> Dict:
        """Load a result file

        Args:
            result_path: Path to results.json

        Returns:
            Dict with results
        """
        with open(result_path, 'r') as f:
            return json.load(f)

    @staticmethod
    def compare_results(result_a: Dict, result_b: Dict) -> Dict:
        """Compare two result dicts

        Args:
            result_a: First result dict
            result_b: Second result dict

        Returns:
            Dict with comparison metrics
        """
        a_results = result_a.get('results', {})
        b_results = result_b.get('results', {})

        # Get metrics
        a_pg = a_results.get('policy_guided', {})
        b_pg = b_results.get('policy_guided', {})

        a_vanilla = a_results.get('vanilla', {})
        b_vanilla = b_results.get('vanilla', {})

        a_improvement = a_results.get('improvement', {})
        b_improvement = b_results.get('improvement', {})

        comparison = {
            'experiment_a': result_a.get('experiment', 'unknown'),
            'experiment_b': result_b.get('experiment', 'unknown'),
            'timestamp_a': result_a.get('timestamp', 'unknown'),
            'timestamp_b': result_b.get('timestamp', 'unknown'),
            'policy_guided_comparison': {
                'top_1': {
                    'a': a_pg.get('top_1_accuracy', 0),
                    'b': b_pg.get('top_1_accuracy', 0),
                    'delta': b_pg.get('top_1_accuracy', 0) - a_pg.get('top_1_accuracy', 0)
                },
                'top_5': {
                    'a': a_pg.get('top_5_accuracy', 0),
                    'b': b_pg.get('top_5_accuracy', 0),
                    'delta': b_pg.get('top_5_accuracy', 0) - a_pg.get('top_5_accuracy', 0)
                },
                'avg_position': {
                    'a': a_pg.get('avg_position', 0),
                    'b': b_pg.get('avg_position', 0),
                    'delta': a_pg.get('avg_position', 0) - b_pg.get('avg_position', 0)  # Lower is better
                }
            }
        }

        # Add baseline comparison if available
        if a_vanilla and b_vanilla:
            comparison['improvement_comparison'] = {
                'queries_improved': {
                    'a': a_improvement.get('queries_improved', 0),
                    'b': b_improvement.get('queries_improved', 0),
                    'delta': b_improvement.get('queries_improved', 0) - a_improvement.get('queries_improved', 0)
                }
            }

        return comparison

    @staticmethod
    def find_latest_runs(experiment_dir: Path, n: int = 2) -> List[Path]:
        """Find the n most recent run directories

        Args:
            experiment_dir: Path to experiment directory
            n: Number of runs to find

        Returns:
            List of paths to run directories, sorted by modification time
        """
        if not experiment_dir.exists():
            return []

        run_dirs = [d for d in experiment_dir.iterdir() if d.is_dir() and d.name.startswith('run_')]
        run_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        return run_dirs[:n]

    @staticmethod
    def compare_latest_runs(experiment_name: str, results_dir: Optional[Path] = None) -> Dict:
        """Compare the two latest runs of an experiment

        Args:
            experiment_name: Name of the experiment
            results_dir: Optional results directory override

        Returns:
            Comparison dict
        """
        if results_dir is None:
            results_dir = Path.cwd() / "results"

        experiment_dir = results_dir / experiment_name
        latest_runs = ResultComparator.find_latest_runs(experiment_dir, 2)

        if len(latest_runs) < 2:
            return {'error': 'Not enough runs to compare'}

        result_a = ResultComparator.load_result(latest_runs[0] / 'results.json')
        result_b = ResultComparator.load_result(latest_runs[1] / 'results.json')

        return ResultComparator.compare_results(result_a, result_b)