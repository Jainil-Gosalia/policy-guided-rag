"""
Attribute-predicate engine for governance policies.

Policies reference item ATTRIBUTES (e.g. classification, status, jurisdiction) rather
than item IDs, so a single rule covers any matching item and stays correct as the corpus
changes. A policy has:

    {
      "id": "...", "source": "...", "rule": "<human text from the schedule>",
      "action": "BOOST" | "DEMOTE" | "EXCLUDE",
      "tier":   "hard" | "soft",
      "weight": <float, soft only>,
      "trigger":   {"keywords": [...]},        # when the rule applies (query-side)
      "predicate": <predicate over item attrs> # which items it targets
    }

Predicate grammar (recursive):
    {"all": [pred, ...]} | {"any": [pred, ...]} | {"not": pred}
    leaf: {"field": <str>, "op": <op>, "value": <any>}
    ops: eq, ne, in, nin, gt, gte, lt, lte, has (membership in a list field), contains
         (case-insensitive substring of a string field), exists
"""
from typing import Dict, List, Any


def _leaf(cond: Dict, attrs: Dict) -> bool:
    field, op, val = cond["field"], cond["op"], cond.get("value")
    actual = attrs.get(field)
    if op == "eq":
        return actual == val
    if op == "ne":
        return actual != val
    if op == "in":
        return actual in (val or [])
    if op == "nin":
        return actual not in (val or [])
    if op in ("gt", "gte", "lt", "lte"):
        if actual is None:
            return False
        try:
            a, v = float(actual), float(val)
        except (TypeError, ValueError):
            return False
        return {"gt": a > v, "gte": a >= v, "lt": a < v, "lte": a <= v}[op]
    if op == "has":
        return isinstance(actual, (list, tuple, set)) and val in actual
    if op == "contains":
        return isinstance(actual, str) and isinstance(val, str) and val.lower() in actual.lower()
    if op == "exists":
        return (field in attrs) == bool(val)
    raise ValueError(f"unknown predicate op: {op}")


def eval_predicate(pred: Any, attrs: Dict) -> bool:
    """Evaluate a predicate against an item's attribute dict."""
    if pred is None:
        return True
    if "all" in pred:
        return all(eval_predicate(p, attrs) for p in pred["all"])
    if "any" in pred:
        return any(eval_predicate(p, attrs) for p in pred["any"])
    if "not" in pred:
        return not eval_predicate(pred["not"], attrs)
    return _leaf(pred, attrs)


def trigger_matches(trigger: Dict, query: str) -> bool:
    """Whether a rule's trigger applies to the query. Empty trigger => always applies."""
    if not trigger:
        return True
    kws = trigger.get("keywords", [])
    if not kws:
        return True
    q = query.lower()
    return any(kw.lower() in q for kw in kws)


def resolve_targets(predicate: Any, items: Dict[str, Dict]) -> List[str]:
    """Item ids whose attributes satisfy the predicate."""
    return [iid for iid, attrs in items.items() if eval_predicate(predicate, attrs)]


def applicable_policies(policy_set: List[Dict], query: str) -> List[Dict]:
    """Policies whose trigger matches the query."""
    return [p for p in policy_set if trigger_matches(p.get("trigger"), query)]
