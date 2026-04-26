from dataclasses import dataclass, field
from typing import Dict, List, Optional


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
    wage_per_year: int
    contract_years: int
    equipment: Dict[str, Item] = field(default_factory=dict)
    injured_years_remaining: int = 0
    wound_history: List[str] = field(default_factory=list)
    current_health: Optional[int] = None
    debt: int = 0

    def total_stat(self, stat_name: str) -> int:
        total = self.stats.get(stat_name, 0)
        for item in self.equipment.values():
            total += item.stat_bonuses.get(stat_name, 0)
        return total

    def max_health(self) -> int:
        return 60 + (self.total_stat("might") * 4) + (self.total_stat("spirit") * 3) + (self.level * 8)

    def reset_health_for_expedition(self) -> None:
        self.current_health = self.max_health()

    def heal(self, amount: int) -> str:
        if self.current_health is None:
            self.reset_health_for_expedition()

        before = self.current_health
        self.current_health = min(self.max_health(), self.current_health + amount)
        healed = self.current_health - before
        return f"{self.name} recovered {healed} HP ({self.current_health}/{self.max_health()} HP)."

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
        return self.signing_bonus + (self.wage_per_year * self.contract_years)

    def combat_power(self) -> int:
        class_rules = CLASS_RULES[self.hero_class]
        primary = sum(self.total_stat(stat) * 3 for stat in class_rules["primary_stats"])
        secondary = sum(self.total_stat(stat) * 2 for stat in class_rules["secondary_stats"])
        general = sum(self.total_stat(stat) for stat in STAT_NAMES)
        injury_penalty = 0.65 if self.injured_years_remaining > 0 else 1.0
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
        import random

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
        import random

        duration_years = random.randint(1, 2)
        self.injured_years_remaining = max(self.injured_years_remaining, duration_years)
        wound = f"Minor wound: injured for {duration_years} year(s)"
        self.wound_history.append(wound)
        return f"{self.name} suffered a minor wound and will need {duration_years} year(s) to recover."

    def apply_mortal_wound(self) -> str:
        import random

        stat = random.choice(STAT_NAMES)
        loss = random.randint(1, 2)
        actual_loss = min(loss, max(0, self.stats[stat] - 1))
        self.stats[stat] -= actual_loss

        duration_years = random.randint(2, 4)
        self.injured_years_remaining = max(self.injured_years_remaining, duration_years)

        wound = f"Mortal wound: -{actual_loss} {stat}, injured for {duration_years} year(s)"
        self.wound_history.append(wound)
        return f"{self.name} suffered a mortal wound: -{actual_loss} {stat}, {duration_years} year recovery."

    def advance_time(self, years_passed: int) -> List[str]:
        messages = []

        self.contract_years -= years_passed

        if self.injured_years_remaining > 0:
            old_injury_years = self.injured_years_remaining
            self.injured_years_remaining = max(0, self.injured_years_remaining - years_passed)

            if self.injured_years_remaining == 0:
                messages.append(f"{self.name} recovered from injury after {old_injury_years} remaining year(s).")
            else:
                messages.append(
                    f"{self.name} is still injured for {self.injured_years_remaining} more year(s)."
                )

        messages.extend(self.apply_aging(years_passed))
        return messages

    def apply_aging(self, years_passed: int) -> List[str]:
        import random

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
        import random

        return random.random() < self.retirement_chance()

    def display_short(self) -> str:
        injury = ""
        if self.injured_years_remaining > 0:
            injury = f" INJURED {self.injured_years_remaining}y"

        debt_text = ""
        if self.debt > 0:
            debt_text = f" | Debt {self.debt}g"

        if self.current_health is None:
            hp_text = f"HP {self.max_health()}/{self.max_health()}"
        else:
            hp_text = f"HP {self.current_health}/{self.max_health()} {self.health_status()}"

        return (
            f"{self.name} | {self.hero_class} | Age {self.age} | Lv {self.level} | "
            f"Power {self.combat_power()} | {hp_text} | Contract {self.contract_years}y | "
            f"Wage {self.wage_per_year}g/y{debt_text}{injury}"
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
            f"  Debt: {self.debt}g\n"
            f"  Retirement Chance After Time Passes: {retire_chance:.1f}%\n"
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

    @property
    def room_count(self) -> int:
        return self.stages

    def room_enemy_power(self, room_number: int, room_type: str) -> int:
        type_multiplier = {
            "Monster": 1.00,
            "Elite": 1.35,
            "Boss": 1.75,
        }.get(room_type, 1.0)

        depth_multiplier = 0.75 + (room_number * 0.18)
        return int(self.enemy_power * depth_multiplier * type_multiplier)

    def stage_enemy_power(self, stage_number: int) -> int:
        return self.room_enemy_power(stage_number, "Monster")

    def display(self) -> str:
        return (
            f"{self.name} | Difficulty {self.difficulty} | {self.years_to_complete} year(s) | "
            f"{self.room_count} room(s) | Base Enemy Power {self.enemy_power} | "
            f"Loot {self.loot_min}-{self.loot_max}g | XP {self.xp_reward}"
        )
