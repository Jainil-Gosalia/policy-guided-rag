"""
Synthetic benchmark experiment.

Evaluates four conditions so the guidance mechanism is fully isolated:

    vanilla      embedding similarity only
    rerank_only  cross-encoder rerank on the RAW query (no guidance)
    pg_augment   guidance rule TEXT appended to the query (original mechanism)
    pg_operator  explicit BOOST/DEMOTE/EXCLUDE operator on rerank scores (raw query)

Metrics:
  * ACCURACY on the relevance-labelled subset (guidance-INDEPENDENT gold):
    top-1/top-5/mean position per condition + paired significance tests.
  * CONTROLLABILITY (BOOST): mean rank of policy-preferred cards per condition;
    steering lift of each PG variant vs rerank_only.
  * ENFORCEMENT (EXCLUDE): rate at which excluded cards still appear in the
    top-n per condition (operator should be exactly 0).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.base import BaseExperiment
from src.evaluation.metrics import (
    get_retrieval_metrics as _get_metrics,
    mean_rank_of,
    any_in_top_n,
)
from src.evaluation.stats import paired_comparison, bootstrap_ci_mean


CONDITIONS = ["vanilla", "rerank_only", "pg_augment", "pg_operator"]


class SyntheticTestExperiment(BaseExperiment):
    """Synthetic benchmark: 4 conditions, significance, controllability, enforcement."""

    def __init__(self, config_overrides=None):
        super().__init__("synthetic_test", config_overrides)

    def run(self, dataset: str = 'synthetic'):
        print("=" * 70)
        print("SYNTHETIC DATASET EXPERIMENT (4 conditions)")
        print("=" * 70)

        queries = self.data_loader.load_queries(dataset)
        print(f"\nLoaded {len(queries)} queries")
        print(f"  relevance gold subset:     {sum(1 for q in queries if q.get('expected_top_cards'))}")
        print(f"  policy-preferred subset:   {sum(1 for q in queries if q.get('policy_preferred_cards'))}")
        print(f"  policy-excluded subset:    {sum(1 for q in queries if q.get('policy_excluded_cards'))}")

        print("\nSetting up vector store...")
        vector_store = self.setup_vector_store(dataset)

        print("\nLoading reranker (shared across conditions)...")
        reranker = self.create_reranker()
        systems = {
            "vanilla": self.create_baseline(vector_store),
            "rerank_only": self.create_rerank_only(vector_store, reranker),
            "pg_augment": self.create_pipeline(vector_store, reranker, policy_mode="augment"),
            "pg_operator": self.create_pipeline(vector_store, reranker, policy_mode="operator"),
        }
        print("  Systems ready")

        acc_metrics = {c: [] for c in CONDITIONS}
        steer_rank = {c: [] for c in CONDITIONS}
        steer_hit = {c: [] for c in CONDITIONS}
        excl_hit = {c: [] for c in CONDITIONS}
        difficulties = []
        detailed = []

        print("\nRunning conditions over all queries...")
        total = len(queries)
        top_n = self.config.pipeline.top_n
        for i, q in enumerate(queries):
            query = q['query']
            gold = q.get('expected_top_cards', [])
            preferred = q.get('policy_preferred_cards', [])
            excluded = q.get('policy_excluded_cards', [])

            finals = {c: systems[c].retrieve(query)['final_chunks'] for c in CONDITIONS}

            if gold:
                difficulties.append(q.get('difficulty', 'unknown'))
                row = {'id': q.get('id', i), 'difficulty': q.get('difficulty', 'unknown')}
                for c in CONDITIONS:
                    m = _get_metrics(finals[c], gold)
                    acc_metrics[c].append(m)
                    row[c] = m['position']
                detailed.append(row)

            if preferred:
                for c in CONDITIONS:
                    steer_rank[c].append(mean_rank_of(finals[c], preferred))
                    steer_hit[c].append(any_in_top_n(finals[c], preferred, n=top_n))

            if excluded:
                for c in CONDITIONS:
                    excl_hit[c].append(any_in_top_n(finals[c], excluded, n=top_n))

            if (i + 1) % 25 == 0:
                print(f"  Processed {i + 1}/{total} queries...")

        results = self._summarize(acc_metrics, steer_rank, steer_hit, excl_hit, difficulties, detailed)
        self._print_summary(results)
        self.save_results(results)
        print("=" * 70)
        return results

    def _agg(self, metrics):
        n = len(metrics)
        return {
            'top_1_accuracy': sum(m['top_1'] for m in metrics) / n,
            'top_5_accuracy': sum(m['top_5'] for m in metrics) / n,
            'avg_position': sum(m['position'] for m in metrics) / n,
            'n': n,
        }

    def _summarize(self, acc_metrics, steer_rank, steer_hit, excl_hit, difficulties, detailed):
        accuracy = {c: self._agg(acc_metrics[c]) for c in CONDITIONS}

        significance = {
            'rerank_only_vs_vanilla': paired_comparison(
                acc_metrics['vanilla'], acc_metrics['rerank_only'], 'vanilla', 'rerank_only'),
            'pg_augment_vs_rerank_only': paired_comparison(
                acc_metrics['rerank_only'], acc_metrics['pg_augment'], 'rerank_only', 'pg_augment'),
            'pg_operator_vs_rerank_only': paired_comparison(
                acc_metrics['rerank_only'], acc_metrics['pg_operator'], 'rerank_only', 'pg_operator'),
        }

        by_difficulty = {}
        for d in ['easy', 'medium', 'hard', 'expert']:
            idx = [i for i, dd in enumerate(difficulties) if dd == d]
            if not idx:
                continue
            by_difficulty[d] = {
                'n': len(idx),
                'rerank_only': self._agg([acc_metrics['rerank_only'][i] for i in idx]),
                'pg_operator': self._agg([acc_metrics['pg_operator'][i] for i in idx]),
            }

        def lift_ci(cond):
            deltas = [ro - x for ro, x in zip(steer_rank['rerank_only'], steer_rank[cond])]
            return bootstrap_ci_mean(deltas)

        controllability = {
            'n': len(steer_rank['rerank_only']),
            'mean_rank': {c: (sum(steer_rank[c]) / len(steer_rank[c]) if steer_rank[c] else None)
                          for c in CONDITIONS},
            'topn_hit_rate': {c: (sum(steer_hit[c]) / len(steer_hit[c]) if steer_hit[c] else None)
                              for c in CONDITIONS},
            'steering_lift_vs_rerank_only': {
                'pg_augment': lift_ci('pg_augment'),
                'pg_operator': lift_ci('pg_operator'),
            },
        }

        enforcement = {
            'n': len(excl_hit['vanilla']),
            'excluded_in_topn_rate': {
                c: (sum(excl_hit[c]) / len(excl_hit[c]) if excl_hit[c] else None)
                for c in CONDITIONS
            },
        }

        return {
            'dataset': 'synthetic',
            'accuracy_subset_n': accuracy['vanilla']['n'],
            'accuracy': accuracy,
            'significance': significance,
            'by_difficulty': by_difficulty,
            'controllability': controllability,
            'enforcement': enforcement,
            'detailed': detailed,
        }

    def _print_summary(self, r):
        print("\n" + "=" * 70)
        print(f"ACCURACY (relevance-labelled subset, n={r['accuracy_subset_n']})")
        print("=" * 70)
        print(f"{'Condition':<16}{'Top-1':>10}{'Top-5':>10}{'AvgPos':>10}")
        print("-" * 46)
        for c in CONDITIONS:
            a = r['accuracy'][c]
            print(f"{c:<16}{a['top_1_accuracy']*100:>9.1f}%{a['top_5_accuracy']*100:>9.1f}%{a['avg_position']:>10.1f}")
        print("\nSignificance (paired, B vs A):")
        for key, s in r['significance'].items():
            t5, w = s['top_5_mcnemar'], s['position_wilcoxon']
            wp = w['p_value'] if w['p_value'] is not None else float('nan')
            print(f"  {s['comparison']:<30} top-5 McNemar p={t5['p_value']:.4f}  pos Wilcoxon p={wp:.4f}")

        ctl = r['controllability']
        print("\n" + "=" * 70)
        print(f"CONTROLLABILITY — BOOST steering (policy-preferred subset, n={ctl['n']})")
        print("=" * 70)
        print(f"{'Condition':<16}{'MeanRank':>12}{'Top-n hit':>12}")
        print("-" * 40)
        for c in CONDITIONS:
            print(f"{c:<16}{ctl['mean_rank'][c]:>12.1f}{ctl['topn_hit_rate'][c]*100:>11.1f}%")
        for cond, ci in ctl['steering_lift_vs_rerank_only'].items():
            print(f"  steering lift {cond} vs rerank_only: {ci['mean']:+.2f} "
                  f"95% CI [{ci['ci_low']:+.2f}, {ci['ci_high']:+.2f}]")

        enf = r['enforcement']
        print("\n" + "=" * 70)
        print(f"ENFORCEMENT — EXCLUDE (policy-excluded subset, n={enf['n']})")
        print("=" * 70)
        print(f"{'Condition':<16}{'Excluded-in-top-n rate':>26}")
        print("-" * 42)
        for c in CONDITIONS:
            rate = enf['excluded_in_topn_rate'][c]
            print(f"{c:<16}{rate*100:>25.1f}%")
        print("(operator should be exactly 0% — hard removal)")


def main():
    SyntheticTestExperiment().run()


if __name__ == '__main__':
    main()
