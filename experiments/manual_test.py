"""
Manual benchmark experiment.

Uses the hand-verified manual dataset (queries + gold loaded from
``data/manual/queries.json`` — NOT hard-coded in this file). Evaluates the same
three conditions as the synthetic experiment so the guidance effect is isolated
from the reranker effect:

    vanilla      embedding similarity only
    rerank_only  embedding -> cross-encoder rerank on the RAW query
    policy_guided embedding -> cross-encoder rerank on the GUIDANCE-augmented query

Reports per-condition top-1/top-5 accuracy and mean target position, plus paired
significance tests (PG vs rerank_only is the key contrast). The manual guidance
rules are free-text (no structured target_cards), so the controllability metric
is reported on the synthetic set only.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.base import BaseExperiment
from src.evaluation.metrics import get_retrieval_metrics as _get_metrics
from src.evaluation.stats import paired_comparison


CONDITIONS = ["vanilla", "rerank_only", "policy_guided"]


class ManualTestExperiment(BaseExperiment):
    """Manual hand-verified benchmark across 3 conditions."""

    def __init__(self, config_overrides=None):
        super().__init__("manual_test", config_overrides)

    def run(self, dataset: str = 'manual'):
        print("=" * 70)
        print("MANUAL TEST EXPERIMENT (3 conditions)")
        print("=" * 70)

        queries = self.data_loader.load_queries(dataset)
        queries = [q for q in queries if q.get('expected_top_cards')]
        print(f"\nLoaded {len(queries)} hand-verified queries with gold labels")

        print("\nSetting up vector store...")
        vector_store = self.setup_vector_store(dataset)

        print("\nLoading reranker (shared across conditions)...")
        reranker = self.create_reranker()
        # Manual guidance is free-text (no structured action/target_cards), so the
        # applicable mechanism here is query augmentation. The structured operator
        # is evaluated on the synthetic set, which carries BOOST/DEMOTE/EXCLUDE.
        systems = {
            "vanilla": self.create_baseline(vector_store),
            "rerank_only": self.create_rerank_only(vector_store, reranker),
            "policy_guided": self.create_pipeline(vector_store, reranker, policy_mode="augment"),
        }
        print("  Systems ready")

        acc_metrics = {c: [] for c in CONDITIONS}
        detailed = []

        print("\nRunning conditions...\n")
        for q in queries:
            query = q['query']
            gold = q['expected_top_cards']
            row = {'id': q.get('id'), 'query': query[:50], 'gold': gold}
            for c in CONDITIONS:
                finals = systems[c].retrieve(query)['final_chunks']
                m = _get_metrics(finals, gold)
                acc_metrics[c].append(m)
                row[c] = {'top_1': m['top_1'], 'top_5': m['top_5'], 'position': m['position']}
            detailed.append(row)
            print(f"  {q.get('id'):<5} {query[:40]:<42} "
                  f"V/RO/PG pos = {row['vanilla']['position']}/"
                  f"{row['rerank_only']['position']}/{row['policy_guided']['position']}")

        results = self._summarize(acc_metrics, detailed)
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

    def _summarize(self, acc_metrics, detailed):
        accuracy = {c: self._agg(acc_metrics[c]) for c in CONDITIONS}
        significance = {
            'rerank_only_vs_vanilla': paired_comparison(
                acc_metrics['vanilla'], acc_metrics['rerank_only'], 'vanilla', 'rerank_only'),
            'policy_guided_vs_vanilla': paired_comparison(
                acc_metrics['vanilla'], acc_metrics['policy_guided'], 'vanilla', 'policy_guided'),
            'policy_guided_vs_rerank_only': paired_comparison(
                acc_metrics['rerank_only'], acc_metrics['policy_guided'], 'rerank_only', 'policy_guided'),
        }
        return {
            'dataset': 'manual',
            'num_queries': accuracy['vanilla']['n'],
            'accuracy': accuracy,
            'significance': significance,
            'detailed': detailed,
        }

    def _print_summary(self, r):
        print("\n" + "=" * 70)
        print(f"ACCURACY (n={r['num_queries']})")
        print("=" * 70)
        print(f"{'Condition':<16}{'Top-1':>10}{'Top-5':>10}{'AvgPos':>10}")
        print("-" * 46)
        for c in CONDITIONS:
            a = r['accuracy'][c]
            print(f"{c:<16}{a['top_1_accuracy']*100:>9.1f}%{a['top_5_accuracy']*100:>9.1f}%{a['avg_position']:>10.1f}")
        print("\nSignificance (paired):")
        for key, s in r['significance'].items():
            t5 = s['top_5_mcnemar']
            w = s['position_wilcoxon']
            wp = w['p_value'] if w['p_value'] is not None else float('nan')
            print(f"  {s['comparison']:<32} top-5 McNemar p={t5['p_value']:.4f}  pos Wilcoxon p={wp:.4f}")


def main():
    ManualTestExperiment().run()


if __name__ == '__main__':
    main()
