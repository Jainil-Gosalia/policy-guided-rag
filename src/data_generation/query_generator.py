"""
Query Generator - Generate queries with ground truth and difficulty levels
"""
import random
from typing import List, Dict, Tuple
from dataclasses import dataclass


# Query templates per category/difficulty
QUERY_TEMPLATES = {
    "easy": {
        # Direct keyword matches - guidance triggers cleanly
        "business": [
            "I need a credit card for my startup business expenses",
            "Looking for a business card for my company",
            "What's a good card for entrepreneur expenses?",
            "I need a card for my small business",
            "Business credit card for company expenses",
            "Recommend a card for my startup",
            "Card for business travel and expenses",
            "Looking for a corporate credit card",
            "Need a card for business purchases",
            "Best business rewards card",
            "Card for LLC expenses",
            "Professional card for self-employed",
        ],
        "student": [
            "I'm a college student looking for my first card",
            "What's a good credit card for a student?",
            "I just started college, need a credit card",
            "Student credit card recommendation",
            "First credit card for a college student",
            "Best card for university student",
            "Need a card as a college freshman",
            "Card for graduate student",
            "Student who wants to build credit",
            "Young adult starting credit",
        ],
        "no_fee": [
            "I don't want to pay any annual fee",
            "Looking for a card with no annual fee",
            "What's the best no-fee credit card?",
            "I want a free credit card",
            "Find me a card with zero annual fee",
            "Recommend a card with no fees",
            "Best annual fee free card",
            "No yearly fee card options",
            "Zero annual cost credit card",
            "Card with no membership fee",
        ],
        "travel": [
            "I travel frequently, recommend a good card",
            "What's the best travel rewards card?",
            "I need a card for my vacations",
            "Looking for airline miles rewards",
            "Best card for frequent flyers",
            "Travel credit card with miles",
            "Card for airline rewards",
            "Best travel points card",
            "Vacation rewards credit card",
            "Frequent traveler card",
        ],
        "lounge": [
            "I want airport lounge access",
            "Which card gives me Priority Pass?",
            "Looking for a card with lounge benefits",
            "Need airport lounge access when I travel",
            "Card with free airport lounge visits",
            "Credit card with airport club access",
            "Lounge access credit card",
            "Free airport lounge membership card",
            "Card that gets me into airport lounges",
            "Premium lounge access credit card",
        ],
        "gas": [
            "What's the best card for gas stations?",
            "I drive a lot, need rewards on gas",
            "Card for commuting and gas purchases",
            "Best card for gas and transit",
            "Rewards for gas station purchases",
            "Gas station rewards credit card",
            "Card for fuel purchases",
            "Best card for drivers",
            "Cashback on gas purchases",
            "Gas rewards card",
        ],
        "cashback": [
            "I want maximum cashback on my purchases",
            "Best cashback credit card?",
            "Which card gives me the most cash back?",
            "I want to earn cash on my spending",
            "Highest cashback rate card",
            "Card that gives me money back",
            "Earn cash on every purchase",
            "Simple cash rewards card",
            "Best flat-rate cashback card",
            "Double cash back credit card",
        ],
        "shopping": [
            "Best card for Amazon purchases",
            "I shop a lot at Amazon, which card?",
            "Card for online shopping rewards",
            "What's good for retail shopping?",
            "Best card for store purchases",
            "Retail store credit card",
            "Card for shopping at department stores",
            "Best card for Target and Walmart",
            "Co-branded store card",
            "Card for frequent shoppers",
        ],
        "crypto": [
            "I want to earn crypto rewards",
            "Which card gives bitcoin rewards?",
            "Looking for a crypto credit card",
            "Card that pays in cryptocurrency",
            "Bitcoin rewards credit card",
            "Ethereum rewards card",
            "Card that converts rewards to crypto",
            "Crypto back on purchases",
            "Digital currency rewards card",
            "Blockchain-based rewards",
        ],
        "good_credit": [
            "I have excellent credit, what's the best card?",
            "750+ credit score, recommend a premium card",
            "Top-tier credit, what cards can I get?",
            "Excellent credit card recommendations",
            "Best cards for someone with 800 credit score",
            "High credit score rewards card",
            "Premium card with great benefits",
            "Credit score over 780, what can I get?",
            "Card for excellent credit history",
            "Best rewards for high credit score",
        ],
        "poor_credit": [
            "I have bad credit, what's available?",
            "Need a card to build my credit",
            "What's the easiest card to get with poor credit?",
            "Secured card for bad credit",
            "First card with no credit history",
            "Easy approval credit card",
            "Card for rebuilding credit",
            "No credit check card",
            "Beginner credit card options",
            "Card for low credit score",
        ],
        "international": [
            "I'll be traveling to Europe soon",
            "Card for international travel no foreign fees",
            "Best card to use abroad",
            "No foreign transaction fee card",
            "Card for overseas travel",
            "Travel outside US credit card",
            "No foreign transaction fees",
            "International friendly credit card",
            "Credit card for foreign travel",
            "Best card for international purchases",
        ],
    },
    "medium": {
        # Implicit needs requiring guidance adjustment
        "business": [
            "I run my own company and need to track expenses",
            "Something for managing business costs",
            "Card that helps with business accounting",
            "Need to separate personal and business spending",
            "Expense tracking for my side hustle",
            "Track business spending with credit card",
            "Need expense reports for my company",
            "Business spending management",
            "Corporate card for expenses",
            "Separate business from personal",
        ],
        "student": [
            "I'm a freshman in college, never had a card before",
            "Building credit for the first time",
            "Just turned 18, what's my options?",
            "Need to establish credit history",
            "First time using credit, very nervous",
            "New to credit, need guidance",
            "Young person getting first credit card",
            "First time applicant, what are my options?",
            "Just became adult, need credit card",
            "Getting started with credit",
        ],
        "no_fee": [
            "I don't want to waste money on fees",
            "Keep it simple, no extra costs",
            "What's the most economical card?",
            "Just started working, need something basic",
            "Don't want to pay for privileges I won't use",
            "Minimize credit card costs",
            "Looking for budget-friendly card",
            "Cheapest credit card option",
            "Lowest cost credit card",
            "Save money on credit card fees",
        ],
        "travel": [
            "Going on vacation, want to save on flights",
            "Travel abroad next month",
            "Want to make my trips more affordable",
            "Frequent business trips, need travel benefits",
            "Planning a honeymoon, need travel rewards",
        ],
        "premium": [
            "I want the best rewards possible",
            "What's the most prestigious card?",
            "Don't mind paying for premium benefits",
            "Want luxury travel perks",
            "Looking for top-tier benefits",
        ],
        "dining": [
            "I eat out frequently at restaurants",
            "Lots of dinners with clients",
            "Foodie looking for dining rewards",
            "Eat at restaurants often",
            "Restaurants and food delivery",
        ],
        "grocery": [
            "I do most of my shopping at grocery stores",
            "Shop at supermarket every week",
            "Family of 4, lots of grocery shopping",
            "Weekly grocery trips",
            "Big household, lots of food purchases",
        ],
    },
    "hard": {
        # Conflicting constraints, multiple guidance rules
        "business": [
            "I need a business card but don't want annual fees",
            "Startup founder, excellent credit, want premium without high fees",
            "Business travel benefits but also need cashback",
            "Company expenses but also personal groceries on same card",
            "Business card for startup with no personal guarantee",
            "Need business rewards but on a budget",
            "Small business owner seeking premium without high cost",
            "Business card for side hustle with no fees",
            "Startup with no revenue, need free business card",
            "Freelancer wants business card with cashback",
        ],
        "student": [
            "College student with good income, want premium rewards",
            "Student but parents said must have no fees",
            "Building credit but also want travel rewards",
            "Freshman with part-time job, need to earn rewards",
            "Grad student needing business features on student card",
            "Student who wants premium travel card",
            "College senior with good income seeking premium",
            "Student need business features but has no credit",
            "Graduate student wants premium rewards card",
            "Undergraduate needs business card for internship",
        ],
        "no_fee": [
            "No fee but want premium travel benefits",
            "Zero annual fee with lounge access",
            "Don't want to pay but need travel insurance",
            "Free card but want the best rewards",
            "No annual fee but high rewards rate",
            "Zero fee card with premium benefits",
            "Budget card with luxury perks",
            "No cost card with travel credits",
            "Free card but airport lounge access",
            "No-fee card with concierge service",
            "No fee but with high rewards rate",
        ],
        "travel": [
            "Travel often but have poor credit",
            "International travel with no credit history",
            "Lounge access but don't want high annual fee",
            "Travel rewards with no foreign transaction fees",
            "Best travel card for someone who can't get premium",
        ],
    },
    "expert": {
        # Semantic conflict with policy
        "give_me_free_money": [
            "I want a card that gives me free money",
            "What's the card that pays me the most?",
            "I just want something for nothing",
            "Maximum value with zero effort",
            "Get paid to use credit card",
            "Card that gives me free stuff",
            "Earn rewards without doing anything",
            "Free credit card benefits",
        ],
        "popular": [
            "What's your most popular card?",
            "Which card do most customers choose?",
            "What card should I get?",
            "What do you recommend?",
            "Give me your best card",
            "What's the best card overall?",
            "One card to rule them all",
            "Your top recommended card",
            "Most recommended credit card",
        ],
        "simple": [
            "I want something simple with no hassle",
            "Don't complicate my life",
            "Keep it easy, I don't want to think about it",
            "What's the easiest card to use?",
            "I just want basic functionality",
            "Don't want to track categories",
            "Just give me a straightforward card",
            "Simple no brainer card",
            "One card for everything",
        ],
        "conflicting": [
            "I want premium benefits but no annual fee and bad credit",
            "Maximum cashback with travel rewards and no fees",
            "Best of everything - travel, dining, gas, groceries",
            "I have very poor credit but want the best rewards",
            "No credit history but want premium card benefits",
            "Maximum rewards but won't pay annual fee",
            "Premium travel card but have bad credit",
            "Best business card but I'm a student",
            "Zero fee but maximum perks",
            "Cashback and travel rewards in one card",
        ],
    }
}

# Vanilla failure scenarios - what vanilla RAG would return vs what guidance should provide
VANILLA_FAILURE_SCENARIOS = [
    {
        "query_pattern": "no fee",
        "vanilla_likely": ["premium cards (better rewards descriptions)"],
        "guidance_should": ["no-fee cards"],
        "reason": "Vanilla RAG ranks by reward description richness, not fee sensitivity"
    },
    {
        "query_pattern": "student",
        "vanilla_likely": ["premium cards (better benefits)"],
        "guidance_should": ["student cards"],
        "reason": "Semantic match for 'student' might not trigger properly"
    },
    {
        "query_pattern": "business",
        "vanilla_likely": ["general cards"],
        "guidance_should": ["business cards"],
        "reason": "Vanilla might miss business context"
    },
    {
        "query_pattern": "excellent credit",
        "vanilla_likely": ["any good card"],
        "guidance_should": ["premium cards requiring excellent credit"],
        "reason": "Credit score context may be lost"
    },
    {
        "query_pattern": "first card",
        "vanilla_likely": ["premium (better descriptions)"],
        "guidance_should": ["student/secured cards"],
        "reason": "First-time user needs guidance for approval likelihood"
    },
]


@dataclass
class QueryGenerator:
    """Generate synthetic queries with ground truth"""

    num_queries: int = 150
    num_cards: int = 50
    num_guidance: int = 25
    difficulty_counts: Dict[str, int] = None
    random_seed: int = 42

    def __post_init__(self):
        random.seed(self.random_seed)
        if self.difficulty_counts is None:
            # Default distribution: 30% easy, 35% medium, 25% hard, 10% expert
            # Use int() and adjust to ensure exact count
            counts = {
                "easy": int(self.num_queries * 0.30),
                "medium": int(self.num_queries * 0.35),
                "hard": int(self.num_queries * 0.25),
                "expert": int(self.num_queries * 0.10),
            }

            # Adjust to match exact num_queries
            current_total = sum(counts.values())
            diff = self.num_queries - current_total

            # Add/subtract from medium to hit exact count
            counts["medium"] += diff

            self.difficulty_counts = counts

    def _calculate_conflict_level(self, difficulty: str) -> int:
        """Calculate how many conflicting guidance rules might apply"""
        if difficulty == "easy":
            return 0
        elif difficulty == "medium":
            return random.choice([0, 1])
        elif difficulty == "hard":
            return random.choice([1, 2])
        else:  # expert
            return random.choice([2, 3])

    def _should_fail_vanilla(self, difficulty: str) -> bool:
        """Determine if vanilla RAG should likely fail"""
        if difficulty == "easy":
            return random.random() < 0.4  # 40% fail - guidance clarifies
        elif difficulty == "medium":
            return random.random() < 0.3  # 30% fail - implicit needs
        elif difficulty == "hard":
            return random.random() < 0.25  # 25% fail - conflicts resolved
        else:  # expert
            return random.random() < 0.15  # 15% fail - ambiguity handled

    def _find_matching_guidance(self, query: str, guidance: List[Dict]) -> List[str]:
        """Find guidance IDs that should apply to this query"""
        matching = []
        query_lower = query.lower()

        for g in guidance:
            keywords = g.get("applicable_keywords", [])
            for kw in keywords:
                if kw.lower() in query_lower:
                    matching.append(g["id"])
                    break

        # Always return at least some guidance
        if not matching and guidance:
            matching = [random.choice(guidance)["id"]]

        return matching[:3]  # Max 3 guidance

    # --- Relevance oracle (guidance-INDEPENDENT) ---------------------------
    #
    # IMPORTANT: ground-truth relevance is derived ONLY from intrinsic card
    # attributes matched to the query's category. It deliberately does NOT use
    # the guidance rules. An earlier version added the guidance BOOST/DEMOTE
    # term to the gold labels, which made the benchmark circular (the
    # policy-guided method was rewarded for reproducing the label generator).
    # Guidance influence is now measured separately via `policy_preferred_cards`
    # and the controllability metric, never via these accuracy labels.
    #
    # Ambiguous / adversarial categories have no objective relevance gold and
    # return [] so the evaluator can exclude them from accuracy.
    AMBIGUOUS_CATEGORIES = {"give_me_free_money", "popular", "conflicting"}

    @staticmethod
    def _card_matches_category(card: Dict, category: str) -> bool:
        """Human-defensible attribute predicate: is this card relevant to the
        category, judging only by the card's own attributes?"""
        tags = set(card.get("tags", []))
        name = card.get("name", "").lower()
        rewards = card.get("rewards", {})
        reward_keys = " ".join(rewards.keys()).lower() if isinstance(rewards, dict) else ""
        fee = card.get("annual_fee", 99)
        credit = card.get("credit_score_required", "").lower()

        if category == "business":
            return "business" in tags or "business" in name
        if category in ("student", "new_credit"):
            return bool(tags & {"student", "secured", "building-credit"})
        if category == "no_fee":
            return fee == 0
        if category == "low_fee":
            return fee <= 100
        if category == "premium":
            return bool(tags & {"premium", "ultra-premium", "lounge"})
        if category == "travel":
            return bool(tags & {"travel", "airline"})
        if category == "lounge":
            return "lounge" in tags
        if category == "gas":
            return ("gas" in tags) or ("transit" in tags) or ("gas" in reward_keys)
        if category == "cashback":
            return "cashback" in tags
        if category == "dining":
            return ("dining" in tags) or ("restaurant" in reward_keys) or ("dining" in reward_keys)
        if category == "grocery":
            return any(k in reward_keys for k in ("grocer", "whole-foods", "supermarket")) or "grocery" in tags
        if category == "shopping":
            return bool(tags & {"shopping", "co-branded", "retail", "amazon"})
        if category == "crypto":
            return ("crypto" in tags) or ("bitcoin" in name)
        if category == "good_credit":
            return ("excellent" in credit) or any(s in credit for s in ("750", "760", "780", "800"))
        if category in ("poor_credit", "fair_credit"):
            return bool(tags & {"secured", "building-credit"}) or any(s in credit for s in ("poor", "fair", "no credit"))
        if category == "international":
            return bool(tags & {"international", "no-fee-foreign"})
        if category == "simple":
            return bool(tags & {"simple", "basic"})
        return False

    def _relevance_gold(self, query: str, category: str, cards: List[Dict]) -> List[str]:
        """Top relevant cards by attribute match (guidance-independent).

        Returns [] for ambiguous/adversarial categories with no objective gold.
        Deterministic tie-break by card id keeps output reproducible.
        """
        if category in self.AMBIGUOUS_CATEGORIES:
            return []

        matches = [c["id"] for c in cards if self._card_matches_category(c, category)]
        matches.sort()  # deterministic
        return matches[:3]

    def _policy_targets(self, query: str, guidance: List[Dict], action: str) -> List[str]:
        """Cards targeted by guidance of a given ACTION whose keywords match the
        query. Used ONLY for controllability/enforcement metrics, never as gold."""
        targets = []
        query_lower = query.lower()
        for g in guidance:
            if g.get("action") != action:
                continue
            for kw in g.get("applicable_keywords", []):
                if kw.lower() in query_lower:
                    targets.extend(g.get("target_cards", []))
                    break
        seen, out = set(), []
        for c in targets:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out[:5]

    def _policy_preferred(self, query: str, guidance: List[Dict]) -> List[str]:
        """BOOST targets matching the query (cards the policy wants surfaced)."""
        return self._policy_targets(query, guidance, "BOOST")

    def generate(self, cards: List[Dict], guidance: List[Dict]) -> List[Dict]:
        """Generate queries with ground truth"""
        queries = []
        query_id = 1

        # Build flat list of difficulties
        difficulty_list = []
        for difficulty, count in self.difficulty_counts.items():
            difficulty_list.extend([difficulty] * count)

        # Shuffle and trim to exact count
        random.shuffle(difficulty_list)
        difficulty_list = difficulty_list[:self.num_queries]

        # Track used queries to avoid duplicates
        used_queries = set()

        for difficulty in difficulty_list:
            # Pick a category template
            templates = QUERY_TEMPLATES.get(difficulty, QUERY_TEMPLATES["easy"])

            # Flatten to (category, query) pairs so the category is preserved —
            # the relevance oracle needs it to assign attribute-based gold.
            all_pairs = [(cat, q) for cat, qs in templates.items() for q in qs]

            # Filter out already used queries
            available = [(c, q) for (c, q) in all_pairs if q not in used_queries]

            # If we've used all, allow repeats but mark as used
            if not available:
                available = all_pairs
                used_queries.clear()

            category, query = random.choice(available)
            used_queries.add(query)

            # Find applicable guidance (keyword match) — kept for traceability
            guidance_should_apply = self._find_matching_guidance(query, guidance)

            # Relevance gold: attribute-based, guidance-INDEPENDENT (may be [])
            expected_cards = self._relevance_gold(query, category, cards)

            # Cards the hidden policy wants surfaced / removed — metrics only
            policy_preferred = self._policy_preferred(query, guidance)
            policy_excluded = self._policy_targets(query, guidance, "EXCLUDE")

            # Determine if vanilla should fail
            vanilla_failure_expected = self._should_fail_vanilla(difficulty)

            # Calculate conflict level
            conflict_level = self._calculate_conflict_level(difficulty)

            # Generate notes
            notes = self._generate_notes(query, difficulty, vanilla_failure_expected, guidance_should_apply)

            query_obj = {
                "id": f"q{query_id:03d}",
                "query": query,
                "category": category,
                "expected_top_cards": expected_cards,        # relevance gold (guidance-independent)
                "policy_preferred_cards": policy_preferred,   # BOOST targets (controllability metric)
                "policy_excluded_cards": policy_excluded,     # EXCLUDE targets (enforcement metric)
                "guidance_should_apply": guidance_should_apply,
                "difficulty": difficulty,
                "conflict_level": conflict_level,
                "vanilla_failure_expected": vanilla_failure_expected,
                "notes": notes
            }

            queries.append(query_obj)
            query_id += 1

        return queries

    def _generate_notes(self, query: str, difficulty: str, vanilla_fail: bool, guidance_ids: List[str]) -> str:
        """Generate explanation notes for the query"""
        notes = []

        if difficulty == "easy":
            notes.append("Direct keyword match - guidance triggers cleanly")
        elif difficulty == "medium":
            notes.append("Implicit needs requiring guidance adjustment")
        elif difficulty == "hard":
            notes.append("Conflicting constraints, multiple guidance may apply")
        else:
            notes.append("Semantic ambiguity - policy guides interpretation")

        if vanilla_fail:
            notes.append("Vanilla RAG would likely miss correct card")

        if guidance_ids:
            notes.append(f"Guidance {', '.join(guidance_ids[:2])} should apply")

        return ". ".join(notes)


def generate_sample_queries(num_cards: int = 15, num_guidance: int = 8, num_queries: int = 12) -> List[Dict]:
    """Generate sample queries"""
    from .card_generator import generate_sample_cards
    from .guidance_generator import generate_sample_guidance

    cards = generate_sample_cards(num_cards)
    guidance = generate_sample_guidance(num_cards, num_guidance)

    gen = QueryGenerator(num_queries=num_queries, num_cards=num_cards, num_guidance=num_guidance,
                         random_seed=42)
    return gen.generate(cards, guidance)


if __name__ == "__main__":
    queries = generate_sample_queries(15, 8, 12)
    import json
    print(json.dumps(queries, indent=2))