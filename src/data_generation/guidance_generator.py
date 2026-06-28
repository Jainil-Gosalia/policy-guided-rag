"""
Guidance Generator - Generate policy rules (BOOST/DEMOTE/EXCLUDE)
"""
import random
from typing import List, Dict
from dataclasses import dataclass


# Guidance action types
class GuidanceAction:
    BOOST = "BOOST"
    DEMOTE = "DEMOTE"
    EXCLUDE = "EXCLUDE"


# Category definitions with keywords
CATEGORY_DEFINITIONS = {
    "business": {
        "keywords": ["business", "startup", "company", "entrepreneur", "expenses", "professional", "office", "work"],
        "description": "Business and professional expenses"
    },
    "student": {
        "keywords": ["student", "college", "university", "freshman", "school", "education"],
        "description": "Student-specific cards"
    },
    "no_fee": {
        "keywords": ["no fee", "no annual fee", "free", "affordable", "cheap", "don't want to pay"],
        "description": "Cards with no annual fee"
    },
    "low_fee": {
        "keywords": ["low fee", "cheap", "minimal fee", "reasonable"],
        "description": "Cards with low annual fees"
    },
    "premium": {
        "keywords": ["premium", "best", "top", "elite", "luxury", "exclusive"],
        "description": "Premium travel cards with benefits"
    },
    "travel": {
        "keywords": ["travel", "trip", "vacation", "flight", "hotel", "airline", "airport", "lounge"],
        "description": "Travel and airline cards"
    },
    "lounge": {
        "keywords": ["lounge", "airport lounge", "priority pass", "club"],
        "description": "Cards with lounge access"
    },
    "gas": {
        "keywords": ["gas", "fuel", "driving", "commute", "transit", "train", "parking", "ev"],
        "description": "Gas and transit cards"
    },
    "cashback": {
        "keywords": ["cashback", "cash back", "get paid", "earn money", "back"],
        "description": "Cashback-focused cards"
    },
    "dining": {
        "keywords": ["dining", "restaurant", "food", "meals", "eat"],
        "description": "Dining rewards"
    },
    "grocery": {
        "keywords": ["grocery", "groceries", "supermarket", "food shopping"],
        "description": "Grocery rewards"
    },
    "shopping": {
        "keywords": ["shopping", "amazon", "retail", "stores", "buy"],
        "description": "Shopping rewards"
    },
    "crypto": {
        "keywords": ["crypto", "bitcoin", "cryptocurrency", "digital currency"],
        "description": "Crypto rewards"
    },
    "good_credit": {
        "keywords": ["good credit", "excellent credit", "750", "760", "800"],
        "description": "Cards for good/excellent credit"
    },
    "fair_credit": {
        "keywords": ["fair credit", "building credit", "improve credit"],
        "description": "Cards for fair credit"
    },
    "poor_credit": {
        "keywords": ["poor credit", "bad credit", "no credit", "secured"],
        "description": "Cards for poor/no credit"
    },
    "international": {
        "keywords": ["international", "abroad", "foreign", "europe", "overseas", "no foreign transaction"],
        "description": "International travel cards"
    },
    "new_credit": {
        "keywords": ["first card", "new credit", "just turned", "18", "no history"],
        "description": "First-time cardholders"
    }
}

# Rule templates per category
RULE_TEMPLATES = {
    "business": {
        "actions": [GuidanceAction.BOOST, GuidanceAction.DEMOTE],
        "description": "BOOST business cards for business queries, DEMOTE personal cards"
    },
    "student": {
        "actions": [GuidanceAction.BOOST, GuidanceAction.DEMOTE],
        "description": "BOOST student cards for student queries, DEMOTE premium"
    },
    "no_fee": {
        "actions": [GuidanceAction.BOOST, GuidanceAction.DEMOTE],
        "description": "BOOST no-fee cards, DEMOTE fee cards"
    },
    "low_fee": {
        "actions": [GuidanceAction.BOOST, GuidanceAction.DEMOTE],
        "description": "BOOST low-fee cards, DEMOTE high-fee"
    },
    "premium": {
        "actions": [GuidanceAction.BOOST, GuidanceAction.DEMOTE],
        "description": "BOOST premium cards, DEMOTE for bad credit"
    },
    "travel": {
        "actions": [GuidanceAction.BOOST, GuidanceAction.DEMOTE],
        "description": "BOOST travel cards, DEMOTE for no-fee seekers"
    },
    "lounge": {
        "actions": [GuidanceAction.BOOST],
        "description": "BOOST lounge access cards"
    },
    "gas": {
        "actions": [GuidanceAction.BOOST],
        "description": "BOOST gas/transit cards"
    },
    "cashback": {
        "actions": [GuidanceAction.BOOST, GuidanceAction.DEMOTE],
        "description": "BOOST cashback cards, DEMOTE points cards"
    },
    "dining": {
        "actions": [GuidanceAction.BOOST],
        "description": "BOOST dining reward cards"
    },
    "grocery": {
        "actions": [GuidanceAction.BOOST],
        "description": "BOOST grocery reward cards"
    },
    "shopping": {
        "actions": [GuidanceAction.BOOST],
        "description": "BOOST shopping/cards"
    },
    "crypto": {
        "actions": [GuidanceAction.BOOST],
        "description": "BOOST crypto cards"
    },
    "good_credit": {
        "actions": [GuidanceAction.BOOST, GuidanceAction.DEMOTE],
        "description": "BOOST cards for good credit, DEMOTE for poor credit"
    },
    "fair_credit": {
        "actions": [GuidanceAction.BOOST, GuidanceAction.DEMOTE],
        "description": "BOOST cards for fair credit, DEMOTE premium"
    },
    "poor_credit": {
        "actions": [GuidanceAction.BOOST, GuidanceAction.DEMOTE],
        "description": "BOOST secured/student cards, DEMOTE premium"
    },
    "international": {
        "actions": [GuidanceAction.BOOST, GuidanceAction.DEMOTE],
        "description": "BOOST no foreign transaction fee cards, DEMOTE cards with FTF"
    },
    "new_credit": {
        "actions": [GuidanceAction.BOOST, GuidanceAction.DEMOTE],
        "description": "BOOST first-time cards, DEMOTE hard-to-get"
    }
}


@dataclass
class GuidanceGenerator:
    """Generate synthetic guidance rules"""

    num_guidance: int = 25
    num_cards: int = 50
    random_seed: int = 42

    def __post_init__(self):
        random.seed(self.random_seed)

    def _get_card_id_by_category(self, cards: List[Dict], category: str) -> List[str]:
        """Find card IDs matching a category"""
        matches = []
        for card in cards:
            tags = card.get("tags", [])
            name = card.get("name", "").lower()

            # Category-specific matching
            if category == "business" and ("business" in tags or "business" in name):
                matches.append(card["id"])
            elif category == "student" and ("student" in tags):
                matches.append(card["id"])
            elif category == "no_fee" and 0 in [card.get("annual_fee", 99)]:
                matches.append(card["id"])
            elif category == "low_fee" and card.get("annual_fee", 99) <= 100:
                matches.append(card["id"])
            elif category == "premium" and ("premium" in tags or "lounge" in tags):
                matches.append(card["id"])
            elif category == "travel" and ("travel" in tags or "airline" in tags):
                matches.append(card["id"])
            elif category == "lounge" and "lounge" in tags:
                matches.append(card["id"])
            elif category == "gas" and ("gas" in tags or "transit" in tags):
                matches.append(card["id"])
            elif category == "cashback" and ("cashback" in tags):
                matches.append(card["id"])
            elif category == "dining" and "dining" in name:
                matches.append(card["id"])
            elif category == "grocery" and "groceries" in card.get("rewards", {}):
                matches.append(card["id"])
            elif category == "shopping" and ("shopping" in tags or "co-branded" in tags):
                matches.append(card["id"])
            elif category == "crypto" and ("crypto" in tags or "bitcoin" in name):
                matches.append(card["id"])
            elif category == "good_credit" and "excellent" in card.get("credit_score_required", "").lower():
                matches.append(card["id"])
            elif category == "fair_credit" and "fair" in card.get("credit_score_required", "").lower():
                matches.append(card["id"])
            elif category == "poor_credit" and ("secured" in tags or "poor" in card.get("credit_score_required", "").lower()):
                matches.append(card["id"])
            elif category == "international" and "no-fee-foreign" in tags:
                matches.append(card["id"])
            elif category == "new_credit" and ("student" in tags or "secured" in tags):
                matches.append(card["id"])

        # Fallback to any card with matching tags
        if not matches:
            for card in cards:
                if category in card.get("tags", []):
                    matches.append(card["id"])

        return matches[:5] if len(matches) > 5 else matches

    def _build_rule_text(self, action: str, card_ids: List[str], category: str, priority: str = "high") -> str:
        """Build the rule text"""
        category_info = CATEGORY_DEFINITIONS.get(category, {})
        keywords = category_info.get("keywords", [])
        keyword_text = ", ".join(keywords[:5])

        card_text = ", ".join(card_ids[:3]) if len(card_ids) >= 3 else ", ".join(card_ids)

        if action == GuidanceAction.BOOST:
            rule = f"BOOST {card_text} for {category} queries. For {keyword_text} queries ALWAYS prioritize these cards."
        elif action == GuidanceAction.DEMOTE:
            rule = f"DEMOTE {card_text} for {category} queries. For {keyword_text} queries avoid these cards."
        else:
            rule = f"EXCLUDE {card_text} for {category} queries. Never recommend these cards for {keyword_text} queries."

        return rule

    def generate(self, cards: List[Dict]) -> List[Dict]:
        """Generate guidance rules"""
        guidance = []
        used_categories = set()

        # Get available categories
        available_categories = list(CATEGORY_DEFINITIONS.keys())
        random.shuffle(available_categories)

        # Force some DEMOTE rules for realism
        demote_indices = set(random.sample(range(self.num_guidance), min(5, self.num_guidance // 4)))

        for i in range(self.num_guidance):
            # Pick a category (try to use each category at least once first)
            if i < len(available_categories):
                category = available_categories[i]
            else:
                category = random.choice(available_categories)

            # Get template
            template = RULE_TEMPLATES.get(category, RULE_TEMPLATES["no_fee"])

            # Force DEMOTE for some, otherwise use template actions
            if i in demote_indices and GuidanceAction.DEMOTE in template["actions"]:
                action = GuidanceAction.DEMOTE
            else:
                action = random.choice(template["actions"])

            # Find matching cards
            target_cards = self._get_card_id_by_category(cards, category)

            if not target_cards:
                # Fallback - find any card
                target_cards = [cards[random.randint(0, len(cards) - 1)]["id"]]

            # Determine priority
            priority = random.choice(["high", "medium", "low"])

            # Build rule
            rule_text = self._build_rule_text(action, target_cards, category, priority)

            guidance_item = {
                "id": f"guidance_{i+1:03d}",
                "rule": rule_text,
                "priority": priority,
                "category": category,
                "applicable_keywords": CATEGORY_DEFINITIONS.get(category, {}).get("keywords", [])[:5],
                "target_cards": target_cards,
                "action": action
            }

            guidance.append(guidance_item)

        # Add "discontinued product" EXCLUDE rules (negative guidance that the
        # operator must enforce by hard removal). These deliberately target cards
        # that ARE relevant to the query category, so a naive ranker WOULD surface
        # them — making the operator's removal observable (and exposing the
        # relevance cost of enforcement).
        for cat in ("cashback", "travel"):
            cat_cards = self._get_card_id_by_category(cards, cat)[:2]
            if not cat_cards:
                continue
            kws = CATEGORY_DEFINITIONS[cat]["keywords"][:5]
            card_text = ", ".join(cat_cards)
            rule_text = (f"EXCLUDE {card_text} for {cat} queries (discontinued). "
                         f"Never recommend these cards for {', '.join(kws[:4])} queries.")
            guidance.append({
                "id": f"guidance_{len(guidance) + 1:03d}",
                "rule": rule_text,
                "priority": "high",
                "category": cat,
                "applicable_keywords": kws,
                "target_cards": cat_cards,
                "action": GuidanceAction.EXCLUDE,
            })

        return guidance


def generate_sample_guidance(num_cards: int = 15, num_guidance: int = 8) -> List[Dict]:
    """Generate sample guidance from existing cards"""
    from .card_generator import generate_sample_cards

    cards = generate_sample_cards(num_cards)
    gen = GuidanceGenerator(num_guidance=num_guidance, num_cards=num_cards, random_seed=42)
    return gen.generate(cards)


if __name__ == "__main__":
    guidance = generate_sample_guidance(15, 8)
    import json
    print(json.dumps(guidance, indent=2))