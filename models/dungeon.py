from dataclasses import dataclass


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
    enemy_type: str = "Beasts"

    @property
    def room_count(self) -> int:
        return self.years_to_complete

    def enemy_type_for_room(self, room_type: str) -> str:
        if room_type == "Event":
            import random
            return random.choice([self.enemy_type, "Spirits", "Bandits", "Beasts"])
        return self.enemy_type

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
            f"{self.name} | {self.enemy_type} | Difficulty {self.difficulty} | {self.years_to_complete} year(s) | "
            f"{self.room_count} room(s) | Base Enemy Power {self.enemy_power} | "
            f"Loot {self.loot_min}-{self.loot_max}g | XP {self.xp_reward}"
        )

