"""
Generator Configuration
"""
from dataclasses import dataclass, field


@dataclass
class GeneratorConfig:
    """Configuration for synthetic dataset generation"""

    # Number of items to generate
    num_cards: int = 50
    num_guidance: int = 25
    num_queries: int = 150

    # Difficulty distribution ratios (must sum to 1.0)
    easy_ratio: float = 0.30
    medium_ratio: float = 0.35
    hard_ratio: float = 0.25
    expert_ratio: float = 0.10

    # Target percentage of queries that should fail vanilla RAG
    vanilla_failure_target: float = 0.30

    # Output directory
    output_dir: str = "data/synthetic"

    # Dataset name
    dataset_name: str = "synthetic_v1"

    def __post_init__(self):
        """Validate configuration"""
        total = self.easy_ratio + self.medium_ratio + self.hard_ratio + self.expert_ratio
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Difficulty ratios must sum to 1.0, got {total}")

    @property
    def difficulty_counts(self) -> dict:
        """Calculate number of queries per difficulty level"""
        # Use int() but adjust to ensure exact count
        counts = {
            "easy": int(self.num_queries * self.easy_ratio),
            "medium": int(self.num_queries * self.medium_ratio),
            "hard": int(self.num_queries * self.hard_ratio),
            "expert": int(self.num_queries * self.expert_ratio),
        }

        # Adjust to match exact num_queries
        current_total = sum(counts.values())
        diff = self.num_queries - current_total

        # Add remainder to medium (largest category)
        if diff != 0:
            counts["medium"] += diff

        return counts