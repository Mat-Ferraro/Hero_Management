import random
from typing import Dict


GROWTH_RATE_MULTIPLIERS: Dict[str, float] = {
    "Mundane": 0.80,
    "Talented": 1.00,
    "Gifted": 1.20,
    "Heroic": 1.40,
    "Legendary": 1.70,
    "Mythic": 2.00,
}


GROWTH_RATE_DESCRIPTIONS: Dict[str, str] = {
    "Mundane": "Slow learner. Lower long-term development potential.",
    "Talented": "Reliable baseline growth.",
    "Gifted": "Strong natural talent and above-average growth.",
    "Heroic": "Elite growth. Excellent long-term investment.",
    "Legendary": "Rare franchise-defining growth.",
    "Mythic": "Extremely rare world-shaping potential.",
}


def growth_multiplier(growth_rate: str) -> float:
    return GROWTH_RATE_MULTIPLIERS.get(growth_rate, 1.0)


def growth_description(growth_rate: str) -> str:
    return GROWTH_RATE_DESCRIPTIONS.get(growth_rate, "Unknown growth potential.")


def random_growth_rate() -> str:
    roll = random.random()

    if roll < 0.40:
        return "Mundane"

    if roll < 0.70:
        return "Talented"

    if roll < 0.88:
        return "Gifted"

    if roll < 0.96:
        return "Heroic"

    if roll < 0.995:
        return "Legendary"

    return "Mythic"
