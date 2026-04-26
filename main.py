import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ============================================================
# Hero Management Autobattler Prototype
# ------------------------------------------------------------
# v0.3:
# - Expedition-based contracts and wages
# - Dungeons take years
# - Multi-stage dungeons with continue/retreat choices
# - Minor wounds, mortal wounds, and death
# - Retired heroes and fallen heroes are tracked
# ============================================================


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


@dataclass
class Item:
    name: str
    slot: str
    stat_bonuses: Dict[str, int]
    value: int

    def display(self) -> str:
        bonuses = ", ".join(f"+{value} {stat}" for stat, value in self.stat_bonuses.items())
        return f"{self.name} [{self.slot}] ({bonuses}) - value {self.value}g"


@dataclass
class Hero:
    name: str
    hero_class: str
    age: int
    level: int
    xp: int
    stats: Dict[str, int]
    signing_bonus: int
    wage_per_expedition: int
    contract_expeditions: int
    equipment: Dict[str, Item] = field(default_factory=dict)
    injured_expeditions: int = 0
    wound_history: List[str] = field(default_factory=list)
    current_health: Optional[int] = None

    def total_stat(self, stat_name: str) -> int:
        total = self.stats.get(stat_name, 0)
        for item in self.equipment.values():
            total += item.stat_bonuses.get(stat_name, 0)
        return total

    def max_health(self) -> int:
        return 60 + (self.total_stat("might") * 4) + (self.total_stat("spirit") * 3) + (self.level * 8)

    def reset_health_for_expedition(self) -> None:
        self.current_health = self.max_health()

    def health_percent(self) -> float:
        if self.current_health is None:
            return 1.0
        return max(0.0, self.current_health / self.max_health())

    def health_status(self) -> str:
        percent = self.health_percent()
        if percent <= 0:
            return "DEAD"
        if percent < 0.25:
            return "CRITICAL"
        if percent < 0.50:
            return "WOUNDED"
        if percent < 0.75:
            return "HURT"
        return "Healthy"

    def total_contract_value(self) -> int:
        return self.signing_bonus + (self.wage_per_expedition * self.contract_expeditions)

    def combat_power(self) -> int:
        class_rules = CLASS_RULES[self.hero_class]
        primary = sum(self.total_stat(stat) * 3 for stat in class_rules["primary_stats"])
        secondary = sum(self.total_stat(stat) * 2 for stat in class_rules["secondary_stats"])
        general = sum(self.total_stat(stat) for stat in STAT_NAMES)
        injury_penalty = 0.65 if self.injured_expeditions > 0 else 1.0
        return max(1, int((primary + secondary + general + self.level * 5) * injury_penalty))

    def xp_to_next_level(self) -> int:
        return 100 + (self.level - 1) * 60

    def add_xp(self, amount: int) -> List[str]:
        messages = []
        adjusted_amount = self.adjust_xp_for_age(amount)
        self.xp += adjusted_amount
        messages.append(f"{self.name} gained {adjusted_amount} XP.")

        while self.xp >= self.xp_to_next_level():
            self.xp -= self.xp_to_next_level()
            self.level += 1
            messages.extend(self.level_up())

        return messages

    def adjust_xp_for_age(self, base_xp: int) -> int:
        rules = CLASS_RULES[self.hero_class]
        if self.age <= rules["young_until"]:
            multiplier = 1.25
        elif self.age <= rules["prime_until"]:
            multiplier = 1.0
        else:
            if self.hero_class == "Mage":
                multiplier = 1.1
            elif self.hero_class == "Cleric":
                multiplier = 0.95
            else:
                multiplier = 0.75
        return max(1, int(base_xp * multiplier))

    def level_up(self) -> List[str]:
        rules = CLASS_RULES[self.hero_class]
        messages = [f"{self.name} reached level {self.level}!"]
        for stat in rules["primary_stats"]:
            self.stats[stat] += 2
            messages.append(f"  +2 {stat}")
        for stat in rules["secondary_stats"]:
            self.stats[stat] += 1
            messages.append(f"  +1 {stat}")
        random_stat = random.choice(STAT_NAMES)
        self.stats[random_stat] += 1
        messages.append(f"  +1 {random_stat}")
        return messages

    def take_damage(self, amount: int) -> str:
        if self.current_health is None:
            self.reset_health_for_expedition()
        self.current_health = max(0, self.current_health - amount)
        return (
            f"{self.name} took {amount} damage "
            f"({self.current_health}/{self.max_health()} HP, {self.health_status()})."
        )

    def apply_minor_wound(self) -> str:
        duration = random.randint(1, 2)
        self.injured_expeditions = max(self.injured_expeditions, duration)
        wound = f"Minor wound: out for {duration} expedition(s)"
        self.wound_history.append(wound)
        return f"{self.name} suffered a minor wound and will miss {duration} expedition(s)."

    def apply_mortal_wound(self) -> str:
        stat = random.choice(STAT_NAMES)
        loss = random.randint(1, 2)
        actual_loss = min(loss, max(0, self.stats[stat] - 1))
        self.stats[stat] -= actual_loss
        self.injured_expeditions = max(self.injured_expeditions, random.randint(2, 4))
        wound = f"Mortal wound: -{actual_loss} {stat}"
        self.wound_history.append(wound)
        return f"{self.name} suffered a mortal wound: -{actual_loss} {stat}."

    def advance_after_expedition(self, years_passed: int) -> List[str]:
        messages = []
        self.contract_expeditions -= 1
        if self.injured_expeditions > 0:
            self.injured_expeditions -= 1
            if self.injured_expeditions == 0:
                messages.append(f"{self.name} has recovered from injury.")
        messages.extend(self.apply_aging(years_passed))
        return messages

    def apply_aging(self, years_passed: int) -> List[str]:
        messages = []
        old_age = self.age
        self.age += years_passed
        rules = CLASS_RULES[self.hero_class]
        decline_stat = rules["old_decline_stat"]
        messages.append(f"{self.name} aged from {old_age} to {self.age}.")

        if decline_stat and self.age > rules["prime_until"]:
            for _ in range(years_passed):
                if random.random() < 0.45 and self.stats[decline_stat] > 1:
                    self.stats[decline_stat] -= 1
                    messages.append(f"Age is catching up with {self.name}: -1 {decline_stat}.")

        if self.hero_class == "Mage" and self.age > 50:
            for _ in range(years_passed):
                if random.random() < 0.35:
                    self.stats["mind"] += 1
                    messages.append(f"{self.name}'s studies deepen with age: +1 mind.")
        return messages

    def retirement_chance(self) -> float:
        rules = CLASS_RULES[self.hero_class]
        if self.age <= rules["retirement_age"]:
            return 0.0
        years_over = self.age - rules["retirement_age"]
        return min(0.75, years_over * 0.06)

    def should_retire(self) -> bool:
        return random.random() < self.retirement_chance()

    def display_short(self) -> str:
        injury = " INJURED" if self.injured_expeditions > 0 else ""
        if self.current_health is None:
            hp_text = f"HP {self.max_health()}/{self.max_health()}"
        else:
            hp_text = f"HP {self.current_health}/{self.max_health()} {self.health_status()}"
        return (
            f"{self.name} | {self.hero_class} | Age {self.age} | Lv {self.level} | "
            f"Power {self.combat_power()} | {hp_text} | Contract {self.contract_expeditions} exp | "
            f"Wage {self.wage_per_expedition}g/exp{injury}"
        )

    def display_contract(self) -> str:
        return (
            f"{self.display_short()} | Signing {self.signing_bonus}g | "
            f"Total Value {self.total_contract_value()}g"
        )

    def display_full(self) -> str:
        stat_text = ", ".join(f"{stat}: {self.total_stat(stat)}" for stat in STAT_NAMES)
        equipped = ", ".join(f"{slot}: {item.name}" for slot, item in self.equipment.items()) or "None"
        wounds = "; ".join(self.wound_history) or "None"
        retire_chance = self.retirement_chance() * 100
        return (
            f"{self.display_short()}\n"
            f"  XP: {self.xp}/{self.xp_to_next_level()}\n"
            f"  Stats: {stat_text}\n"
            f"  Equipment: {equipped}\n"
            f"  Wounds: {wounds}\n"
            f"  Retirement Chance After Expedition: {retire_chance:.1f}%\n"
        )


@dataclass
class Dungeon:
    name: str
    difficulty: int
    years_to_complete: int
    stages: int
    enemy_power: int
    loot_min: int
    loot_max: int
    xp_reward: int
    minor_wound_chance: float
    mortal_wound_chance: float
    death_chance: float
    item_drop_chance: float

    def stage_enemy_power(self, stage_number: int) -> int:
        multiplier = 0.75 + (stage_number * 0.18)
        return int(self.enemy_power * multiplier)

    def display(self) -> str:
        return (
            f"{self.name} | Difficulty {self.difficulty} | {self.years_to_complete} year(s) | "
            f"{self.stages} stage(s) | Final Enemy Power {self.enemy_power} | "
            f"Loot {self.loot_min}-{self.loot_max}g | XP {self.xp_reward}"
        )


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


# ============================================================
# Data Creation
# ============================================================


def create_hero(name: str, hero_class: str, age: int, stats: Dict[str, int], signing_bonus: int, wage: int, contract_expeditions: int) -> Hero:
    return Hero(name, hero_class, age, 1, 0, stats, signing_bonus, wage, contract_expeditions)


def create_initial_contracts() -> List[Hero]:
    return [
        create_hero("Brakka Ironjaw", "Warrior", 26, {"might": 8, "agility": 4, "mind": 2, "spirit": 5}, 80, 18, 4),
        create_hero("Old Garron", "Warrior", 44, {"might": 10, "agility": 3, "mind": 3, "spirit": 7}, 45, 12, 3),
        create_hero("Sil Tanglefoot", "Rogue", 22, {"might": 4, "agility": 9, "mind": 4, "spirit": 3}, 75, 17, 4),
        create_hero("Vera Quickhand", "Rogue", 35, {"might": 5, "agility": 10, "mind": 5, "spirit": 4}, 100, 22, 3),
        create_hero("Sister Maela", "Cleric", 39, {"might": 3, "agility": 3, "mind": 7, "spirit": 9}, 95, 20, 4),
        create_hero("Brother Tor", "Cleric", 58, {"might": 3, "agility": 2, "mind": 9, "spirit": 11}, 120, 28, 2),
        create_hero("Nim the Unready", "Mage", 19, {"might": 1, "agility": 3, "mind": 8, "spirit": 5}, 60, 15, 5),
        create_hero("Archmage Pell", "Mage", 72, {"might": 1, "agility": 2, "mind": 14, "spirit": 10}, 160, 40, 2),
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
    return GameState(1, 1, 500, [], create_initial_contracts(), [], create_dungeons())


# ============================================================
# Battle / Economy / Rewards
# ============================================================


def estimate_success_chance(party: List[Hero], enemy_power: int) -> float:
    party_power = sum(hero.combat_power() for hero in party)
    if party_power <= 0:
        return 0.0
    return party_power / (party_power + enemy_power)


def pay_expedition_wages(state: GameState) -> List[str]:
    messages = ["=== Expedition Wages ==="]
    for hero in list(state.roster):
        if state.gold >= hero.wage_per_expedition:
            state.gold -= hero.wage_per_expedition
            messages.append(f"Paid {hero.name} {hero.wage_per_expedition}g.")
        else:
            state.roster.remove(hero)
            messages.append(f"Could not pay {hero.name}'s {hero.wage_per_expedition}g wage. {hero.name} leaves the guild.")
    return messages


def apply_stage_damage_and_casualties(
    state: GameState,
    party: List[Hero],
    dungeon: Dungeon,
    stage_success: bool,
    enemy_power: int,
) -> List[str]:
    messages = []
    risk_multiplier = 0.75 if stage_success else 1.45
    party_power = max(1, sum(hero.combat_power() for hero in party))
    danger_ratio = enemy_power / party_power

    for hero in list(party):
        base_damage = random.randint(8, 18)
        scaled_damage = int(base_damage * danger_ratio * risk_multiplier * dungeon.difficulty)
        damage = max(3, scaled_damage)
        messages.append(hero.take_damage(damage))

        if hero.current_health is not None and hero.current_health <= 0:
            party.remove(hero)
            if hero in state.roster:
                state.roster.remove(hero)
            state.fallen_heroes.append(hero)
            messages.append(f"{hero.name} died from their wounds.")
            continue

        health_risk = 1.0
        if hero.health_percent() < 0.25:
            health_risk = 3.0
        elif hero.health_percent() < 0.50:
            health_risk = 1.8

        mortal_roll = dungeon.mortal_wound_chance * risk_multiplier * health_risk
        minor_roll = dungeon.minor_wound_chance * risk_multiplier * health_risk

        roll = random.random()
        if roll < mortal_roll:
            messages.append(hero.apply_mortal_wound())
        elif roll < mortal_roll + minor_roll:
            messages.append(hero.apply_minor_wound())

    return messages


def generate_item_drop(dungeon: Dungeon) -> Item:
    item = random.choice(create_item_pool())
    if dungeon.difficulty >= 4 and random.random() < 0.35:
        return Item(f"Masterwork {item.name}", item.slot, {s: v + 2 for s, v in item.stat_bonuses.items()}, int(item.value * 2.2))
    if dungeon.difficulty >= 3 and random.random() < 0.5:
        return Item(f"Fine {item.name}", item.slot, {s: v + 1 for s, v in item.stat_bonuses.items()}, int(item.value * 1.5))
    return item


def simulate_multi_stage_dungeon(state: GameState, party: List[Hero], dungeon: Dungeon) -> List[str]:
    for hero in party:
        hero.reset_health_for_expedition()

    messages = ["=== Dungeon Expedition Begins ===", f"Dungeon: {dungeon.name}"]
    completed_stages = 0
    loot_earned = 0
    xp_earned = 0

    for stage in range(1, dungeon.stages + 1):
        if not party:
            messages.append("No heroes remain. The expedition has failed.")
            break

        enemy_power = dungeon.stage_enemy_power(stage)
        party_power = sum(hero.combat_power() for hero in party)
        success_chance = estimate_success_chance(party, enemy_power)

        print("\n" + "-" * 60)
        print(f"Stage {stage}/{dungeon.stages}: {dungeon.name}")
        print(f"Current Party Power: {party_power}")
        print(f"Stage Enemy Power: {enemy_power}")
        print(f"Estimated Stage Success Chance: {success_chance * 100:.1f}%")
        print(f"Loot Secured So Far: {loot_earned}g")
        print("Party Status:")
        for hero in party:
            print(f"  - {hero.display_short()}")

        if stage > 1:
            choice = input("Continue deeper? [y/N]: ").strip().lower()
            if choice != "y":
                messages.append(f"The party retreats after clearing {completed_stages} stage(s).")
                break

        stage_success = random.random() <= success_chance
        if stage_success:
            completed_stages += 1
            stage_loot = random.randint(dungeon.loot_min, dungeon.loot_max) // dungeon.stages
            stage_xp = max(1, dungeon.xp_reward // dungeon.stages)
            loot_earned += stage_loot
            xp_earned += stage_xp
            messages.append(f"Stage {stage} cleared. Secured {stage_loot}g and {stage_xp} XP value.")
        else:
            partial_loot = random.randint(dungeon.loot_min // 10, dungeon.loot_max // 6) // dungeon.stages
            loot_earned += partial_loot
            messages.append(f"Stage {stage} failed. The party salvaged {partial_loot}g while escaping the immediate threat.")

        messages.extend(apply_stage_damage_and_casualties(state, party, dungeon, stage_success, enemy_power))

        if not stage_success:
            choice = input("The stage was failed. Try to push onward anyway? [y/N]: ").strip().lower()
            if choice != "y":
                messages.append("The party abandons the expedition.")
                break

    state.gold += loot_earned
    messages.append(f"Total expedition loot: {loot_earned}g.")

    if completed_stages == dungeon.stages:
        messages.append("The dungeon was fully cleared!")
        if random.random() < dungeon.item_drop_chance:
            item = generate_item_drop(dungeon)
            state.inventory.append(item)
            messages.append(f"The party found an item: {item.display()}")

    for hero in party:
        messages.extend(hero.add_xp(xp_earned))
        hero.current_health = None

    return messages


def finish_expedition(state: GameState, dungeon: Dungeon) -> List[str]:
    messages = ["=== Time, Contracts, and Retirement ==="]
    state.expedition += 1
    state.year += dungeon.years_to_complete
    expired_heroes = []
    retired_heroes = []

    for hero in list(state.roster):
        messages.extend(hero.advance_after_expedition(dungeon.years_to_complete))
        if hero.should_retire():
            retired_heroes.append(hero)
        elif hero.contract_expeditions <= 0:
            expired_heroes.append(hero)

    for hero in retired_heroes:
        if hero in state.roster:
            state.roster.remove(hero)
        state.retired_heroes.append(hero)
        messages.append(f"{hero.name} retires from adventuring at age {hero.age}.")

    for hero in expired_heroes:
        if hero in state.roster:
            state.roster.remove(hero)
            messages.append(f"{hero.name}'s contract has expired. They leave the guild.")

    refresh_contract_market(state)
    return messages


# ============================================================
# Menus
# ============================================================


def print_header(state: GameState) -> None:
    print("\n" + "=" * 70)
    print(f"Hero Management Prototype | Year {state.year} | Expedition {state.expedition} | Gold: {state.gold}g")
    print("=" * 70)


def main_menu() -> None:
    print("\nMain Menu")
    print("1. View roster")
    print("2. View available contracts")
    print("3. Sign hero")
    print("4. View inventory")
    print("5. Equip item")
    print("6. Choose dungeon and raid")
    print("7. View retired heroes")
    print("8. View fallen heroes")
    print("9. View class rules")
    print("10. Quit")


def get_choice(prompt: str, minimum: int, maximum: int) -> Optional[int]:
    raw = input(prompt).strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        print("Please enter a number.")
        return None
    if value < minimum or value > maximum:
        print(f"Please enter a number from {minimum} to {maximum}.")
        return None
    return value


def view_roster(state: GameState) -> None:
    print("\n=== Roster ===")
    if not state.roster:
        print("No heroes signed yet.")
        return
    print(f"Total wage bill per expedition: {sum(hero.wage_per_expedition for hero in state.roster)}g")
    for index, hero in enumerate(state.roster, start=1):
        print(f"\n{index}. {hero.display_full()}")


def view_contracts(state: GameState) -> None:
    print("\n=== Available Contracts ===")
    if not state.available_contracts:
        print("No available contracts.")
        return
    for index, hero in enumerate(state.available_contracts, start=1):
        print(f"{index}. {hero.display_contract()}")


def sign_hero(state: GameState) -> None:
    view_contracts(state)
    if not state.available_contracts:
        return
    choice = get_choice("\nSign which hero? Enter number or blank to cancel: ", 1, len(state.available_contracts))
    if choice is None:
        return
    hero = state.available_contracts[choice - 1]
    if state.gold < hero.signing_bonus:
        print(f"Not enough gold. Need {hero.signing_bonus}g for the signing bonus.")
        return
    state.gold -= hero.signing_bonus
    state.roster.append(hero)
    state.available_contracts.pop(choice - 1)
    print(f"Signed {hero.name}. Paid {hero.signing_bonus}g. Wage: {hero.wage_per_expedition}g/expedition.")


def view_inventory(state: GameState) -> None:
    print("\n=== Inventory ===")
    if not state.inventory:
        print("No items yet.")
        return
    for index, item in enumerate(state.inventory, start=1):
        print(f"{index}. {item.display()}")


def equip_item(state: GameState) -> None:
    if not state.roster:
        print("You need heroes before equipping items.")
        return
    if not state.inventory:
        print("No items to equip.")
        return
    view_inventory(state)
    item_choice = get_choice("\nChoose item to equip or blank to cancel: ", 1, len(state.inventory))
    if item_choice is None:
        return
    item = state.inventory[item_choice - 1]
    print("\nChoose hero:")
    for index, hero in enumerate(state.roster, start=1):
        print(f"{index}. {hero.display_short()}")
    hero_choice = get_choice("Hero number or blank to cancel: ", 1, len(state.roster))
    if hero_choice is None:
        return
    hero = state.roster[hero_choice - 1]
    old_item = hero.equipment.get(item.slot)
    hero.equipment[item.slot] = item
    state.inventory.pop(item_choice - 1)
    if old_item:
        state.inventory.append(old_item)
        print(f"Equipped {item.name} to {hero.name}. Returned {old_item.name} to inventory.")
    else:
        print(f"Equipped {item.name} to {hero.name}.")


def choose_dungeon_and_raid(state: GameState) -> None:
    if not state.roster:
        print("You need to sign heroes before raiding dungeons.")
        return

    print("\nBefore each expedition, all active heroes must be paid their wage.")
    print(f"Current wage bill: {sum(hero.wage_per_expedition for hero in state.roster)}g. Current gold: {state.gold}g.")

    print("\n=== Dungeons ===")
    for index, dungeon in enumerate(state.dungeons, start=1):
        print(f"{index}. {dungeon.display()}")
    dungeon_choice = get_choice("\nChoose dungeon or blank to cancel: ", 1, len(state.dungeons))
    if dungeon_choice is None:
        return
    dungeon = state.dungeons[dungeon_choice - 1]

    print("\n".join(pay_expedition_wages(state)))
    available_heroes = [hero for hero in state.roster if hero.injured_expeditions <= 0]
    if not available_heroes:
        print("No available heroes can raid after wages/injuries are resolved.")
        return

    print("\nAvailable heroes:")
    for index, hero in enumerate(available_heroes, start=1):
        print(f"{index}. {hero.display_short()}")
    print("\nEnter up to 4 hero numbers separated by commas. Example: 1,2,3")
    raw_party = input("Party: ").strip()
    if not raw_party:
        return
    try:
        selected_indexes = [int(value.strip()) for value in raw_party.split(",") if value.strip()]
    except ValueError:
        print("Invalid party selection.")
        return
    if not selected_indexes or len(selected_indexes) > 4 or len(set(selected_indexes)) != len(selected_indexes):
        print("Party must include 1 to 4 unique heroes.")
        return
    party = []
    for index in selected_indexes:
        if index < 1 or index > len(available_heroes):
            print("Invalid hero number.")
            return
        party.append(available_heroes[index - 1])

    print("\n".join(simulate_multi_stage_dungeon(state, party, dungeon)))
    print("\n".join(finish_expedition(state, dungeon)))


def view_retired_heroes(state: GameState) -> None:
    print("\n=== Retired Heroes ===")
    if not state.retired_heroes:
        print("No retired heroes yet.")
        return
    for index, hero in enumerate(state.retired_heroes, start=1):
        print(f"{index}. {hero.name} | {hero.hero_class} | Retired Age {hero.age} | Lv {hero.level}")


def view_fallen_heroes(state: GameState) -> None:
    print("\n=== Fallen Heroes ===")
    if not state.fallen_heroes:
        print("No fallen heroes yet.")
        return
    for index, hero in enumerate(state.fallen_heroes, start=1):
        print(f"{index}. {hero.name} | {hero.hero_class} | Died Age {hero.age} | Lv {hero.level}")


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
            hero.wage_per_expedition = max(1, int(hero.wage_per_expedition * random.uniform(0.9, 1.2)))
            state.available_contracts.append(hero)
            names.append(hero.name)


def view_class_rules() -> None:
    print("\n=== Class Rules ===")
    for class_name, rules in CLASS_RULES.items():
        print(f"\n{class_name}")
        print(f"  {rules['description']}")
        print(f"  Young until: {rules['young_until']}")
        print(f"  Prime until: {rules['prime_until']}")
        print(f"  Retirement risk starts after age: {rules['retirement_age']}")
        if rules["old_decline_stat"]:
            print(f"  Declines after prime: {rules['old_decline_stat']}")
        else:
            print("  No automatic age decline in this prototype.")


def run_game() -> None:
    random.seed()
    state = create_game()
    print("Hero Management Autobattler Prototype")
    print("Recruit heroes, raid dungeons, earn loot, and build your guild.")

    while True:
        print_header(state)
        main_menu()
        choice = get_choice("Choose an action: ", 1, 10)
        if choice is None:
            continue
        if choice == 1:
            view_roster(state)
        elif choice == 2:
            view_contracts(state)
        elif choice == 3:
            sign_hero(state)
        elif choice == 4:
            view_inventory(state)
        elif choice == 5:
            equip_item(state)
        elif choice == 6:
            choose_dungeon_and_raid(state)
        elif choice == 7:
            view_retired_heroes(state)
        elif choice == 8:
            view_fallen_heroes(state)
        elif choice == 9:
            view_class_rules()
        elif choice == 10:
            print("Thanks for playing.")
            break


if __name__ == "__main__":
    run_game()
