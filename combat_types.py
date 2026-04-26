from typing import Dict, List

from ui import info, success, warning


CLASS_DAMAGE_TYPES: Dict[str, str] = {
    "Warrior": "Physical",
    "Rogue": "Physical",
    "Mage": "Magic",
    "Cleric": "Holy",
}


ENEMY_TYPE_RULES: Dict[str, Dict[str, object]] = {
    "Beasts": {
        "weak_to": ["Physical"],
        "resists": [],
        "description": "Living monsters. Vulnerable to direct physical force.",
    },
    "Bandits": {
        "weak_to": ["Physical"],
        "resists": ["Holy"],
        "description": "Human enemies. Vulnerable to martial pressure; less affected by holy rites.",
    },
    "Undead": {
        "weak_to": ["Holy"],
        "resists": ["Physical"],
        "description": "Dead things. Holy power is effective; physical attacks are less reliable.",
    },
    "Spirits": {
        "weak_to": ["Magic", "Holy"],
        "resists": ["Physical"],
        "description": "Incorporeal enemies. Physical attacks struggle; magic and holy power work well.",
    },
    "Demons": {
        "weak_to": ["Holy"],
        "resists": ["Magic"],
        "description": "Corrupt outsiders. Holy power is strong; raw magic is resisted.",
    },
    "Dragons": {
        "weak_to": ["Magic"],
        "resists": ["Physical"],
        "description": "Ancient monsters. Physical attacks struggle against scales; magic is effective.",
    },
}


def damage_type_for_hero(hero) -> str:
    return CLASS_DAMAGE_TYPES.get(hero.hero_class, "Physical")


def enemy_rules(enemy_type: str) -> Dict[str, object]:
    return ENEMY_TYPE_RULES.get(
        enemy_type,
        {
            "weak_to": [],
            "resists": [],
            "description": "Unknown enemy type.",
        },
    )


def hero_matchup_multiplier(hero, enemy_type: str) -> float:
    damage_type = damage_type_for_hero(hero)
    rules = enemy_rules(enemy_type)

    multiplier = 1.0

    if damage_type in rules.get("weak_to", []):
        multiplier *= 1.25

    if damage_type in rules.get("resists", []):
        multiplier *= 0.75

    for item in hero.equipment.values():
        multiplier *= 1.0 + item.damage_type_bonus.get(damage_type, 0.0)
        multiplier *= 1.0 + item.enemy_type_bonus.get(enemy_type, 0.0)

    return multiplier


def incoming_damage_multiplier(hero, enemy_type: str) -> float:
    multiplier = 1.0

    for item in hero.equipment.values():
        multiplier *= 1.0 - item.enemy_type_resistance.get(enemy_type, 0.0)

    return max(0.35, multiplier)


def effective_power_against_enemy(hero, enemy_type: str, base_power: int) -> int:
    return max(1, int(base_power * hero_matchup_multiplier(hero, enemy_type)))


def item_matches_enemy_type(item, enemy_type: str) -> bool:
    if enemy_type in getattr(item, "enemy_affinity", []):
        return True

    if enemy_type in getattr(item, "enemy_type_bonus", {}):
        return True

    if enemy_type in getattr(item, "enemy_type_resistance", {}):
        return True

    rules = enemy_rules(enemy_type)
    for damage_type in item.damage_type_bonus.keys():
        if damage_type in rules.get("weak_to", []):
            return True

    return False


def party_matchup_summary(party, enemy_type: str) -> List[str]:
    lines = []
    rules = enemy_rules(enemy_type)

    lines.append(info(f"Enemy Type: {enemy_type} - {rules.get('description', '')}"))

    weak_to = rules.get("weak_to", [])
    resists = rules.get("resists", [])

    if weak_to:
        lines.append(success(f"Weak to: {', '.join(weak_to)}"))

    if resists:
        lines.append(warning(f"Resists: {', '.join(resists)}"))

    for hero in party:
        damage_type = damage_type_for_hero(hero)
        multiplier = hero_matchup_multiplier(hero, enemy_type)
        defense = incoming_damage_multiplier(hero, enemy_type)

        if multiplier > 1.05:
            lines.append(success(f"{hero.name}: {damage_type} damage is effective (x{multiplier:.2f})."))
        elif multiplier < 0.95:
            lines.append(warning(f"{hero.name}: {damage_type} damage is resisted (x{multiplier:.2f})."))
        else:
            lines.append(info(f"{hero.name}: {damage_type} damage is neutral (x{multiplier:.2f})."))

        if defense < 0.95:
            lines.append(success(f"{hero.name}: gear reduces incoming {enemy_type} damage (x{defense:.2f})."))

    return lines
