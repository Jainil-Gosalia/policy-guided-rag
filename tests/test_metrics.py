"""Unit tests for the retrieval metrics (pure logic, no model downloads)."""


def _chunk(card_id):
    return {"metadata": {"card_id": card_id, "chunk_type": "context"}}


def test_top_1_and_position(metrics):
    retrieved = [_chunk("card_1"), _chunk("card_2"), _chunk("card_3")]
    m = metrics.get_retrieval_metrics(retrieved, ["card_1"])
    assert m["top_1"] is True
    assert m["top_5"] is True
    assert m["position"] == 1


def test_position_when_not_first(metrics):
    retrieved = [_chunk("card_9"), _chunk("card_2"), _chunk("card_1")]
    m = metrics.get_retrieval_metrics(retrieved, ["card_1"])
    assert m["top_1"] is False
    assert m["top_5"] is True
    assert m["position"] == 3


def test_missing_target_uses_sentinel(metrics):
    retrieved = [_chunk("card_9"), _chunk("card_8")]
    m = metrics.get_retrieval_metrics(retrieved, ["card_1"])
    assert m["top_5"] is False
    assert m["position"] == 99


def test_best_of_multiple_expected(metrics):
    retrieved = [_chunk("card_5"), _chunk("card_3")]
    m = metrics.get_retrieval_metrics(retrieved, ["card_3", "card_5"])
    # best (lowest) position among expected cards is used
    assert m["position"] == 1
    assert m["top_1"] is True


def test_aggregate_accuracy(metrics):
    mlist = [
        {"top_1": True, "top_5": True, "position": 1},
        {"top_1": False, "top_5": True, "position": 3},
        {"top_1": False, "top_5": False, "position": 99},
    ]
    assert metrics.top_1_accuracy(mlist) == 1 / 3
    assert metrics.top_k_accuracy(mlist, 5) == 2 / 3


def test_improvement_rate(metrics):
    pg = [{"position": 1}, {"position": 5}, {"position": 99}]
    vanilla = [{"position": 3}, {"position": 5}, {"position": 2}]
    # query 0 improved (1<3), query 1 same, query 2 worse -> 1/3
    assert metrics.improvement_rate(pg, vanilla) == 1 / 3
