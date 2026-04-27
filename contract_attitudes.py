import random
from typing import Dict


CONTRACT_ATTITUDE_MULTIPLIERS: Dict[str, Dict[str, float]] = {
    "Modest": {
        "signing_bonus": 0.85,
        "wage": 0.85,
    },
    "Practical": {
        "signing_bonus": 1.00,
        "wage": 1.00,
    },
    "Ambitious": {
        "signing_bonus": 1.15,
        "wage": 1.20,
    },
    "Mercenary": {
        "signing_bonus": 1.35,
        "wage": 1.45,
    },
    "Noble": {
        "signing_bonus": 0.95,
        "wage": 0.90,
    },
}


CONTRACT_ATTITUDE_DESCRIPTIONS: Dict[str, str] = {
    "Modest": "Accepts lower pay and values opportunity.",
    "Practical": "Negotiates around market value.",
    "Ambitious": "Expects above-market pay and believes they deserve investment.",
    "Mercenary": "Follows gold first and demands premium contracts.",
    "Noble": "May accept less from a respected and honorable guild.",
}


def random_contract_attitude() -> str:
    roll = random.random()

    if roll < 0.20:
        return "Modest"

    if roll < 0.62:
        return "Practical"

    if roll < 0.82:
        return "Ambitious"

    if roll < 0.94:
        return "Mercenary"

    return "Noble"


def attitude_description(contract_attitude: str) -> str:
    return CONTRACT_ATTITUDE_DESCRIPTIONS.get(contract_attitude, "Unknown contract attitude.")


def attitude_multiplier(contract_attitude: str, field: str, reputation=None) -> float:
    multipliers = CONTRACT_ATTITUDE_MULTIPLIERS.get(
        contract_attitude,
        CONTRACT_ATTITUDE_MULTIPLIERS["Practical"],
    )
    multiplier = multipliers.get(field, 1.0)

    # Noble heroes give better terms to reputable and safe managers,
    # but are less impressed by unreliable managers.
    if contract_attitude == "Noble" and reputation is not None:
        goodwill = (reputation.overall + reputation.safety + reputation.reliability) / 3

        if goodwill >= 25:
            multiplier *= 0.85
        elif goodwill <= -25:
            multiplier *= 1.20

    return max(0.50, multiplier)
