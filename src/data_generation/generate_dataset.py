"""
Synthetic Dataset Generator - CLI Entry Point

Generate synthetic datasets for Policy-Guided RAG evaluation.
"""
import argparse
import json
import os
import sys
from pathlib import Path

from .config import GeneratorConfig
from .card_generator import CardGenerator
from .guidance_generator import GuidanceGenerator
from .query_generator import QueryGenerator
from .validator import DatasetValidator


def generate_dataset(config: GeneratorConfig) -> dict:
    """Generate a complete synthetic dataset"""

    print(f"Generating synthetic dataset: {config.dataset_name}")
    print(f"  - Cards: {config.num_cards}")
    print(f"  - Guidance: {config.num_guidance}")
    print(f"  - Queries: {config.num_queries}")
    print(f"  - Difficulty distribution: {config.difficulty_counts}")
    print()

    # Step 1: Generate cards
    print("Step 1/4: Generating credit cards...")
    card_gen = CardGenerator(num_cards=config.num_cards, random_seed=config.random_seed)
    cards = card_gen.generate()
    print(f"  - Generated {len(cards)} cards")

    # Step 2: Generate guidance
    print("Step 2/4: Generating guidance rules...")
    guidance_gen = GuidanceGenerator(
        num_guidance=config.num_guidance,
        num_cards=config.num_cards,
        random_seed=config.random_seed
    )
    guidance = guidance_gen.generate(cards)
    print(f"  - Generated {len(guidance)} guidance rules")

    # Step 3: Generate queries
    print("Step 3/4: Generating queries with ground truth...")
    query_gen = QueryGenerator(
        num_queries=config.num_queries,
        num_cards=config.num_cards,
        num_guidance=config.num_guidance,
        difficulty_counts=config.difficulty_counts,
        random_seed=config.random_seed
    )
    queries = query_gen.generate(cards, guidance)
    print(f"  - Generated {len(queries)} queries")

    # Step 4: Validate
    print("Step 4/4: Validating dataset...")
    validator = DatasetValidator()
    result = validator.validate(cards, guidance, queries)
    validator.print_report(result)

    return {
        "cards": cards,
        "guidance": guidance,
        "queries": queries
    }


def save_dataset(dataset: dict, output_dir: str, dataset_name: str):
    """Save dataset to JSON files"""

    # Create output directory
    output_path = Path(output_dir) / dataset_name
    output_path.mkdir(parents=True, exist_ok=True)

    # Save each file
    for filename, data in dataset.items():
        filepath = output_path / f"{filename}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved: {filepath}")

    # Create metadata file
    metadata = {
        "dataset_name": dataset_name,
        "num_cards": len(dataset["cards"]),
        "num_guidance": len(dataset["guidance"]),
        "num_queries": len(dataset["queries"]),
        "files": {
            "cards": "cards.json",
            "guidance": "guidance.json",
            "queries": "queries.json"
        }
    }

    metadata_path = output_path / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved: {metadata_path}")


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Generate synthetic datasets for Policy-Guided RAG evaluation"
    )

    # Generation parameters
    parser.add_argument("--num-cards", type=int, default=50,
                        help="Number of credit cards to generate (default: 50)")
    parser.add_argument("--num-guidance", type=int, default=25,
                        help="Number of guidance rules to generate (default: 25)")
    parser.add_argument("--num-queries", type=int, default=150,
                        help="Number of queries to generate (default: 150)")

    # Difficulty distribution
    parser.add_argument("--easy-ratio", type=float, default=0.30,
                        help="Ratio of easy queries (default: 0.30)")
    parser.add_argument("--medium-ratio", type=float, default=0.35,
                        help="Ratio of medium queries (default: 0.35)")
    parser.add_argument("--hard-ratio", type=float, default=0.25,
                        help="Ratio of hard queries (default: 0.25)")
    parser.add_argument("--expert-ratio", type=float, default=0.10,
                        help="Ratio of expert queries (default: 0.10)")

    # Output
    parser.add_argument("--output", type=str, default="data/synthetic",
                        help="Output directory (default: data/synthetic)")
    parser.add_argument("--name", type=str, default="synthetic_v1",
                        help="Dataset name (default: synthetic_v1)")

    # Other options
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")
    parser.add_argument("--validate-only", action="store_true",
                        help="Only validate existing dataset (requires --dataset-path)")
    parser.add_argument("--dataset-path", type=str,
                        help="Path to existing dataset for validation")

    args = parser.parse_args()

    # Validation-only mode
    if args.validate_only:
        if not args.dataset_path:
            parser.error("--dataset-path required when using --validate-only")

        dataset_path = Path(args.dataset_path)
        if not dataset_path.exists():
            print(f"Error: Dataset path does not exist: {dataset_path}")
            sys.exit(1)

        # Load existing dataset
        try:
            with open(dataset_path / "cards.json") as f:
                cards = json.load(f)
            with open(dataset_path / "guidance.json") as f:
                guidance = json.load(f)
            with open(dataset_path / "queries.json") as f:
                queries = json.load(f)
        except FileNotFoundError as e:
            print(f"Error: Missing file in dataset: {e}")
            sys.exit(1)

        # Validate
        validator = DatasetValidator()
        result = validator.validate(cards, guidance, queries)
        validator.print_report(result)
        sys.exit(0 if result.is_valid else 1)

    # Create config
    config = GeneratorConfig(
        num_cards=args.num_cards,
        num_guidance=args.num_guidance,
        num_queries=args.num_queries,
        easy_ratio=args.easy_ratio,
        medium_ratio=args.medium_ratio,
        hard_ratio=args.hard_ratio,
        expert_ratio=args.expert_ratio,
        output_dir=args.output,
        dataset_name=args.name
    )

    # Add random seed to config (as attribute, not field)
    config.random_seed = args.seed

    # Generate dataset
    dataset = generate_dataset(config)

    # Save
    save_dataset(dataset, config.output_dir, config.dataset_name)

    print("\n[OK] Dataset generation complete!")


if __name__ == "__main__":
    main()