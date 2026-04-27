import random
from typing import List

from combat_types import item_matches_enemy_type
from game_state import create_item_pool
from models import Dungeon, Hero, Item


def clone_item_with_quality(item: Item, prefix: str, stat_bonus: int, value_multiplier: float, rarity: str) -> Item:
    return Item(
        name=f"{prefix} {item.name}",
        slot=item.slot,
        stat_bonuses={stat: value + stat_bonus for stat, value in item.stat_bonuses.items()},
        value=int(item.value * value_multiplier),
        rarity=rarity,
        damage_type_bonus=dict(item.damage_type_bonus),
        enemy_type_bonus=dict(item.enemy_type_bonus),
        enemy_type_resistance=dict(item.enemy_type_resistance),
        class_restrictions=list(item.class_restrictions),
        enemy_affinity=list(item.enemy_affinity),
    )

def generate_item_drop(dungeon: Dungeon, party: List[Hero] | None = None) -> Item:
    item_pool = create_item_pool()
    weighted_pool = []

    for item in item_pool:
        weight = 3

        if item_matches_enemy_type(item, dungeon.enemy_type):
            weight += 5

        if party:
            for hero in party:
                if item.can_equip(hero.hero_class):
                    weight += 1

        weighted_pool.extend([item] * max(1, weight))

    item = random.choice(weighted_pool)

    if dungeon.difficulty >= 5 and random.random() < 0.25:
        return clone_item_with_quality(item, "Legendary", 3, 3.0, "Legendary")

    if dungeon.difficulty >= 4 and random.random() < 0.35:
        return clone_item_with_quality(item, "Masterwork", 2, 2.2, "Epic")

    if dungeon.difficulty >= 3 and random.random() < 0.5:
        return clone_item_with_quality(item, "Fine", 1, 1.5, "Rare")

    return item

