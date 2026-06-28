"""
Dataset Validator - Validate generated synthetic datasets
"""
import json
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of dataset validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    stats: Dict


class DatasetValidator:
    """Validate synthetic dataset for completeness and correctness"""

    def validate(self, cards: List[Dict], guidance: List[Dict], queries: List[Dict]) -> ValidationResult:
        """Validate the entire dataset"""
        errors = []
        warnings = []
        stats = {}

        # Validate cards
        card_errors, card_warnings, card_stats = self._validate_cards(cards)
        errors.extend(card_errors)
        warnings.extend(card_warnings)
        stats.update(card_stats)

        # Validate guidance
        guidance_errors, guidance_warnings, guidance_stats = self._validate_guidance(guidance, cards)
        errors.extend(guidance_errors)
        warnings.extend(guidance_warnings)
        stats.update(guidance_stats)

        # Validate queries
        query_errors, query_warnings, query_stats = self._validate_queries(queries, cards, guidance)
        errors.extend(query_errors)
        warnings.extend(query_warnings)
        stats.update(query_stats)

        # Check coverage
        coverage_errors, coverage_warnings = self._check_coverage(cards, guidance, queries)
        errors.extend(coverage_errors)
        warnings.extend(coverage_warnings)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            stats=stats
        )

    def _validate_cards(self, cards: List[Dict]) -> Tuple[List[str], List[str], Dict]:
        """Validate card structure"""
        errors = []
        warnings = []
        stats = {"num_cards": len(cards)}

        required_fields = ["id", "name", "annual_fee", "rewards", "benefits", "credit_score_required", "tags"]
        card_ids = set()

        for i, card in enumerate(cards):
            # Check required fields
            for field in required_fields:
                if field not in card:
                    errors.append(f"Card {i}: missing required field '{field}'")

            # Check ID uniqueness
            card_id = card.get("id", "")
            if card_id in card_ids:
                errors.append(f"Duplicate card ID: {card_id}")
            card_ids.add(card_id)

            # Check field types
            if "annual_fee" in card and not isinstance(card["annual_fee"], (int, float)):
                errors.append(f"Card {card_id}: annual_fee must be number")

            if "rewards" in card and not isinstance(card["rewards"], dict):
                errors.append(f"Card {card_id}: rewards must be dict")

            if "benefits" in card and not isinstance(card["benefits"], list):
                errors.append(f"Card {card_id}: benefits must be list")

            if "tags" in card and not isinstance(card["tags"], list):
                errors.append(f"Card {card_id}: tags must be list")

        # Check tag coverage
        all_tags = set()
        for card in cards:
            all_tags.update(card.get("tags", []))
        stats["unique_tags"] = len(all_tags)
        stats["tags"] = list(all_tags)

        if len(all_tags) < 5:
            warnings.append(f"Only {len(all_tags)} unique tags - may want more diversity")

        return errors, warnings, stats

    def _validate_guidance(self, guidance: List[Dict], cards: List[Dict]) -> Tuple[List[str], List[str], Dict]:
        """Validate guidance structure"""
        errors = []
        warnings = []
        stats = {"num_guidance": len(guidance)}

        required_fields = ["id", "rule", "priority", "category", "applicable_keywords", "target_cards", "action"]
        guidance_ids = set()
        card_ids = {card["id"] for card in cards}

        valid_actions = ["BOOST", "DEMOTE", "EXCLUDE"]
        valid_priorities = ["high", "medium", "low"]

        for i, g in enumerate(guidance):
            # Check required fields
            for field in required_fields:
                if field not in g:
                    errors.append(f"Guidance {i}: missing required field '{field}'")

            # Check ID uniqueness
            g_id = g.get("id", "")
            if g_id in guidance_ids:
                errors.append(f"Duplicate guidance ID: {g_id}")
            guidance_ids.add(g_id)

            # Check action validity
            if g.get("action") not in valid_actions:
                errors.append(f"Guidance {g_id}: invalid action '{g.get('action')}' - must be one of {valid_actions}")

            # Check priority validity
            if g.get("priority") not in valid_priorities:
                errors.append(f"Guidance {g_id}: invalid priority '{g.get('priority')}'")

            # Check target cards exist
            target_cards = g.get("target_cards", [])
            for card_id in target_cards:
                if card_id not in card_ids:
                    warnings.append(f"Guidance {g_id}: target card {card_id} not found in cards")

        stats["unique_categories"] = len(set(g.get("category") for g in guidance))
        stats["action_breakdown"] = self._count_field(guidance, "action")
        stats["priority_breakdown"] = self._count_field(guidance, "priority")

        return errors, warnings, stats

    def _validate_queries(self, queries: List[Dict], cards: List[Dict], guidance: List[Dict]) -> Tuple[List[str], List[str], Dict]:
        """Validate query structure"""
        errors = []
        warnings = []
        stats = {"num_queries": len(queries)}

        required_fields = ["id", "query", "expected_top_cards", "guidance_should_apply", "difficulty", "conflict_level", "vanilla_failure_expected", "notes"]
        query_ids = set()
        card_ids = {card["id"] for card in cards}
        guidance_ids = {g["id"] for g in guidance}
        valid_difficulties = ["easy", "medium", "hard", "expert"]

        for i, q in enumerate(queries):
            # Check required fields
            for field in required_fields:
                if field not in q:
                    errors.append(f"Query {i}: missing required field '{field}'")

            # Check ID uniqueness
            q_id = q.get("id", "")
            if q_id in query_ids:
                errors.append(f"Duplicate query ID: {q_id}")
            query_ids.add(q_id)

            # Check difficulty
            if q.get("difficulty") not in valid_difficulties:
                errors.append(f"Query {q_id}: invalid difficulty '{q.get('difficulty')}'")

            # Check expected cards exist
            for card_id in q.get("expected_top_cards", []):
                if card_id not in card_ids:
                    errors.append(f"Query {q_id}: expected card {card_id} not found in cards")

            # Check guidance exists
            for g_id in q.get("guidance_should_apply", []):
                if g_id not in guidance_ids:
                    warnings.append(f"Query {q_id}: guidance {g_id} not found in guidance")

            # Check boolean field
            if not isinstance(q.get("vanilla_failure_expected"), bool):
                errors.append(f"Query {q_id}: vanilla_failure_expected must be boolean")

            # Check conflict level
            conflict = q.get("conflict_level", 0)
            if not isinstance(conflict, int) or conflict < 0 or conflict > 3:
                errors.append(f"Query {q_id}: conflict_level must be int 0-3")

        stats["difficulty_breakdown"] = self._count_field(queries, "difficulty")
        stats["vanilla_failure_rate"] = sum(q.get("vanilla_failure_expected", False) for q in queries) / len(queries) if queries else 0
        stats["avg_conflict_level"] = sum(q.get("conflict_level", 0) for q in queries) / len(queries) if queries else 0

        return errors, warnings, stats

    def _check_coverage(self, cards: List[Dict], guidance: List[Dict], queries: List[Dict]) -> Tuple[List[str], List[str]]:
        """Check that queries cover all guidance and cards"""
        errors = []
        warnings = []

        # Check that queries reference existing cards
        card_ids = {c["id"] for c in cards}
        guidance_ids = {g["id"] for g in guidance}

        referenced_cards = set()
        referenced_guidance = set()

        for q in queries:
            referenced_cards.update(q.get("expected_top_cards", []))
            referenced_guidance.update(q.get("guidance_should_apply", []))

        # Find unreferenced cards
        unreferenced = card_ids - referenced_cards
        if len(unreferenced) > len(card_ids) * 0.3:
            warnings.append(f"{len(unreferenced)} cards ({len(unreferenced)/len(card_ids)*100:.1f}%) not referenced by any query")

        return errors, warnings

    def _count_field(self, items: List[Dict], field: str) -> Dict[str, int]:
        """Count occurrences of a field value"""
        counts = {}
        for item in items:
            value = item.get(field, "unknown")
            counts[value] = counts.get(value, 0) + 1
        return counts

    def print_report(self, result: ValidationResult):
        """Print validation report"""
        print("\n" + "=" * 60)
        print("DATASET VALIDATION REPORT")
        print("=" * 60)

        if result.is_valid:
            print("\n[PASSED] VALIDATION PASSED")
        else:
            print("\n[FAILED] VALIDATION FAILED")

        # Stats
        print("\n[STATS] STATISTICS:")
        for key, value in result.stats.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    print(f"    - {k}: {v}")
            elif isinstance(value, float):
                print(f"  {key}: {value:.2%}")
            else:
                print(f"  {key}: {value}")

        # Errors
        if result.errors:
            print(f"\n[ERROR] ERRORS ({len(result.errors)}):")
            for error in result.errors[:10]:  # Show first 10
                print(f"  - {error}")
            if len(result.errors) > 10:
                print(f"  ... and {len(result.errors) - 10} more")

        # Warnings
        if result.warnings:
            print(f"\n[WARN] WARNINGS ({len(result.warnings)}):")
            for warning in result.warnings[:10]:
                print(f"  - {warning}")
            if len(result.warnings) > 10:
                print(f"  ... and {len(result.warnings) - 10} more")

        print("=" * 60)


if __name__ == "__main__":
    # Quick test with sample data
    from .card_generator import generate_sample_cards
    from .guidance_generator import generate_sample_guidance
    from .query_generator import generate_sample_queries

    cards = generate_sample_cards(15)
    guidance = generate_sample_guidance(15, 8)
    queries = generate_sample_queries(15, 8, 12)

    validator = DatasetValidator()
    result = validator.validate(cards, guidance, queries)
    validator.print_report(result)