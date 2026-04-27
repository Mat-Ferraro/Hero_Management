import random
from typing import Dict, List, Set

from contract_attitudes import attitude_multiplier, random_contract_attitude
from data_loader import load_hero_generation_rules, load_hero_names
from growth_rates import random_growth_rate
from hero_specialties import random_specialty_for_class
from models import Hero


def weighted_choice(weight_map: Dict[str, int]) -> str:
    total = sum(int(weight) for weight in weight_map.values())
    roll = random.randint(1, total)
    running = 0

    for value, weight in weight_map.items():
        running += int(weight)
        if roll <= running:
            return value

    return next(iter(weight_map))


def generate_name(existing_names: Set[str]) -> str:
    names = load_hero_names()
    first_names = names.get("first_names", ["Nameless"])
    titles = names.get("titles", ["Adventurer"])

    for _ in range(100):
        name = f"{random.choice(first_names)} {random.choice(titles)}"
        if name not in existing_names:
            return name

    return f"{random.choice(first_names)} {random.choice(titles)} {random.randint(100, 999)}"


def scale_stats_for_level(stats: Dict[str, int], level: int, hero_class: str) -> Dict[str, int]:
    if level <= 1:
        return stats

    primary_stats = {
        "Warrior": ["might"],
        "Rogue": ["agility"],
        "Cleric": ["spirit"],
        "Mage": ["mind"],
    }.get(hero_class, [])

    scaled = dict(stats)

    for _ in range(level - 1):
        for stat in primary_stats:
            scaled[stat] = scaled.get(stat, 0) + 2

        random_stat = random.choice(["might", "agility", "mind", "spirit"])
        scaled[random_stat] = scaled.get(random_stat, 0) + 1

    return scaled


def base_combat_power(hero_class: str, level: int, stats: Dict[str, int]) -> int:
    primary = {
        "Warrior": ["might"],
        "Rogue": ["agility"],
        "Cleric": ["spirit"],
        "Mage": ["mind"],
    }.get(hero_class, [])

    secondary = {
        "Warrior": ["spirit"],
        "Rogue": ["might"],
        "Cleric": ["mind"],
        "Mage": ["spirit"],
    }.get(hero_class, [])

    primary_power = sum(stats.get(stat, 0) * 3 for stat in primary)
    secondary_power = sum(stats.get(stat, 0) * 2 for stat in secondary)
    general_power = sum(stats.values())
    return max(1, primary_power + secondary_power + general_power + level * 5)


def calculate_contract_values(
    hero_class: str,
    age: int,
    level: int,
    stats: Dict[str, int],
    contract_attitude: str,
    reputation,
    injured: bool = False,
) -> tuple[int, int]:
    rules = load_hero_generation_rules()
    pricing = rules.get("pricing", {})

    power = base_combat_power(hero_class, level, stats)

    signing = pricing.get("signing_base", 25)
    signing += power * pricing.get("signing_power_multiplier", 2.2)
    signing += level * pricing.get("signing_level_multiplier", 35)

    wage = pricing.get("wage_base", 6)
    wage += power * pricing.get("wage_power_multiplier", 0.35)
    wage += level * pricing.get("wage_level_multiplier", 5)

    if age <= pricing.get("young_premium_age", 24):
        signing *= pricing.get("young_premium", 1.10)
        wage *= pricing.get("young_premium", 1.10)

    if age >= pricing.get("old_discount_age", 55):
        signing *= pricing.get("old_discount", 0.80)
        wage *= pricing.get("old_discount", 0.80)

    if injured:
        signing *= pricing.get("injury_discount", 0.70)
        wage *= pricing.get("injury_discount", 0.70)

    signing *= attitude_multiplier(contract_attitude, "signing_bonus", reputation)
    wage *= attitude_multiplier(contract_attitude, "wage", reputation)

    return max(1, int(signing)), max(1, int(wage))


def apply_reputation_to_contract(hero: Hero, reputation) -> None:
    def reputation_multiplier(score: int, positive_discount: float, negative_markup: float) -> float:
        if score > 0:
            return max(0.70, 1.0 - ((score / 100.0) * positive_discount))

        if score < 0:
            return min(1.75, 1.0 + ((abs(score) / 100.0) * negative_markup))

        return 1.0

    class_key = hero.hero_class.lower()
    class_score = getattr(reputation, class_key, 0)

    wage_multiplier = 1.0
    signing_multiplier = 1.0

    wage_multiplier *= reputation_multiplier(reputation.reliability, positive_discount=0.15, negative_markup=0.45)
    wage_multiplier *= reputation_multiplier(class_score, positive_discount=0.12, negative_markup=0.25)

    signing_multiplier *= reputation_multiplier(reputation.safety, positive_discount=0.10, negative_markup=0.35)
    signing_multiplier *= reputation_multiplier(reputation.overall, positive_discount=0.08, negative_markup=0.20)
    signing_multiplier *= reputation_multiplier(class_score, positive_discount=0.10, negative_markup=0.20)

    hero.wage_per_year = max(1, int(hero.wage_per_year * wage_multiplier))
    hero.signing_bonus = max(1, int(hero.signing_bonus * signing_multiplier))


def generate_hero(existing_names: Set[str], reputation) -> Hero:
    rules = load_hero_generation_rules()
    class_name = random.choice(list(rules["classes"].keys()))
    class_rules = rules["classes"][class_name]

    age = random.randint(class_rules["age_min"], class_rules["age_max"])
    level = int(weighted_choice(class_rules.get("level_weights", {"1": 1})))

    stats = {}
    for stat, stat_range in class_rules["stat_ranges"].items():
        stats[stat] = random.randint(int(stat_range[0]), int(stat_range[1]))

    stats = scale_stats_for_level(stats, level, class_name)

    contract_attitude = random_contract_attitude()
    signing_bonus, wage_per_year = calculate_contract_values(
        hero_class=class_name,
        age=age,
        level=level,
        stats=stats,
        contract_attitude=contract_attitude,
        reputation=reputation,
    )

    contract_rules = rules.get("contract_years", {"min": 2, "max": 7})
    contract_years = random.randint(int(contract_rules["min"]), int(contract_rules["max"]))

    hero = Hero(
        name=generate_name(existing_names),
        hero_class=class_name,
        age=age,
        level=level,
        xp=0,
        stats=stats,
        signing_bonus=signing_bonus,
        wage_per_year=wage_per_year,
        contract_years=contract_years,
        specialty=random_specialty_for_class(class_name),
        growth_rate=random_growth_rate(),
        contract_attitude=contract_attitude,
    )

    apply_reputation_to_contract(hero, reputation)
    return hero


def generate_contract_market(state, count: int | None = None) -> List[Hero]:
    rules = load_hero_generation_rules()
    market_size = count or int(rules.get("market_size", 8))

    existing_names = {
        hero.name for hero in state.roster
    } | {
        hero.name for hero in state.available_contracts
    } | {
        hero.name for hero in state.retired_heroes
    } | {
        hero.name for hero in state.fallen_heroes
    }

    generated = []
    while len(generated) < market_size:
        hero = generate_hero(existing_names, state.reputation)
        existing_names.add(hero.name)
        generated.append(hero)

    return generated
