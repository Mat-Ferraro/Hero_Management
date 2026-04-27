from typing import Iterable, List

from models import Dungeon, Hero, Item
from ui import Color, bold, color_text, pad_col


def separator_for(columns: List[str]) -> str:
    return "-" * len(" | ".join(columns))


def print_table(header_columns: List[str], rows: Iterable[str]) -> None:
    print(bold(" | ".join(header_columns)))
    print(separator_for(header_columns))

    for row in rows:
        print(row)


def numbered_prefix(index: int) -> str:
    return pad_col(f"{index}.", 4)


def hero_header_columns(include_money: bool = False) -> List[str]:
    columns = [
        pad_col("#", 4),
        pad_col("Name", 18),
        pad_col("Class", 8),
        pad_col("Specialty", 16),
        pad_col("Damage", 8),
        pad_col("Growth", 9),
        pad_col("Terms", 10),
        pad_col("Age", 3, align="right"),
        pad_col("Lv", 5),
        pad_col("Pwr", 5, align="right"),
        pad_col("HP", 9, align="right"),
        pad_col("Status", 17),
        pad_col("Ct", 4, align="right"),
        pad_col("Wage", 12, align="right"),
    ]

    if include_money:
        columns.extend(
            [
                pad_col("Signing", 14, align="right"),
                pad_col("Total", 15, align="right"),
            ]
        )

    return columns


def hero_row(index: int, hero: Hero, include_money: bool = False) -> str:
    return f"{numbered_prefix(index)} | {hero.display_short(include_money=include_money)}"


def print_hero_table(heroes: List[Hero], include_money: bool = False) -> None:
    print_table(
        hero_header_columns(include_money=include_money),
        [hero_row(index, hero, include_money=include_money) for index, hero in enumerate(heroes, start=1)],
    )


def rarity_color(rarity: str) -> str:
    return {
        "Common": Color.WHITE,
        "Uncommon": Color.GREEN,
        "Rare": Color.CYAN,
        "Epic": Color.MAGENTA,
        "Legendary": Color.RED,
    }.get(rarity, Color.WHITE)


def inventory_header_columns() -> List[str]:
    return [
        pad_col("#", 4),
        pad_col("Item", 24),
        pad_col("Rarity", 10),
        pad_col("Slot", 10),
        pad_col("Stats", 24),
        pad_col("Damage Bonus", 24),
        pad_col("Enemy Bonus", 24),
        pad_col("Resist", 24),
        pad_col("Classes", 18),
        pad_col("Value", 8, align="right"),
    ]


def format_stat_bonuses(item: Item) -> str:
    if not item.stat_bonuses:
        return "-"
    return ", ".join(f"+{value} {stat}" for stat, value in item.stat_bonuses.items())


def format_percent_map(values: dict, suffix: str = "") -> str:
    if not values:
        return "-"

    parts = []
    for name, value in values.items():
        percent = int(value * 100)
        if suffix:
            parts.append(f"+{percent}% {suffix} {name}")
        else:
            parts.append(f"+{percent}% {name}")

    return ", ".join(parts)


def format_resistance_map(values: dict) -> str:
    if not values:
        return "-"

    return ", ".join(f"-{int(value * 100)}% {enemy}" for enemy, value in values.items())


def inventory_row(index: int, item: Item) -> str:
    rarity = getattr(item, "rarity", "Common")
    classes = ", ".join(item.class_restrictions) if item.class_restrictions else "Any"

    return " | ".join(
        [
            numbered_prefix(index),
            pad_col(item.name, 24),
            pad_col(rarity, 10, rarity_color(rarity)),
            pad_col(item.slot, 10),
            pad_col(format_stat_bonuses(item), 24),
            pad_col(format_percent_map(item.damage_type_bonus), 24),
            pad_col(format_percent_map(item.enemy_type_bonus, "vs"), 24),
            pad_col(format_resistance_map(item.enemy_type_resistance), 24),
            pad_col(classes, 18),
            pad_col(f"{item.value}g", 8, Color.GREEN if item.value < 150 else Color.YELLOW if item.value < 300 else Color.RED, align="right"),
        ]
    )


def print_inventory_table(items: List[Item]) -> None:
    print_table(
        inventory_header_columns(),
        [inventory_row(index, item) for index, item in enumerate(items, start=1)],
    )


def enemy_type_color(enemy_type: str) -> str:
    return {
        "Beasts": Color.GREEN,
        "Bandits": Color.YELLOW,
        "Undead": Color.CYAN,
        "Spirits": Color.MAGENTA,
        "Demons": Color.RED,
        "Dragons": Color.RED,
    }.get(enemy_type, Color.WHITE)


def difficulty_color(difficulty: int) -> str:
    if difficulty >= 5:
        return Color.RED
    if difficulty >= 3:
        return Color.YELLOW
    return Color.GREEN


def dungeon_header_columns() -> List[str]:
    return [
        pad_col("#", 4),
        pad_col("Dungeon", 28),
        pad_col("Enemy", 10),
        pad_col("Diff", 4, align="right"),
        pad_col("Years", 5, align="right"),
        pad_col("Rooms", 5, align="right"),
        pad_col("Enemy Pwr", 9, align="right"),
        pad_col("Loot", 15),
        pad_col("XP", 6, align="right"),
        pad_col("Debt Req", 10, align="right"),
        pad_col("Full Wages", 12, align="right"),
    ]


def dungeon_row(index: int, dungeon: Dungeon, total_debt: int = 0, wage_per_year: int = 0) -> str:
    projected_wages = wage_per_year * dungeon.room_count
    difficulty = getattr(dungeon, "difficulty", 1)
    enemy_type = getattr(dungeon, "enemy_type", "Unknown")

    return " | ".join(
        [
            numbered_prefix(index),
            pad_col(dungeon.name, 28),
            pad_col(enemy_type, 10, enemy_type_color(enemy_type)),
            pad_col(difficulty, 4, difficulty_color(difficulty), align="right"),
            pad_col(f"{dungeon.years_to_complete}y", 5, align="right"),
            pad_col(dungeon.room_count, 5, align="right"),
            pad_col(dungeon.enemy_power, 9, align="right"),
            pad_col(f"{dungeon.loot_min}-{dungeon.loot_max}g", 15),
            pad_col(dungeon.xp_reward, 6, align="right"),
            pad_col(f"{total_debt}g", 10, Color.RED if total_debt > 0 else Color.GREEN, align="right"),
            pad_col(f"{projected_wages}g", 12, Color.RED if projected_wages >= 300 else Color.YELLOW if projected_wages >= 150 else Color.GREEN, align="right"),
        ]
    )


def print_dungeon_table(dungeons: List[Dungeon], total_debt: int = 0, wage_per_year: int = 0) -> None:
    print_table(
        dungeon_header_columns(),
        [dungeon_row(index, dungeon, total_debt=total_debt, wage_per_year=wage_per_year) for index, dungeon in enumerate(dungeons, start=1)],
    )


def compact_legacy_hero_header_columns(label: str) -> List[str]:
    return [
        pad_col("#", 4),
        pad_col("Name", 18),
        pad_col("Class", 8),
        pad_col(label, 12),
        pad_col("Age", 4, align="right"),
        pad_col("Lv", 5),
        pad_col("Growth", 9),
        pad_col("Power", 5, align="right"),
    ]


def compact_legacy_hero_row(index: int, hero: Hero, label: str) -> str:
    class_col = {
        "Warrior": Color.RED,
        "Rogue": Color.GREEN,
        "Cleric": Color.CYAN,
        "Mage": Color.MAGENTA,
    }.get(hero.hero_class, Color.WHITE)

    growth_col = {
        "Mundane": Color.DIM,
        "Talented": Color.WHITE,
        "Gifted": Color.GREEN,
        "Heroic": Color.CYAN,
        "Legendary": Color.MAGENTA,
        "Mythic": Color.RED,
    }.get(getattr(hero, "growth_rate", "Talented"), Color.WHITE)

    return " | ".join(
        [
            numbered_prefix(index),
            pad_col(hero.name, 18),
            pad_col(hero.hero_class, 8, class_col),
            pad_col(label, 12),
            pad_col(hero.age, 4, align="right"),
            pad_col(f"Lv {hero.level}", 5),
            pad_col(getattr(hero, "growth_rate", "Talented"), 9, growth_col),
            pad_col(hero.combat_power(), 5, align="right"),
        ]
    )


def print_compact_legacy_hero_table(heroes: List[Hero], label: str) -> None:
    print_table(
        compact_legacy_hero_header_columns(label),
        [compact_legacy_hero_row(index, hero, label) for index, hero in enumerate(heroes, start=1)],
    )
