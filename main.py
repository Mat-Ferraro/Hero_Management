import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ============================================================
# Hero Management Autobattler Prototype
# ------------------------------------------------------------
# v0.2 Design Direction:
# - Time is measured in expedition cycles, not weeks.
# - Dungeons take years to complete.
# - Contracts last for a number of expeditions.
# - Heroes have an upfront signing bonus and a wage per expedition.
# - If you cannot pay a hero's expedition wage, that hero leaves.
# - Heroes age after expeditions and may retire.
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

    def total_stat(self, stat_name: str) -> int:
        total = self.stats.get(stat_name, 0)
        for item in self.equipment.values():
            total += item.stat_bonuses.get(stat_name, 0)
        return total

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
        return (
            f"{self.name} | {self.hero_class} | Age {self.age} | Lv {self.level} | "
            f"Power {self.combat_power()} | Contract {self.contract_expeditions} exp | "
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
        retire_chance = self.retirement_chance() * 100
        return (
            f"{self.display_short()}\n"
            f"  XP: {self.xp}/{self.xp_to_next_level()}\n"
            f"  Stats: {stat_text}\n"
            f"  Equipment: {equipped}\n"
            f"  Retirement Chance After Expedition: {retire_chance:.1f}%\n"
        )


@dataclass
class Dungeon:
    name: str
    difficulty: int
    years_to_complete: int
    enemy_power: int
    loot_min: int
    loot_max: int
    xp_reward: int
    injury_chance: float
    item_drop_chance: float

    def display(self) -> str:
        return (
            f"{self.name} | Difficulty {self.difficulty} | {self.years_to_complete} year(s) | "
            f"Enemy Power {self.enemy_power} | Loot {self.loot_min}-{self.loot_max}g | XP {self.xp_reward}"
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


# ============================================================
# Data Creation
# ============================================================


def create_hero(
    name: str,
    hero_class: str,
    age: int,
    stats: Dict[str, int],
    signing_bonus: int,
    wage: int,
    contract_expeditions: int,
) -> Hero:
    return Hero(
        name=name,
        hero_class=hero_class,
        age=age,
        level=1,
        xp=0,
        stats=stats,
        signing_bonus=signing_bonus,
        wage_per_expedition=wage,
        contract_expeditions=contract_expeditions,
    )


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
        Dungeon("Goblin Toll Caves", 1, 1, 45, 90, 170, 55, 0.08, 0.25),
        Dungeon("Crypt of Wet Bones", 2, 2, 80, 180, 330, 90, 0.13, 0.35),
        Dungeon("Bandit King's Vault", 3, 3, 125, 330, 560, 145, 0.20, 0.45),
        Dungeon("Ash Dragon Hatchery", 4, 5, 185, 650, 1050, 240, 0.30, 0.60),
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


# ============================================================
# Battle / Economy / Rewards
# ============================================================


def pay_expedition_wages(state: GameState) -> List[str]:
    messages = ["=== Expedition Wages ==="]

    for hero in list(state.roster):
        if state.gold >= hero.wage_per_expedition:
            state.gold -= hero.wage_per_expedition
            messages.append(f"Paid {hero.name} {hero.wage_per_expedition}g.")
        else:
            state.roster.remove(hero)
            messages.append(
                f"Could not pay {hero.name}'s {hero.wage_per_expedition}g wage. "
                f"{hero.name} leaves the guild."
            )

    return messages


def simulate_dungeon_run(state: GameState, party: List[Hero], dungeon: Dungeon) -> List[str]:
    messages = []
    party_power = sum(hero.combat_power() for hero in party)
    success_chance = party_power / (party_power + dungeon.enemy_power)
    roll = random.random()
    success = roll <= success_chance

    messages.append("=== Dungeon Result ===")
    messages.append(f"Dungeon: {dungeon.name}")
    messages.append(f"Time Passed: {dungeon.years_to_complete} year(s)")
    messages.append(f"Party Power: {party_power}")
    messages.append(f"Enemy Power: {dungeon.enemy_power}")
    messages.append(f"Success Chance: {success_chance * 100:.1f}%")

    if success:
        loot = random.randint(dungeon.loot_min, dungeon.loot_max)
        state.gold += loot
        messages.append(f"SUCCESS! The party recovered {loot} gold.")
        xp_amount = dungeon.xp_reward
    else:
        loot = random.randint(dungeon.loot_min // 5, dungeon.loot_max // 3)
        state.gold += loot
        messages.append(f"FAILURE. The party escaped with only {loot} gold.")
        xp_amount = max(1, dungeon.xp_reward // 2)

    for hero in party:
        messages.extend(hero.add_xp(xp_amount))

        if random.random() < dungeon.injury_chance:
            injury_duration = random.randint(1, 2)
            hero.injured_expeditions = max(hero.injured_expeditions, injury_duration)
            messages.append(f"{hero.name} was injured for {injury_duration} expedition(s).")

    if success and random.random() < dungeon.item_drop_chance:
        item = generate_item_drop(dungeon)
        state.inventory.append(item)
        messages.append(f"The party found an item: {item.display()}")

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
            continue

        if hero.contract_expeditions <= 0:
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


def generate_item_drop(dungeon: Dungeon) -> Item:
    item_pool = create_item_pool()
    item = random.choice(item_pool)

    if dungeon.difficulty >= 4 and random.random() < 0.35:
        improved_bonuses = {stat: value + 2 for stat, value in item.stat_bonuses.items()}
        return Item(f"Masterwork {item.name}", item.slot, improved_bonuses, int(item.value * 2.2))

    if dungeon.difficulty >= 3 and random.random() < 0.5:
        improved_bonuses = {stat: value + 1 for stat, value in item.stat_bonuses.items()}
        return Item(f"Fine {item.name}", item.slot, improved_bonuses, int(item.value * 1.5))

    return item


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
    print("8. View class rules")
    print("9. Quit")


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

    total_wages = sum(hero.wage_per_expedition for hero in state.roster)
    print(f"Total wage bill per expedition: {total_wages}g")

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
    print(
        f"Signed {hero.name} for {hero.contract_expeditions} expedition(s). "
        f"Paid {hero.signing_bonus}g signing bonus. Wage: {hero.wage_per_expedition}g/expedition."
    )


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
    total_wages = sum(hero.wage_per_expedition for hero in state.roster)
    print(f"Current wage bill: {total_wages}g. Current gold: {state.gold}g.")

    print("\n=== Dungeons ===")
    for index, dungeon in enumerate(state.dungeons, start=1):
        print(f"{index}. {dungeon.display()}")

    dungeon_choice = get_choice("\nChoose dungeon or blank to cancel: ", 1, len(state.dungeons))
    if dungeon_choice is None:
        return

    dungeon = state.dungeons[dungeon_choice - 1]

    wage_messages = pay_expedition_wages(state)
    print("\n".join(wage_messages))

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

    if not selected_indexes or len(selected_indexes) > 4:
        print("Party must include 1 to 4 heroes.")
        return

    if len(set(selected_indexes)) != len(selected_indexes):
        print("Cannot select the same hero more than once.")
        return

    party = []
    for index in selected_indexes:
        if index < 1 or index > len(available_heroes):
            print("Invalid hero number.")
            return
        party.append(available_heroes[index - 1])

    messages = simulate_dungeon_run(state, party, dungeon)
    print("\n".join(messages))

    finish_messages = finish_expedition(state, dungeon)
    print("\n".join(finish_messages))


def view_retired_heroes(state: GameState) -> None:
    print("\n=== Retired Heroes ===")
    if not state.retired_heroes:
        print("No retired heroes yet.")
        return

    for index, hero in enumerate(state.retired_heroes, start=1):
        print(f"{index}. {hero.name} | {hero.hero_class} | Retired Age {hero.age} | Lv {hero.level}")


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


# ============================================================
# Main Game Loop
# ============================================================


def run_game() -> None:
    random.seed()
    state = create_game()

    print("Hero Management Autobattler Prototype")
    print("Recruit heroes, raid dungeons, earn loot, and build your guild.")

    while True:
        print_header(state)
        main_menu()
        choice = get_choice("Choose an action: ", 1, 9)

        if choice is None:
            continue
        elif choice == 1:
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
            view_class_rules()
        elif choice == 9:
            print("Thanks for playing.")
            break


if __name__ == "__main__":
    run_game()
