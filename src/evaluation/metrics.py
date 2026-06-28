"""
Evaluation metrics for Policy-Guided RAG
"""
from typing import List, Dict


def get_retrieval_metrics(retrieved: List[Dict], expected_cards: List[str]) -> Dict:
    """Get multiple metrics for a single retrieval result

    Args:
        retrieved: List of retrieved chunk dicts
        expected_cards: List of expected card IDs

    Returns:
        Dict with top_1, top_5, position, positions
    """
    positions = []
    for expected in expected_cards:
        position = 99  # Not in top-5
        for i, chunk in enumerate(retrieved):
            if chunk['metadata'].get('card_id') == expected:
                position = i + 1
                break
        positions.append(position)

    # Use best position (lowest number)
    best_pos = min(positions)

    return {
        'top_1': best_pos == 1,
        'top_5': best_pos <= 5,
        'position': best_pos,
        'positions': positions  # All expected card positions
    }


def mean_rank_of(retrieved: List[Dict], card_ids: List[str], miss: int = 99) -> float:
    """Mean 1-based rank of a set of target cards within a retrieved list.

    Cards absent from the list are assigned ``miss``. Used by the
    controllability metric to measure how high a system ranks the
    policy-preferred cards.

    Args:
        retrieved: ordered list of retrieved chunk dicts
        card_ids: target card IDs whose ranks to average
        miss: rank assigned to a target card that is not retrieved

    Returns:
        Mean rank (lower is better), or ``miss`` if ``card_ids`` is empty.
    """
    if not card_ids:
        return float(miss)

    rank_by_card = {}
    for i, chunk in enumerate(retrieved):
        cid = chunk['metadata'].get('card_id')
        if cid is not None and cid not in rank_by_card:
            rank_by_card[cid] = i + 1

    ranks = [rank_by_card.get(cid, miss) for cid in card_ids]
    return sum(ranks) / len(ranks)


def any_in_top_n(retrieved: List[Dict], card_ids: List[str], n: int = 5) -> bool:
    """Whether any target card appears in the top-n retrieved chunks."""
    top = retrieved[:n]
    present = {c['metadata'].get('card_id') for c in top}
    return any(cid in present for cid in card_ids)


def top_1_accuracy(metrics_list: List[Dict]) -> float:
    """Calculate top-1 accuracy from a list of metric dicts

    Args:
        metrics_list: List of dicts with 'top_1' key

    Returns:
        Fraction of queries where top-1 is correct
    """
    if not metrics_list:
        return 0.0
    return sum(m['top_1'] for m in metrics_list) / len(metrics_list)


def top_k_accuracy(metrics_list: List[Dict], k: int = 5) -> float:
    """Calculate top-k accuracy from a list of metric dicts

    Args:
        metrics_list: List of dicts with 'top_k' key (e.g., 'top_5')
        k: The k value to check

    Returns:
        Fraction of queries where expected is in top-k
    """
    if not metrics_list:
        return 0.0
    key = f'top_{k}'
    return sum(m.get(key, False) for m in metrics_list) / len(metrics_list)


def average_position(metrics_list: List[Dict]) -> float:
    """Calculate average position from a list of metric dicts

    Args:
        metrics_list: List of dicts with 'position' key

    Returns:
        Average position across all queries
    """
    if not metrics_list:
        return 0.0
    return sum(m['position'] for m in metrics_list) / len(metrics_list)


def improvement_rate(pg_metrics: List[Dict], vanilla_metrics: List[Dict]) -> float:
    """Calculate the rate of improvement of PG over vanilla

    Args:
        pg_metrics: List of policy-guided metric dicts
        vanilla_metrics: List of vanilla metric dicts

    Returns:
        Fraction of queries where PG improved over vanilla
    """
    if not pg_metrics or len(pg_metrics) != len(vanilla_metrics):
        return 0.0

    improvements = 0
    for pg, vanilla in zip(pg_metrics, vanilla_metrics):
        if pg['position'] < vanilla['position']:
            improvements += 1

    return improvements / len(pg_metrics)


def compute_detailed_metrics(pg_metrics_list: List[Dict], vanilla_metrics_list: List[Dict]) -> Dict:
    """Compute comprehensive metrics comparing PG to Vanilla

    Args:
        pg_metrics_list: List of policy-guided metric dicts
        vanilla_metrics_list: List of vanilla metric dicts

    Returns:
        Dict with all computed metrics
    """
    n = len(pg_metrics_list)

    v_top1 = top_1_accuracy(vanilla_metrics_list)
    v_top5 = top_k_accuracy(vanilla_metrics_list, 5)
    v_avg_pos = average_position(vanilla_metrics_list)

    pg_top1 = top_1_accuracy(pg_metrics_list)
    pg_top5 = top_k_accuracy(pg_metrics_list, 5)
    pg_avg_pos = average_position(pg_metrics_list)

    return {
        'vanilla': {
            'top_1_accuracy': v_top1,
            'top_5_accuracy': v_top5,
            'avg_position': v_avg_pos
        },
        'policy_guided': {
            'top_1_accuracy': pg_top1,
            'top_5_accuracy': pg_top5,
            'avg_position': pg_avg_pos
        },
        'improvement': {
            'top_1_delta': pg_top1 - v_top1,
            'top_5_delta': pg_top5 - v_top5,
            'position_delta': v_avg_pos - pg_avg_pos,
            'queries_improved': improvement_rate(pg_metrics_list, vanilla_metrics_list)
        }
    }