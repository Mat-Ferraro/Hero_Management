import random
from typing import Dict, List

from ui import highlight, info, success, warning


SPECIALTIES_BY_CLASS: Dict[str, List[str]] = {
    "Warrior": ["Guardian", "Weapon Master", "Vanguard"],
    "Rogue": ["Treasure Hunter", "Scout", "Boss Killer"],
    "Cleric": ["Life Cleric", "Grave Cleric", "War Cleric"],
    "Mage": ["Seer", "Evoker", "Scholar"],
}


SPECIALTY_DESCRIPTIONS: Dict[str, str] = {
    "Guardian": "May prevent lethal damage to an ally.",
    "Weapon Master": "Future: can equip extra weapon. Currently gains small combat bonus.",
    "Vanguard": "Reduces party damage in the first room.",
    "Treasure Hunter": "Increases gold found in treasure rooms.",
    "Scout": "Future: improves room information. Currently improves retreat/control flavor only.",
    "Boss Killer": "Gains extra combat power in boss rooms.",
    "Life Cleric": "Heals the party after each room.",
    "Grave Cleric": "May prevent a hero death once per expedition.",
    "War Cleric": "Reduces chance of wounds after combat.",
    "Seer": "Improves item discovery chance.",
    "Evoker": "Gains extra combat power in monster rooms.",
    "Scholar": "Increases combat XP earned by the party.",
}


def random_specialty_for_class(hero_class: str) -> str:
    options = SPECIALTIES_BY_CLASS.get(hero_class, [])
    if not options:
        return "Adventurer"
    return random.choice(options)


def specialty_description(specialty: str) -> str:
    return SPECIALTY_DESCRIPTIONS.get(specialty, "No specialty description yet.")


def count_specialty(party, specialty: str) -> int:
    return sum(1 for hero in party if getattr(hero, "specialty", "") == specialty)


def has_specialty(party, specialty: str) -> bool:
    return count_specialty(party, specialty) > 0


def specialty_combat_power_bonus(hero, room_type: str) -> int:
    specialty = getattr(hero, "specialty", "")

    if specialty == "Boss Killer" and room_type == "Boss":
        return max(5, int(hero.combat_power() * 0.25))

    if specialty == "Evoker" and room_type == "Monster":
        return max(4, int(hero.combat_power() * 0.20))

    if specialty == "Weapon Master":
        return max(2, int(hero.combat_power() * 0.08))

    return 0


def effective_party_power_for_room(party, room_type: str) -> int:
    total = 0
    for hero in party:
        total += hero.combat_power()
        total += specialty_combat_power_bonus(hero, room_type)
    return total


def treasure_gold_multiplier(party) -> float:
    treasure_hunters = count_specialty(party, "Treasure Hunter")
    return 1.0 + (0.20 * treasure_hunters)


def xp_multiplier(party) -> float:
    scholars = count_specialty(party, "Scholar")
    return 1.0 + (0.15 * scholars)


def item_drop_bonus(party) -> float:
    seers = count_specialty(party, "Seer")
    return 0.15 * seers


def wound_chance_multiplier(party) -> float:
    war_clerics = count_specialty(party, "War Cleric")
    return max(0.55, 1.0 - (0.20 * war_clerics))


def first_room_damage_multiplier(party, room_number: int) -> float:
    if room_number != 1:
        return 1.0

    vanguards = count_specialty(party, "Vanguard")
    return max(0.60, 1.0 - (0.15 * vanguards))


def apply_life_cleric_healing(party) -> List[str]:
    messages = []
    life_clerics = count_specialty(party, "Life Cleric")

    if life_clerics <= 0:
        return messages

    heal_amount = 6 * life_clerics
    messages.append(success(f"Life Cleric passive restores {heal_amount} HP to the party."))

    for hero in party:
        if hero.current_health is not None and hero.current_health > 0:
            messages.append(success(hero.heal(heal_amount)))

    return messages


def try_grave_cleric_save(party, dying_hero) -> List[str]:
    messages = []

    grave_clerics = [
        hero for hero in party
        if getattr(hero, "specialty", "") == "Grave Cleric"
        and hero is not dying_hero
        and getattr(hero, "current_health", 0) > 0
    ]

    if not grave_clerics:
        return messages

    # First pass: 35% save chance per available Grave Cleric, capped.
    save_chance = min(0.80, 0.35 * len(grave_clerics))

    if random.random() <= save_chance:
        dying_hero.current_health = max(1, int(dying_hero.max_health() * 0.15))
        messages.append(highlight(
            f"Grave Cleric intervention saves {dying_hero.name} from death "
            f"({dying_hero.current_health}/{dying_hero.max_health()} HP)."
        ))

    return messages


def describe_party_specialties(party) -> List[str]:
    messages = []

    active = []
    for hero in party:
        specialty = getattr(hero, "specialty", "")
        if specialty:
            active.append(f"{hero.name}: {specialty}")

    if active:
        messages.append(info("Active party specialties: " + "; ".join(active)))

    return messages
