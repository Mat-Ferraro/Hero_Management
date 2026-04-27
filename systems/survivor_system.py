import random
from typing import List

from game_state import GameState
from hero_specialties import apply_life_cleric_healing, random_specialty_for_class
from manager_reputation import reputation_for_survivor_rescued
from models import Dungeon, Hero
from .room_resolution import RoomResolution
from ui import highlight, info, success


def create_survivor(dungeon: Dungeon) -> Hero:
    survivor_class = random.choice(["Warrior", "Rogue", "Cleric", "Mage"])
    name_prefix = random.choice(["Lost", "Wounded", "Stranded", "Cornered", "Desperate"])
    name_suffix = random.choice(["Adventurer", "Mercenary", "Acolyte", "Delver", "Scout"])

    base_stat = 3 + dungeon.difficulty
    stats = {
        "might": random.randint(2, base_stat + 3),
        "agility": random.randint(2, base_stat + 3),
        "mind": random.randint(2, base_stat + 3),
        "spirit": random.randint(2, base_stat + 3),
    }

    if survivor_class == "Warrior":
        stats["might"] += 3
        stats["spirit"] += 1
    elif survivor_class == "Rogue":
        stats["agility"] += 3
        stats["might"] += 1
    elif survivor_class == "Cleric":
        stats["spirit"] += 3
        stats["mind"] += 1
    elif survivor_class == "Mage":
        stats["mind"] += 3
        stats["spirit"] += 1

    survivor = Hero(
        name=f"{name_prefix} {name_suffix}",
        hero_class=survivor_class,
        age=random.randint(18, 55),
        level=max(1, dungeon.difficulty),
        xp=0,
        stats=stats,
        signing_bonus=0,
        wage_per_year=0,
        contract_years=0,
        specialty=random_specialty_for_class(survivor_class),
        is_temporary_survivor=True,
    )
    survivor.reset_health_for_expedition()

    missing_health = random.randint(5, max(10, survivor.max_health() // 3))
    survivor.current_health = max(1, survivor.max_health() - missing_health)

    return survivor

def resolve_survivor_room(party: List[Hero], dungeon: Dungeon) -> RoomResolution:
    survivor = create_survivor(dungeon)
    party.append(survivor)

    messages = [
        highlight("The party finds a stranded survivor hiding among the ruins."),
        success(f"{survivor.name}, a {survivor.hero_class} {survivor.specialty}, joins for the rest of the dungeon."),
        info(f"{survivor.name} requires no wages and will leave after the expedition."),
        info(f"Survivor Status: {survivor.display_short()}"),
    ]

    messages.extend(apply_life_cleric_healing(party))
    return RoomResolution(messages=messages, loot=0, xp=0)

def remove_temporary_survivors_from_party(state: GameState, party: List[Hero]) -> List[str]:
    messages = []
    for hero in list(party):
        if hero.is_temporary_survivor:
            party.remove(hero)
            if hero.current_health and hero.current_health > 0:
                messages.append(info(f"{hero.name} parts ways with the guild after the expedition."))
                messages.extend(reputation_for_survivor_rescued(state.reputation))
    return messages

