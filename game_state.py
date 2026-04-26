import random
from dataclasses import dataclass, field
from typing import List

from models import Dungeon, Hero, Item


@dataclass
class GameState:
    expedition: int
    year: int
    gold: int
    roster: List[Hero]
    available_contracts: List[Hero]
    inventory: List[Item]
    dungeons: List[Dungeon]
    retired_heroes: List[Hero] = field(default_factory=list)
    fallen_heroes: List[Hero] = field(default_factory=list)


def create_hero(
    name: str,
    hero_class: str,
    age: int,
    stats: dict,
    signing_bonus: int,
    wage_per_year: int,
    contract_years: int,
) -> Hero:
    return Hero(
        name=name,
        hero_class=hero_class,
        age=age,
        level=1,
        xp=0,
        stats=stats,
        signing_bonus=signing_bonus,
        wage_per_year=wage_per_year,
        contract_years=contract_years,
    )


def create_initial_contracts() -> List[Hero]:
    return [
        create_hero("Brakka Ironjaw", "Warrior", 26, {"might": 8, "agility": 4, "mind": 2, "spirit": 5}, 80, 18, 6),
        create_hero("Old Garron", "Warrior", 44, {"might": 10, "agility": 3, "mind": 3, "spirit": 7}, 45, 12, 5),
        create_hero("Sil Tanglefoot", "Rogue", 22, {"might": 4, "agility": 9, "mind": 4, "spirit": 3}, 75, 17, 6),
        create_hero("Vera Quickhand", "Rogue", 35, {"might": 5, "agility": 10, "mind": 5, "spirit": 4}, 100, 22, 5),
        create_hero("Sister Maela", "Cleric", 39, {"might": 3, "agility": 3, "mind": 7, "spirit": 9}, 95, 20, 7),
        create_hero("Brother Tor", "Cleric", 58, {"might": 3, "agility": 2, "mind": 9, "spirit": 11}, 120, 28, 4),
        create_hero("Nim the Unready", "Mage", 19, {"might": 1, "agility": 3, "mind": 8, "spirit": 5}, 60, 15, 8),
        create_hero("Archmage Pell", "Mage", 72, {"might": 1, "agility": 2, "mind": 14, "spirit": 10}, 160, 40, 4),
    ]


def create_dungeons() -> List[Dungeon]:
    return [
        Dungeon("Goblin Toll Caves", 1, 1, 2, 45, 90, 170, 55, 0.07, 0.015, 0.005, 0.25),
        Dungeon("Crypt of Wet Bones", 2, 2, 3, 80, 180, 330, 90, 0.11, 0.035, 0.012, 0.35),
        Dungeon("Bandit King's Vault", 3, 3, 4, 125, 330, 560, 145, 0.15, 0.06, 0.025, 0.45),
        Dungeon("Ash Dragon Hatchery", 4, 5, 5, 185, 650, 1050, 240, 0.20, 0.09, 0.045, 0.60),
    ]


def create_item_pool() -> List[Item]:
    return [
        Item("Rusty Longsword", "weapon", {"might": 2}, 60),
        Item("Knight's Axe", "weapon", {"might": 4}, 150),
        Item("Balanced Dagger", "weapon", {"agility": 3}, 100),
        Item("Shadow Bow", "weapon", {"agility": 5}, 220),
        Item("Apprentice Wand", "weapon", {"mind": 3}, 110),
        Item("Elder Staff", "weapon", {"mind": 5, "spirit": 2}, 300),
        Item("Blessed Charm", "trinket", {"spirit": 3}, 120),
        Item("War Banner", "trinket", {"might": 1, "spirit": 2}, 140),
        Item("Quickstep Boots", "boots", {"agility": 2}, 75),
        Item("Scholar's Ring", "trinket", {"mind": 2}, 90),
    ]


def create_game() -> GameState:
    return GameState(
        expedition=1,
        year=1,
        gold=500,
        roster=[],
        available_contracts=create_initial_contracts(),
        inventory=[],
        dungeons=create_dungeons(),
    )


def refresh_contract_market(state: GameState) -> None:
    target_contract_count = 6
    names = [hero.name for hero in state.available_contracts] + [hero.name for hero in state.roster]
    possible_new_heroes = create_initial_contracts()
    random.shuffle(possible_new_heroes)

    for hero in possible_new_heroes:
        if len(state.available_contracts) >= target_contract_count:
            break

        if hero.name not in names:
            hero.signing_bonus = int(hero.signing_bonus * random.uniform(0.9, 1.2))
            hero.wage_per_year = max(1, int(hero.wage_per_year * random.uniform(0.9, 1.2)))
            state.available_contracts.append(hero)
            names.append(hero.name)
