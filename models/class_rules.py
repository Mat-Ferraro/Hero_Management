STAT_NAMES = ["might", "agility", "mind", "spirit"]


CLASS_RULES = {
    "Warrior": {
        "primary_stats": ["might"],
        "secondary_stats": ["spirit"],
        "young_until": 28,
        "prime_until": 40,
        "retirement_age": 52,
        "old_decline_stat": "might",
        "description": "Strong physical fighter. Peaks early and can decline after 40.",
    },
    "Rogue": {
        "primary_stats": ["agility"],
        "secondary_stats": ["might"],
        "young_until": 30,
        "prime_until": 42,
        "retirement_age": 55,
        "old_decline_stat": "agility",
        "description": "Fast damage dealer. Strong early growth and moderate late decline.",
    },
    "Cleric": {
        "primary_stats": ["spirit"],
        "secondary_stats": ["mind"],
        "young_until": 35,
        "prime_until": 55,
        "retirement_age": 70,
        "old_decline_stat": None,
        "description": "Reliable support class. Improves steadily for a long time.",
    },
    "Mage": {
        "primary_stats": ["mind"],
        "secondary_stats": ["spirit"],
        "young_until": 45,
        "prime_until": 90,
        "retirement_age": 88,
        "old_decline_stat": None,
        "description": "Weak physically but scales with knowledge. Can keep improving with age.",
    },
}
