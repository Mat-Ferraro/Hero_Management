import json
from pathlib import Path
from typing import List

from hero_specialties import random_specialty_for_class
from models import Dungeon, Hero, Item


DATA_DIR = Path("data")
HEROES_PATH = DATA_DIR / "heroes.json"
DUNGEONS_PATH = DATA_DIR / "dungeons.json"
ITEMS_PATH = DATA_DIR / "items.json"


def load_json_file(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Required data file not found: {path}")

    with path.open("r", encoding="utf-8") as data_file:
        return json.load(data_file)


def hero_from_data(data: dict) -> Hero:
    hero_class = data["hero_class"]

    return Hero(
        name=data["name"],
        hero_class=hero_class,
        age=int(data["age"]),
        level=int(data.get("level", 1)),
        xp=int(data.get("xp", 0)),
        stats=dict(data["stats"]),
        signing_bonus=int(data["signing_bonus"]),
        wage_per_year=int(data["wage_per_year"]),
        contract_years=int(data["contract_years"]),
        specialty=data.get("specialty") or random_specialty_for_class(hero_class),
    )


def item_from_data(data: dict) -> Item:
    return Item(
        name=data["name"],
        slot=data["slot"],
        stat_bonuses=dict(data.get("stat_bonuses", {})),
        value=int(data["value"]),
        rarity=data.get("rarity", "Common"),
        damage_type_bonus=dict(data.get("damage_type_bonus", {})),
        enemy_type_bonus=dict(data.get("enemy_type_bonus", {})),
        enemy_type_resistance=dict(data.get("enemy_type_resistance", {})),
        class_restrictions=list(data.get("class_restrictions", [])),
        enemy_affinity=list(data.get("enemy_affinity", [])),
    )


def dungeon_from_data(data: dict) -> Dungeon:
    return Dungeon(
        name=data["name"],
        difficulty=int(data["difficulty"]),
        years_to_complete=int(data["years_to_complete"]),
        stages=int(data.get("stages", data["years_to_complete"])),
        enemy_power=int(data["enemy_power"]),
        loot_min=int(data["loot_min"]),
        loot_max=int(data["loot_max"]),
        xp_reward=int(data["xp_reward"]),
        minor_wound_chance=float(data["minor_wound_chance"]),
        mortal_wound_chance=float(data["mortal_wound_chance"]),
        death_chance=float(data["death_chance"]),
        item_drop_chance=float(data["item_drop_chance"]),
        enemy_type=data.get("enemy_type", "Beasts"),
    )


def load_heroes() -> List[Hero]:
    return [hero_from_data(hero_data) for hero_data in load_json_file(HEROES_PATH)]


def load_items() -> List[Item]:
    return [item_from_data(item_data) for item_data in load_json_file(ITEMS_PATH)]


def load_dungeons() -> List[Dungeon]:
    return [dungeon_from_data(dungeon_data) for dungeon_data in load_json_file(DUNGEONS_PATH)]
