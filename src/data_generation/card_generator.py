"""
Card Generator - Generate diverse credit card datasets
"""
import random
import copy
from typing import List, Dict
from dataclasses import dataclass


# Card templates for each category
CARD_TEMPLATES = {
    "premium_travel": {
        "annual_fee_range": (250, 695),
        "credit_score": "Excellent (750+)",
        "reward_types": ["travel", "dining", "airline", "lounge"],
        "benefit_templates": [
            ["Priority Pass lounge access", "Travel insurance up to $500k", "Global Entry credit"],
            ["Unlimited lounge access", "Concierge service", "Travel credits"],
            ["Airport lounge access", "Free checked bags", "Travel insurance", "Concierge service"],
            ["Hotel elite status", "Dining credits", "Airport lounge access"],
        ],
        "tags": ["premium", "travel", "lounge", "high-fee"]
    },
    "business": {
        "annual_fee_range": (95, 395),
        "credit_score": "Good (680+)",
        "reward_types": ["office_supplies", "telecom", "advertising", "travel"],
        "benefit_templates": [
            ["Employee cards at no extra cost", "Expense management tools"],
            ["Business lounge access", "Purchase protection", "Travel benefits"],
            ["Quarterly bonus categories", "Receipt scanning", "Integration with accounting"],
        ],
        "tags": ["business", "office", "expenses", "professional"]
    },
    "cashback_daily": {
        "annual_fee_range": (0, 0),
        "credit_score": "Good (670+)",
        "reward_types": ["groceries", "gas", "dining", "utilities"],
        "benefit_templates": [
            ["No annual fee", "Purchase protection", "Extended warranty"],
            ["No annual fee", "Cell phone protection", "Travel assistance"],
        ],
        "tags": ["no-fee", "cashback", "daily", "simple"]
    },
    "student": {
        "annual_fee_range": (0, 0),
        "credit_score": "Fair (580+)",
        "reward_types": ["restaurants", "streaming", "entertainment"],
        "benefit_templates": [
            ["No annual fee", "Build credit history", "Student-friendly approval"],
            ["No annual fee", "Credit education tools", "First-year rewards bonus"],
        ],
        "tags": ["student", "no-fee", "building-credit"]
    },
    "secured": {
        "annual_fee_range": (0, 0),
        "credit_score": "Poor (580+)",
        "reward_types": ["everything"],
        "benefit_templates": [
            ["No annual fee", "Builds credit", "Refundable deposit"],
            ["No annual fee", "Graduation bonus", "Credit monitoring"],
        ],
        "tags": ["secured", "building-credit", "no-fee"]
    },
    "cobrand_amazon": {
        "annual_fee_range": (0, 0),
        "credit_score": "Good (670+)",
        "reward_types": ["amazon", "whole-foods", "gas", "restaurants"],
        "benefit_templates": [
            ["No annual fee (with Prime)", "Purchase protection"],
            ["No annual fee", "Extended warranty", "Exclusive deals"],
        ],
        "tags": ["co-branded", "shopping", "no-fee", "amazon"]
    },
    "cobrand_other": {
        "annual_fee_range": (0, 95),
        "credit_score": "Fair (640+)",
        "reward_types": ["department-stores", "clothing", "home", "gas"],
        "benefit_templates": [
            ["No annual fee", "Extended returns"],
            ["Store discounts", "Birthday rewards", "Early access to sales"],
        ],
        "tags": ["co-branded", "retail", "shopping"]
    },
    "crypto_tech": {
        "annual_fee_range": (0, 0),
        "credit_score": "Good (660+)",
        "reward_types": ["crypto-purchases", "dining", "travel", "tech"],
        "benefit_templates": [
            ["No annual fee", "Crypto rewards", "Blockchain rewards"],
            ["No annual fee", "Tech purchase protection", "Extended warranty"],
        ],
        "tags": ["crypto", "no-fee", "tech", "bitcoin"]
    },
    "gas_transit": {
        "annual_fee_range": (0, 0),
        "credit_score": "Good (660+)",
        "reward_types": ["gas", "transit", "parking", "ride-share"],
        "benefit_templates": [
            ["No annual fee", "No foreign fees"],
            ["No annual fee", "EV charging rewards", "Transit discounts"],
        ],
        "tags": ["no-fee", "gas", "commute", "transit"]
    },
    "airline": {
        "annual_fee_range": (59, 199),
        "credit_score": "Good (680+)",
        "reward_types": ["airlines", "hotel", "travel", "airport-services"],
        "benefit_templates": [
            ["Free checked bag", "Priority boarding", "10% off award flights"],
            ["Companion certificate", "Reduced processing fees", "Zone upgrades"],
        ],
        "tags": ["airline", "travel", "fee"]
    },
    "international": {
        "annual_fee_range": (95, 250),
        "credit_score": "Good (700+)",
        "reward_types": ["foreign-spending", "travel", "dining"],
        "benefit_templates": [
            ["No foreign transaction fees", "Travel insurance", "Emergency assistance"],
            ["Global Entry credit", "Travel credit", "Concierge"],
        ],
        "tags": ["international", "travel", "no-fee-foreign"]
    },
    "balance_transfer": {
        "annual_fee_range": (0, 95),
        "credit_score": "Fair (620+)",
        "reward_types": ["balance-transfer", "other"],
        "benefit_templates": [
            ["0% intro APR", "No fee balance transfers"],
            ["Low ongoing APR", "Free credit score"],
        ],
        "tags": ["balance-transfer", "debt", "fee"]
    }
}

# Reward templates per category
REWARD_TEMPLATES = {
    "travel": "{category}: {multiplier}x points",
    "dining": "{category}: {multiplier}x points",
    "airline": "{category}: {multiplier}x miles",
    "lounge": "Lounge access included",
    "office_supplies": "{category}: {multiplier}x points",
    "telecom": "{category}: {multiplier}x points",
    "advertising": "{category}: {multiplier}x points",
    "groceries": "{category}: {multiplier}% cashback",
    "gas": "{category}: {multiplier}% cashback",
    "utilities": "{category}: {multiplier}% cashback",
    "restaurants": "{category}: {multiplier}% cashback",
    "streaming": "{category}: {multiplier}% cashback",
    "entertainment": "{category}: {multiplier}% cashback",
    "everything": "{category}: {multiplier}% cashback",
    "amazon": "{category}: {multiplier}% cashback",
    "whole-foods": "{category}: {multiplier}% cashback",
    "department-stores": "{category}: {multiplier}% cashback",
    "clothing": "{category}: {multiplier}% cashback",
    "home": "{category}: {multiplier}% cashback",
    "crypto-purchases": "{category}: {multiplier}% back in crypto",
    "tech": "{category}: {multiplier}% cashback",
    "transit": "{category}: {multiplier}% cashback",
    "parking": "{category}: {multiplier}% cashback",
    "ride-share": "{category}: {multiplier}% cashback",
    "hotel": "{category}: {multiplier}x points",
    "airport-services": "{category}: {multiplier}x points",
    "foreign-spending": "{category}: {multiplier}x points",
    "balance-transfer": "Balance transfer offer available",
}

# Name components for generating varied card names
NAME_PREFIXES = [
    "Premium", "Elite", "Platinum", "Gold", "Silver", "Basic",
    "Everyday", "Travel", "Business", "Professional", "Rewards",
    "Cashback", "Points", "Miles", "Freedom", "Sapphire"
]

NAME_SUFFIXES = [
    "Plus", "Elite", "Card", "Rewards", "Preferred", "Signature",
    "Platinum", "Gold", "World", "Prestige", "Advantage", "Pro"
]

CATEGORY_ADJECTIVES = [
    "Travel", "Business", "Cashback", "Rewards", "Points", "Miles",
    "Crypto", "Amazon", "International", "Transit", "Gas"
]


@dataclass
class CardGenerator:
    """Generate synthetic credit cards"""

    num_cards: int = 50
    random_seed: int = 42

    def __post_init__(self):
        random.seed(self.random_seed)
        self._category_weights = [
            ("premium_travel", 0.15),
            ("business", 0.12),
            ("cashback_daily", 0.20),
            ("student", 0.08),
            ("secured", 0.06),
            ("cobrand_amazon", 0.06),
            ("cobrand_other", 0.06),
            ("crypto_tech", 0.05),
            ("gas_transit", 0.08),
            ("airline", 0.06),
            ("international", 0.05),
            ("balance_transfer", 0.03),
        ]

    def _choose_category(self) -> str:
        """Choose a card category based on weights"""
        r = random.random()
        cumulative = 0
        for cat, weight in self._category_weights:
            cumulative += weight
            if r < cumulative:
                return cat
        return "cashback_daily"

    def _generate_name(self, category: str) -> str:
        """Generate a card name"""
        if category == "student":
            return f"{random.choice(['Student', 'Campus', 'First', 'Starter'])} {random.choice(['Card', 'Starter', 'Build', 'Journey'])}"
        elif category == "secured":
            return f"{random.choice(['Secured', 'Build', 'Start', 'Foundation'])} {random.choice(['Card', 'Credit', 'Journey'])}"
        elif category == "cobrand_amazon":
            return f"Amazon {random.choice(['Prime', 'Rewards', 'Store'])} Card"
        elif category == "crypto_tech":
            return f"{random.choice(['Crypto', 'Bitcoin', 'Digital', 'Blockchain'])} {random.choice(['Card', 'Rewards', 'Plus'])}"
        elif category == "gas_transit":
            return f"{random.choice(['Gas', 'Transit', 'Commute', 'Drive'])} & {random.choice(['Transit', 'Commute', 'Rewards'])} Card"
        elif category == "airline":
            return f"{random.choice(['Sky', 'Air', 'Flight', 'Travel'])} {random.choice(['Miles', 'Rewards', 'Elite', 'Plus'])} Card"
        elif category == "business":
            return f"{random.choice(['Business', 'Professional', 'Enterprise', 'Startup'])} {random.choice(['Pro', 'Plus', 'Elite', 'Rewards'])}"
        elif category == "balance_transfer":
            return f"{random.choice(['Balance', 'Transfer', 'Freedom'])} {random.choice(['Card', 'Plus', 'Choice'])}"

        prefix = random.choice(NAME_PREFIXES)
        suffix = random.choice(NAME_SUFFIXES)
        if random.random() < 0.3:
            return f"{prefix} {suffix}"
        return f"{prefix} {suffix} Card"

    def _generate_rewards(self, template: Dict) -> Dict[str, str]:
        """Generate rewards dictionary for a card"""
        rewards = {}
        categories = template["reward_types"]

        for cat in categories:
            if cat == "everything":
                rewards["everything"] = "1-2% cashback"
            else:
                # Pick a multiplier
                if cat in ["groceries", "gas", "dining"]:
                    mult = random.choice([2, 3, 4, 5])
                elif cat in ["travel", "airline", "hotel"]:
                    mult = random.choice([2, 3, 4, 5])
                elif cat in ["office_supplies", "telecom", "advertising"]:
                    mult = random.choice([2, 3, 5])
                elif cat in ["amazon", "crypto-purchases"]:
                    mult = random.choice([2, 3, 4, 5])
                else:
                    mult = random.choice([1, 2, 3])

                # Determine if points or cashback
                if cat in ["travel", "airline", "hotel", "office_supplies", "telecom", "advertising"]:
                    rewards[cat] = f"{mult}x points"
                else:
                    rewards[cat] = f"{mult}% cashback"

        # Ensure at least one reward
        if not rewards:
            rewards["other"] = "1% cashback"

        return rewards

    def generate(self) -> List[Dict]:
        """Generate a list of credit cards"""
        cards = []
        used_names = set()

        for i in range(1, self.num_cards + 1):
            # Pick category
            category = self._choose_category()
            template = CARD_TEMPLATES[category]

            # Generate name (ensure unique)
            name = self._generate_name(category)
            if name in used_names:
                name = f"{name} {random.choice(['Plus', 'Select', 'Preferred'])}"
            used_names.add(name)

            # Generate annual fee
            fee_range = template["annual_fee_range"]
            if fee_range[0] == fee_range[1]:
                annual_fee = fee_range[0]
            else:
                annual_fee = random.randint(fee_range[0], fee_range[1])

            # Generate rewards
            rewards = self._generate_rewards(template)

            # Generate benefits
            benefits = random.choice(template["benefit_templates"]).copy()

            # Add fee-based benefit for high-fee cards
            if annual_fee > 200:
                extra_benefits = [
                    "Annual travel credit",
                    "Global Entry/TSA Pre credit",
                    "Quarterly dining credits",
                    "Hotel elite status",
                ]
                benefits.append(random.choice(extra_benefits))

            # Add credit score if needed
            if category == "premium_travel" and "excellent" not in template["credit_score"].lower():
                template["credit_score"] = "Excellent (750+)"

            # Generate tags (use set to avoid duplicates)
            tags = list(set(template["tags"].copy()))
            if annual_fee == 0:
                tags.append("no-fee")
            if annual_fee > 300:
                tags.append("high-fee")
            if annual_fee > 0 and annual_fee <= 100:
                tags.append("low-fee")

            card = {
                "id": f"card_{i:03d}",
                "name": name,
                "annual_fee": annual_fee,
                "rewards": rewards,
                "benefits": benefits,
                "credit_score_required": template["credit_score"],
                "tags": tags
            }

            cards.append(card)

        return cards


def generate_sample_cards(num_cards: int = 15) -> List[Dict]:
    """Generate sample cards matching the original dataset structure"""
    gen = CardGenerator(num_cards=num_cards, random_seed=42)
    return gen.generate()


if __name__ == "__main__":
    cards = generate_sample_cards(15)
    import json
    print(json.dumps(cards, indent=2))