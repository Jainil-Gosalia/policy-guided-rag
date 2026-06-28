#!/usr/bin/env python
"""
Unified CLI for running experiments with config overrides
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.config import load_config


def _build_overrides(args):
    """Collect CLI overrides into a single nested config dict."""
    overrides = {}
    pipeline = {}
    if getattr(args, 'k_context', None):
        pipeline['k_context'] = args.k_context
    if getattr(args, 'k_guidance', None):
        pipeline['k_guidance'] = args.k_guidance
    if getattr(args, 'top_n', None):
        pipeline['top_n'] = args.top_n
    if getattr(args, 'policy_mode', None):
        pipeline['policy_mode'] = args.policy_mode
    if getattr(args, 'policy_weight', None) is not None:
        pipeline['policy_weight'] = args.policy_weight
    if pipeline:
        overrides['pipeline'] = pipeline
    if getattr(args, 'reranker', None):
        overrides['reranker'] = {'default': args.reranker}
    return overrides or None


def run_manual_test(args):
    """Run manual test experiment"""
    from experiments.manual_test import ManualTestExperiment
    experiment = ManualTestExperiment(_build_overrides(args))
    experiment.run(dataset=args.dataset)


def run_synthetic_test(args):
    """Run synthetic test experiment"""
    from experiments.synthetic_test import SyntheticTestExperiment
    experiment = SyntheticTestExperiment(_build_overrides(args))
    # Default to 'synthetic' dataset for this experiment
    dataset = args.dataset if args.dataset != 'manual' else 'synthetic'
    experiment.run(dataset=dataset)


def run_cross_encoder_comparison(args):
    """Run cross-encoder comparison experiment"""
    from experiments.cross_encoder_comparison import CrossEncoderComparisonExperiment
    experiment = CrossEncoderComparisonExperiment(_build_overrides(args))
    experiment.run(dataset=args.dataset)


def list_experiments(args):
    """List available experiments"""
    print("Available experiments:")
    print("  manual_test                  - Run manual test with 15 queries")
    print("  synthetic_test               - Run synthetic test with 150 queries")
    print("  cross_encoder_comparison     - Compare multiple reranker models")
    print("\nOptions:")
    print("  --reranker MODEL             - Override reranker model")
    print("  --k_context N                - Override context retrieval count")
    print("  --k_guidance N               - Override guidance retrieval count")
    print("  --top_n N                    - Override final results count")
    print("  --dataset NAME               - Dataset to use (default: manual/synthetic)")


def main():
    parser = argparse.ArgumentParser(
        description="Run Policy-Guided RAG experiments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_experiment.py manual_test
  python scripts/run_experiment.py synthetic_test --dataset synthetic
  python scripts/run_experiment.py manual_test --reranker mxbai-rerank-base-v1
  python scripts/run_experiment.py cross_encoder_comparison
        """
    )

    parser.add_argument(
        'experiment',
        nargs='?',
        default='list',
        help='Experiment to run (default: list available experiments)'
    )

    parser.add_argument('--reranker', type=str, help='Override reranker model')
    parser.add_argument('--k-context', type=int, dest='k_context', help='Context retrieval count')
    parser.add_argument('--k-guidance', type=int, dest='k_guidance', help='Guidance retrieval count')
    parser.add_argument('--top-n', type=int, dest='top_n', help='Final results count')
    parser.add_argument('--policy-mode', type=str, dest='policy_mode',
                        choices=['augment', 'operator', 'both', 'none'],
                        help='Guidance mechanism (default from config)')
    parser.add_argument('--policy-weight', type=float, dest='policy_weight',
                        help='BOOST/DEMOTE magnitude for the operator')
    parser.add_argument('--dataset', type=str, default='manual', help='Dataset to use')

    args = parser.parse_args()

    # Route to appropriate experiment
    if args.experiment == 'manual_test':
        run_manual_test(args)
    elif args.experiment == 'synthetic_test':
        run_synthetic_test(args)
    elif args.experiment == 'cross_encoder_comparison':
        run_cross_encoder_comparison(args)
    elif args.experiment == 'list':
        list_experiments(args)
    else:
        print(f"Unknown experiment: {args.experiment}")
        print("Run without arguments to see available experiments")
        sys.exit(1)


if __name__ == '__main__':
    main()